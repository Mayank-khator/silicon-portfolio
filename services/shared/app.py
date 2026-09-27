from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import Settings


def base_app(name: str, settings: Settings | None = None, transport=None) -> FastAPI:
    config = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app):
        async with httpx.AsyncClient(base_url=config.supabase_url or 'http://unconfigured.invalid',
                                     timeout=httpx.Timeout(15.0), transport=transport, follow_redirects=False) as client:
            app.state.http = client
            yield

    app = FastAPI(title=f'Silicon Portfolio — {name}', version='1.0.0', lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = config
    if config.cors_origins:
        app.add_middleware(CORSMiddleware, allow_origins=list(config.cors_origins),
                           allow_credentials=False, allow_methods=['GET', 'POST', 'PATCH'],
                           allow_headers=['Authorization', 'Content-Type'])

    @app.middleware('http')
    async def privacy_headers(request, call_next):
        response = await call_next(request)
        response.headers['Cache-Control'] = 'no-store'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        return response

    @app.get('/health')
    async def health():
        return {'status': 'ok', 'service': name}

    return app
