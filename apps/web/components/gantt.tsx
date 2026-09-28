'use client';
import type { Project,State,Task } from '@/lib/domain';
import { dateLabel } from '@/lib/domain';
import { buildGanttRange,ganttBarFor } from '@/lib/gantt-range';
import { ArrowRight, CalendarDays } from 'lucide-react';
import { Button } from './ui/button';
import { Status } from './dashboard';
export function Gantt({projects,onOpen}:{projects:Project[];onOpen:(p:Project)=>void}){
  const range=buildGanttRange(projects);
  return <section className="card">
    <div className="section-title"><div><h2>NPI release roadmap</h2><p>Select a program to update its schedule. Changes sync through the active data connection.</p></div><CalendarDays size={19} className="muted"/></div>
    {!range?<p className="empty">{projects.length?'No valid project schedules to display. Update the project dates to view the roadmap.':'No projects to show. Create a project or adjust your filters.'}</p>:<div className="gantt-scroll"><div className="gantt" style={{minWidth:Math.max(850,245+range.months.length*74+18)}}>
      <div className="gantt-head"><span>Development program</span><div style={{gridTemplateColumns:range.months.map(month=>`${month.days}fr`).join(' '),marginRight:18}}>{range.months.map(month=><b key={month.key}>{month.label}</b>)}</div></div>
      {projects.map((project,index)=>{
        const bar=ganttBarFor(project,range);
        const description=`${project.name}: ${project.start_date} to ${project.end_date}`;
        return <div className="gantt-row" key={project.id}>
          <button onClick={()=>onOpen(project)}><strong>{project.name}</strong><small>{project.node} · {project.stage}</small></button>
          <div className="gantt-track">
            {range.months.map(month=><i className="gantt-gridline" key={month.key} style={{left:`${month.left}%`}}/>)}
            {bar?<button className={`gantt-bar gantt-color-${index%4}`} onClick={()=>onOpen(project)} style={{left:`${bar.left}%`,width:`${bar.width}%`}} title={description} aria-label={`Edit ${description}`}><span style={{width:`${project.progress}%`}}/><b>{project.stage} · {project.progress}%</b></button>:<small className="muted" style={{position:'absolute',top:28,left:12}}>Schedule unavailable</small>}
          </div>
        </div>;
      })}
      <div className="gantt-foot"><span>Planning horizon</span><p>{range.label}</p></div>
    </div></div>}
  </section>;
}
export function Kanban({state,onTask}:{state:State;onTask:(t:Task)=>void}){return <div className="kanban">{(['todo','in_progress','done'] as const).map(status=><section key={status}><div className="kanban-title"><Status value={status}/><span className="count">{state.tasks.filter(t=>t.status===status).length}</span></div>{state.tasks.filter(t=>t.status===status).map(t=><article className="card task-card" key={t.id}><small>{state.projects.find(p=>p.id===t.project_id)?.code}</small><h3>{t.title}</h3><span className="phase-chip">{t.stage}</span><footer><span>{dateLabel(t.end_date)}</span><Button size="icon" variant="ghost" onClick={()=>onTask(t)} aria-label={`Edit ${t.title}`}><ArrowRight size={17}/></Button></footer></article>)}</section>)}</div>}
