"""Opt-in weekly portfolio drafts; run as a private worker, never an HTTP API.

The report UUID is derived from tenant + ISO week. PostgreSQL's primary key
arbitrates competing replicas, and retries never overwrite a saved report.
"""
from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import logging
import os
from urllib.parse import urlparse
from uuid import UUID, uuid5

import httpx

from services.agentic_ai.analysis import (
    build_report,
    capacity_insights,
    historical_delay_insights,
)

logger = logging.getLogger('silicon.weekly_reports')
PAGE_SIZE = 200
MAX_SOURCE_ROWS = 100_000
REPORT_TYPE = 'weekly_portfolio'


@dataclass(frozen=True)
class WeeklySettings:
    supabase_url: str
    service_key: str
    targets: tuple[tuple[str, str], ...]
    hour_utc: int = 8
    poll_seconds: int = 300

    @classmethod
    def from_env(cls):
        url = os.getenv('SUPABASE_URL', '').rstrip('/')
        key = os.getenv('SUPABASE_SERVICE_ROLE_KEY', '')
        parsed = urlparse(url)
        if not key or parsed.scheme not in {'http', 'https'} or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError('Weekly worker needs a valid SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY')
        if parsed.scheme != 'https' and parsed.hostname not in {'localhost', '127.0.0.1', '::1', 'host.docker.internal'}:
            raise ValueError('Remote Supabase connections require HTTPS')
        try:
            raw_targets = json.loads(os.getenv('WEEKLY_REPORT_TARGETS', '{}'))
            if not isinstance(raw_targets, dict) or not raw_targets:
                raise ValueError
            targets = tuple((str(UUID(tenant)), str(UUID(owner))) for tenant, owner in raw_targets.items())
            hour = int(os.getenv('WEEKLY_REPORT_HOUR_UTC', '8'))
            poll = int(os.getenv('WEEKLY_REPORT_POLL_SECONDS', '300'))
            if not 0 <= hour <= 23 or not 15 <= poll <= 3600:
                raise ValueError
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError('Configure WEEKLY_REPORT_TARGETS as tenant UUID to member UUID JSON; hour 0–23 and poll 15–3600 seconds') from exc
        return cls(url, key, targets, hour, poll)


def scheduled_week(now: datetime, hour_utc: int = 8) -> tuple[str, datetime] | None:
    """Return this week's Monday schedule after it is due, including catch-up.

    No old weeks are backfilled: current data cannot reconstruct old snapshots.
    ISO year, rather than calendar year, handles the late-December boundary.
    """
    if now.tzinfo is None:
        raise ValueError('The scheduling clock must be timezone-aware')
    now = now.astimezone(timezone.utc)
    monday = (now - timedelta(days=now.weekday())).replace(hour=hour_utc, minute=0, second=0, microsecond=0)
    if now < monday:
        return None
    year, week, _ = monday.isocalendar()
    return f'{year}-W{week:02d}', monday


def report_id_for(tenant_id: str, iso_week: str) -> str:
    return str(uuid5(UUID(tenant_id), f'silicon-ppm:weekly-portfolio:{iso_week}'))


class WeeklyReportGateway:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def existing(self, tenant_id: str, report_id: str, iso_week: str) -> bool:
        response = await self.client.get('/rest/v1/reports', params={
            'id': f'eq.{report_id}', 'tenant_id': f'eq.{tenant_id}',
            'select': 'id,tenant_id,report_type,report_data',
        })
        response.raise_for_status()
        rows = response.json()
        if not isinstance(rows, list) or len(rows) > 1:
            raise RuntimeError('Unexpected report lookup shape')
        if not rows:
            return False
        row = rows[0]
        if (row.get('id') != report_id or row.get('tenant_id') != tenant_id
                or row.get('report_type') != REPORT_TYPE
                or row.get('report_data', {}).get('iso_week') != iso_week):
            raise RuntimeError('Reserved weekly report identifier conflicts with another record')
        return True

    async def require_owner(self, tenant_id: str, owner_id: str):
        response = await self.client.get('/rest/v1/memberships', params={
            'tenant_id': f'eq.{tenant_id}', 'user_id': f'eq.{owner_id}',
            'select': 'tenant_id,user_id', 'limit': '1',
        })
        response.raise_for_status()
        if response.json() != [{'tenant_id': tenant_id, 'user_id': owner_id}]:
            raise RuntimeError('Configured report owner is not a member of the target tenant')

    async def rows(self, table: str, tenant_id: str) -> list[dict]:
        if table not in {'projects', 'resources', 'allocations', 'historical_phase_metrics'}:
            raise ValueError('Unsupported report source table')
        result: list[dict] = []
        after = None
        while True:
            params = {'tenant_id': f'eq.{tenant_id}', 'select': '*', 'order': 'id.asc', 'limit': str(PAGE_SIZE)}
            if after is not None:
                params['id'] = f'gt.{after}'
            response = await self.client.get('/rest/v1/' + table, params=params)
            response.raise_for_status()
            page = response.json()
            if not isinstance(page, list):
                raise RuntimeError('Unexpected report source response')
            for row in page:
                if row.get('tenant_id') != tenant_id:
                    raise RuntimeError('Upstream returned a different tenant')
                current_id = str(UUID(row['id']))
                if after is not None and current_id <= after:
                    raise RuntimeError('Source pagination did not advance')
                after = current_id
            result.extend(page)
            if len(result) > MAX_SOURCE_ROWS:
                raise RuntimeError('Source exceeds report safety limit; report was not saved')
            if len(page) < PAGE_SIZE:
                return result

    async def save(self, record: dict, iso_week: str) -> bool:
        # Plain INSERT is intentional: never upsert over another replica's draft.
        response = await self.client.post('/rest/v1/reports', json=record, headers={'Prefer': 'return=minimal'})
        if response.status_code == 409:
            if await self.existing(record['tenant_id'], record['id'], iso_week):
                return False
        response.raise_for_status()
        return True


