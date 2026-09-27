import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readAllRows, mapAudit, RequestEpoch } from '../../apps/web/lib/connected-data';

test('connected reads page beyond the first server batch without losing totals',async()=>{
  const data=Array.from({length:5},(_,id)=>({id}));
  const requested:number[]=[];
  const rows=await readAllRows(async(from,to)=>{requested.push(from);return {rows:data.slice(from,to+1),total:5};},2);
  assert.deepEqual(rows,data);
  assert.deepEqual(requested,[0,2,4]);
});
test('oversized or interrupted collections fail visibly rather than undercount',async()=>{
  await assert.rejects(()=>readAllRows(async()=>({rows:[1,2],total:100}),2,5),/too large/);
  let request=0;
  await assert.rejects(()=>readAllRows(async()=>({rows:request++===0?[1,2]:[],total:4}),2),/incomplete/);
});
test('audit mapping consumes migration column names',()=>{
  assert.deepEqual(mapAudit({id:'a',operation:'UPDATE',entity:'projects',occurred_at:'2026-09-27T00:00:00Z',actor_id:'u',new_data:{name:'Chip'}}),{
    id:'a',action:'UPDATE',entity_type:'projects',created_at:'2026-09-27T00:00:00Z',actor:'u',detail:'{"name":"Chip"}',
  });
});
test('old account responses and older refreshes cannot become current',()=>{
  const gate=new RequestEpoch();
  const accountA=gate.start();
  gate.invalidate();
  assert.equal(gate.isCurrent(accountA),false);
  const oldRefresh=gate.start();
  const newRefresh=gate.start();
  assert.equal(gate.isCurrent(oldRefresh),false);
  assert.equal(gate.isCurrent(newRefresh),true);
});
