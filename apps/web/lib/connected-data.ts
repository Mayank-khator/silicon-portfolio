import type { Audit } from './domain';
export type Page<T>={rows:T[];total:number|null};
/** Exact counts prevent a server page-size cap from silently hiding records. */
export async function readAllRows<T>(readPage:(from:number,to:number)=>Promise<Page<T>>,pageSize=200,maxRows=20000):Promise<T[]>{
  const rows:T[]=[];
  let expected:number|undefined;
  while(true){
    const page=await readPage(rows.length,rows.length+pageSize-1);
    if(page.total===null)throw new Error('The data service did not return a complete record count.');
    if(page.total>maxRows)throw new Error('This collection is too large for the workspace. Narrow the portfolio scope.');
    if(expected!==undefined&&expected!==page.total)throw new Error('The collection changed while loading. Refresh to load a consistent count.');
    expected=page.total;
    if(!page.rows.length&&rows.length<expected)throw new Error('The data service returned an incomplete collection. Refresh to retry.');
    rows.push(...page.rows);
    if(rows.length>=expected)return rows;
  }
}
export function mapAudit(row:Record<string,unknown>):Audit{
  return {id:String(row.id),action:String(row.operation),entity_type:String(row.entity),created_at:String(row.occurred_at),actor:String(row.actor_id||'System'),detail:JSON.stringify(row.new_data||row.previous_data||{}).slice(0,180)};
}
/** Results may commit only while their request remains the newest in this scope. */
export class RequestEpoch{
  private generation=0;
  start(){return ++this.generation;}
  invalidate(){this.generation++;}
  isCurrent(generation:number){return generation===this.generation;}
}
export function errorMessage(error:unknown):string{
  return error instanceof Error?error.message:String((error as {message?:string})?.message||error);
}
