"""Only the public application key and validated user JWT cross this boundary.

RLS remains authoritative, including reads. No admin/service-role fallback exists.
"""
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import httpx
from fastapi import HTTPException, Request


@dataclass(frozen=True)
class Identity:
    id: UUID
    token: str
    email: str | None = None


def upstream_error(response: httpx.Response):
    if response.is_success:
        return
    try:
        code = response.json().get('code', '')
    except (ValueError, AttributeError):
        code = ''
    if response.status_code == 401:
        raise HTTPException(401, 'Session expired or invalid', headers={'WWW-Authenticate': 'Bearer'})
    if response.status_code == 403 or code == '42501':
        raise HTTPException(403, 'This operation is not permitted')
    if response.status_code == 409 or code in {'40001', '23505'}:
        raise HTTPException(409, 'Record changed or conflicts with an existing record')
    if response.status_code == 400 or code in {'23514', '23503', '22023', 'P0001'}:
        raise HTTPException(422, 'The change violates a validation, relationship, or phase approval rule')
    raise HTTPException(502, 'The data service could not complete this request')


class Supabase:
    def __init__(self, client: httpx.AsyncClient, identity: Identity, public_key: str):
        self.client = client
        self.headers = {'Authorization': f'Bearer {identity.token}', 'apikey': public_key}

    async def request(self, method: str, table: str, *, params=None, body=None):
        try:
            response = await self.client.request(method, '/rest/v1/' + table, params=params, json=body,
                                                 headers=self.headers | {'Prefer': 'return=representation'})
        except httpx.RequestError as exc:
            raise HTTPException(503, 'The data service is temporarily unavailable') from exc
        upstream_error(response)
        try:
            return response.json() if response.content else []
        except ValueError as exc:
            raise HTTPException(502, 'The data service returned an invalid response') from exc

    async def list(self, table: str, tenant_id: UUID, limit=200, offset=0, **filters):
        params = {'select': '*', 'tenant_id': f'eq.{tenant_id}', 'order': 'id.asc', 'limit': str(limit), 'offset': str(offset)}
        params.update({key: f'eq.{value}' for key, value in filters.items() if value is not None})
        return await self.request('GET', table, params=params)

    async def all(self, table: str, tenant_id: UUID, max_rows=10000):
        rows = []
        while len(rows) < max_rows:
            page = await self.list(table, tenant_id, limit=200, offset=len(rows))
            rows.extend(page)
            if len(page) < 200:
                return rows
        raise HTTPException(413, f'Tenant {table} dataset is too large for synchronous analysis; narrow the reporting scope')

    async def create(self, table: str, body: dict):
        rows = await self.request('POST', table, body=body)
        if not isinstance(rows, list) or len(rows) != 1:
            raise HTTPException(502, 'The data service did not return the saved record')
        return rows[0]


async def current_identity(request: Request) -> Identity:
    authorization = request.headers.get('Authorization', '')
    scheme, _, token = authorization.partition(' ')
    if scheme.lower() != 'bearer' or not token or ' ' in token or len(token) > 16000:
        raise HTTPException(401, 'A Supabase bearer session is required', headers={'WWW-Authenticate': 'Bearer'})
    settings = request.app.state.settings
    if not settings.supabase_url or not settings.supabase_publishable_key:
        raise HTTPException(503, 'Supabase is not configured')
    try:
        response = await request.app.state.http.get('/auth/v1/user', headers={
            'Authorization': f'Bearer {token}', 'apikey': settings.supabase_publishable_key,
        })
    except httpx.RequestError as exc:
        raise HTTPException(503, 'Authentication is temporarily unavailable') from exc
    if response.status_code in {400, 401, 403}:
        raise HTTPException(401, 'Session expired or invalid', headers={'WWW-Authenticate': 'Bearer'})
    if not response.is_success:
        raise HTTPException(503, 'Authentication is temporarily unavailable')
    try:
        data = response.json()
        return Identity(id=UUID(data['id']), token=token, email=data.get('email'))
    except (ValueError, KeyError, TypeError) as exc:
        raise HTTPException(502, 'Authentication returned an invalid identity') from exc


def database(request: Request, identity: Identity) -> Supabase:
    return Supabase(request.app.state.http, identity, request.app.state.settings.supabase_publishable_key)
