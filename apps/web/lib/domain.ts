export const phases = ['Ideation','Feasibility','EVT','DVT','PVT','Ramp/Launch'] as const;
export type Phase = typeof phases[number];
export type Project = { id:string; tenant_id:string; name:string; code:string; node:string; stage:Phase; status:'on_track'|'at_risk'|'delayed'; progress:number; budget:number; spent:number; roi:number; start_date:string; end_date:string; owner:string; strategic_alignment:number; version:number; design_frozen?:boolean };
export type Task = { id:string; tenant_id:string; project_id:string; title:string; stage:Phase; status:'todo'|'in_progress'|'done'; start_date:string; end_date:string; progress:number; version:number };
export type Resource = {id:string; tenant_id:string; name:string; role:string; skills:string[]; fab_nodes:string[]; weekly_capacity:number};
export type Allocation = {id:string; tenant_id:string; resource_id:string; project_id:string; hours_per_week:number; start_date:string; end_date:string};
export type Demand = {id:string; tenant_id:string; title:string; category:string; node:string; estimated_budget:number; strategic_score:number; status:string; version:number};
export type TimeEntry = {id:string; tenant_id:string; user_id:string; project_id:string; task_id:string|null; phase:Phase; work_date:string; hours:number; billable:boolean; note:string; status:string; version?:number};
export type Audit = {id:string; action:string; entity_type:string; created_at:string; actor:string; detail:string};
export type State = { projects:Project[]; tasks:Task[]; resources:Resource[]; allocations:Allocation[]; demands:Demand[]; time_entries:TimeEntry[]; audit:Audit[] };
export function capacityAt(rows:Pick<Allocation,'resource_id'|'hours_per_week'|'start_date'|'end_date'>[], id:string, date:string):number { return rows.filter(r=>r.resource_id===id && r.start_date<=date && r.end_date>=date).reduce((n,r)=>n+Number(r.hours_per_week),0); }
export function validateHours(hours:number):boolean { return Number.isFinite(hours) && hours>0 && hours<=24; }
export function nextPhase(phase:Phase):Phase|null { return phases[phases.indexOf(phase)+1]??null; }
export function portfolioTotals(rows:Pick<Project,'budget'|'spent'|'roi'>[]) { const budget=rows.reduce((s,p)=>s+Number(p.budget),0);return {budget,spent:rows.reduce((s,p)=>s+Number(p.spent),0),roi:budget?rows.reduce((s,p)=>s+Number(p.budget)*Number(p.roi),0)/budget:0}; }
export function historicalDelay(delays:number[]):number|null { const sorted=delays.filter(Number.isFinite).sort((a,b)=>a-b);if(!sorted.length)return null;const m=Math.floor(sorted.length/2);return sorted.length%2?sorted[m]:(sorted[m-1]+sorted[m])/2; }
export const money=(n:number,compact=true)=>new Intl.NumberFormat('en-US',{style:'currency',currency:'USD',notation:compact?'compact':'standard',maximumFractionDigits:1}).format(n);
export const dateLabel=(s:string)=>new Date(s+'T12:00:00').toLocaleDateString('en-US',{month:'short',day:'numeric'});
