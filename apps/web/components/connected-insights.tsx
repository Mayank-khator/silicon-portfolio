'use client';
import {useEffect,useState} from 'react';
import {Activity} from 'lucide-react';
type Insight={id:string;title:string;explanation:string;method:string;sample_count?:number;median_delay_days?:number;confidence:string};
export function formatReport(report:{summary?:string;metrics?:Record<string,number>;insights?:Insight[];limitations?:string[];optional_narrative?:string}){
  return `# Weekly portfolio health\n\nDRAFT — review before distributing\n\n${report.summary||''}\n\n## Portfolio metrics\n${Object.entries(report.metrics||{}).map(([k,v])=>`- ${k.replaceAll('_',' ')}: ${v.toLocaleString()}`).join('\n')}\n\n## Evidence and recommended review\n${(report.insights||[]).map(i=>`### ${i.title}\n${i.explanation}\nMethod: ${i.method}`).join('\n\n')||'No findings.'}\n\n${report.optional_narrative?'## Optional AI narrative (unverified)\n'+report.optional_narrative+'\n\n':''}## Limitations\n${(report.limitations||[]).map(l=>'- '+l).join('\n')}`;
}
export function ConnectedInsights({tenant,token}:{tenant:string;token:string}){
  const [insights,setInsights]=useState<Insight[]>([]),[status,setStatus]=useState('Loading agent evidence…');
  useEffect(()=>{const controller=new AbortController();setInsights([]);setStatus('Loading agent evidence…');fetch(`${process.env.NEXT_PUBLIC_API_URL||'http://localhost:8000'}/api/insights?tenant_id=${encodeURIComponent(tenant)}`,{headers:{Authorization:`Bearer ${token}`},signal:controller.signal}).then(async r=>{if(!r.ok)throw new Error('Agent evidence unavailable. Check the service connection and your permissions.');const data=await r.json();setInsights(data.insights);setStatus(`${data.historical_sample_count} historical phase observations · Live agent analysis`);}).catch(e=>{if(!controller.signal.aborted)setStatus(e.message);});return()=>controller.abort();},[tenant,token]);
  return <section className="card" style={{marginBottom:22}}><div className="section-title"><div><h2>Agent evidence</h2><p>{status}</p></div><Activity size={19}/></div><div className="audit-list">{insights.map(i=><article key={i.id} className="audit-event"><div><strong>{i.title}</strong><p>{i.explanation}</p><small>{i.method} · {i.confidence}{i.sample_count?` · n=${i.sample_count}`:''}</small></div></article>)}</div></section>;
}
