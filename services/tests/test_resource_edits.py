"""Resource edits exercise real routes; only external Supabase HTTP is stubbed."""
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from services.resource_time.app import create_app
from services.shared.config import Settings

TENANT = '11111111-1111-4111-8111-111111111111'
RECORD = '22222222-2222-4222-8222-222222222222'
USER = '33333333-3333-4333-8333-333333333333'
OTHER = '44444444-4444-4444-8444-444444444444'
SETTINGS = Settings(supabase_url='http://supabase.test', supabase_publishable_key='test-public-key')
HEADERS = {'Authorization': 'Bearer user-session'}


def client_for(table, *, version=4, patch_response=None):
    writes = []
    existing = {'id': RECORD, 'tenant_id': TENANT, 'version': version,
                'start_date': '2026-09-01', 'end_date': '2026-10-31'}

    def handle(request):
        if request.url.path == '/auth/v1/user':
            return httpx.Response(200, json={'id': USER, 'email': 'test@example.test'})
        assert request.url.path == '/rest/v1/' + table
        assert request.headers['authorization'] == 'Bearer user-session'
        assert request.url.params['tenant_id'] == f'eq.{TENANT}'
        if request.method == 'GET':
            return httpx.Response(200, json=[existing])
        assert request.method == 'PATCH'
        writes.append(request)
        if patch_response is not None:
            return patch_response
        return httpx.Response(200, json=[existing | json.loads(request.content) | {'version': version + 1}])

    return TestClient(create_app(SETTINGS, httpx.MockTransport(handle))), writes


@pytest.mark.parametrize(('table', 'changes'), [
    ('allocations', {'resource_id': OTHER, 'project_id': OTHER, 'hours_per_week': 12,
                     'start_date': '2026-09-02', 'end_date': '2026-09-20'}),
    ('resources', {'name': 'Updated engineer', 'role': 'QA Engineer', 'skills': ['DFT'],
                   'fab_nodes': ['5nm', '7nm'], 'weekly_capacity': 32}),
])
def test_edits_forward_allowlisted_changes_with_atomic_version_filter(table, changes):
    client, writes = client_for(table)
    with client:
        response = client.patch(f'/api/{table}/{RECORD}', headers=HEADERS,
                                json={'tenant_id': TENANT, 'version': 4} | changes)
    assert response.status_code == 200
    assert response.json()['version'] == 5
    for field, value in changes.items():
        assert response.json()[field] == value
    assert len(writes) == 1
    assert writes[0].url.params['id'] == f'eq.{RECORD}'
    assert writes[0].url.params['version'] == 'eq.4'
    # Tenant and version constrain the query; clients cannot rewrite them.
    assert json.loads(writes[0].content) == changes


@pytest.mark.parametrize(('table', 'changes'), [
    ('allocations', {'hours_per_week': 0}),
    ('allocations', {'hours_per_week': -2}),
    ('allocations', {'hours_per_week': 169}),
    ('allocations', {'resource_id': 'not-a-uuid'}),
    ('allocations', {'hours_per_week': None}),
    ('allocations', {'start_date': '2026-11-01', 'end_date': '2026-10-01'}),
    ('allocations', {'user_id': USER}),
    ('resources', {'weekly_capacity': 0}),
    ('resources', {'weekly_capacity': 169}),
    ('resources', {'name': '   '}),
    ('resources', {'skills': ['']}),
    ('resources', {'fab_nodes': None}),
    ('resources', {'user_id': USER}),
    ('resources', {}),
])
def test_invalid_edits_never_reach_database_write(table, changes):
    client, writes = client_for(table)
    with client:
        response = client.patch(f'/api/{table}/{RECORD}', headers=HEADERS,
                                json={'tenant_id': TENANT, 'version': 4} | changes)
    assert response.status_code == 422
    assert writes == []


def test_partial_allocation_end_date_is_checked_against_stored_start():
    client, writes = client_for('allocations')
    with client:
        response = client.patch(f'/api/allocations/{RECORD}', headers=HEADERS,
                                json={'tenant_id': TENANT, 'version': 4, 'end_date': '2026-08-31'})
    assert response.status_code == 422
    assert writes == []


@pytest.mark.parametrize('table', ['allocations', 'resources'])
def test_stale_edit_is_rejected_before_write(table):
    client, writes = client_for(table, version=5)
    changes = {'hours_per_week': 8} if table == 'allocations' else {'weekly_capacity': 24}
    with client:
        response = client.patch(f'/api/{table}/{RECORD}', headers=HEADERS,
                                json={'tenant_id': TENANT, 'version': 4} | changes)
    assert response.status_code == 409
    assert writes == []


@pytest.mark.parametrize(('upstream_status', 'payload', 'expected'), [
    (200, [], 409),  # Another transaction won after the version precheck.
    (403, {'code': '42501', 'message': 'private role detail'}, 403),
    (400, {'code': '23503', 'message': 'private cross-tenant foreign key'}, 422),
    (400, {'code': '23514', 'message': 'private schedule check'}, 422),
])
def test_allocation_database_concurrency_and_permission_guards_remain_authoritative(upstream_status, payload, expected):
    client, writes = client_for('allocations', patch_response=httpx.Response(upstream_status, json=payload))
    with client:
        response = client.patch(f'/api/allocations/{RECORD}', headers=HEADERS,
                                json={'tenant_id': TENANT, 'version': 4, 'hours_per_week': 8})
    assert response.status_code == expected
    assert 'private' not in response.text
    assert len(writes) == 1


def test_resource_skills_can_be_cleared_and_allocation_can_end_in_the_past():
    resource_client, _ = client_for('resources')
    with resource_client:
        response = resource_client.patch(f'/api/resources/{RECORD}', headers=HEADERS,
                                         json={'tenant_id': TENANT, 'version': 4, 'skills': [], 'fab_nodes': []})
    assert response.status_code == 200
    assert response.json()['skills'] == []
    allocation_client, _ = client_for('allocations')
    with allocation_client:
        response = allocation_client.patch(f'/api/allocations/{RECORD}', headers=HEADERS,
                                           json={'tenant_id': TENANT, 'version': 4, 'end_date': '2026-09-20'})
    assert response.status_code == 200
    assert response.json()['end_date'] == '2026-09-20'


@pytest.mark.parametrize('table', ['allocations', 'resources'])
def test_resource_edit_routes_require_authentication(table):
    client, writes = client_for(table)
    with client:
        response = client.patch(f'/api/{table}/{RECORD}', json={'tenant_id': TENANT, 'version': 4})
    assert response.status_code == 401
    assert writes == []
