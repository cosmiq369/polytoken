/* PolyToken renders checked claims. It never recomputes measurements or verdicts. */
'use strict';
(() => {
  const $ = selector => document.querySelector(selector);
  const list = value => Array.isArray(value) ? value : [];
  const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const finite = value => typeof value === 'number' && Number.isFinite(value);
  const names = {samudra:'Samudra Telecom', swara:'Swara Care'};
  const parts = {system_prompt:'System prompt', user:'User turns and their replay', assistant:'Replayed answers', output:'New answers'};
  const steps = ['clarify','measure','locate','hypothesise','experiment','judge','speed','check','report'];
  const titles = {clarify:'Understand the workload',measure:'Measure the language gap',locate:'Locate the cost',hypothesise:'Choose a change',experiment:'Run the paired experiment',judge:'Check meaning is preserved',speed:'Measure reply time',check:'Recompute the claims',report:'Report what holds up'};
  const state = {companies:[], company:null, report:null, claims:new Map(), evidence:new Map(), evidenceErrors:new Map(), pendingEvidence:new Map(), events:[], source:null, timer:null, runId:null, mode:'live', screen:'ask', back:'report', tokenizer:null, ratioPart:'system_prompt', billing:'billed', generation:0, evidenceView:0, lastEventId:-1, posting:false};
  const number = (value, digits=2) => finite(value) ? new Intl.NumberFormat('en-IN',{maximumFractionDigits:digits}).format(value) : 'not measured';
  function format(claim, style) {
    if (!claim) return 'not measured';
    if (style === 'share') return new Intl.NumberFormat('en-IN',{style:'percent',maximumFractionDigits:1}).format(claim.value);
    if (style === 'signed') return new Intl.NumberFormat('en-IN',{signDisplay:'exceptZero',maximumFractionDigits:2}).format(claim.value) + (claim.unit === 'percent' ? '%' : ' tokens');
    if (claim.unit === 'INR') return new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:2}).format(claim.value);
    return number(claim.value) + (style === 'ratio' ? '×' : claim.unit === 'seconds' ? ' s' : claim.unit === 'tokens/s' ? ' tokens/s' : claim.unit === 'percent' ? '%' : '');
  }
  function notice(message='') { $('#notice').textContent=message; $('#notice').hidden=!message; }
  function missingReason(id) {
    const dropped=list(state.report?.dropped_claims).find(c=>c.id===id);
    return dropped?.reason || state.report?.partial_reason || (id.startsWith('quality/aa/') ? 'This report has no checked A/A control.' : 'No checked claim was supplied.');
  }
  function metric(id, style, label) {
    const claim=state.claims.get(id);
    return claim ? `<button type="button" class="metric" data-claim="${escape(id)}" aria-label="${escape((label || claim.text || id)+': '+format(claim,style)+'. Open evidence')}">${escape(format(claim,style))}</button>` : `<span class="metric missing" title="${escape(missingReason(id))}">not measured — ${escape(missingReason(id))}</span>`;
  }
  function tag(text, tone='') { return `<span class="tag ${tone}">${escape(text)}</span>`; }
  function show(screen, focus=true) {
    if (screen==='report' && !state.report) return;
    if (screen==='investigation' && !state.runId) return;
    state.screen=screen;
    document.querySelectorAll('.screen').forEach(el=>el.hidden=el.id!==screen);
    document.querySelectorAll('nav [data-screen]').forEach(el=>{
      if(el.dataset.screen===screen) el.setAttribute('aria-current','page'); else el.removeAttribute('aria-current');
    });
    document.title=`PolyToken · ${screen.charAt(0).toUpperCase()+screen.slice(1)}`;
    if(focus) { $('#main').focus(); window.scrollTo(0,0); }
  }
  function enableViews() {
    document.querySelectorAll('[data-screen="investigation"]').forEach(b=>b.disabled=!state.runId);
    document.querySelectorAll('[data-screen="report"]').forEach(b=>b.disabled=!state.report);
  }
  async function fetchJSON(url, options) {
    const response=await fetch(url, options);
    let data; try { data=await response.json(); } catch { throw new Error('The server returned an unreadable response.'); }
    if(!response.ok) throw new Error(typeof data.detail==='string' ? data.detail : `Request failed (${response.status}).`);
    return {data,status:response.status};
  }
  function renderCompanies() {
    $('#companies').innerHTML=state.companies.map(c=>`<button type="button" class="company-card" data-company="${escape(c.company)}" aria-pressed="${state.company===c.company}"><strong>${escape(names[c.company] || c.company)}</strong><span class="language">${escape(({te:'Telugu · తెలుగు',hi:'Hindi · हिन्दी'})[c.language] || c.language || 'Language not supplied')}</span><small>${escape(c.model_in_use || 'Model not supplied')}</small></button>`).join('');
    $('#investigate').disabled=!state.company || state.posting;
  }
  async function loadCompanies() {
    $('#retry-companies').hidden=true;
    try {
      const {data}=await fetchJSON('/companies');
      state.companies=list(data).filter(c=>c && ['samudra','swara'].includes(c.company));
      if(!state.companies.length) throw new Error('No supported company configuration was returned.');
      state.company=state.companies[0].company;
      renderCompanies(); $('#connection').textContent='Company configuration loaded · Zetaris';
    } catch(error) {
      $('#companies').innerHTML='<p class="muted">Company configuration is unavailable. Retry the lookup, or open a saved investigation.</p>';
      $('#connection').textContent='Company lookup unavailable'; $('#retry-companies').hidden=false;
    }
  }
  function stopStream() { state.source?.close(); state.source=null; clearTimeout(state.timer); state.timer=null; }
  function resetRun(mode, id) {
    stopStream(); state.generation++; state.evidenceView++; state.mode=mode; state.runId=id;
    state.report=null; state.claims=new Map(); state.events=[]; state.evidence=new Map(); state.evidenceErrors=new Map(); state.pendingEvidence=new Map();
    state.tokenizer=null; state.lastEventId=-1; state.billing='billed'; enableViews();
  }
  function setReport(report) {
    if(!report || typeof report!=='object' || !Array.isArray(report.claims) || typeof report.id!=='string') throw new Error('Choose an investigation report with an id and a claims array.');
    state.report=report; state.runId=report.id;
    const dropped=new Set(list(report.dropped_claims).map(c=>c.id));
    state.claims=new Map(list(report.claims).filter(c=>c && typeof c.id==='string' && c.verified===true && finite(c.value) && list(c.evidence_ids).length && !dropped.has(c.id)).map(c=>[c.id,c]));
    const tokenizers=baselineTokenizers();
    if(!tokenizers.includes(state.tokenizer)) {
      const configured=state.companies.find(c=>c.company===report.company)?.model_in_use;
      // Archived snapshots identify the company's tokenizer without guessing from a provider alias.
      const snapshot=[...state.evidence.values()].find(e=>e.payload?.config?.company===report.company || e.payload?.items?.[0]?.company===report.company);
      const preferred=snapshot?.payload?.config?.model_in_use || configured;
      const matches=tokenizers.filter(t=>t===preferred || t.endsWith('/'+preferred));
      state.tokenizer=matches.length===1 ? matches[0] : tokenizers.find(t=>state.claims.has(`baseline/${t}/monthly_inr`)) || tokenizers[0];
    }
    renderReport(); enableViews(); renderInvestigation();
  }
  function baselineTokenizers() {
    const ids=[...state.claims.keys()].flatMap(id=>{const match=id.match(/^baseline\/(.+)\/(?:chat_count|monthly_inr|system_prompt_share)$/); return match ? [match[1]] : [];});
    return [...new Set(ids)];
  }
  function ratioTokenizers() {
    return [...new Set([...state.claims.keys()].flatMap(id=>{const match=id.match(/^ratios\/(.+)\/(?:system_prompt|user|assistant)\/native_to_english_ratio$/);return match ? [match[1]] : [];}))];
  }
  function budgetHTML() {
    const event=[...state.events].reverse().find(e=>e.event==='budget');
    const prefix=state.report?.jobs?.budget ? 'jobs/' : 'budget/';
    const fields=[['nemotron','Nemotron calls'],['hosted','Hosted calls'],['sql','SQL queries'],['duration_s','Elapsed time']];
    return fields.map(([key,label])=>{
      const claim=state.claims.get(prefix+key);
      const value=claim ? metric(prefix+key) : event && finite(event[key]) ? `<button type="button" class="metric" data-budget-record>${escape(number(event[key]))}${key==='duration_s'?' s':''}</button>` : 'not measured';
      return `<div class="budget"><label>${label}</label><strong>${value}</strong><progress aria-label="${label}: ceiling not supplied"></progress><small>${key==='duration_s' && (claim || finite(event?.remaining_s)) ? `Remaining: ${state.claims.has(prefix+'remaining_s') ? metric(prefix+'remaining_s') : escape(number(event?.remaining_s))+' s'}` : 'Ceiling not supplied by API'}</small></div>`;
    }).join('');
  }
  function evidencePreview(record) {
    const payload=record?.payload || {};
    const first=Object.entries(payload).find(([key,value])=>['status','text','note','value','result','model_label','reason'].includes(key) && ['number','string','boolean'].includes(typeof value));
    const query=record?.provenance?.query;
    return first ? `${first[0]}: ${first[1]}` : query ? (typeof query==='string' ? query : JSON.stringify(query)) : 'Open the recorded observation';
  }
  function renderCards() {
    const ids=[...new Set(state.events.filter(e=>e.event==='evidence_added').map(e=>e.evidence_id))];
    $('#evidence-cards').innerHTML=ids.length ? ids.map(id=>{
      const record=state.evidence.get(id), event=state.events.find(e=>e.evidence_id===id);
      return `<button type="button" class="evidence-card" data-evidence="${escape(id)}"><span class="kind">${escape(record?.kind || event?.kind || 'Evidence')}</span><span class="preview">${escape(record ? evidencePreview(record) : state.evidenceErrors.get(id) || 'Open the recorded observation')}</span><small>${escape(record?.provenance?.source || record?.provenance?.kind || id)}</small></button>`;
    }).join('') : '<p class="empty">No evidence events recorded yet.</p>';
  }
  function renderInvestigation() {
    $('#run-context').textContent=`${state.mode==='saved'?'Saved investigation':'Investigation'} · ${names[state.report?.company || state.company] || state.report?.company || ''}`;
    $('#budgets').innerHTML=budgetHTML();
    const ended=state.events.some(e=>e.event==='done') || ['complete','partial'].includes(state.report?.status);
    const active=[...state.events].reverse().find(e=>e.event==='step_started')?.step;
    $('#timeline').innerHTML=steps.map(step=>{
      const events=state.events.filter(e=>e.step===step), started=events.some(e=>e.event==='step_started');
      const tool=[...events].reverse().find(e=>e.event==='tool_called');
      const why=[...events].reverse().find(e=>e.why)?.why;
      return `<li class="${started?'started':''} ${started && active===step && !ended?'running':''}"><h3>${escape(titles[step])} ${started && active===step && !ended ? tag(state.mode==='saved'?'Last recorded step':'Running','good') : ''}</h3><span class="tool">${escape(tool?.tool || 'Tool not recorded')}</span><p class="muted">${escape(why || 'No step explanation recorded yet.')}</p>${events.filter(e=>e.event==='finding').map(e=>`<p class="finding">${escape(e.text)}</p>`).join('')}</li>`;
    }).join('');
    const progress=[...state.events].reverse().find(e=>e.event==='experiment_progress');
    const done=[...state.events].reverse().find(e=>e.event==='experiment_done');
    $('#experiment-progress').innerHTML=progress ? `<button type="button" class="metric" data-progress-record>Background calls: ${escape(number(progress.done))} done · ${escape(number(progress.failed))} failed · ${escape(number(progress.total))} total</button>${done ? ` · Final paired experiment: ${escape(done.status)}` : ''}` : `Background experiment: ${escape(state.report?.jobs?.status || 'not measured — no progress event received.')}`;
    renderCards();
  }
  async function getEvidence(id) {
    if(state.evidence.has(id)) return state.evidence.get(id);
    if(state.mode==='saved') throw new Error('Raw evidence not loaded. Add the matching World Model JSONL file from the Ask screen.');
    if(state.pendingEvidence.has(id)) return state.pendingEvidence.get(id);
    const generation=state.generation;
    const request=fetchJSON('/evidence/'+encodeURIComponent(id)).then(({data})=>{
      if(generation===state.generation) {state.evidence.set(id,data);state.evidenceErrors.delete(id);renderCards();}
      return data;
    }).catch(error=>{if(generation===state.generation) state.evidenceErrors.set(id,error.message);throw error;}).finally(()=>{if(generation===state.generation) state.pendingEvidence.delete(id);});
    state.pendingEvidence.set(id,request); return request;
  }
  async function pollReport(generation=state.generation) {
    if(generation!==state.generation || state.mode!=='live' || !state.runId) return;
    try {
      const {data,status}=await fetchJSON(`/investigations/${encodeURIComponent(state.runId)}/report`);
      if(generation!==state.generation) return;
      if(Array.isArray(data.claims)) setReport(data);
      if(status===200 && data.status!=='running') {
        clearTimeout(state.timer); state.timer=null;
        // A final report can precede delivery of the last SSE frames. Let done drain them.
        if(state.events.some(e=>e.event==='done')) {state.source?.close();state.source=null;}
        $('#stream-status').textContent=`Investigation ${data.status || 'finished'}. Open the report to inspect checked claims.`;
        return;
      }
    } catch(error) {
      if(generation!==state.generation) return;
      $('#stream-status').textContent='Report temporarily unavailable. Retrying while the investigation runs.';
    }
    if(generation===state.generation) {clearTimeout(state.timer);state.timer=setTimeout(()=>pollReport(generation),2500);}
  }
  function connectEvents() {
    const generation=state.generation;
    const source=new EventSource(`/investigations/${encodeURIComponent(state.runId)}/events`); state.source=source;
    source.onopen=()=>{if(generation===state.generation) $('#stream-status').textContent='Connected to the investigation event stream.';};
    source.onerror=()=>{
      if(generation!==state.generation) return;
      if(['complete','partial'].includes(state.report?.status)) {source.close();return;}
      $('#stream-status').textContent='Event connection interrupted. Reconnecting; the report is checked separately.';
    };
    for(const type of ['step_started','tool_called','evidence_added','finding','budget','claim_dropped','experiment_progress','experiment_done','done']) source.addEventListener(type,event=>{
      if(generation!==state.generation) return;
      try {
        const id=Number(event.lastEventId); if(event.lastEventId && id<=state.lastEventId) return;
        const row=JSON.parse(event.data); if(row.investigation_id!==state.runId) return;
        if(event.lastEventId) state.lastEventId=id;
        state.events.push(row); renderInvestigation();
        if(type==='evidence_added') getEvidence(row.evidence_id).catch(()=>renderCards());
        if(type==='done') {source.close();$('#stream-status').textContent=`Workflow ended: ${row.status || 'report pending'}. Retrieving the final report…`;pollReport(generation);}
      } catch { $('#stream-status').textContent='An unreadable event was skipped. The checked report remains available.'; }
    });
    pollReport(generation);
  }
  function quality(prefix, title) {
    if(!state.claims.has(prefix+'passed') && !state.claims.has(prefix+'judged')) return `<span>${title}: <small>not measured — ${escape(missingReason(prefix+'judged'))}</small></span>`;
    return `<span>${title}: ${metric(prefix+'passed')} / ${metric(prefix+'judged')} <small>judged</small></span>`;
  }
  function fixStatus(status='not testable') {
    if(status.startsWith('provisional')) return tag('Recommended provisionally · native review pending','good');
    if(status==='rejected' || status==='failed') return tag('Failed','failed');
    if(status.includes('inconclusive') || status==='insufficient sample') return tag('Inconclusive','warm');
    if(status==='untested estimate') return tag('Untested estimate','warm');
    return tag(status);
  }
  function renderRatios() {
    const tokenizers=ratioTokenizers();
    return `<section class="panel"><div class="toolbar"><h2>Native / English</h2><label>Conversation part <select id="ratio-part">${['system_prompt','user','assistant'].map(p=>`<option value="${p}" ${state.ratioPart===p?'selected':''}>${escape(p==='assistant'?'Answers':parts[p])}</option>`).join('')}</select></label></div><p class="hint">Paired token ratio · whole-chat bootstrap interval</p>${tokenizers.map(t=>{
      const prefix=`ratios/${t}/${state.ratioPart}/`, ratio=state.claims.get(prefix+'native_to_english_ratio');
      return `<div class="ratio-row"><div class="ratio-label"><span>${escape(t)}</span>${metric(prefix+'native_to_english_ratio','ratio')}</div>${ratio ? `<div class="ratio-track" aria-hidden="true"><div class="ratio-bar" style="--ratio:${ratio.value}"></div></div>` : ''}<div class="interval">Interval ${metric(prefix+'ci_low')} – ${metric(prefix+'ci_high')}</div></div>`;
    }).join('') || '<p class="empty">not measured — no checked paired ratios supplied.</p>'}</section>`;
  }
  function renderBilling() {
    const prefix=`baseline/${state.tokenizer}/`;
    const available=Object.keys(parts).every(p=>state.claims.has(prefix+p+'_share'));
    const content=state.billing==='transcript' ? '<p class="empty">not measured — this report schema supplies billed content totals only. Transcript totals have no checked claims; they are not calculated here.</p>' : `${available ? `<div class="stack" aria-label="Billed token composition">${Object.keys(parts).map(p=>`<button type="button" class="stack-segment part-${p}" style="width:${state.claims.get(prefix+p+'_share').value*100}%" data-claim="${escape(prefix+p+'_share')}" aria-label="${escape(parts[p]+': '+format(state.claims.get(prefix+p+'_share'),'share')+'. Open evidence')}"></button>`).join('')}</div>` : '<p class="empty">Composition not measured — one or more checked shares are absent.</p>'}${Object.keys(parts).map(p=>`<div class="part-row"><span class="part-name"><i class="swatch part-${p}" aria-hidden="true"></i>${parts[p]}</span>${metric(prefix+p+'_share','share')}</div>`).join('')}<p class="hint">Shares of billed content tokens. History is counted each time it is sent; new answers are output.</p>`;
    return `<section class="panel"><h2>Where the billed tokens go</h2><div class="toolbar"><label>Tokenizer <select id="billing-tokenizer">${baselineTokenizers().map(t=>`<option value="${escape(t)}" ${state.tokenizer===t?'selected':''}>${escape(t)}</option>`).join('')}</select></label><div class="segmented" role="group" aria-label="Token accounting"><button type="button" data-billing="billed" aria-pressed="${state.billing==='billed'}">Billed</button><button type="button" data-billing="transcript" aria-pressed="${state.billing==='transcript'}">Transcript</button></div></div>${content}<div class="cost-total"><span class="hint">Quoted monthly content bill</span><strong>${metric(prefix+'monthly_inr')}</strong><p class="hint">At ${metric(prefix+'monthly_chats')} chats per month.</p><p class="hint">${escape(state.report?.money_status || 'Price status not supplied.')}</p></div></section>`;
  }
  function renderSpeed() {
    return `<section class="panel"><div class="toolbar"><h2>Reply time</h2>${tag(state.report.speed_status || 'not measured','warm')}</div><p class="hint">Recorded original and changed medians, with observed spread.</p>${[['ttft_s','First visible token'],['latency_s','Complete reply']].map(([key,title])=>`<h3 style="margin-top:20px">${title}</h3><div class="speed-row">${['original','changed'].map(side=>`<div><p class="hint">${side==='original'?'Original':'Changed'}</p><p class="speed-number">${metric(`speed/${key}/${side}_median`)}</p><p class="hint">${metric(`speed/${key}/${side}_min`)} – ${metric(`speed/${key}/${side}_max`)}</p></div>`).join('')}</div>`).join('')}<p class="hint">${escape(state.report.experiment?.model_label || 'Hosting relationship not supplied.')}</p><p class="hint">Throughput: ${escape(state.report.throughput_status || 'not measured — no throughput status supplied.')}</p></section>`;
  }
  function renderMarkovian() {
    return `<section class="panel"><h2>What compression saved</h2><p class="hint">Signed Markovian accounting. Negative values mean extra tokens. All reported runs are retained.</p>${list(state.report.markovian_runs).map(run=>`<div class="markovian-row"><span><code>${escape(run.claim_prefix)}</code> · ${escape(run.token_label)}</span><span>${metric(run.claim_prefix+'net_tokens','signed')}<br>${metric(run.claim_prefix+'net_percent','signed')}</span></div>`).join('') || '<p class="empty">not measured — no compression runs supplied.</p>'}<p class="hint">Reference history-replay counterfactual; not an independently measured second execution.</p></section>`;
  }
  function renderReport() {
    const r=state.report; if(!r) return;
    const part=Object.keys(parts).find(p=>r.top_finding?.includes(p));
    const leadId=part && state.tokenizer ? `baseline/${state.tokenizer}/${part}_cost_share` : null;
    const fixes=list(r.fixes); // The server supplies the checked ranking; do not re-rank here.
    $('#report-content').innerHTML=`<section class="panel report-hero"><div class="report-meta"><p class="eyebrow">${escape(names[r.company] || r.company || 'Investigation report')}</p>${tag(r.status || 'Status not supplied')}${tag(state.mode==='saved'?'Saved report · recorded checker verdicts':'Checked report','good')}</div><h1 id="report-title">${escape(r.top_finding || 'No checked top finding is available.')}</h1>${leadId ? `<div class="lead-metric">${metric(leadId,'share')}</div><p class="lead-caption">${escape(parts[part])} share of quoted cost · ${escape(state.tokenizer)}</p>` : ''}<p class="hint">${escape(r.partial_reason || '')}</p><div class="actions"><button type="button" id="download-report">Download report JSON</button><button type="button" data-screen="investigation">View reasoning trail →</button></div><p class="hint">Run <code>${escape(r.id)}</code></p></section>
      <div class="report-grid">${renderRatios()}${renderBilling()}</div>
      <section class="panel report-wide"><div class="toolbar"><h2>Fixes, ranked by monthly saving</h2>${tag('Native review: '+(r.review_status || 'not supplied'))}</div><p class="hint">${escape(r.experiment?.accounting || 'Each hypothesis retains its reported accounting basis.')}</p>${fixes.map(f=>{
        const tested=list(f.experiment_evidence_ids).length>0;
        const title={english_system:'Keep system instructions in English',answer_cap:'Cap answer length',model_switch:'Switch the model'}[f.lever] || f.lever;
        return `<article class="fix"><div class="fix-heading"><div><h3>${escape(title)}${f.tokenizer?` · ${escape(f.tokenizer)}`:''}</h3>${fixStatus(f.status)}</div><div class="fix-money">${metric(f.claim_id)}<small>per month · quoted scenario</small></div></div><p>${escape(f.reason || f.basis || 'No reason supplied.')}</p>${f.reason && f.basis?`<p>${escape(f.basis)}</p>`:''}${tested ? `<div class="quality-line">${quality('quality/','A/B same facts')}${quality('quality/aa/','A/A floor')}</div><p>${escape(r.quality_interpretation || r.quality_status || 'Quality interpretation not supplied.')}</p><p>${escape(f.model_label || r.experiment?.model_label || '')}</p>` : '<p>Quality: not measured — this hypothesis has no paired experiment in this report.</p>'}</article>`;
      }).join('') || '<p class="empty">No checked fix is available.</p>'}</section>
      <div class="report-grid">${renderSpeed()}${renderMarkovian()}</div>
      <div class="report-grid"><section class="panel"><h2>Dropped claims</h2><p class="hint">Rejected numbers are not displayed.</p><ul class="reason-list">${list(r.dropped_claims).map(c=>`<li><code>${escape(c.id)}</code><br>${escape(c.reason)}</li>`).join('')}</ul>${!list(r.dropped_claims).length?'<p class="muted">No dropped claims listed in this report.</p>':''}</section><section class="panel"><h2>Read this with the result</h2><ul class="reason-list">${list(r.limitations).map(item=>`<li>${escape(item)}</li>`).join('')}${list(r.needs_input).map(item=>`<li>Input needed: ${escape(typeof item==='string'?item:JSON.stringify(item))}</li>`).join('')}</ul><p class="hint">${escape(r.quoted_price?.provider || 'Price provider not supplied.')}<br>${escape(r.quoted_price?.fetched_at || '')}</p></section></div>
      <section class="panel"><h2>Every checked claim</h2><p class="hint">Open a value to see its formula, source records and provenance.</p><details><summary>Browse the claim ledger</summary><div class="claim-list">${[...state.claims.values()].map(c=>`<div><span>${escape(c.id)}</span>${metric(c.id)}</div>`).join('')}</div></details></section>`;
  }
  function formula(claim) {
    const id=claim.id;
    if(id.endsWith('_cost_share')) return 'Quoted cost of this billed component ÷ quoted cost of all billed components.';
    if(id.endsWith('_share')) return 'Billed tokens in this component ÷ all billed input and output tokens.';
    if(id.endsWith('/monthly_inr')) return '((Billed input × input USD price per million + billed output × output USD price per million) ÷ 1,000,000) × monthly chats ÷ sample chats × INR per USD.';
    if(id.endsWith('monthly_saving_inr')) return 'Original monthly quoted cost − changed monthly quoted cost, using the recorded scenario and price inputs.';
    if(id.endsWith('native_to_english_ratio')) return 'Paired native-token total ÷ English-token total for this tokenizer and conversation part.';
    if(id.endsWith('/ci_low') || id.endsWith('/ci_high')) return 'Recorded bound of the paired whole-chat bootstrap interval; recomputed by the server checker.';
    if(id.startsWith('quality/')) return 'Count of recorded eligible same-facts verdicts, judged pairs or pending reviews, as selected by the claim ID.';
    if(id.startsWith('speed/')) return 'Recorded timing statistic over valid paired trials, selected by the exact claim ID. Difference = changed − original.';
    if(id.startsWith('markovian/')) return 'Signed reference history-replay token cost − compressed-run token cost; percent uses the reference cost as denominator.';
    return `Checker operation: ${claim.recompute?.operation || 'not supplied'}. The exact claim ID selects the statistic from the recorded inputs.`;
  }
  function recordHTML(record) {
    const p=record.provenance || {}, payload=record.payload || {};
    const supports=list(payload.supports);
    return `<article class="panel evidence-record"><p class="eyebrow">${escape(record.kind || 'Recorded event')}</p><h3>${escape(record.event_id || 'Event record')}</h3><dl><dt>Source</dt><dd>${escape(p.source || p.kind || 'not supplied')}</dd><dt>Query</dt><dd><code>${escape(typeof p.query==='string'?p.query:JSON.stringify(p.query) || 'not supplied')}</code></dd><dt>Fetched at</dt><dd>${escape(p.fetched_at || 'not supplied')}</dd><dt>Time window</dt><dd>${escape(typeof p.time_window==='string'?p.time_window:JSON.stringify(p.time_window) || 'not supplied')}</dd><dt>Evidence run ID</dt><dd>${escape(p.run_id || payload.run_id || 'not supplied; the report run is shown above')}</dd></dl><details><summary>Raw rows or call record</summary><pre>${escape(JSON.stringify(payload,null,2))}</pre></details><details><summary>Complete provenance and event</summary><pre>${escape(JSON.stringify(record,null,2))}</pre></details>${supports.length?`<details><summary>Supporting source records</summary><div class="actions">${supports.map(id=>`<button type="button" data-evidence="${escape(id)}">${escape(id)}</button>`).join('')}</div></details>`:''}</article>`;
  }
  async function openEvidence(claimId, evidenceId) {
    if(state.screen!=='evidence') state.back=state.screen;
    $('#back-evidence').textContent=`← Back to ${state.back==='investigation'?'investigation':'report'}`;
    const view=++state.evidenceView, claim=state.claims.get(claimId);
    const ids=claim ? list(claim.evidence_ids) : [evidenceId];
    $('#evidence-content').innerHTML=`<section class="panel"><p class="eyebrow">${claim?'Checked claim':'Recorded observation'}</p><h2>${escape(claim?.text || evidenceId)}</h2>${claim?`<p class="lead-metric">${escape(format(claim,claim.id.endsWith('_share')?'share':undefined))}</p><code>${escape(claim.id)}</code><div class="formula">${escape(formula(claim))}</div><details><summary>Exact checked claim</summary><pre>${escape(JSON.stringify(claim,null,2))}</pre></details><h3>Formula inputs</h3><pre>${escape(JSON.stringify(claim.recompute || {reason:'No recipe supplied'},null,2))}</pre>`:''}<p class="hint">Report / investigation run: <code>${escape(state.runId || 'not supplied')}</code></p></section><div id="raw-evidence"><p class="empty">Loading recorded evidence…</p></div>`;
    show('evidence');
    const records=await Promise.all(ids.map(async id=>{try{return recordHTML(await getEvidence(id));}catch(error){return `<section class="panel evidence-record"><h3>${escape(id)}</h3><p class="muted">${escape(error.message)}</p><button type="button" data-evidence="${escape(id)}">Retry evidence lookup</button></section>`;}}));
    if(view===state.evidenceView) $('#raw-evidence').innerHTML=records.join('');
  }
  function openEvent(row) {
    if(!row) return;state.back=state.screen;state.evidenceView++;
    $('#back-evidence').textContent='← Back to investigation';
    $('#evidence-content').innerHTML=`<section class="panel"><p class="eyebrow">Runtime telemetry · recorded event</p><h2>${escape(row.event)}</h2><p class="hint">Direct event values. No browser aggregation.</p><pre>${escape(JSON.stringify(row,null,2))}</pre></section>`;show('evidence');
  }
  async function importFiles(files) {
    // Parse the whole selection before changing the current run; invalid files leave it intact.
    const records=[];
    for(const file of files) {
      const text=await file.text();
      if(file.name.endsWith('.jsonl')) records.push(...text.split(/\r?\n/).filter(line=>line.trim()).map(line=>JSON.parse(line)));
      else records.push(JSON.parse(text));
    }
    const reports=records.filter(r=>r && typeof r.id==='string' && Array.isArray(r.claims));
    if(reports.length>1) throw new Error('Choose one report at a time, with its supporting JSONL files.');
    const report=reports[0] || (state.mode==='saved'?state.report:null);
    if(!report) throw new Error('Include a report JSON before adding supporting files.');
    if(reports.length) resetRun('saved',report.id);
    for(const row of records) {
      const evidence=row.world_event || (row.event_id && row.payload ? row : null);
      if(evidence?.event_id) state.evidence.set(evidence.event_id,evidence);
      if(row.event && row.investigation_id===report.id && !state.events.some(e=>JSON.stringify(e)===JSON.stringify(row))) state.events.push(row);
    }
    setReport(report);$('#stream-status').textContent='Saved event log · no live calls. Steps and progress retain their recorded values.';
    notice();show('report');
  }
  document.addEventListener('click',event=>{
    const button=event.target.closest('button');
    if(!button || button.disabled) return;
    if(button.dataset.screen) show(button.dataset.screen);
    else if(button.dataset.company) {state.company=button.dataset.company;renderCompanies();}
    else if(button.dataset.claim) openEvidence(button.dataset.claim);
    else if(button.dataset.evidence) openEvidence(null,button.dataset.evidence);
    else if(button.dataset.billing) {state.billing=button.dataset.billing;renderReport();$(`[data-billing="${state.billing}"]`).focus();}
    else if(button.hasAttribute('data-budget-record')) openEvent([...state.events].reverse().find(e=>e.event==='budget'));
    else if(button.hasAttribute('data-progress-record')) openEvent([...state.events].reverse().find(e=>e.event==='experiment_progress'));
    else if(button.id==='back-evidence') {state.evidenceView++;show(state.back);}
    else if(button.id==='retry-companies') loadCompanies();
    else if(button.id==='download-report') {
      const url=URL.createObjectURL(new Blob([JSON.stringify(state.report,null,2)],{type:'application/json'}));
      const a=document.createElement('a');a.href=url;a.download=`polytoken-${state.report.id}.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    }
  });
  $('.brand').addEventListener('click',event=>{event.preventDefault();show('ask');});
  document.addEventListener('change',event=>{
    if(event.target.id==='ratio-part') {state.ratioPart=event.target.value;renderReport();$('#ratio-part').focus();}
    if(event.target.id==='billing-tokenizer') {state.tokenizer=event.target.value;renderReport();$('#billing-tokenizer').focus();}
  });
  $('#saved-files').addEventListener('change',async event=>{
    try {await importFiles([...event.target.files]);}catch(error){notice('Could not open saved investigation: '+error.message);}finally{event.target.value='';}
  });
  $('#ask-form').addEventListener('submit',async event=>{
    event.preventDefault(); if(!state.company || state.posting) return;
    const body={company:state.company,question:$('#question').value.trim()};
    if($('#monthly-chats').value) body.monthly_chats=Number($('#monthly-chats').value);
    if($('#latency-target').value) body.latency_target_s=Number($('#latency-target').value);
    state.posting=true;$('#investigate').disabled=true;notice();
    try {
      const {data}=await fetchJSON('/investigations',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
      if(typeof data.id!=='string') throw new Error('The server did not return an investigation ID.');
      resetRun('live',data.id);renderInvestigation();show('investigation');$('#stream-status').textContent='Investigation queued. Waiting for the worker…';connectEvents();
    }catch(error){notice('Could not start the investigation: '+error.message);}
    finally{state.posting=false;$('#investigate').disabled=!state.company;}
  });
  window.addEventListener('beforeunload',stopStream);
  loadCompanies();
})();
