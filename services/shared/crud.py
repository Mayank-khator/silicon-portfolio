from uuid import UUID

from fastapi import Depends, HTTPException, Query, Request

from .domain import validate_stage_transition
from .supabase import Identity, current_identity, database


def add_crud(app, path: str, table: str, create_model, patch_model=None):
    async def list_records(request: Request, tenant_id: UUID, limit: int = Query(100, ge=1, le=200),
                           offset: int = Query(0, ge=0), project_id: UUID | None = None,
                           identity: Identity = Depends(current_identity)):
        if project_id is not None and table not in {'tasks', 'allocations', 'time_entries'}:
            raise HTTPException(422, 'project_id filter is not supported for this collection')
        return await database(request, identity).list(table, tenant_id, limit, offset, project_id=project_id)

    async def create_record(body: create_model, request: Request, identity: Identity = Depends(current_identity)):
        data = body.model_dump(mode='json', exclude_none=True)
        if table == 'time_entries':
            if data.get('user_id', str(identity.id)) != str(identity.id):
                raise HTTPException(403, 'Time entries must belong to the authenticated user')
            data['user_id'] = str(identity.id)
        if table == 'projects' and data.get('stage') != 'Ideation':
            raise HTTPException(422, 'New projects start in Ideation and advance through approved phase gates')
        return await database(request, identity).create(table, data)

    app.add_api_route(path, list_records, methods=['GET'], name=f'list_{table}')
    app.add_api_route(path, create_record, methods=['POST'], status_code=201, name=f'create_{table}')
    if patch_model is None:
        return

    async def patch_record(record_id: UUID, body: patch_model, request: Request,
                           identity: Identity = Depends(current_identity)):
        db = database(request, identity)
        changes = body.model_dump(mode='json', exclude_unset=True, exclude={'tenant_id', 'version'})
        rows = await db.list(table, body.tenant_id, limit=1, id=record_id)
        if not rows:
            raise HTTPException(404, 'Record not found or not accessible')
        current = rows[0]
        if current.get('version') != body.version:
            raise HTTPException(409, 'Record changed; refresh before saving')
        start = changes.get('start_date', current.get('start_date'))
        end = changes.get('end_date', current.get('end_date'))
        if start and end and end < start:
            raise HTTPException(422, 'end_date must be on or after start_date')
        if table == 'projects' and 'stage' in changes:
            try:
                validate_stage_transition(current['stage'], changes['stage'], changes.get('design_frozen', current.get('design_frozen', False)))
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from exc
        params = {'id': f'eq.{record_id}', 'tenant_id': f'eq.{body.tenant_id}', 'version': f'eq.{body.version}'}
        saved = await db.request('PATCH', table, params=params, body=changes)
        if not saved:
            raise HTTPException(409, 'Record changed or is no longer writable; refresh before saving')
        return saved[0]

    app.add_api_route(path + '/{record_id}', patch_record, methods=['PATCH'], name=f'patch_{table}')
