import React, {useEffect, useState} from 'react';
import {createRoot} from 'react-dom/client';
import './style.css';

async function api(path, body) {
  const response = await fetch('/api'+path, body === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Request failed');
  return data;
}
function App() {
  const [config,setConfig]=useState(null), [request,setRequest]=useState(''), [runs,setRuns]=useState([]), [id,setId]=useState(()=>new URLSearchParams(window.location.search).get('run')||''), [run,setRun]=useState(null), [error,setError]=useState(''), [busy,setBusy]=useState(false), [inspection,setInspection]=useState(null);
  useEffect(()=>{api('/config').then(c=>{setConfig(c);setRequest(c.request)}).catch(e=>setError(e.message));},[]);
  useEffect(()=>{let live=true; const refresh=()=>api('/runs').then(data=>{if(!live)return;setRuns(data);setRun(data.find(r=>r.id===id)||null)}).catch(e=>live&&setError(e.message));refresh();const timer=setInterval(refresh,2000);return()=>{live=false;clearInterval(timer)};},[id]);
  async function launch(){setBusy(true);setError('');try{const d=await api('/runs',{request});setId(d.id)}catch(e){setError(e.message)}finally{setBusy(false)}}
  async function select(candidate){setBusy(true);setError('');try{const d=await api(`/runs/${id}/select`,{candidate});setRun(await api(`/runs/${id}`));window.location.assign(d.download)}catch(e){setError(e.message)}finally{setBusy(false)}}
  async function cleanup(){setBusy(true);setError('');try{setRun(await api(`/runs/${id}/cleanup`,{}))}catch(e){setError(e.message)}finally{setBusy(false)}}
  async function inspect(candidate,file){setError('');try{const r=await fetch(`/api/runs/${id}/candidates/${candidate}/artifacts/${file}`);if(!r.ok)throw new Error('Artifact unavailable');setInspection({title:`${candidate} / ${file}`,text:await r.text()})}catch(e){setError(e.message)}}
  const active=runs.some(r=>r.active);
  return <main><header><div className="brand">PARALLEL <span>AI</span></div><div className="subbrand">NOSANA INFERENCE · DAYTONA EXECUTION</div></header><section className="intro"><p className="eyebrow">IMPLEMENT. COMPARE. CHOOSE.</p><h1>Two approaches.<br/><span>Your decision.</span></h1><p>Give independent AI sessions the same starting point. Review working previews and real checks before choosing a change.</p></section>
    <section className="launcher"><div className="sectiontitle"><h2>Start a comparison</h2><span className="pill">Day Planner.html</span></div><label htmlFor="request">What should change?</label><textarea id="request" value={request} onChange={e=>setRequest(e.target.value)} rows={5}/><div className="launchbar"><small>{config?.model || 'Loading configuration…'} · 2 independent sessions</small><button disabled={busy||active||!request.trim()} onClick={launch}>{active?'Run in progress':'Launch 2 candidates'} <span>↗</span></button></div></section>
    {error&&<div className="error" role="alert">{error}</div>}
    <div className="toolbar"><h2>Candidate workspace</h2><select aria-label="Choose run" value={id} onChange={e=>setId(e.target.value)}><option value="">Choose a recorded run</option>{runs.map(r=><option key={r.id} value={r.id}>{r.id}{r.active?' · running':''}</option>)}</select>{run&&<button className="secondary" onClick={cleanup} disabled={busy||run.active}>Clean up sandboxes</button>}</div>
    {run&&<><div className="runmeta">Same baseline <code>{run.base_sha?.slice(0,12)}</code> · {run.active?'Live progress updates every 2 seconds':'Recorded run'}{run.selection&&<strong> · Selected {run.selection.candidate} — patch application verified</strong>}</div><div className="cards">{run.candidates.map((c,i)=>{const files=c.artifacts||[];const href=f=>`/api/runs/${id}/candidates/${c.candidate}/artifacts/${f}`;return <article key={c.candidate}><div className="cardtop"><div><span className="eyebrow">CANDIDATE {String(i+1).padStart(2,'0')}</span><h3>{c.status==='ready'?'Ready to explore':(c.stage||'Queued').replaceAll('_',' ')}</h3></div><span className={'dot '+(c.status==='ready'?'green':'')}/></div><p className="model">{c.model||config?.model}</p><div className="badges">{[['Checks',c.feature_check],['Preview',c.preview],['Export',files.includes('changes.diff')?'saved':'not_run'],['Cleanup',c.cleanup]].map(([name,status])=><span key={name} className={'badge '+(status==='passed'||status==='confirmed'?'pass':'')}>{name}: {(status||'not_run').replaceAll('_',' ')}</span>)}</div>
      {c.preview_url&&c.cleanup==='pending_review'?<a className="preview" href={c.preview_url} target="_blank" rel="noopener noreferrer">Open live preview ↗</a>:<div className="previewpending">{c.status==='ready'?'Preview expired or cleaned up':'Live preview appears after verification passes'}</div>}
      {(c.error||c.validation_error)&&<p className="error">{c.validation_error||`${c.error}${c.failed_stage?' at '+c.failed_stage:''}`}</p>}
      <div className="artifactbar">{['changes.diff','checks.json','attempt-1.log','attempt-2.log','baseline.log','infrastructure.log'].filter(f=>files.includes(f)).map(f=><button className="textbutton" key={f} onClick={()=>inspect(c.candidate,f)}>{f==='changes.diff'?'Diff':f==='checks.json'?'Checks':f}</button>)}</div>
      <div className="screens">{['desktop.png','mobile.png','failure.png'].filter(f=>files.includes(f)).map(f=><a key={f} href={href(f)} target="_blank" rel="noopener noreferrer"><img src={href(f)} alt={`${c.candidate} ${f.replace('.png','')} screenshot`}/><span>{f.replace('.png','')}</span></a>)}</div>
      <button className="choose" disabled={busy||run.active||c.feature_check!=='passed'||!files.includes('changes.diff')} onClick={()=>select(c.candidate)}>Select & download patch</button></article>})}</div></>}
    {!run&&<p className="guidance">Launch a comparison or choose a recorded run above. Results are captured from execution; missing checks remain unverified.</p>}
    {inspection&&<div className="modal" role="dialog" aria-modal="true" aria-label={inspection.title}><div className="modalbox"><div className="sectiontitle"><h2>{inspection.title}</h2><button className="secondary" onClick={()=>setInspection(null)}>Close</button></div><pre>{inspection.text}</pre></div></div>}
    <footer>Independent implementations. Captured evidence. Human selection.</footer></main>;
}
createRoot(document.getElementById('root')).render(<App/>);