async def draft_for_tenant(gateway: WeeklyReportGateway, tenant_id: str, owner_id: str,
                           iso_week: str, scheduled_at: datetime, generated_at: datetime) -> bool:
    report_id = report_id_for(tenant_id, iso_week)
    if await gateway.existing(tenant_id, report_id, iso_week):
        return False
    await gateway.require_owner(tenant_id, owner_id)
    projects, resources, allocations, history = await asyncio.gather(*(
        gateway.rows(table, tenant_id)
        for table in ('projects', 'resources', 'allocations', 'historical_phase_metrics')
    ))
    insights = capacity_insights(resources, allocations) + historical_delay_insights(projects, history)
    report = build_report('portfolio', {'projects': projects, 'insights': insights})
    report.update({
        'iso_week': iso_week,
        'draft_status': 'awaiting_human_review',
        'scheduled_at': scheduled_at.isoformat(),
        'generated_at': generated_at.isoformat(),
        'generated_by': 'weekly_portfolio_worker',
        'owner_id': owner_id,
        'historical_sample_count': len(history),
        'snapshot_kind': 'current_records_at_generation',
    })
    report['limitations'] = [
        text for text in report['limitations']
        if text != 'Analysis is limited to records visible to the authenticated user.'
    ] + [
        'This scheduled draft uses only its explicitly configured tenant.',
        'Source tables are read in separate requests; concurrent edits may span different instants.',
        'A late run summarizes current records, not a reconstructed historical snapshot.',
    ]
    return await gateway.save({
        'id': report_id, 'tenant_id': tenant_id, 'created_by': owner_id,
        'report_type': REPORT_TYPE, 'title': f'Weekly portfolio draft · {iso_week}',
        'status': 'complete', 'report_data': report,
    }, iso_week)


async def run_cycle(gateway: WeeklyReportGateway, settings: WeeklySettings, now: datetime) -> dict[str, int]:
    result = {'generated': 0, 'existing': 0, 'failed': 0}
    due = scheduled_week(now, settings.hour_utc)
    if due is None:
        return result
    iso_week, scheduled_at = due
    for tenant_id, owner_id in settings.targets:
        try:
            saved = await draft_for_tenant(gateway, tenant_id, owner_id, iso_week, scheduled_at, now)
            result['generated' if saved else 'existing'] += 1
            if saved:
                logger.info('Weekly portfolio draft saved for tenant %s, %s', tenant_id, iso_week)
        except Exception as exc:
            # Never log raw HTTP exceptions or payloads: they may include secrets.
            logger.warning('Weekly report deferred for tenant %s: %s', tenant_id, type(exc).__name__)
            result['failed'] += 1
    return result


async def run(*, once: bool = False) -> int:
    settings = WeeklySettings.from_env()
    async with httpx.AsyncClient(base_url=settings.supabase_url, timeout=30, follow_redirects=False,
                                headers={'apikey': settings.service_key,
                                         'Authorization': f'Bearer {settings.service_key}'}) as client:
        gateway = WeeklyReportGateway(client)
        while True:
            result = await run_cycle(gateway, settings, datetime.now(timezone.utc))
            if once:
                logger.info('Weekly report cycle finished: %s', result)
                return 1 if result['failed'] else 0
            await asyncio.sleep(settings.poll_seconds)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--once', action='store_true', help='Check the current due week once, suitable for a cron job')
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    # httpx INFO logs contain URLs; keep SDK request logging off in the worker.
    logging.getLogger('httpx').setLevel(logging.WARNING)
    try:
        raise SystemExit(asyncio.run(run(once=args.once)))
    except ValueError:
        logger.error('Weekly report configuration is invalid; see docs/weekly-reports.md')
        raise SystemExit(2) from None
