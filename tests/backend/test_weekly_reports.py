from datetime import datetime, timezone
from uuid import UUID

import httpx
import pytest

from services.worker.weekly_reports import (
    REPORT_TYPE,
    WeeklyReportGateway,
    WeeklySettings,
    draft_for_tenant,
    report_id_for,
    run_cycle,
    scheduled_week,
)

TENANT = '10000000-0000-0000-0000-000000000001'
OTHER_TENANT = '10000000-0000-0000-0000-000000000002'
OWNER = '00000000-0000-0000-0000-000000000001'
MONDAY = datetime(2026, 9, 28, 8, tzinfo=timezone.utc)


def test_schedule_respects_monday_hour_and_catches_up_current_week():
    assert scheduled_week(MONDAY.replace(hour=7, minute=59)) is None
    assert scheduled_week(MONDAY) == ('2026-W40', MONDAY)
    assert scheduled_week(MONDAY.replace(day=30)) == ('2026-W40', MONDAY)


def test_iso_year_boundary_and_deterministic_report_identity():
    boundary = datetime(2025, 12, 29, 8, tzinfo=timezone.utc)
    assert scheduled_week(boundary)[0] == '2026-W01'
    assert report_id_for(TENANT, '2026-W40') == report_id_for(TENANT, '2026-W40')
    assert report_id_for(TENANT, '2026-W40') != report_id_for(OTHER_TENANT, '2026-W40')
    assert report_id_for(TENANT, '2026-W40') != report_id_for(TENANT, '2026-W41')


def test_worker_config_requires_explicit_tenant_member_mapping(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'http://127.0.0.1:54321')
    monkeypatch.setenv('SUPABASE_SERVICE_ROLE_KEY', 'private-test-value')
    monkeypatch.setenv('WEEKLY_REPORT_TARGETS', '{}')
    with pytest.raises(ValueError):
        WeeklySettings.from_env()
    monkeypatch.setenv('WEEKLY_REPORT_TARGETS', f'{{"{TENANT}":"{OWNER}"}}')
    settings = WeeklySettings.from_env()
    assert settings.targets == ((TENANT, OWNER),)
    monkeypatch.setenv('SUPABASE_URL', 'http://remote.example.com')
    with pytest.raises(ValueError):
        WeeklySettings.from_env()


@pytest.mark.asyncio
async def test_tenant_source_reads_paginate_instead_of_truncating():
    calls = []
    def handler(request):
        calls.append(dict(request.url.params))
        start, end = (1, 201) if len(calls) == 1 else (201, 204)
        return httpx.Response(200, json=[{'id': str(UUID(int=i)), 'tenant_id': TENANT} for i in range(start, end)])
    async with httpx.AsyncClient(base_url='https://example.test', transport=httpx.MockTransport(handler)) as client:
        rows = await WeeklyReportGateway(client).rows('projects', TENANT)
    assert len(rows) == 203
    assert calls[1]['id'] == f'gt.{str(UUID(int=200))}'
    assert all(call['tenant_id'] == f'eq.{TENANT}' for call in calls)


@pytest.mark.asyncio
async def test_worker_refuses_unexpected_cross_tenant_source_data():
    def handler(request):
        return httpx.Response(200, json=[{'id': OWNER, 'tenant_id': OTHER_TENANT}])
    async with httpx.AsyncClient(base_url='https://example.test', transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(RuntimeError, match='different tenant'):
            await WeeklyReportGateway(client).rows('projects', TENANT)


@pytest.mark.asyncio
async def test_competing_replica_conflict_is_existing_without_overwrite():
    report_id = report_id_for(TENANT, '2026-W40')
    requests = []
    record = {'id': report_id, 'tenant_id': TENANT, 'report_type': REPORT_TYPE, 'report_data': {'iso_week': '2026-W40'}}
    def handler(request):
        requests.append(request.method)
        return httpx.Response(409, json={'code': '23505'}) if request.method == 'POST' else httpx.Response(200, json=[record])
    async with httpx.AsyncClient(base_url='https://example.test', transport=httpx.MockTransport(handler)) as client:
        assert await WeeklyReportGateway(client).save(record, '2026-W40') is False
    assert requests == ['POST', 'GET']


class FakeGateway:
    def __init__(self):
        self.saved = []
        self.present = False
        self.fail_tenant = None

    async def existing(self, tenant_id, report_id, iso_week):
        if tenant_id == self.fail_tenant:
            raise ConnectionError('https://user:secret@invalid.example')
        return self.present

    async def require_owner(self, tenant_id, owner_id):
        assert owner_id == OWNER

    async def rows(self, table, tenant_id):
        return [{'id': OWNER, 'tenant_id': tenant_id, 'name': 'Synthetic project', 'stage': 'Ideation',
                 'status': 'at_risk', 'budget': 100, 'spent': 20}] if table == 'projects' else []

    async def save(self, record, iso_week):
        self.saved.append(record)
        return True


@pytest.mark.asyncio
async def test_scheduled_report_is_deterministic_review_draft_and_existing_is_skipped():
    gateway = FakeGateway()
    assert await draft_for_tenant(gateway, TENANT, OWNER, '2026-W40', MONDAY, MONDAY)
    record = gateway.saved[0]
    assert record['created_by'] == OWNER
    assert record['status'] == 'complete'
    assert record['report_data']['source'] == 'deterministic'
    assert record['report_data']['llm_status'] == 'not_requested'
    assert record['report_data']['human_review_required'] is True
    assert record['report_data']['draft_status'] == 'awaiting_human_review'
    assert record['report_data']['metrics']['project_count'] == 1
    gateway.present = True
    assert not await draft_for_tenant(gateway, TENANT, OWNER, '2026-W40', MONDAY, MONDAY)
    assert len(gateway.saved) == 1


@pytest.mark.asyncio
async def test_tenant_failure_isolated_and_logs_hide_secrets(caplog):
    gateway = FakeGateway()
    gateway.fail_tenant = TENANT
    settings = WeeklySettings('https://example.test', 'secret', ((TENANT, OWNER), (OTHER_TENANT, OWNER)))
    result = await run_cycle(gateway, settings, MONDAY)
    assert result == {'generated': 1, 'existing': 0, 'failed': 1}
    assert gateway.saved[0]['tenant_id'] == OTHER_TENANT
    assert 'ConnectionError' in caplog.text
    assert 'user:secret' not in caplog.text


@pytest.mark.asyncio
async def test_not_due_cycle_saves_nothing():
    gateway = FakeGateway()
    settings = WeeklySettings('https://example.test', 'secret', ((TENANT, OWNER),))
    assert await run_cycle(gateway, settings, MONDAY.replace(hour=7)) == {'generated': 0, 'existing': 0, 'failed': 0}
    assert gateway.saved == []
