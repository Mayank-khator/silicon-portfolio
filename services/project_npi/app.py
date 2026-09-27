from services.shared.app import base_app
from services.shared.crud import add_crud
from services.shared.models import ProjectCreate, ProjectPatch, TaskCreate, TaskPatch, DemandCreate, DemandPatch


def create_app(settings=None, transport=None):
    app = base_app('project-npi', settings, transport)
    add_crud(app, '/api/projects', 'projects', ProjectCreate, ProjectPatch)
    add_crud(app, '/api/tasks', 'tasks', TaskCreate, TaskPatch)
    add_crud(app, '/api/demands', 'demands', DemandCreate, DemandPatch)
    return app


app = create_app()
