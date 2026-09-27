import type { State, Phase } from './domain';
export const TENANT = '11111111-1111-4111-8111-111111111111';
export const USER = '22222222-2222-4222-8222-222222222222';
const uid = (n:number) => `00000000-0000-4000-8000-${String(n).padStart(12,'0')}`;
export function seedState():State {
  const definitions = [
    ['Atlas AI Accelerator','ATL-001','5nm','DVT','at_risk',68,4200000,2860000,4.2,'2026-05-04','2026-11-20','Maya Chen',96],
    ['Orion Automotive SoC','ORN-002','7nm','EVT','on_track',42,3600000,1420000,3.8,'2026-06-15','2026-12-18','James Park',94],
    ['Nova Power Management','NVA-003','28nm','PVT','on_track',86,1800000,1460000,3.2,'2026-03-02','2026-10-30','Priya Shah',88],
    ['Helios RF Transceiver','HEL-004','16nm','DVT','delayed',61,2400000,1720000,2.9,'2026-04-13','2026-11-13','Alex Rivera',85],
    ['Vega Edge Processor','VEG-005','7nm','Feasibility','on_track',24,2800000,460000,4.6,'2026-08-03','2027-02-26','Sam Wilson',92],
    ['Lyra Sensor Interface','LYR-006','28nm','EVT','on_track',47,1200000,510000,3.5,'2026-06-01','2026-12-04','Nina Patel',84],
  ] as const;
  const projects = definitions.map((p,i)=>({id:uid(i+1),tenant_id:TENANT,name:p[0],code:p[1],node:p[2],stage:p[3],status:p[4],progress:p[5],budget:p[6],spent:p[7],roi:p[8],start_date:p[9],end_date:p[10],owner:p[11],strategic_alignment:p[12],version:1,design_frozen:['DVT','PVT','Ramp/Launch'].includes(p[3])}));
  const roles = [ ['Maya Chen','Lead Architect',['Architecture','RTL'],['5nm','7nm'],40], ['James Park','RTL Designer',['RTL','SystemVerilog'],['7nm'],40], ['Priya Shah','Yield Analyst',['Yield analysis','SPC'],['28nm'],40], ['Alex Rivera','Layout Engineer',['Physical design','Timing closure'],['5nm','16nm'],40], ['Sam Wilson','QA Engineer',['Verification','DFT'],['7nm','16nm'],40], ['Nina Patel','Validation Engineer',['EVT','Reliability'],['28nm','7nm'],32] ] as const;
  const resources = roles.map((r,i)=>({id:uid(20+i),tenant_id:TENANT,name:r[0],role:r[1],skills:[...r[2]],fab_nodes:[...r[3]],weekly_capacity:r[4]}));
  const assignments = [[0,0,32],[0,4,8],[1,1,28],[1,4,8],[2,2,32],[3,0,28],[3,3,24],[4,1,24],[4,3,22],[5,5,24],[5,1,4]];
  const allocations = assignments.map((a,i)=>({id:uid(40+i),tenant_id:TENANT,resource_id:resources[a[0]].id,project_id:projects[a[1]].id,hours_per_week:a[2],start_date:'2026-09-01',end_date:'2026-10-31'}));
  const tasks = projects.flatMap((p,i)=>['Design review & sign-off','Verification campaign','Qualification & release'].map((title,j)=>({id:uid(100+i*3+j),tenant_id:TENANT,project_id:p.id,title,stage:p.stage as Phase,status:(j===0?'done':j===1?'in_progress':'todo') as 'done'|'in_progress'|'todo',start_date:`2026-09-${j===0?'01':j===1?'14':'28'}`,end_date:j===2?'2026-10-16':`2026-09-${j===0?'11':'25'}`,progress:j===0?100:j===1?55:0,version:1})));
  return {projects,resources,allocations,tasks,
    demands:[{id:uid(200),tenant_id:TENANT,title:'Next-gen automotive radar IC',category:'IC design',node:'16nm',estimated_budget:2200000,strategic_score:92,status:'under_review',version:1},{id:uid(201),tenant_id:TENANT,title:'5nm shuttle tape-out expansion',category:'Tape-out',node:'5nm',estimated_budget:680000,strategic_score:87,status:'submitted',version:1},{id:uid(202),tenant_id:TENANT,title:'28nm fab capacity reservation',category:'Fab capacity',node:'28nm',estimated_budget:450000,strategic_score:78,status:'approved',version:1}],
    time_entries:[{id:uid(300),tenant_id:TENANT,user_id:USER,project_id:projects[0].id,task_id:tasks[1].id,phase:'DVT',work_date:'2026-09-25',hours:6,billable:true,note:'Timing closure review',status:'draft',version:1},{id:uid(301),tenant_id:TENANT,user_id:USER,project_id:projects[1].id,task_id:tasks[4].id,phase:'EVT',work_date:'2026-09-25',hours:2,billable:false,note:'Cross-team verification sync',status:'draft',version:1}],
    audit:[{id:uid(400),action:'Updated schedule',entity_type:'project',created_at:'2026-09-27T08:40:00Z',actor:'Maya Chen',detail:'Atlas AI Accelerator · DVT checkpoint moved to 2 Oct'},{id:uid(401),action:'Completed gate review',entity_type:'project',created_at:'2026-09-26T14:20:00Z',actor:'Priya Shah',detail:'Nova Power Management · PVT readiness approved'},{id:uid(402),action:'Submitted demand',entity_type:'demand',created_at:'2026-09-26T09:10:00Z',actor:'James Park',detail:'Next-gen automotive radar IC'}]};
}
