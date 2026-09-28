import type { State } from './domain';
import { seedState,TENANT } from './seed';

export type WorkspaceInfo={id:string;name:string;role:string};
type StorageLike=Pick<Storage,'getItem'|'setItem'>;
export const WORKSPACES_KEY='silicon-portfolio-workspaces-v1';
export const PROFILE_KEY='silicon-portfolio-profile-v1';
export const ACTIVE_WORKSPACE_KEY='silicon-portfolio-active-workspace';
export const DEFAULT_WORKSPACE:WorkspaceInfo={id:TENANT,name:'Semiconductor R&D',role:'Local workspace editor'};
export const emptyState=():State=>({projects:[],tasks:[],resources:[],allocations:[],demands:[],time_entries:[],audit:[]});
export const workspaceKey=(id:string)=>id===TENANT?'silicon-portfolio-demo-v1':`silicon-portfolio-demo-v1:${id}`;
export function readWorkspaces(storage:StorageLike):WorkspaceInfo[]{
  const raw=storage.getItem(WORKSPACES_KEY);if(!raw)return [DEFAULT_WORKSPACE];
  const rows=JSON.parse(raw);
  if(!Array.isArray(rows)||!rows.length||!rows.every(w=>typeof w.id==='string'&&typeof w.name==='string'))throw new Error('Saved workspace list could not be read.');
  return rows.map(w=>({...w,role:'Local workspace editor'}));
}
export function samplesForWorkspace(id:string):State{
  const state=seedState();
  for(const table of ['projects','tasks','resources','allocations','demands','time_entries'] as const){
    state[table].forEach(row=>{row.tenant_id=id;if(!('version' in row))Object.assign(row,{version:1});});
  }
  return state;
}
export function readWorkspace(storage:StorageLike,id:string):State{
  const raw=storage.getItem(workspaceKey(id));if(!raw)return id===TENANT?samplesForWorkspace(id):emptyState();
  try{
    const value=JSON.parse(raw);
    if(!Object.keys(emptyState()).every(key=>Array.isArray(value[key])))throw new Error();
    const fields:Record<keyof State,{strings:string[];numbers:string[];arrays?:string[]}>= {
      projects:{strings:['id','tenant_id','name','code','node','stage','status','owner','start_date','end_date'],numbers:['progress','budget','spent','roi','strategic_alignment','version']},
      tasks:{strings:['id','tenant_id','project_id','title','stage','status','start_date','end_date'],numbers:['progress','version']},
      resources:{strings:['id','tenant_id','name','role'],numbers:['weekly_capacity'],arrays:['skills','fab_nodes']},
      allocations:{strings:['id','tenant_id','resource_id','project_id','start_date','end_date'],numbers:['hours_per_week']},
      demands:{strings:['id','tenant_id','title','category','node','status'],numbers:['estimated_budget','strategic_score','version']},
      time_entries:{strings:['id','tenant_id','user_id','project_id','phase','work_date','note','status'],numbers:['hours']},
      audit:{strings:['id','action','entity_type','created_at','actor','detail'],numbers:[]},
    };
    for(const [table,shape] of Object.entries(fields)){
      if(!value[table].every((row:Record<string,unknown>)=>row&&shape.strings.every(key=>typeof row[key]==='string')&&shape.numbers.every(key=>typeof row[key]==='number'&&Number.isFinite(row[key]))&&(shape.arrays||[]).every(key=>Array.isArray(row[key])&&(row[key] as unknown[]).every(v=>typeof v==='string'))))throw new Error();
    }
    // Migrate versionless allocations/resources from earlier releases.
    for(const table of ['resources','allocations'])value[table].forEach((row:Record<string,unknown>)=>{row.version??=1;});
    return value;
  }catch{throw new Error('Saved portfolio could not be read. Export a backup before resetting this workspace.');}
}
export function writeWorkspace(storage:StorageLike,id:string,state:State){storage.setItem(workspaceKey(id),JSON.stringify(state));}
function validName(name:string){const trimmed=name.trim();if(!trimmed||trimmed.length>80)throw new Error('Enter a name between 1 and 80 characters.');return trimmed;}
export function createWorkspace(storage:StorageLike,name:string,samples:boolean):WorkspaceInfo{
  const trimmed=validName(name),workspaces=readWorkspaces(storage);
  if(workspaces.some(w=>w.name.toLocaleLowerCase()===trimmed.toLocaleLowerCase()))throw new Error('A workspace with that name already exists.');
  const workspace={id:crypto.randomUUID(),name:trimmed,role:'Local workspace editor'};
  writeWorkspace(storage,workspace.id,samples?samplesForWorkspace(workspace.id):emptyState());
  storage.setItem(WORKSPACES_KEY,JSON.stringify([...workspaces,workspace]));return workspace;
}
export function readProfile(storage:StorageLike):{name:string}{
  const raw=storage.getItem(PROFILE_KEY);if(!raw)return {name:'Demo User'};
  const value=JSON.parse(raw);return {name:validName(value.name)};
}
export function writeProfile(storage:StorageLike,name:string){const profile={name:validName(name)};storage.setItem(PROFILE_KEY,JSON.stringify(profile));return profile;}
