import json

import httpx
import pytest
from fastapi.testclient import TestClient

from services.shared.config import Settings
from services.project_npi.app import create_app
from services.resource_time.app import create_app as resource_app
from services.agentic_ai.app import create_app as agent_app
from services.user.app import create_app as user_app

TENANT = '11111111-1111-4111-8111-111111111111'
PROJECT = '22222222-2222-4222-8222-222222222222'
USER = '33333333-3333-4333-8333-333333333333'
SETTINGS = Settings(supabase_url='http://supabase.test', supabase_publishable_key='publishable-test')


def auth_reply(request):
    if request.url.path == '/auth/v1/user':
        return httpx.Response(200, json={'id': USER, 'email': 'test@example.test'})
    return None


def test_missing_or_bad_bearer_cannot_reach_data():
    paths = []
    def handle(request):
        paths.append(request.url.path)
        return httpx.Response(401, json={'message': 'Invalid token'})
    with TestClient(create_app(SETTINGS, httpx.MockTransport(handle))) as client:
        assert client.get('/api/projects', params={'tenant_id': TENANT}).status_code == 401
        assert client.get('/api/projects', params={'tenant_id': TENANT}, headers={'Authorization': 'Bearer invalid'}).status_code == 401
    assert paths == ['/auth/v1/user']


def test_forwards_user_token_and_scopes_tenant_instead_of_role_header():
    observed = []
    def handle(request):
        observed.append(request)
        return auth_reply(request) or httpx.Response(200, json=[{'id': PROJECT, 'tenant_id': TENANT}])
    with TestClient(create_app(SETTINGS, httpx.MockTransport(handle))) as client:
        reply = client.get('/api/projects', params={'tenant_id': TENANT}, headers={'Authorization': 'Bearer user-token', 'X-Role': 'admin'})
    assert reply.status_code == 200
    data_request = observed[-1]
    assert data_request.headers['authorization'] == 'Bearer user-token'
    assert data_request.headers['apikey'] == 'publishable-test'
    assert 'x-role' not in data_request.headers
    assert data_request.url.params['tenant_id'] == f'eq.{TENANT}'


def test_patch_uses_version_filter_and_returns_conflict_on_stale_version():
    observed = []
    def handle(request):
        observed.append(request)
        if result := auth_reply(request):
            return result
        if request.method == 'GET':
            return httpx.Response(200, json=[{'id': PROJECT, 'tenant_id': TENANT, 'name': 'Chip', 'code': 'C-1', 'node': '5nm', 'stage': 'EVT', 'version': 2, 'start_date': '2026-01-01', 'end_date': '2026-02-01', 'design_frozen': False}])
        return httpx.Response(200, json=[])
    with TestClient(create_app(SETTINGS, httpx.MockTransport(handle))) as client:
        reply = client.patch(f'/api/projects/{PROJECT}', json={'tenant_id': TENANT, 'version': 2, 'name': 'New'}, headers={'Authorization': 'Bearer user-token'})
    assert reply.status_code == 409
    patch = observed[-1]
    assert patch.method == 'PATCH'
    assert patch.url.params['version'] == 'eq.2'
    assert json.loads(patch.content) == {'name': 'New'}


def test_stage_skip_is_rejected_without_write():
    methods = []
    def handle(request):
        methods.append(request.method)
        return auth_reply(request) or httpx.Response(200, json=[{'id': PROJECT, 'tenant_id': TENANT, 'stage': 'Ideation', 'version': 1, 'design_frozen': True}])
    with TestClient(create_app(SETTINGS, httpx.MockTransport(handle))) as client:
        reply = client.patch(f'/api/projects/{PROJECT}', json={'tenant_id': TENANT, 'version': 1, 'stage': 'DVT'}, headers={'Authorization': 'Bearer user-token'})
    assert reply.status_code == 422
    assert methods == ['GET', 'GET']


def test_postgrest_denial_is_not_exposed_as_success_or_database_detail():
    def handle(request):
        return auth_reply(request) or httpx.Response(403, json={'code': '42501', 'message': 'secret internal table detail'})
    with TestClient(create_app(SETTINGS, httpx.MockTransport(handle))) as client:
        reply = client.get('/api/projects', params={'tenant_id': TENANT}, headers={'Authorization': 'Bearer user-token'})
    assert reply.status_code == 403
    assert 'secret internal' not in reply.text


