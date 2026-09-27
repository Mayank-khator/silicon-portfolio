from services.shared.app import base_app
from services.shared.crud import add_crud
from services.shared.models import ResourceCreate, AllocationCreate, TimeEntryCreate, TimeEntryPatch


def create_app(settings=None, transport=None):
    app = base_app('resource-time', settings, transport)
    add_crud(app, '/api/resources', 'resources', ResourceCreate)
    add_crud(app, '/api/allocations', 'allocations', AllocationCreate)
    add_crud(app, '/api/time-entries', 'time_entries', TimeEntryCreate, TimeEntryPatch)
    return app


app = create_app()
