from datetime import date
from uuid import UUID

import pytest
from pydantic import ValidationError

from services.shared.models import AllocationCreate, ProjectCreate, ProjectPatch, TimeEntryCreate
from services.shared.domain import validate_stage_transition
from services.agentic_ai.analysis import capacity_insights, historical_delay_insights, build_report

TENANT = '11111111-1111-4111-8111-111111111111'
PROJECT = '22222222-2222-4222-8222-222222222222'
RESOURCE = '33333333-3333-4333-8333-333333333333'


def test_project_rejects_reversed_dates_and_extra_roles():
    valid = dict(tenant_id=TENANT, name='Test chip', code='CHIP-1', node='5nm', start_date='2026-01-02', end_date='2026-02-01')
    assert ProjectCreate(**valid).stage == 'Ideation'
    with pytest.raises(ValidationError):
        ProjectCreate(**(valid | {'end_date': '2026-01-01'}))
    with pytest.raises(ValidationError):
        ProjectCreate(**(valid | {'role': 'admin'}))


@pytest.mark.parametrize('changes', [{'version': 0}, {'name': None}, {'progress': 101}, {'spent': -1}])
def test_patch_rejects_invalid_or_null_values(changes):
    with pytest.raises(ValidationError):
        ProjectPatch(**({'tenant_id': TENANT, 'version': 1} | changes))


def test_stage_gate_requires_sequence_and_freeze():
    validate_stage_transition('Feasibility', 'EVT', False)
    validate_stage_transition('EVT', 'DVT', True)
    with pytest.raises(ValueError, match='sequential'):
        validate_stage_transition('Ideation', 'DVT', True)
    with pytest.raises(ValueError, match='freeze'):
        validate_stage_transition('EVT', 'DVT', False)
    with pytest.raises(ValueError, match='sequential'):
        validate_stage_transition('DVT', 'EVT', True)


@pytest.mark.parametrize('hours', [0, -1, 25, 'NaN'])
def test_time_rejects_impossible_daily_hours(hours):
    with pytest.raises(ValidationError):
        TimeEntryCreate(tenant_id=TENANT, project_id=PROJECT, phase='EVT', work_date='2026-01-01', hours=hours)


def test_time_rejects_future_dates_and_whitespace_names():
    with pytest.raises(ValidationError):
        TimeEntryCreate(tenant_id=TENANT, project_id=PROJECT, phase='EVT', work_date='2999-01-01', hours=2)
    with pytest.raises(ValidationError):
        ProjectCreate(tenant_id=TENANT, name='  ', code='X', node='5nm', start_date='2026-01-01', end_date='2026-02-01')


def test_capacity_only_counts_overlapping_allocations_and_inclusive_dates():
    resources = [{'id': RESOURCE, 'name': 'Engineer', 'weekly_capacity': 40}]
    allocations = [
        {'resource_id': RESOURCE, 'project_id': PROJECT, 'hours_per_week': 25, 'start_date': '2026-01-01', 'end_date': '2026-01-07'},
        {'resource_id': RESOURCE, 'project_id': PROJECT, 'hours_per_week': 30, 'start_date': '2026-01-07', 'end_date': '2026-01-10'},
        {'resource_id': RESOURCE, 'project_id': PROJECT, 'hours_per_week': 40, 'start_date': '2026-02-01', 'end_date': '2026-02-05'},
    ]
    result = capacity_insights(resources, allocations)
    assert len(result) == 1
    assert result[0]['peak_hours'] == 55
    assert result[0]['overload_hours'] == 15
    assert result[0]['start_date'] == '2026-01-07'
    assert result[0]['end_date'] == '2026-01-07'


def test_nonoverlapping_allocations_do_not_raise_capacity_warning():
    resources = [{'id': RESOURCE, 'name': 'Engineer', 'weekly_capacity': 40}]
    allocations = [
        {'resource_id': RESOURCE, 'hours_per_week': 35, 'start_date': '2026-01-01', 'end_date': '2026-01-07'},
        {'resource_id': RESOURCE, 'hours_per_week': 35, 'start_date': '2026-01-08', 'end_date': '2026-01-15'},
    ]
    assert capacity_insights(resources, allocations) == []


def test_delay_estimate_uses_matching_phase_and_node_with_evidence():
    projects = [{'id': PROJECT, 'name': 'Chip', 'node': '5nm', 'stage': 'EVT'}]
    history = [
        {'node': '5nm', 'phase': 'EVT', 'planned_days': 10, 'actual_days': 12},
        {'node': '5nm', 'phase': 'EVT', 'planned_days': 10, 'actual_days': 14},
        {'node': '5nm', 'phase': 'EVT', 'planned_days': 10, 'actual_days': 16},
        {'node': '3nm', 'phase': 'EVT', 'planned_days': 10, 'actual_days': 100},
    ]
    result = historical_delay_insights(projects, history)
    assert result[0]['sample_count'] == 3
    assert result[0]['median_delay_days'] == 4
    assert result[0]['confidence'] == 'limited'
    assert historical_delay_insights(projects, history[:1]) == []


def test_report_is_deterministic_and_has_no_llm_claim():
    data = {'projects': [{'id': PROJECT, 'name': 'Chip', 'status': 'at_risk', 'budget': 100, 'spent': 60}], 'insights': []}
    result = build_report('executive', data)
    assert result == build_report('executive', data)
    assert result['source'] == 'deterministic'
    assert result['metrics']['total_budget'] == 100
    assert result['metrics']['at_risk_projects'] == 1
    assert result['human_review_required'] is True
