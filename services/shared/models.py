from datetime import date
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Text = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)]
Nonnegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]
Percent = Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]
Stage = Literal['Ideation', 'Feasibility', 'EVT', 'DVT', 'PVT', 'Ramp/Launch']
ProjectStatus = Literal['on_track', 'at_risk', 'delayed']
TaskStatus = Literal['todo', 'in_progress', 'done']
DemandStatus = Literal['submitted', 'under_review', 'approved', 'rejected', 'converted']


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True, allow_inf_nan=False)

    @model_validator(mode='after')
    def ordered_dates(self):
        start = getattr(self, 'start_date', None)
        end = getattr(self, 'end_date', None)
        if start and end and end < start:
            raise ValueError('end_date must be on or after start_date')
        return self


class TenantModel(StrictModel):
    tenant_id: UUID


class ProjectCreate(TenantModel):
    name: Text
    code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
    node: Text
    stage: Stage = 'Ideation'
    status: ProjectStatus = 'on_track'
    progress: Percent = 0
    budget: Nonnegative = 0
    spent: Nonnegative = 0
    roi: Annotated[float, Field(allow_inf_nan=False)] = 0
    start_date: date
    end_date: date
    owner: Annotated[str, Field(max_length=240)] = ''
    strategic_alignment: Percent = 0


class PatchBase(TenantModel):
    version: Annotated[int, Field(ge=1)]

    @model_validator(mode='after')
    def no_explicit_nulls(self):
        for key in self.model_fields_set:
            if getattr(self, key) is None:
                raise ValueError(f'{key} cannot be null')
        if self.model_fields_set <= {'tenant_id', 'version'}:
            raise ValueError('At least one change is required')
        return self


class ProjectPatch(PatchBase):
    name: Text | None = None
    code: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)] | None = None
    node: Text | None = None
    stage: Stage | None = None
    status: ProjectStatus | None = None
    progress: Percent | None = None
    budget: Nonnegative | None = None
    spent: Nonnegative | None = None
    roi: float | None = None
    start_date: date | None = None
    end_date: date | None = None
    owner: Annotated[str, Field(max_length=240)] | None = None
    strategic_alignment: Percent | None = None
    design_frozen: bool | None = None


class TaskCreate(TenantModel):
    project_id: UUID
    title: Text
    stage: Stage
    status: TaskStatus = 'todo'
    start_date: date
    end_date: date
    progress: Percent = 0


class TaskPatch(PatchBase):
    title: Text | None = None
    stage: Stage | None = None
    status: TaskStatus | None = None
    start_date: date | None = None
    end_date: date | None = None
    progress: Percent | None = None


class DemandCreate(TenantModel):
    title: Text
    category: Text
    node: Text
    estimated_budget: Nonnegative = 0
    strategic_score: Percent = 0
    status: DemandStatus = 'submitted'


class DemandPatch(PatchBase):
    title: Text | None = None
    category: Text | None = None
    node: Text | None = None
    estimated_budget: Nonnegative | None = None
    strategic_score: Percent | None = None
    status: DemandStatus | None = None


class ResourceCreate(TenantModel):
    name: Text
    role: Text
    skills: list[Text] = Field(default_factory=list, max_length=100)
    fab_nodes: list[Text] = Field(default_factory=list, max_length=30)
    weekly_capacity: Annotated[float, Field(gt=0, le=168)] = 40


class ResourcePatch(PatchBase):
    name: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=160)] | None = None
    role: Text | None = None
    skills: Annotated[list[Text], Field(max_length=100)] | None = None
    fab_nodes: Annotated[list[Text], Field(max_length=30)] | None = None
    weekly_capacity: Annotated[float, Field(gt=0, le=168)] | None = None


class AllocationCreate(TenantModel):
    resource_id: UUID
    project_id: UUID
    hours_per_week: Annotated[float, Field(gt=0, le=168)]
    start_date: date
    end_date: date


class AllocationPatch(PatchBase):
    resource_id: UUID | None = None
    project_id: UUID | None = None
    hours_per_week: Annotated[float, Field(gt=0, le=168)] | None = None
    start_date: date | None = None
    end_date: date | None = None


class TimeEntryCreate(TenantModel):
    user_id: UUID | None = None
    project_id: UUID
    task_id: UUID | None = None
    phase: Stage
    work_date: date
    hours: Annotated[float, Field(gt=0, le=24, multiple_of=0.25)]
    billable: bool = True
    note: Annotated[str, Field(max_length=2000)] = ''
    status: Literal['draft', 'submitted'] = 'draft'

    @model_validator(mode='after')
    def not_future(self):
        if self.work_date > date.today():
            raise ValueError('Time cannot be logged for a future day')
        return self


class TimeEntryPatch(PatchBase):
    phase: Stage | None = None
    work_date: date | None = None
    hours: Annotated[float, Field(gt=0, le=24, multiple_of=0.25)] | None = None
    billable: bool | None = None
    note: Annotated[str, Field(max_length=2000)] | None = None
    status: Literal['draft', 'submitted', 'approved', 'rejected'] | None = None

    @model_validator(mode='after')
    def not_future(self):
        if self.work_date and self.work_date > date.today():
            raise ValueError('Time cannot be logged for a future day')
        return self


class ReportRequest(TenantModel):
    report_type: Literal['executive', 'resource', 'risk'] = 'executive'
    use_llm: bool = False
