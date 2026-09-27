from fastapi import Depends, Request

from services.shared.app import base_app
from services.shared.supabase import Identity, current_identity, database


def create_app(settings=None, transport=None):
    app = base_app('user', settings, transport)

    @app.get('/api/me')
    async def me(request: Request, identity: Identity = Depends(current_identity)):
        memberships = await database(request, identity).request('GET', 'memberships', params={
            'select': 'tenant_id,user_id,role', 'user_id': f'eq.{identity.id}', 'limit': '200',
        })
        return {'user': {'id': str(identity.id), 'email': identity.email}, 'memberships': memberships}

    return app


app = create_app()
