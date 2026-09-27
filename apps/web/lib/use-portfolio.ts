'use client';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { createClient, type Session } from '@supabase/supabase-js';
import { seedState,TENANT,USER } from './seed';
import type { State } from './domain';
import { errorMessage,mapAudit,readAllRows,RequestEpoch } from './connected-data';
const KEY='silicon-portfolio-demo-v1';
const connected=process.env.NEXT_PUBLIC_DATA_MODE==='connected';
const supabaseUrl=process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseKey=process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
const empty:State={projects:[],tasks:[],resources:[],allocations:[],demands:[],time_entries:[],audit:[]};
export function usePortfolio(){
  const client=useMemo(()=>connected&&supabaseUrl&&supabaseKey?createClient(supabaseUrl,supabaseKey):null,[]);
  const [state,setState]=useState<State>(connected?empty:seedState);
  const [ready,setReady]=useState(false),[session,setSession]=useState<Session|null>(null);
  const [tenant,setTenant]=useState(connected?'':TENANT),[membershipUser,setMembershipUser]=useState('');
  const [error,setError]=useState(''),[live,setLive]=useState(false),[loading,setLoading]=useState(connected);
  const current=useRef(state);current.current=state;
  const identity=useRef<string|null>(null);
  const requests=useRef(new RequestEpoch());
  const userId=session?.user.id;
  const membershipReady=Boolean(userId&&membershipUser===userId&&tenant);
  const accountKey=connected?`${userId||'signed-out'}:${tenant}`:'demo';
  const applySession=useCallback((next:Session|null)=>{
    const nextId=next?.user.id||null;
    if(identity.current!==nextId){
      identity.current=nextId;requests.current.invalidate();
      setState(empty);setTenant('');setMembershipUser('');setLive(false);setError('');setLoading(Boolean(nextId));
    }
    if(!nextId)setLoading(false);
    setSession(next);setReady(true);
  },[]);
  const refresh=useCallback(async()=>{
    if(!client||!session||!membershipReady)return false;
    const request=requests.current.start(),requestUser=session.user.id;
    const isCurrent=()=>requests.current.isCurrent(request)&&identity.current===requestUser;
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
    try{const raw=localStorage.getItem(KEY);if(raw){const parsed=JSON.parse(raw);if(parsed.projects&&parsed.resources&&parsed.audit)setState(parsed);}}catch{setError('Saved demo data could not be read. Reset the demo to restore samples.');}
    setReady(true);setLive(true);setLoading(false);
    const onStorage=(event:StorageEvent)=>{if(event.key===KEY&&event.newValue){try{setState(JSON.parse(event.newValue));}catch{setError('Unable to synchronize this demo tab.');}}};
    window.addEventListener('storage',onStorage);return()=>window.removeEventListener('storage',onStorage);
  },[client,applySession]);
  useEffect(()=>{
    if(!client||!userId)return;
    let active=true;setLoading(true);
    (async()=>{
      try{
        const {data,error}=await client.from('memberships').select('tenant_id').eq('user_id',userId).order('tenant_id').limit(1);
        if(!active||identity.current!==userId)return;
        if(error)throw error;
        if(!data?.length)throw new Error('No tenant membership is provisioned. Ask your administrator, then sign in again.');
        setTenant(data[0].tenant_id);setMembershipUser(userId);
      }catch(e){if(active&&identity.current===userId){setState(empty);setTenant('');setMembershipUser(userId);setError(errorMessage(e));setLoading(false);}}
    })();
    return()=>{active=false;};
  },[client,userId]);
  useEffect(()=>{
    if(!client||!userId||!membershipReady)return;
    let active=true;
    const reload=()=>{if(active&&identity.current===userId)void refresh();};
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
      if(identity.current!==session.user.id)return;
      await refresh();return;
    }
    // Device-local demonstration only; this is not a transactional database.
    let base=current.current;try{const stored=localStorage.getItem(KEY);if(stored)base=JSON.parse(stored);}catch{}
    const previous=(base[table] as {id:string;version?:number}[]).find(x=>x.id===values.id);
    if(isUpdate&&(!previous||values.version!==undefined&&previous.version!==values.version))throw new Error('This record changed in another tab. Reload and try again.');
    const row={...previous,...values,id:values.id||crypto.randomUUID(),tenant_id:TENANT,version:isUpdate?(previous?.version||0)+1:1};
    const rows=isUpdate?base[table].map(x=>x.id===row.id?row:x):[...base[table],row];
    const next={...base,[table]:rows,audit:[{id:crypto.randomUUID(),action,entity_type:table,created_at:new Date().toISOString(),actor:'Demo user',detail:String(values.name||values.title||values.note||row.id)},...base.audit].slice(0,200)} as State;
    localStorage.setItem(KEY,JSON.stringify(next));setState(next);
  }
  async function login(email:string,password:string){if(!client)throw new Error('Supabase is not configured.');const {error}=await client.auth.signInWithPassword({email,password});if(error)throw error;}
  async function logout(){if(!client)return;const {error}=await client.auth.signOut();if(error){setError(error.message);return;}applySession(null);}
  function reset(){if(connected)return;const fresh=seedState();localStorage.setItem(KEY,JSON.stringify(fresh));setState(fresh);setError('');}
  const visibleState=connected&&!membershipReady?empty:state;
  const workspaceReady=ready&&(!connected||!session||membershipUser===userId);
  return {state:visibleState,ready:workspaceReady,connected,session,tenant,userId:userId||USER,error,live,loading,accountKey,membershipReady,mutate,login,logout,reset,refresh};
}
