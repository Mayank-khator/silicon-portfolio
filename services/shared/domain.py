STAGES = ('Ideation', 'Feasibility', 'EVT', 'DVT', 'PVT', 'Ramp/Launch')


def validate_stage_transition(current: str, proposed: str, design_frozen: bool):
    if current == proposed:
        return
    if current not in STAGES or proposed not in STAGES or STAGES.index(proposed) != STAGES.index(current) + 1:
        raise ValueError('NPI advancement must be sequential; stage skips and reversals are prohibited')
    if STAGES.index(proposed) >= STAGES.index('DVT') and not design_frozen:
        raise ValueError('Design freeze approval is required before entering DVT or a later stage')
