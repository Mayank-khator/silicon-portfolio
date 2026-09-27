import asyncio
import json
from uuid import UUID

from fastapi import Depends, Request

from services.shared.app import base_app
from services.shared.models import ReportRequest
from services.shared.supabase import Identity, current_identity, database
from .analysis import capacity_insights, historical_delay_insights, build_report


async def analysis_data(request: Request, identity: Identity, tenant_id: UUID):
    db = database(request, identity)
    projects, resources, allocations, history = await asyncio.gather(
        db.all('projects', tenant_id), db.all('resources', tenant_id),
        db.all('allocations', tenant_id), db.all('historical_phase_metrics', tenant_id),
    )
    insights = capacity_insights(resources, allocations) + historical_delay_insights(projects, history)
    return {'projects': projects, 'insights': insights, 'history_samples': len(history)}


async def optional_narrative(report, settings):
    """Two opt-ins: operator provider enablement and this request's use_llm.

    Groq additionally requires ALLOW_EXTERNAL_LLM=true. Only aggregate report
    metrics are sent; project names, people, notes, JWTs and IDs are excluded.
    """
    provider = settings.llm_provider
    if provider not in {'ollama', 'groq'} or not settings.llm_model:
        return report | {'llm_status': 'disabled'}
    if provider == 'groq' and not settings.allow_external_llm:
        return report | {'llm_status': 'external_provider_not_allowed'}
    try:
        if provider == 'ollama':
            from langchain_ollama import ChatOllama
            model = ChatOllama(model=settings.llm_model, base_url=settings.ollama_base_url, temperature=0)
        else:
            from langchain_groq import ChatGroq
            model = ChatGroq(model=settings.llm_model, temperature=0, timeout=20, max_retries=0)
        prompt = 'Write a short factual portfolio summary using ONLY these aggregate numbers. Do not invent forecasts or actions taken. Numbers: ' + json.dumps(report['metrics'], sort_keys=True)
        response = await asyncio.wait_for(model.ainvoke(prompt), timeout=25)
        if not isinstance(response.content, str) or not response.content.strip():
            raise ValueError('Empty narrative')
        return report | {'source': 'deterministic_with_optional_narrative', 'llm_status': 'complete',
                         'optional_narrative': response.content[:6000], 'narrative_provider': provider}
    except Exception:
        # Provider outages, missing optional extras and malformed output cannot
        # prevent the deterministic report. Never log keys or full prompts.
        return report | {'llm_status': 'unavailable_fallback'}


def create_app(settings=None, transport=None):
    app = base_app('agentic-ai', settings, transport)

    @app.get('/api/insights')
    async def insights(request: Request, tenant_id: UUID, identity: Identity = Depends(current_identity)):
        data = await analysis_data(request, identity, tenant_id)
        return {'insights': data['insights'], 'source': 'deterministic',
                'historical_sample_count': data['history_samples'], 'human_review_required': True}

    @app.post('/api/reports')
    async def reports(body: ReportRequest, request: Request, identity: Identity = Depends(current_identity)):
        data = await analysis_data(request, identity, body.tenant_id)
        report = build_report(body.report_type, data)
        if body.use_llm:
            report = await optional_narrative(report, request.app.state.settings)
        return report

    return app


app = create_app()
