'use client';
import { useState } from 'react';
import { Check,Download,Plus } from 'lucide-react';
import type { usePortfolio } from '@/lib/use-portfolio';
import { Button } from './ui/button';
import { Dialog } from './ui/dialog';
import { Avatar } from './dashboard';

export function WorkspaceSettings({mode,data,onClose}:{mode:'workspace'|'profile';data:ReturnType<typeof usePortfolio>;onClose:()=>void}){
  const [error,setError]=useState(''),[busy,setBusy]=useState(false);
  async function submit(operation:()=>Promise<void>){setBusy(true);setError('');try{await operation();onClose();}catch(e){setError(e instanceof Error?e.message:String(e));}finally{setBusy(false);}}
  function exportData(){const content=data.exportSnapshot();const url=URL.createObjectURL(new Blob([content],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download='silicon-portfolio-data.json';link.click();URL.revokeObjectURL(url);}
  return <Dialog open onOpenChange={open=>!open&&onClose()} title={mode==='workspace'?'Your workspaces':'Your profile'} description={mode==='workspace'?'Choose the portfolio you want to work in. Each workspace keeps its own projects, tasks, and allocations.':data.connected?'Update your display name. Organization access is managed by your administrator.':'Your display name is saved in this browser and appears in the local activity log.'}>
    {mode==='workspace'?<>
      <div className="workspace-options">{data.workspaces.map(w=><button className={w.id===data.tenant?'workspace-option selected':'workspace-option'} key={w.id} disabled={busy} onClick={()=>submit(()=>data.switchWorkspace(w.id))}><span className="workspace-letter">{w.name[0]}</span><span><strong>{w.name}</strong><small>{w.role}</small></span>{w.id===data.tenant&&<Check size={18}/>}</button>)}</div>
      {!data.connected?<form className="form-grid settings-create" onSubmit={e=>{e.preventDefault();const form=new FormData(e.currentTarget);submit(()=>data.createWorkspace(String(form.get('name')),form.get('samples')==='on'));}}><h3 className="span-2">Create a workspace</h3><label className="span-2">Workspace name<input name="name" required maxLength={80} placeholder="e.g. Automotive silicon"/></label><label className="span-2 checkbox-label"><input type="checkbox" name="samples" defaultChecked/>Start with fictional sample records</label><p className="muted span-2">Workspaces are saved on this device. Visitors to your share link start with their own data.</p><div className="dialog-actions span-2"><Button type="submit" disabled={busy}><Plus size={16}/>Create workspace</Button></div></form>:<p className="method-note">Only organizations where your account has an active membership appear here. Ask an administrator to provision additional workspaces.</p>}
    </>:<form className="form-grid" onSubmit={e=>{e.preventDefault();const form=new FormData(e.currentTarget);submit(()=>data.updateProfile(String(form.get('name'))));}}>
      <div className="profile-summary span-2"><Avatar name={data.profileName}/><span><strong>{data.profileName}</strong><small>{data.connected?'Authenticated account':'Browser-local profile'}</small></span></div>
      <label className="span-2">Display name<input name="name" required maxLength={80} defaultValue={data.profileName}/></label>
      {data.connected&&<label className="span-2">Account email<input type="email" readOnly value={data.session?.user.email||''}/></label>}
      <label>Current workspace<input readOnly value={data.workspace?.name||'Organization workspace'}/></label><label>Access<input readOnly value={data.workspace?.role||'Member'}/></label>
      <p className="muted span-2">{data.connected?'Your role is enforced by database policies. Changing a display name does not change permissions.':'This public showcase uses fictional data. It does not create a shared account or synchronize between devices.'}</p>
      <div className="dialog-actions span-2"><Button type="button" variant="outline" onClick={exportData}><Download size={16}/>Export workspace data</Button><Button type="submit" disabled={busy}>Save profile</Button></div>
    </form>}
    {error&&<p className="form-error" role="alert">{error}</p>}
  </Dialog>;
}
