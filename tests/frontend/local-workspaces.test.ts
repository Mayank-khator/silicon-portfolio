import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createWorkspace, readWorkspaces, readWorkspace, writeWorkspace, readProfile, writeProfile, DEFAULT_WORKSPACE } from '../../apps/web/lib/local-workspaces';
class Storage { values=new Map<string,string>(); getItem(key:string){return this.values.get(key)??null;} setItem(key:string,value:string){this.values.set(key,value);} }
test('new workspaces are isolated and preserve the original portfolio',()=>{
  const storage=new Storage();
  const original=readWorkspace(storage,DEFAULT_WORKSPACE.id);
  original.projects[0].name='Original change';writeWorkspace(storage,DEFAULT_WORKSPACE.id,original);
  const second=createWorkspace(storage,'  Management planning  ',false);
  assert.equal(second.name,'Management planning');assert.equal(readWorkspaces(storage).length,2);
  assert.equal(readWorkspace(storage,second.id).projects.length,0);
  assert.equal(readWorkspace(storage,DEFAULT_WORKSPACE.id).projects[0].name,'Original change');
});
test('creating sample workspaces gives each record the new tenant and independent data',()=>{
  const storage=new Storage();const second=createWorkspace(storage,'Sample portfolio',true);
  const state=readWorkspace(storage,second.id);
  assert.ok(state.projects.length>0);assert.ok(state.projects.every(p=>p.tenant_id===second.id));
  state.projects[0].name='Second change';writeWorkspace(storage,second.id,state);
  assert.notEqual(readWorkspace(storage,DEFAULT_WORKSPACE.id).projects[0].name,'Second change');
});
test('workspace names reject whitespace and duplicates without overwriting data',()=>{
  const storage=new Storage();assert.throws(()=>createWorkspace(storage,' ',true));
  assert.throws(()=>createWorkspace(storage,'semiconductor r&d',false));
  assert.equal(readWorkspaces(storage).length,1);
});
test('profile display name persists without creating or elevating authorization',()=>{
  const storage=new Storage();writeProfile(storage,'  Mayank Khator  ');
  assert.deepEqual(readProfile(storage),{name:'Mayank Khator'});
  assert.throws(()=>writeProfile(storage,' '));assert.equal(readProfile(storage).name,'Mayank Khator');
});
test('malformed saved portfolio is reported instead of silently overwritten',()=>{
  const storage=new Storage();storage.setItem('silicon-portfolio-demo-v1','{"projects":[]}');
  assert.throws(()=>readWorkspace(storage,DEFAULT_WORKSPACE.id),/could not be read/);
  assert.equal(storage.getItem('silicon-portfolio-demo-v1'),'{"projects":[]}');
});
test('corrupted saved rows are rejected before they can crash the workspace',()=>{
  const storage=new Storage();const state=readWorkspace(storage,DEFAULT_WORKSPACE.id);
  for(const bad of [null,{id:'bad'},{...state.projects[0],budget:'not-a-number'}]){
    storage.setItem('silicon-portfolio-demo-v1',JSON.stringify({...state,projects:[bad]}));
    assert.throws(()=>readWorkspace(storage,DEFAULT_WORKSPACE.id),/could not be read/);
  }
});