def test_time_entry_always_uses_authenticated_user():
    written = []
    def handle(request):
        if result := auth_reply(request):
            return result
        written.append(json.loads(request.content))
        return httpx.Response(201, json=[written[-1]])
    with TestClient(resource_app(SETTINGS, httpx.MockTransport(handle))) as client:
        reply = client.post('/api/time-entries', json={'tenant_id': TENANT, 'project_id': PROJECT, 'phase': 'EVT', 'work_date': '2026-01-01', 'hours': 4}, headers={'Authorization': 'Bearer user-token'})
        other = client.post('/api/time-entries', json={'tenant_id': TENANT, 'project_id': PROJECT, 'user_id': PROJECT, 'phase': 'EVT', 'work_date': '2026-01-01', 'hours': 4}, headers={'Authorization': 'Bearer user-token'})
    assert reply.status_code == 201
    assert written[0]['user_id'] == USER
    assert other.status_code == 403
    assert len(written) == 1


def test_time_submit_patch_returns_incremented_database_record():
    def handle(request):
        if result := auth_reply(request):
            return result
        if request.method == 'GET':
            return httpx.Response(200, json=[{'id': PROJECT, 'user_id': USER, 'version': 1, 'status': 'draft'}])
        assert json.loads(request.content) == {'status': 'submitted'}
        assert request.url.params['version'] == 'eq.1'
        return httpx.Response(200, json=[{'id': PROJECT, 'version': 2, 'status': 'submitted'}])
    with TestClient(resource_app(SETTINGS, httpx.MockTransport(handle))) as client:
        reply = client.patch(f'/api/time-entries/{PROJECT}', json={'tenant_id': TENANT, 'version': 1, 'status': 'submitted'}, headers={'Authorization': 'Bearer user-token'})
    assert reply.status_code == 200
    assert reply.json() == {'id': PROJECT, 'version': 2, 'status': 'submitted'}


def test_me_returns_memberships_for_authenticated_user_without_token():
    def handle(request):
        if result := auth_reply(request):
            return result
        assert request.url.path == '/rest/v1/memberships'
        assert request.url.params['user_id'] == f'eq.{USER}'
        return httpx.Response(200, json=[{'tenant_id': TENANT, 'user_id': USER, 'role': 'engineer'}])
    with TestClient(user_app(SETTINGS, httpx.MockTransport(handle))) as client:
        reply = client.get('/api/me', headers={'Authorization': 'Bearer user-token'})
    assert reply.status_code == 200
    assert reply.json()['user']['id'] == USER
    assert reply.json()['memberships'][0]['role'] == 'engineer'
    assert 'user-token' not in reply.text
    assert 'publishable-test' not in reply.text


def test_report_defaults_to_offline_and_llm_opt_in_fails_closed():
    def handle(request):
        return auth_reply(request) or httpx.Response(200, json=[])
    with TestClient(agent_app(SETTINGS, httpx.MockTransport(handle))) as client:
        headers = {'Authorization': 'Bearer user-token'}
        reply = client.post('/api/reports', json={'tenant_id': TENANT}, headers=headers)
        explicit = client.post('/api/reports', json={'tenant_id': TENANT, 'use_llm': True}, headers=headers)
    assert reply.status_code == 200
    assert reply.json()['source'] == 'deterministic'
    assert explicit.status_code == 200
    assert explicit.json()['source'] == 'deterministic'
    assert explicit.json()['llm_status'] == 'disabled'


def test_missing_tenant_is_rejected_and_date_patch_checks_existing_start():
    def handle(request):
        return auth_reply(request) or httpx.Response(200, json=[{'id': PROJECT, 'version': 1, 'start_date': '2026-02-01', 'end_date': '2026-03-01'}])
    with TestClient(create_app(SETTINGS, httpx.MockTransport(handle))) as client:
        headers = {'Authorization': 'Bearer user-token'}
        assert client.get('/api/projects', headers=headers).status_code == 422
        reply = client.patch(f'/api/projects/{PROJECT}', json={'tenant_id': TENANT, 'version': 1, 'end_date': '2026-01-01'}, headers=headers)
    assert reply.status_code == 422


@pytest.mark.asyncio
async def test_optional_llm_failure_returns_deterministic_report(monkeypatch):
    import sys
    from types import SimpleNamespace
    from services.agentic_ai.app import optional_narrative
    class BrokenModel:
        def __init__(self, **kwargs):
            pass
        async def ainvoke(self, prompt):
            raise TimeoutError('private provider details')
    monkeypatch.setitem(sys.modules, 'langchain_ollama', SimpleNamespace(ChatOllama=BrokenModel))
    settings = Settings(llm_provider='ollama', llm_model='test-model')
    result = await optional_narrative({'source': 'deterministic', 'metrics': {'project_count': 2}}, settings)
    assert result['source'] == 'deterministic'
    assert result['llm_status'] == 'unavailable_fallback'
    assert 'private provider' not in json.dumps(result)


@pytest.mark.asyncio
async def test_external_llm_requires_operator_permission():
    from services.agentic_ai.app import optional_narrative
    result = await optional_narrative({'source': 'deterministic', 'metrics': {}}, Settings(llm_provider='groq', llm_model='test-model'))
    assert result['llm_status'] == 'external_provider_not_allowed'
