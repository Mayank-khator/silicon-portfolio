'use client';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createClient, type Session } from '@supabase/supabase-js';
import { seedState,TENANT,USER } from './seed';
import type { State } from './domain';
import { errorMessage,mapAudit,readAllRows,RequestEpoch } from './connected-data';
import { ACTIVE_WORKSPACE_KEY,DEFAULT_WORKSPACE,PROFILE_KEY,WORKSPACES_KEY,createWorkspace as createLocalWorkspace,readWorkspace,readWorkspaces,readProfile,writeProfile,writeWorkspace,workspaceKey,samplesForWorkspace,type WorkspaceInfo } from './local-workspaces';
const connected=process.env.NEXT_PUBLIC_DATA_MODE==='connected';
const supabaseUrl=process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey=process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
const empty:State={projects:[],tasks:[],resources:[],allocations:[],demands:[],time_entries:[],audit:[]};
export function usePortfolio(){
  const client=useMemo(()=>connected&&supabaseUrl&&supabaseKey?createClient(supabaseUrl,supabaseKey):null,[]);
  const [state,setState]=useState<State>(connected?empty:seedState);
  const [ready,setReady]=useState(false),[session,setSession]=useState<Session|null>(null);
  const [tenant,setTenant]=useState(connected?'':TENANT),[membershipUser,setMembershipUser]=useState('');
  const [workspaces,setWorkspaces]=useState<WorkspaceInfo[]>(connected?[]:[DEFAULT_WORKSPACE]);
  const [localProfile,setLocalProfile]=useState({name:'Demo User'});
  const [error,setError]=useState(''),[live,setLive]=useState(false),[loading,setLoading]=useState(connected);
  const activeTenant=useRef(tenant);activeTenant.current=tenant;
  const identity=useRef<string|null>(null);
  const requests=useRef(new RequestEpoch());
  const userId=session?.user.id;
  const membershipReady=Boolean(userId&&membershipUser===userId&&tenant);
  const accountKey=connected?`${userId||'signed-out'}:${tenant}`:`demo:${tenant}`;
  const workspace=workspaces.find(w=>w.id===tenant);
  const profileName=connected?(session?.user.user_metadata?.display_name||session?.user.email||'Team member'):localProfile.name;
  const applySession=useCallback((next:Session|null)=>{
    const nextId=next?.user.id||null;
    if(identity.current!==nextId){
      identity.current=nextId;requests.current.invalidate();
      setState(empty);setTenant('');setWorkspaces([]);setMembershipUser('');setLive(false);setError('');setLoading(Boolean(nextId));
    }
    if(!nextId)setLoading(false);
    setSession(next);setReady(true);
  },[]);
  const refresh=useCallback(async()=>{
    if(!client||!session||!membershipReady||activeTenant.current!==tenant)return false;
    const request=requests.current.start(),requestUser=session.user.id;
    const isCurrent=()=>requests.current.isCurrent(request)&&identity.current===requestUser&&activeTenant.current===tenant;
    setLoading(true);
    try{
      const tables=['projects','tasks','resources','allocations','demands','time_entries'] as const;
      const result:State={...empty};
      await Promise.all([
        ...tables.map(async table=>{
          const rows=await readAllRows(async(from,to)=>{
            const {data,error,count}=await client.from(table).select('*',{count:'exact'}).eq('tenant_id',tenant).order('id',{ascending:true}).range(from,to);
            if(error)throw error;
            return {rows:data||[],total:count};
          });Object.assign(result,{[table]:rows});
        }),
        (async()=>{
          const audit=await client.from('audit_logs').select('*').eq('tenant_id',tenant).order('occurred_at',{ascending:false}).limit(80);
          if(audit.error)throw audit.error;
          result.audit=(audit.data||[]).map(mapAudit);
        })(),
      ]);
      if(!isCurrent())return false;
      setState(result);setError('');return true;
    }catch(e){if(isCurrent())setError(errorMessage(e));return false;}
    finally{if(isCurrent())setLoading(false);}
  },[client,session,tenant,membershipReady]);
  useEffect(()=>{
    if(connected){
      if(!client){setError('Connected mode requires Supabase URL and publishable key.');setReady(true);setLoading(false);return;}
      let active=true,authEventSeen=false;
      const {data:{subscription}}=client.auth.onAuthStateChange((_event,next)=>{authEventSeen=true;if(active)applySession(next);});
      client.auth.getSession().then(({data,error})=>{
        if(!active||authEventSeen)return;
        if(error){setError(error.message);setReady(true);setLoading(false);return;}
        applySession(data.session);
      }).catch(e=>{if(active&&!authEventSeen){setError(errorMessage(e));setReady(true);setLoading(false);}});
      return()=>{active=false;requests.current.invalidate();subscription.unsubscribe();};
    }
    try{
      const list=readWorkspaces(localStorage),saved=sessionStorage.getItem(ACTIVE_WORKSPACE_KEY);
      const id=list.find(w=>w.id===saved)?.id||list[0].id;
      setWorkspaces(list);setTenant(id);activeTenant.current=id;
      setState(readWorkspace(localStorage,id));setLocalProfile(readProfile(localStorage));
    }catch(e){setState(empty);setError(errorMessage(e));}
    setReady(true);setLive(true);setLoading(false);
    const onStorage=(event:StorageEvent)=>{
      try{
        if(event.key===workspaceKey(activeTenant.current))setState(readWorkspace(localStorage,activeTenant.current));
        if(event.key===WORKSPACES_KEY)setWorkspaces(readWorkspaces(localStorage));
        if(event.key===PROFILE_KEY)setLocalProfile(readProfile(localStorage));
      }catch(e){setError(errorMessage(e));}
    };
    window.addEventListener('storage',onStorage);return()=>window.removeEventListener('storage',onStorage);
  },[client,applySession]);
  useEffect(()=>{
    if(!client||!userId)return;
    let active=true;setLoading(true);
    (async()=>{
      try{
        const {data,error}=await client.from('memberships').select('tenant_id,role').eq('user_id',userId).order('tenant_id');
        if(!active||identity.current!==userId)return;
        if(error)throw error;
        if(!data?.length)throw new Error('No tenant membership is provisioned. Ask your administrator, then sign in again.');
        const names=await client.from('tenants').select('id,name').in('id',data.map(m=>m.tenant_id));
        if(!active||identity.current!==userId)return;
        if(names.error)throw names.error;
        setWorkspaces(data.map(m=>({id:m.tenant_id,name:names.data?.find(t=>t.id===m.tenant_id)?.name||'Organization workspace',role:m.role.replaceAll('_',' ')})));
        setTenant(data[0].tenant_id);setMembershipUser(userId);
      }catch(e){if(active&&identity.current===userId){setState(empty);setTenant('');setMembershipUser(userId);setError(errorMessage(e));setLoading(false);}}
    })();
    return()=>{active=false;};
  },[client,userId]);
  useEffect(()=>{
    if(!client||!userId||!membershipReady)return;
    let active=true;
    const reload=()=>{if(active&&identity.current===userId&&activeTenant.current===tenant)void refresh();};
    const onVisibility=()=>{if(document.visibilityState==='visible')reload();};
    const onOffline=()=>setLive(false);
    reload();
    const channel=client.channel('portfolio-'+userId+'-'+tenant)
      .on('postgres_changes',{event:'*',schema:'public',filter:`tenant_id=eq.${tenant}`},reload)
      .subscribe(status=>{
        if(!active||identity.current!==userId)return;
        setLive(status==='SUBSCRIBED');if(status==='SUBSCRIBED')reload();
      });
    window.addEventListener('online',reload);window.addEventListener('offline',onOffline);document.addEventListener('visibilitychange',onVisibility);
    return()=>{
      active=false;requests.current.invalidate();setLive(false);void client.removeChannel(channel);
      window.removeEventListener('online',reload);window.removeEventListener('offline',onOffline);document.removeEventListener('visibilitychange',onVisibility);
    };
  },[client,userId,tenant,membershipReady,refresh]);
  async function mutate(table:Exclude<keyof State,'audit'>, values:Record<string,unknown>, action='Updated'){
    setError('');const isUpdate=Boolean(values.id);
    if(connected){
      if(!session)throw new Error('Sign in to save changes.');
      if(!membershipReady)throw new Error('A provisioned tenant membership is required before saving changes.');
      const endpoint=table.replaceAll('_','-');const {id,...body}=values;
      const res=await fetch(`${process.env.NEXT_PUBLIC_API_URL||'http://localhost:8000'}/api/${endpoint}${isUpdate?'/'+id:''}`,{method:isUpdate?'PATCH':'POST',headers:{'Content-Type':'application/json',Authorization:`Bearer ${session.access_token}`},body:JSON.stringify({...body,tenant_id:tenant})});
      if(!res.ok){const result=await res.json().catch(()=>({detail:'Request failed'}));throw new Error(typeof result.detail==='string'?result.detail:JSON.stringify(result.detail));}
      if(identity.current!==session.user.id||activeTenant.current!==tenant)return;
      await refresh();return;
    }
    // Device-local demonstration only; this is not a transactional database.
    const base=readWorkspace(localStorage,tenant);
    const previous=(base[table] as {id:string;version?:number}[]).find(x=>x.id===values.id);
    if(isUpdate&&(!previous||values.version!==undefined&&previous.version!==values.version))throw new Error('This record changed in another tab. Reload and try again.');
    const row={...previous,...values,id:values.id||crypto.randomUUID(),tenant_id:tenant,version:isUpdate?(previous?.version||0)+1:1};
    const rows=isUpdate?base[table].map(x=>x.id===row.id?row:x):[...base[table],row];
    const next={...base,[table]:rows,audit:[{id:crypto.randomUUID(),action,entity_type:table,created_at:new Date().toISOString(),actor:profileName,detail:String(values.name||values.title||values.note||row.id)},...base.audit].slice(0,200)} as State;
    writeWorkspace(localStorage,tenant,next);setState(next);
  }
  async function login(email:string,password:string){if(!client)throw new Error('Supabase is not configured.');const {error}=await client.auth.signInWithPassword({email,password});if(error)throw error;}
  async function logout(){if(!client)return;const {error}=await client.auth.signOut();if(error){setError(error.message);return;}applySession(null);}
  function reset(){if(connected)return;const fresh=samplesForWorkspace(tenant);writeWorkspace(localStorage,tenant,fresh);setState(fresh);setError('');}
  async function switchWorkspace(id:string){
    if(!workspaces.some(w=>w.id===id))throw new Error('Workspace is not available to this account.');
    if(id===activeTenant.current)return;
    if(connected){requests.current.invalidate();setState(empty);setLoading(true);setLive(false);}
    else{const saved=readWorkspace(localStorage,id);sessionStorage.setItem(ACTIVE_WORKSPACE_KEY,id);setState(saved);}
    activeTenant.current=id;setTenant(id);setError('');
  }
  async function createWorkspace(name:string,samples:boolean){
    if(connected)throw new Error('An administrator must provision organization membership.');
    const created=createLocalWorkspace(localStorage,name,samples);
    sessionStorage.setItem(ACTIVE_WORKSPACE_KEY,created.id);setWorkspaces(readWorkspaces(localStorage));
    activeTenant.current=created.id;setTenant(created.id);setState(readWorkspace(localStorage,created.id));setError('');
  }
  async function updateProfile(name:string){
    const trimmed=name.trim();if(!trimmed||trimmed.length>80)throw new Error('Enter a name between 1 and 80 characters.');
    if(client&&session){const result=await client.auth.updateUser({data:{display_name:trimmed}});if(result.error)throw result.error;setSession({...session,user:result.data.user});}
    else setLocalProfile(writeProfile(localStorage,trimmed));
  }
  function exportSnapshot(){return !connected?localStorage.getItem(workspaceKey(tenant))||JSON.stringify(state,null,2):JSON.stringify(state,null,2);}
  function dismissError(){setError('');}
  const visibleState=connected&&!membershipReady?empty:state;
  const workspaceReady=ready&&(!connected||!session||membershipUser===userId);
  return {state:visibleState,ready:workspaceReady,connected,session,tenant,userId:userId||USER,error,live,loading,accountKey,membershipReady,mutate,login,logout,reset,refresh,workspaces,workspace,profileName,switchWorkspace,createWorkspace,updateProfile,exportSnapshot,dismissError};
}
