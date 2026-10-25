/* A shared event reducer powers live runs, archives and deterministic replay. */
'use strict';
(() => {
 const a=window.polyConsole,s=a.state,$=q=>document.querySelector(q),esc=a.escape;
 const c={tab:'activity',billing:'composition',history:[],demo:false,replay:null,loaded:null,started:Date.now(),lastRun:null,open:new Set(),loadVersion:0};
 const time=ms=>{const sec=Math.max(0,Math.floor(ms/1000));return `${String(Math.floor(sec/60)).padStart(2,'0')}:${String(sec%60).padStart(2,'0')}`;};
 const stamp=e=>Date.parse(e.timestamp || e.ts) || 0;
 const safe=text=>/[\p{N}%₹$€£]|\b(zero|one|two|three|four|five|six|seven|eight|nine|ten|hundred|thousand|million|half|double|percent)\b/iu.test(String(text))?'The planner selected this step using the available evidence. Quantities are shown only in checked findings.':String(text || 'Explanation not recorded.');
 window.polySafeExplanation=safe;
 const services=[['planner','Planner','Nemotron',20,75],['tools','Tools','Bounded execution',205,75],['company','Zetaris','Company DB',405,10],['measurements','Zetaris','Measurements',600,10],['reference','Zetaris','Reference',405,65],['prices','Zetaris','Prices',600,65],['nvidia','NVIDIA','Nemotron / hosted',405,120],['world','Meterless','World Model',205,180],['hmem','Meterless','H-MEM',405,180],['markovian','Meterless','Markovian',600,180],['checker','Checker','Recompute',800,75]];
 function status(){
  const end=[...s.events].reverse().find(e=>e.event==='done');
  if(end)return ({complete:'Complete',partial:'Partial',failed:'Failed'})[end.status] || 'Complete';
  if(c.replay && c.replay.position===0)return 'Queued';
  if(s.report && s.report.status!=='running')return ({complete:'Complete',partial:'Partial',failed:'Failed'})[s.report.status] || 'Partial';
  if(s.events.some(e=>e.event==='experiment_progress') || s.report?.jobs?.status==='running' || s.report?.jobs?.status==='queued')return 'Waiting on experiment';
  return s.events.length?'Running':'Queued';
 }
 function bar(){
  $('#run-shell').hidden=!s.runId;
  if(!s.runId)return;
  if(c.lastRun!==s.runId){c.lastRun=s.runId;c.started=Date.now();}
  $('#run-company').textContent=({samudra:'Samudra Telecom',swara:'Swara Care'})[s.report?.company || c.loaded?.report.company || s.company] || 'Investigation';
  $('#console-run-id').textContent=s.runId;
  const st=status();$('#run-status').textContent=st;$('#run-status').dataset.status=st;
  $('#stop-run').disabled=!c.replay && (s.mode!=='live' || ['Complete','Partial','Failed'].includes(st));
  $('#stop-run').textContent=c.replay?'Stop replay':s.events.some(e=>e.event==='stop_requested') && !['Complete','Partial','Failed'].includes(st)?'Stopping…':'Stop';
  $('#replay-controls').hidden=!c.replay;
  const entry=c.history.find(r=>r.id===s.runId);
  const current=s.report?.status || st.toLowerCase();
  if(!entry){c.history.push({id:s.runId,company:s.company,status:current,saved:s.mode==='saved'});renderHistory();}
  else if(entry.status!==current){entry.status=current;entry.saved=s.mode==='saved' || ['Complete','Partial','Failed'].includes(st);renderHistory();}
  clock();
 }
 function clock(){
  let elapsed;
  if(c.replay)elapsed=c.replay.position;
  else {const first=s.events[0],last=s.events.at(-1);elapsed=['Complete','Partial','Failed'].includes(status())?Math.max(0,stamp(last || {})-stamp(first || {})):Date.now()-(stamp(first || {}) || c.started);}
  $('#elapsed').textContent=time(elapsed);
  if(c.replay){$('#replay-position').value=c.replay.duration?c.replay.position/c.replay.duration*1000:0;$('#replay-time').textContent=`${time(c.replay.position)} / ${time(c.replay.duration)}`;$('#replay-play').textContent=c.replay.playing?'Pause':'Play';}
 }
 function spans(){
  const out=[],byId=new Map();
  for(const [index,e] of s.events.entries()){
   if(/^(tool|sql|model_call)_started$/.test(e.event)) {const span={...e,key:e.span_id || `event-${index}`,start:stamp(e),end:null};out.push(span);byId.set(span.key,span);}
   if(/^(tool|sql|model_call)_finished$/.test(e.event)){const span=byId.get(e.span_id);if(span)Object.assign(span,{end:stamp(e),finish:e});}
   if(e.event==='tool_called' && !s.events.some(r=>r.event==='tool_started' && r.step===e.step))out.push({...e,key:`legacy-${index}`,name:e.tool,service:'tools',legacy:true,start:stamp(e),end:stamp(e)});
  }
  return out;
 }
 function map(rows){
  const nodes=new Map(services.map(([id])=>[id,{count:0,active:0,error:false,duration:null,legacy:false}]));
  for(const row of rows){let ids=[row.service];if(row.role==='planner')ids.push('planner');for(const id of ids){const node=nodes.get(id);if(!node)continue;node.count++;node.active+=!row.end && !row.legacy?1:0;node.error ||= row.finish?.status==='error';node.legacy ||= !!row.legacy;if(row.finish)node.duration=row.finish.duration_ms;}}
  // Older logs only establish observations, not in-flight calls or latencies.
  const last=s.events.at(-1),observed=last?.event==='tool_called'?'tools':last?.event==='evidence_added'?'world':last?.event==='step_started'?'planner':null;
  const legacy=!s.events.some(e=>e.span_id && e.event!=='step_started');
  $('#map-caption').textContent=legacy?'Legacy log · observed steps; call timing unavailable':'Physical call telemetry · latency in ms';
  const edges=services.filter(([id])=>id!=='planner').map(([id,,,x,y])=>{
   const n=nodes.get(id),from=id==='tools'?[180,99]:[365,99];
   return `<path data-edge="${id}" class="circuit-edge ${n.active?'active':''} ${n.error?'error':''} ${legacy && observed===id?'observed':''}" d="M${from[0]} ${from[1]} H${x-15} V${y+24} H${x}"/>`;
  }).join('');
  const svg=services.map(([id,label,sub,x,y])=>{const n=nodes.get(id),st=n.active?'active':n.error?'error':'idle';return `<g data-node="${id}" class="circuit-node ${st}" transform="translate(${x} ${y})"><rect width="160" height="48" rx="5"/><text x="12" y="15" class="node-title">${label}</text><text x="12" y="29">${sub}</text><text x="12" y="42" class="node-state">${legacy && !n.count?'not recorded':n.count+' calls · '+st}${n.duration!==null?' · '+Math.round(n.duration)+'ms':''}</text></g>`;}).join('');
  $('#service-map').innerHTML=`<svg viewBox="0 0 1000 235" role="img" aria-label="Service map. ${[...nodes].map(([id,n])=>`${id}: ${n.count} calls, ${n.active?'active':n.error?'error':'idle'}`).join('; ')}">${edges}${svg}</svg><div class="mobile-services">${services.map(([id,label,sub])=>{const n=nodes.get(id);return `<div class="${n.active?'active':''}"><strong>${label} / ${sub}</strong><span>${legacy && !n.count?'not recorded':n.count+' calls · '+(n.active?'active':n.error?'error':'idle')}${n.duration!==null?' · '+Math.round(n.duration)+' ms':''}</span></div>`;}).join('')}</div><div class="tool-nodes">${['clarify','measure','locate','hypothesise','experiment','judge','speed','check','report'].map(name=>{const calls=rows.filter(r=>r.service==='tools' && r.name===name),active=calls.some(r=>!r.end && !r.legacy);return `<span class="tool-node ${active?'active':''}">${name}<small>${calls.length} calls · ${active?'active':calls.some(r=>r.finish?.status==='error')?'error':'idle'}</small></span>`;}).join('')}</div>`;
 }
 function trace(rows){
  const seen=new Set();
  const starts=s.events.filter(e=>e.event==='step_started');
  const steps=[...new Set([...starts.map(e=>e.step),...rows.map(e=>e.step)])];
  const origin=stamp(s.events[0] || {}),total=Math.max(1,(c.replay?c.replay.position:stamp(s.events.at(-1) || {})-origin));
  function render(row,depth=0){
   if(seen.has(row.key))return '';seen.add(row.key);
   const finish=row.finish,ms=finish?.duration_ms,children=rows.filter(r=>r.parent_id===row.key);
   const left=Math.min(99,Math.max(0,(row.start-origin)/total*100)),width=Math.min(100-left,Math.max(.5,(ms || 1)/total*100));
   return `<details class="trace-span ${finish?.status==='error'?'error':''}" data-span="${esc(row.key)}" data-parent="${esc(row.parent_id || '')}" ${c.open.has(row.key)?'open':''}><summary><span>${esc(row.name || row.tool || row.event)}${row.model?` <small>${esc(row.model)}</small>`:''}</span><span class="span-duration">${row.legacy?'not recorded':ms!==undefined?Math.round(ms)+' ms':'active'} · ${row.legacy?'legacy':finish?.status || 'running'}${finish?.retry?' · retries '+finish.retry:''}</span><span class="span-track"><i style="margin-left:${left}%;width:${width}%"></i></span></summary>${finish?.error_class?`<p class="error">${esc(finish.error_class)} · ${esc(finish.next_action)}</p>`:''}<div class="span-detail"><details><summary>Input · redacted</summary><pre>${esc(JSON.stringify(row.input || row.args || {note:'Not recorded'},null,2))}</pre></details><details><summary>Output · redacted</summary><pre>${esc(JSON.stringify(finish?.output || {tokens:finish?.tokens,note:row.legacy?'Not recorded':finish?'Call completed':'Waiting for call'},null,2))}</pre></details></div><div class="span-children">${depth<12?children.map(ch=>render(ch,depth+1)).join(''):''}</div></details>`;
  }
  $('#trace-tree').innerHTML=steps.map(step=>{
   const key='step:'+step,items=rows.filter(r=>r.step===step),why=[...s.events].reverse().find(e=>e.step===step && (e.event==='planner_reason' || e.why));
   return `<details class="trace-step" data-trace-step="${esc(step)}" data-span="${key}" ${c.open.has(key)?'open':''}><summary><strong>${esc(step)}</strong><span>${items.length} ${items.some(r=>r.legacy)?'recorded tools':'recorded calls'}</span></summary><p class="planner-why">${esc(safe(why?.text || why?.why))}</p>${items.filter(r=>!items.some(p=>p.key===r.parent_id)).map(r=>render(r)).join('')}</details>`;
  }).join('') || '<p class="empty">Queued. The first step will appear when the worker begins.</p>';
 }
 function findings(){
  const claims=[...s.claims.values()].filter(cl=>cl.verified===true && Number.isFinite(cl.value) && cl.evidence_ids?.length);
  const preferred=new Set(['monthly_usd','language_tax_usd','token_multiplier','resend_factor','system_cost_share'].map(k=>s.billingData?.headline?.[k]).filter(Boolean));
  const configured=s.tokenizer || s.companies.find(row=>row.company===s.company)?.model_in_use;
  const rank=cl=>preferred.has(cl.id)?0:cl.id.includes(configured || '__none__') && /monthly_inr|saving_inr|cost_share|ratio/.test(cl.id)?1:cl.id.startsWith('quality/')?2:3;
  const selected=claims.filter(cl=>!/^markovian|^budget|^jobs/.test(cl.id)).sort((a,b)=>rank(a)-rank(b));
  $('#live-findings').innerHTML=selected.slice(0,12).map(cl=>`<article class="finding-card" data-verified="true"><span class="tag good">VERIFIED</span><small>${esc(cl.id)}</small><strong>${a.metric(cl.id)}</strong><span>${esc(cl.unit)}</span><button data-claim="${esc(cl.id)}">Open receipt ↗</button></article>`).join('') || '<p class="empty">No checked claims yet. Observations are visible in the trace.</p>';
 }
 function budgets(){
  const e=[...s.events].reverse().find(e=>e.event==='budget');
  $('#budgets').innerHTML=['nemotron','judge','hosted','sql','duration_s'].map(key=>{const value=e?.[key],max=e?.ceilings?.[key],label=key==='duration_s'?'Time (s)':key==='sql'?'SQL':key[0].toUpperCase()+key.slice(1);return `<div class="budget"><label>${label}</label><strong>${Number.isFinite(value)?Math.round(value):'—'} <small>/ ${Number.isFinite(max)?max:'—'}</small></strong><progress aria-label="${label} budget" max="${max || 1}" value="${max?Math.min(max,value || 0):0}"></progress><small>${max?'Physical attempts / ceiling':'Ceiling not recorded'}</small></div>`;}).join('');
 }
 function tail(){
  $('#event-tail').innerHTML=s.events.slice(-100).map(e=>`<div><time>${esc((e.timestamp || '').slice(11,23))}</time><b>${esc(e.event)}</b><span>${esc(e.step)}</span><span>${esc(e.error_class || e.name || e.tool || e.status || safe(e.text || e.why || ''))}</span></div>`).join('');
 }
 function update(){bar();const rows=spans();map(rows);trace(rows);findings();budgets();if(!$('#event-console').hidden)tail();}
 function reportTabs(){
  const children=[...$('#report-content').children];
  const groups=['overview','composition','replay','quality','models','scenario','timing','evidence','compression','evidence','evidence'];
  children.forEach((el,i)=>{el.dataset.reportGroup=groups[i] || 'evidence';el.hidden=!(c.tab==='overview' && i===0 || c.tab==='billing' && el.dataset.reportGroup===c.billing || c.tab==='quality' && ['quality','timing'].includes(el.dataset.reportGroup));});
  const hero=$('#report-content .report-hero');
  if(hero && s.report){let verdict=hero.querySelector('.overview-verdict');if(!verdict){verdict=document.createElement('div');verdict.className='overview-verdict panel';hero.append(verdict);}verdict.innerHTML=`<h2>Verdict</h2><p>${esc(s.report.quality_interpretation || s.report.quality_status || 'No quality verdict recorded.')}</p><p class="hint">${esc(s.report.top_fix || 'No verified fix recommended')} · ${esc(s.report.review_status || 'Native review pending')}</p>`;}
  let nav=$('#billing-tabs');if(!nav){nav=document.createElement('nav');nav.id='billing-tabs';nav.setAttribute('aria-label','Billing views');$('#report').prepend(nav);}
  nav.hidden=c.tab!=='billing';nav.innerHTML=[['composition','Composition'],['replay','History replay'],['models','Models'],['scenario','What-if'],['compression','Agent overhead']].map(([key,label])=>`<button data-bill-tab="${key}" aria-pressed="${c.billing===key}">${label}</button>`).join('');
  if(c.tab==='evidence')evidenceIndex();
  findings();
 }
 function evidenceIndex(){
  $('#evidence-ledger').innerHTML=`<p class="hint">Every number links to its source and recomputation. ${s.report?.dropped_claims?.length || 0} claims dropped.</p><div class="claim-list">${[...s.claims.values()].map(cl=>`<div><span>${esc(cl.id)}</span>${a.metric(cl.id)}</div>`).join('')}</div><h2>Accounting and review</h2><p>${esc(s.report?.review_status || 'Review status not recorded')}</p><details><summary>Accounting limits</summary><ul>${[...(s.report?.limitations || []),...(s.billingData?.limitations || [])].map(x=>`<li>${esc(x)}</li>`).join('')}</ul></details><h2>Dropped claims</h2>${(s.report?.dropped_claims || []).map((cl,i)=>`<p><button data-dropped="${i}">${esc(cl.id)}</button> · ${esc(cl.reason)}</p>`).join('') || '<p>None listed.</p>'}`;
 }
 function select(tab){
  c.tab=tab;
  const screen=tab==='tokens'?'tokens':tab==='evidence'?'evidence-index':['overview','billing','quality'].includes(tab)?'report':'investigation';
  if(screen==='report' && !s.report){a.notice('The checked result will be available when the run publishes its report.');return;}
  a.notice();a.show(screen);$('#investigation').dataset.view=tab;
  document.querySelectorAll('[data-console-tab]').forEach(b=>b.setAttribute('aria-current',b.dataset.consoleTab===tab?'page':'false'));
  reportTabs();if(tab==='tokens' && !s.tokenResults.size)a.inspectTokens();
 }
 async function history(){
  try{c.history=(await a.fetchJSON('/investigations')).data;}catch{c.history=[];}
  renderHistory();
 }
 function renderHistory(){
  const html=c.history.slice().reverse().sort((a,b)=>Number(b.demo || false)-Number(a.demo || false)).map(r=>`<button class="history-run" data-run="${esc(r.id)}"><strong>${esc(r.company || 'Investigation')}</strong><span class="tag">${esc(r.status)}</span><code>${esc(r.id)}</code><small>${r.saved?'Replay saved run':'Open live run'}</small></button>`).join('');
  $('#run-history').innerHTML=html || '<p class="hint">No saved runs yet.</p>';$('#history-list').innerHTML=html || '<p>No saved runs found. Import a report and its event log from Companies.</p>';
 }
 async function openRun(id){
  const entry=c.history.find(r=>r.id===id);
  if(entry && !entry.saved){c.replay=null;c.loaded=null;a.resetRun('live',id);s.company=entry.company;a.renderInvestigation();select('activity');a.connectEvents();return;}
  const version=++c.loadVersion;a.notice('Loading recorded evidence…');
  try{const {data}=await a.fetchJSON(`/investigations/${encodeURIComponent(id)}/replay`);if(version!==c.loadVersion)return;c.loaded=data;replay(data);a.notice();}
  catch(error){a.notice('Replay unavailable: '+error.message);}
 }
 function replay(data){
  a.resetRun('saved',data.report.id);s.company=data.report.company;
  for(const e of data.evidence || [])s.evidence.set(e.event_id,e);
  const events=data.events.filter(e=>e.investigation_id===data.report.id).slice().sort((a,b)=>stamp(a)-stamp(b));
  const start=stamp(events[0] || {}),end=stamp(events.at(-1) || {});
  c.replay={events,start,duration:Math.max(1,end-start),position:0,playing:true,last:performance.now(),index:0,completed:false};
  c.tab='activity';a.renderInvestigation();select('activity');bar();
 }
 function applyReplay(position){
  const r=c.replay;if(!r)return;
  const backwards=position<r.position;r.position=Math.min(r.duration,Math.max(0,position));
  if(backwards){s.events=[];s.claims=new Map();s.report=null;s.billingData=null;s.billingKey=null;r.index=0;r.completed=false;a.enableViews?.();}
  let changed=backwards;
  while(r.index<r.events.length && stamp(r.events[r.index])-r.start<=r.position){const row=r.events[r.index++];s.events.push(row);if(row.event==='claim_verified' && row.claim?.verified && Number.isFinite(row.claim.value) && row.claim.evidence_ids?.length)s.claims.set(row.claim.id,row.claim);changed=true;}
  if(r.position>=r.duration){r.playing=false;if(!r.completed){r.completed=true;a.setReport(c.loaded.report);changed=true;}}
  if(changed)a.renderInvestigation();clock();
 }
 function imported(){c.replay=null;c.loaded={report:s.report,events:[...s.events],evidence:[...s.evidence.values()]};c.tab='overview';reportTabs();bar();}
 document.addEventListener('toggle',event=>{const key=event.target.dataset?.span;if(key){if(event.target.open)c.open.add(key);else c.open.delete(key);}},true);
 document.addEventListener('click',async event=>{
  const b=event.target.closest('button');if(!b || b.disabled)return;
  if(b.dataset.consoleTab)select(b.dataset.consoleTab);
  if(b.dataset.billTab){c.billing=b.dataset.billTab;reportTabs();}
  if(b.dataset.run)openRun(b.dataset.run);
  if(b.id==='refresh-history')history();
  if(b.id==='toggle-events'){$('#event-console').hidden=!$('#event-console').hidden;b.setAttribute('aria-expanded',String(!$('#event-console').hidden));tail();}
  if(b.id==='replay-play'){if(c.replay){if(c.replay.position>=c.replay.duration)applyReplay(0);c.replay.playing=!c.replay.playing;c.replay.last=performance.now();clock();}}
  if(b.id==='stop-run'){if(c.replay){c.replay.playing=false;clock();}else try{await a.fetchJSON(`/investigations/${encodeURIComponent(s.runId)}/stop`,{method:'POST'});b.textContent='Stopping…';b.disabled=true;}catch(error){a.notice(error.message);}}
  if(b.id==='rerun'){if(s.mode==='saved' && c.loaded)replay(c.loaded);else{c.replay=null;c.loaded=null;$('#ask-form').requestSubmit();}}
  if(b.id==='replay-saved'){if(c.loaded?.events.length)replay(c.loaded);else{await history();a.show('history');}}
  if(b.id==='demo-run'){await history();const run=c.history.find(r=>r.company==='samudra' && r.demo) || c.history.find(r=>r.company==='samudra' && r.saved && r.status==='complete') || c.history.find(r=>r.saved);if(run)openRun(run.id);else a.notice('No saved demo found. Import a report with its event log.');}
 });
 $('#replay-position').addEventListener('input',()=>{if(c.replay){c.replay.playing=false;applyReplay(Number($('#replay-position').value)/1000*c.replay.duration);}});
 $('#theme').addEventListener('change',()=>{const t=$('#theme').value;document.documentElement.dataset.theme=t;try{localStorage.setItem('polytoken.theme',t);}catch{}});
 try{$('#theme').value=localStorage.getItem('polytoken.theme') || 'system';document.documentElement.dataset.theme=$('#theme').value;}catch{}
 window.addEventListener('polytoken:reset',()=>{if(s.mode==='live'){c.replay=null;c.loaded=null;}});
 window.addEventListener('polytoken:update',update);window.addEventListener('polytoken:report',reportTabs);window.addEventListener('polytoken:import',imported);
 window.addEventListener('polytoken:screen',event=>{if(event.detail==='report' && !['overview','billing','quality'].includes(c.tab))c.tab='overview';if(event.detail==='history')history();reportTabs();});
 document.addEventListener('keydown',event=>{if(!event.altKey || event.ctrlKey || event.metaKey)return;const key=event.key.toLowerCase();if(key==='r'){event.preventDefault();if(s.runId)$('#rerun').click();else $('#ask-form').requestSubmit();}if(key==='s'){event.preventDefault();$('#stop-run').click();}if(/^[1-8]$/.test(key)){event.preventDefault();if(key==='8')$('#toggle-events').click();else select(['activity','trace','overview','billing','quality','evidence','tokens'][Number(key)-1]);}});
 setInterval(()=>{const r=c.replay;if(r?.playing){const now=performance.now(),delta=now-r.last;r.last=now;applyReplay(r.position+delta*Number($('#replay-speed').value));}else if(r)r.last=performance.now();clock();},100);
 a.fetchJSON('/console/config').then(({data})=>{c.demo=s.demo=data.demo;$('#mode-note').textContent=c.demo?'Offline demo. Saved runs are ready; live provider calls are disabled.':'Live mode. Start a configured investigation or replay a saved run.';if(c.demo){$('#connection').textContent='Offline demo · recorded Zetaris evidence';$('#investigate').textContent='Live calls disabled in demo';$('#investigate').disabled=true;}}).catch(()=>{});
 history();
})();
