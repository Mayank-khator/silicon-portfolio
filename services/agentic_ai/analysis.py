from collections import defaultdict
from datetime import date, timedelta
from statistics import median


def capacity_insights(resources: list[dict], allocations: list[dict]) -> list[dict]:
    """Sweep date boundaries; allocation end dates are inclusive.

    Hours/week describes a constant weekly run rate over the interval, not
    recorded daily hours. Nonoverlapping work is never added together.
    """
    by_resource = defaultdict(list)
    for row in allocations:
        by_resource[str(row['resource_id'])].append(row)
    result = []
    for resource in resources:
        boundaries = defaultdict(float)
        for row in by_resource[str(resource['id'])]:
            start = date.fromisoformat(row['start_date'])
            end = date.fromisoformat(row['end_date'])
            boundaries[start] += float(row['hours_per_week'])
            # Python's maximum date has no representable successor.
            if end < date.max:
                boundaries[end + timedelta(days=1)] -= float(row['hours_per_week'])
        points = sorted(boundaries)
        running = 0.0
        peak = 0.0
        peak_start = peak_end = None
        capacity = float(resource['weekly_capacity'])
        for i, point in enumerate(points):
            running += boundaries[point]
            if running > capacity and running > peak:
                peak = running
                peak_start = point
                peak_end = points[i + 1] - timedelta(days=1) if i + 1 < len(points) else date.max
        if peak_start:
            result.append({
                'id': f'capacity:{resource["id"]}', 'type': 'capacity', 'severity': 'high',
                'resource_id': str(resource['id']), 'title': f'{resource["name"]} exceeds available capacity',
                'peak_hours': round(peak, 2), 'weekly_capacity': capacity,
                'overload_hours': round(peak - capacity, 2),
                'start_date': peak_start.isoformat(), 'end_date': peak_end.isoformat(),
                'explanation': f'Overlapping allocations total {peak:g} hours/week against {capacity:g} available. Shift dates or reassign work after human review.',
                'method': 'inclusive-date overlap sweep', 'confidence': 'calculated',
            })
    return result


def historical_delay_insights(projects: list[dict], history: list[dict]) -> list[dict]:
    """Descriptive median from at least three completed same-node phase samples.

    This is an explainable historical comparison, not a fitted ML predictor.
    """
    groups = defaultdict(list)
    for row in history:
        planned, actual = float(row['planned_days']), float(row['actual_days'])
        if planned > 0 and actual >= 0:
            groups[(row['node'], row['phase'])].append(actual - planned)
    result = []
    for project in projects:
        if project.get('stage') not in {'EVT', 'DVT'}:
            continue
        samples = groups[(project['node'], project['stage'])]
        if len(samples) < 3:
            continue
        delay = round(median(samples), 1)
        if delay <= 0:
            continue
        result.append({
            'id': f'history:{project["id"]}', 'type': 'historical_delay', 'severity': 'medium',
            'project_id': str(project['id']), 'title': f'{project["name"]}: historical {project["stage"]} delay signal',
            'median_delay_days': delay, 'sample_count': len(samples),
            'confidence': 'limited' if len(samples) < 10 else 'historical',
            'explanation': f'{len(samples)} completed {project["node"]} {project["stage"]} samples have a median {delay:g}-day delay. This descriptive comparison is not a guaranteed forecast.',
            'method': 'median(actual_days - planned_days), matching node and phase; minimum 3 samples',
        })
    return result


def build_report(report_type: str, data: dict) -> dict:
    projects = data.get('projects', [])
    metrics = {
        'project_count': len(projects),
        'at_risk_projects': sum(p.get('status') == 'at_risk' for p in projects),
        'delayed_projects': sum(p.get('status') == 'delayed' for p in projects),
        'total_budget': round(sum(float(p.get('budget', 0)) for p in projects), 2),
        'total_spent': round(sum(float(p.get('spent', 0)) for p in projects), 2),
    }
    insights = data.get('insights', [])
    if report_type == 'resource':
        insights = [i for i in insights if i['type'] == 'capacity']
    summary = f'{metrics["project_count"]} projects; {metrics["at_risk_projects"]} at risk and {metrics["delayed_projects"]} delayed. {len(insights)} actionable analysis findings.'
    return {
        'report_type': report_type, 'source': 'deterministic', 'llm_status': 'not_requested',
        'summary': summary, 'metrics': metrics, 'insights': insights,
        'human_review_required': True,
        'limitations': ['Historical comparisons are descriptive, not validated ML forecasts.',
                        'Capacity is an allocation run rate; calendars, holidays and individual availability are not modeled.',
                        'Analysis is limited to records visible to the authenticated user.'],
    }
