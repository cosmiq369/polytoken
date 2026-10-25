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
  const state = {companies:[], company:null, report:null, claims:new Map(), evidence:new Map(), evidenceErrors:new Map(), pendingEvidence:new Map(), events:[], source:null, timer:null, runId:null, mode:'live', screen:'ask', back:'report', tokenizer:null, ratioPart:'system_prompt', billing:'billed', generation:0, evidenceView:0, lastEventId:-1, posting:false, billingData:null, billingKey:null, billingReason:null, currencies:[{currency:'USD',per_usd:1,verified:true}], currency:'INR', scenario:{volume:null,input:1,output:1}, tokenResults:new Map(),tokenSequence:0};
  try {state.currency=localStorage.getItem('polytoken.currency') || 'INR';}catch {}
  const number = (value, digits=2) => finite(value) ? new Intl.NumberFormat('en-IN',{maximumFractionDigits:digits}).format(value) : 'not measured';
  function format(claim, style) {
    if (!claim) return 'not measured';
    if (style === 'cost-ratio') return number(claim.value,1)+'×';
    if (style === 'share') return new Intl.NumberFormat('en-IN',{style:'percent',maximumFractionDigits:1}).format(claim.value);
    if (style === 'signed') return new Intl.NumberFormat('en-IN',{signDisplay:'exceptZero',maximumFractionDigits:2}).format(claim.value) + (claim.unit === 'percent' ? '%' : ' tokens');
    if(claim.unit==='USD') return money(claim.value);
    if(claim.unit==='INR') {
      const usd=state.billingData?.report_money?.[claim.id]?.value;
      if(finite(usd)) return money(usd);
      const fx=state.evidence.get(claim.recompute?.inputs?.fx)?.payload?.inr_per_usd;
      if(finite(fx) && fx>0) return money(claim.value/fx);
      return new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:2}).format(claim.value)+' (recorded INR)';
    }
    return number(claim.value) + (style === 'ratio' ? '×' : claim.unit === 'seconds' ? ' s' : claim.unit === 'tokens/s' ? ' tokens/s' : claim.unit === 'percent' ? '%' : claim.unit==='tokens'?' tokens':'');
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
    if(screen==='tokens' && !state.report)return;
    state.screen=screen;
    window.dispatchEvent(new CustomEvent('polytoken:screen',{detail:screen}));
    document.querySelectorAll('.screen').forEach(el=>el.hidden=el.id!==screen);
    document.querySelectorAll('nav [data-screen]').forEach(el=>{
      const workspaceScreen=['investigation','report','evidence-index','evidence'].includes(screen)?'history':screen;
      if(el.dataset.screen===(el.closest('.rail')?workspaceScreen:screen)) el.setAttribute('aria-current','page'); else el.removeAttribute('aria-current');
    });
    document.title=`PolyToken · ${screen.charAt(0).toUpperCase()+screen.slice(1)}`;
    if(focus) { $('#main').focus(); window.scrollTo(0,0); }
  }
  function enableViews() {
    document.querySelectorAll('[data-screen="investigation"]').forEach(b=>b.disabled=!state.runId);
    document.querySelectorAll('[data-screen="report"],[data-console-tab="billing"],[data-console-tab="quality"]').forEach(b=>b.disabled=!state.report);
    document.querySelectorAll('[data-screen="tokens"]').forEach(b=>b.disabled=!state.report);
  }
  async function fetchJSON(url, options) {
    const response=await fetch(url, options);
    let data; try { data=await response.json(); } catch { throw new Error('The server returned an unreadable response.'); }
    if(!response.ok) throw new Error(typeof data.detail==='string' ? data.detail : `Request failed (${response.status}).`);
    return {data,status:response.status};
  }
  function renderCompanies() {
    $('#companies').innerHTML=state.companies.map(c=>`<button type="button" class="company-card" data-company="${escape(c.company)}" aria-pressed="${state.company===c.company}"><strong>${escape(names[c.company] || c.company)}</strong><span class="language">${escape(({te:'Telugu · తెలుగు',hi:'Hindi · हिन्दी'})[c.language] || c.language || 'Language not supplied')}</span><small>${escape(c.model_in_use || 'Model not supplied')}</small><small class="company-volume">${finite(c.monthly_chats)?number(c.monthly_chats,0)+' conversations / month':'Volume not supplied'}</small></button>`).join('');
    $('#investigate').disabled=!state.company || state.posting || state.demo;
  }
  async function loadCompanies() {
    $('#retry-companies').hidden=true;
    try {
      const {data}=await fetchJSON('/companies');
      state.companies=list(data).filter(c=>c && ['samudra','swara'].includes(c.company));
      if(!state.companies.length) throw new Error('No supported company configuration was returned.');
      state.company=state.companies[0].company;
      renderCompanies(); $('#connection').textContent=state.demo?'Offline demo · recorded Zetaris evidence':'Company configuration loaded · Zetaris';
    } catch(error) {
      $('#companies').innerHTML='<p class="muted">Company configuration is unavailable. Retry the lookup, or open a saved investigation.</p>';
      $('#connection').textContent='Company lookup unavailable'; $('#retry-companies').hidden=false;
    }
  }
  function stopStream() { state.source?.close(); state.source=null; clearTimeout(state.timer); state.timer=null; }
  function resetRun(mode, id) {
    stopStream(); state.generation++; state.evidenceView++; state.mode=mode; state.runId=id;
    window.dispatchEvent(new Event('polytoken:reset'));
    state.report=null; state.claims=new Map(); state.events=[]; state.evidence=new Map(); state.evidenceErrors=new Map(); state.pendingEvidence=new Map();
    state.tokenizer=null;state.billingData=null;state.billingKey=null;state.billingReason=null;state.scenario={volume:null,input:1,output:1};state.tokenResults=new Map();state.tokenSequence++;$('#token-text').value='';state.lastEventId=-1; state.billing='billed'; enableViews();
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
    attachBilling();renderReport(); enableViews(); renderInvestigation();loadBilling(report);
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
      return `<div class="budget"><label>${label}</label><strong>${value}</strong><svg viewBox="0 0 200 10" class="budget-gauge" aria-label="${label}: ceiling not supplied"><path d="M0 5 H200"/></svg><small>${key==='duration_s' && (claim || finite(event?.remaining_s)) ? `Remaining: ${state.claims.has(prefix+'remaining_s') ? metric(prefix+'remaining_s') : escape(number(event?.remaining_s))+' s'}` : 'Ceiling not supplied by API'}</small></div>`;
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
      const stamps={clarify:'Recorded',measure:'Measured',locate:'Located',hypothesise:'Hypothesised',experiment:'Tested',judge:'Judged',speed:'Timed',check:'Checked',report:'Reported'};
      const observed=events.some(e=>e.event==='finding' || e.event==='evidence_added') || (step==='experiment' && state.report?.jobs?.status==='complete') || (step==='judge' && state.claims.has('quality/judged')) || (step==='speed' && state.claims.has('speed/completed_runs')) || (step==='check' && !!state.report) || (step==='report' && !!state.report);
      const stamp=started && active===step && !ended ? 'Running' : !started ? 'Awaiting' : observed ? stamps[step] : 'Recorded';
      return `<li class="${started?'started':''} ${started && active===step && !ended?'running':''}"><h3>${escape(titles[step])} ${tag(stamp,stamp==='Checked'?'good':'')}</h3><span class="tool">${escape(tool?.tool || 'Tool not recorded')}</span><p class="muted">${escape(window.polySafeExplanation ? window.polySafeExplanation(why || 'No step explanation recorded yet.') : 'Explanation available in the trace.')}</p>${events.filter(e=>e.event==='finding').map(e=>`<p class="finding">${escape(e.text)}</p>`).join('')}</li>`;
    }).join('');
    const progress=[...state.events].reverse().find(e=>e.event==='experiment_progress');
    const done=[...state.events].reverse().find(e=>e.event==='experiment_done');
    $('#experiment-progress').innerHTML=progress ? `<button type="button" class="metric" data-progress-record>Background calls: ${escape(number(progress.done))} done · ${escape(number(progress.failed))} failed · ${escape(number(progress.total))} total</button>${done ? ` · Final paired experiment: ${escape(done.status)}` : ''}` : `Background experiment: ${escape(state.report?.jobs?.status || 'not measured — no progress event received.')}`;
    renderCards();
    window.dispatchEvent(new Event('polytoken:update'));
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
    for(const type of ['step_started','step_finished','planner_reason','tool_called','tool_started','tool_finished','model_call_started','model_call_finished','sql_started','sql_finished','claim_verified','evidence_added','finding','budget','claim_dropped','experiment_progress','experiment_done','price_unavailable','stop_requested','done']) source.addEventListener(type,event=>{
      if(generation!==state.generation) return;
      try {
        const id=Number(event.lastEventId); if(event.lastEventId && id<=state.lastEventId) return;
        const row=JSON.parse(event.data); if(row.investigation_id!==state.runId) return;
        if(event.lastEventId) state.lastEventId=id;
        state.events.push(row);
        if(type==='claim_verified' && row.claim?.verified===true && finite(row.claim.value) && list(row.claim.evidence_ids).length) state.claims.set(row.claim.id,row.claim);
        renderInvestigation();
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
  function rate() { return state.currencies.find(r=>r.currency===state.currency) || state.currencies[0]; }
  function money(value) {
    if(!finite(value)) return 'not measured';
    return new Intl.NumberFormat('en-IN',{style:'currency',currency:state.currency,minimumFractionDigits:2,maximumFractionDigits:Math.abs(value*(rate()?.per_usd || 1))<.1?6:2}).format(value*(rate()?.per_usd || 1));
  }
  function rateNote() {
    const r=rate();
    return state.currency==='USD' ? 'USD · quoted provider prices; no exchange conversion' : `${state.currency} per USD ${number(r.per_usd,6)} · ${r.source} · rate as of ${r.as_of} · fetched ${r.fetched_at}`;
  }
  async function loadCurrencies() {
    try {
      const {data}=await fetchJSON('/currencies');
      if(data.base!=='USD' || !Array.isArray(data.rates)) throw new Error('Invalid currency list');
      state.currencies=data.rates.filter(r=>r.verified===true && finite(r.per_usd) && r.per_usd>0 && /^[A-Z]{3}$/.test(r.currency));
      if(!state.currencies.some(r=>r.currency===state.currency)) state.currency='USD';
    } catch {state.currency='USD';}
    $('#currency').innerHTML=state.currencies.map(r=>`<option value="${r.currency}" ${r.currency===state.currency?'selected':''}>${r.currency}</option>`).join('');
    $('#currency-source').textContent=rateNote();if(state.report) renderReport();
  }
  function billMetric(key,style,label) {
    const id=state.billingData?.headline?.[key];
    return id ? metric(id,style,label) : `<span class="metric missing">not measured — ${escape(state.billingReason || 'Billing evidence is loading.')}</span>`;
  }
  function claimValue(id) {return state.claims.get(id)?.value;}
  function attachBilling() {
    for(const c of list(state.billingData?.claims)) if(c.verified===true && finite(c.value) && list(c.evidence_ids).length) state.claims.set(c.id,c);
  }
  async function loadBilling(report) {
    const key=JSON.stringify([report.id,report.status,report.claims,report.fixes,report.quality_interpretation]);
    if(key===state.billingKey) {attachBilling();return;}
    state.billingKey=key;state.billingData=null;state.billingReason='Billing evidence is loading.';
    for(const id of [...state.claims.keys()])if(id.startsWith('billing/'))state.claims.delete(id);
    renderReport();
    const generation=state.generation;
    try {
      const {data}=await fetchJSON(`/investigations/${encodeURIComponent(report.id)}/billing`);
      if(generation!==state.generation || key!==state.billingKey) return;
      if(data.status!=='checked' || data.id!==report.id) throw new Error(data.reason || 'No checked billing view is available.');
      state.billingData=data;state.billingReason=null;state.tokenizer=data.tokenizer;
      list(data.records).forEach(e=>{if(e.event_id)state.evidence.set(e.event_id,e);});
      attachBilling();renderReport();renderInvestigation();enableViews();
      if(!$('#token-text').value) $('#token-text').value=data.default_text?.native || '';
    } catch(error) {
      if(generation!==state.generation || key!==state.billingKey)return;
      state.billingReason=error.message;renderReport();
    }
  }
  function svg(content,label,view='0 0 640 150',className='ledger-chart') {
    return `<svg class="${className}" viewBox="${view}" role="img" aria-label="${escape(label)}">${content}</svg>`;
  }
  function renderRatios() {
    const tokenizers=ratioTokenizers();
    const max=Math.max(1,...tokenizers.map(t=>claimValue(`ratios/${t}/${state.ratioPart}/native_to_english_ratio`) || 0));
    return `<section class="panel ratio-section"><div class="toolbar"><h2>Same content. Different token bill.</h2><label>Compare <select id="ratio-part">${['system_prompt','user','assistant'].map(p=>`<option value="${p}" ${state.ratioPart===p?'selected':''}>${escape(p==='assistant'?'Answers':parts[p])}</option>`).join('')}</select></label></div>${tokenizers.map(t=>{
      const prefix=`ratios/${t}/${state.ratioPart}/`, value=claimValue(prefix+'native_to_english_ratio'),low=claimValue(prefix+'ci_low'),high=claimValue(prefix+'ci_high');
      const interval=finite(low)&&finite(high)&&high>low ? `<span class="interval">Paired interval ${metric(prefix+'ci_low')} – ${metric(prefix+'ci_high')}</span>` : `<span class="hint">${state.ratioPart==='system_prompt'?'One system prompt per company; no sampling interval.':'No non-zero sampling interval in this report.'}</span>`;
      return `<div class="ratio-row"><div class="ratio-label"><span>${escape(t)}</span>${metric(prefix+'native_to_english_ratio','ratio')}</div>${finite(value)?svg(`<path class="chart-rule" d="M0 8 H640"/><path class="chart-tax" stroke-width="6" d="M0 8 H${value/max*600}"/>`,'Paired native-to-English token ratio','0 0 640 16','ratio-chart'):''}${interval}</div>`;
    }).join('') || '<p class="empty">not measured — no checked paired ratios.</p>'}</section>`;
  }
  function renderComposition() {
    const b=state.billingData,rows=list(b?.composition?.[state.billing]);
    let x=0;
    const chart=svg(rows.map((row,i)=>{const width=(claimValue(row.share)||0)*640;const start=x;x+=width;return `<rect class="part-fill-${i}" x="${start}" y="12" width="${width}" height="24"/>`;}).join(''),'Billed or transcript content-token composition','0 0 640 48');
    return `<section class="panel report-wide"><div class="toolbar"><div><p class="eyebrow">Where does it come from?</p><h2>Paying for the same instructions again.</h2></div><div class="segmented" role="group" aria-label="Token accounting"><button type="button" data-billing="billed" aria-pressed="${state.billing==='billed'}">Billed</button><button type="button" data-billing="transcript" aria-pressed="${state.billing==='transcript'}">Transcript</button></div></div><div class="composition-grid"><div>${rows.length?chart:'<p class="empty">not measured — no checked composition is available.</p>'}${rows.map((row,i)=>`<div class="part-row"><span class="part-name"><i class="swatch part-fill-${i}" aria-hidden="true"></i>${escape(parts[row.part])}</span><span>${metric(row.tokens)} <small>/ conversation</small> · ${metric(row.share,'share')} <small>of ${state.billing==='billed'?'billed':'transcript'} tokens</small></span></div>`).join('')}<p class="hint">${state.billing==='billed'?'Counts content each time it is sent. Prior answers and user turns reappear as input.':'Counts the prompt once per conversation and each transcript turn once. No history replay.'}</p></div><div class="margin-facts"><div><span class="eyebrow">Resend factor</span><strong>${billMetric('resend_factor','ratio')}</strong><p class="hint">System prompts paid per conversation.</p></div><div><span class="eyebrow">Cacheable input share</span><strong>${billMetric('cacheable_share','share')}</strong><p class="hint">Identical system prefix only. A provider cache discount has not been verified.</p></div></div></div></section>`;
  }
  function renderStaircase() {
    const s=state.billingData?.staircase,rows=list(s?.steps),max=Math.max(1,...rows.map(r=>claimValue(r.fields.input)||0));
    const cumulativeMax=Math.max(1,...rows.map(r=>claimValue(r.fields.cumulative_input)||0));
    const points=rows.map((r,i)=>`${470+(claimValue(r.fields.cumulative_input)||0)/cumulativeMax*135},${42+i*38}`).join(' ');
    const drawing=rows.map((r,i)=>{
      let x=85;const y=30+i*38;
      const bars=[['system',0],['replayed_history',2],['new_user',1]].map(([key,part])=>{
        const width=(claimValue(r.fields[key])||0)/max*330,start=x;x+=width;
        return `<rect class="part-fill-${part}" x="${start}" y="${y}" width="${width}" height="24"><title>${escape(key)}: ${number(claimValue(r.fields[key]),0)} tokens</title></rect>`;
      }).join('');
      return `<text x="0" y="${y+16}">Reply ${i+1}</text>${bars}<circle cx="${470+(claimValue(r.fields.cumulative_input)||0)/cumulativeMax*135}" cy="${y+12}" r="3" fill="currentColor"/>`;
    }).join('');
    return `<section class="panel report-wide"><p class="eyebrow">The resend staircase</p><h2>Every reply carries what came before.</h2>${rows.length?`<p class="hint">Recorded conversation <code>${escape(s.chat_id)}</code> · ${escape(s.selection)}.</p><p class="hint">System prompt: same ${metric(rows[0].fields.system)} tokens, paid again. Bars: system prompt · history · new user turn.</p>${svg(`<text x="85" y="14">Input per reply</text><text x="455" y="14">Cumulative billed</text><polyline class="stair-line" points="${points}"/>${drawing}`,'Horizontal input stacks by reply; adjacent line shows cumulative billed input','0 0 660 '+(40+rows.length*38),'ledger-chart resend-chart')}<details><summary>Open each reply’s token receipt</summary><div class="step-receipts">${rows.map(r=>`<div><h3>Reply turn ${escape(r.turn)}</h3><p>Input ${metric(r.fields.input)}</p><p class="hint">System ${metric(r.fields.system)} + history ${metric(r.fields.replayed_history)} + new user ${metric(r.fields.new_user)}</p><p class="hint">Cumulative billed input ${metric(r.fields.cumulative_input)} · transcript so far ${metric(r.fields.transcript_so_far)}</p></div>`).join('')}</div></details>`:'<p class="empty">not measured — no authenticated conversation reconstruction.</p>'}</section>`;
  }
  function dotStrip(variant,title) {
    const prefix=variant==='aa'?'quality/aa/':'quality/',passed=state.claims.get(prefix+'passed'),judged=state.claims.get(prefix+'judged');
    if(!passed || !judged)return `<div class="dot-strip"><h4>${title}</h4><p class="hint">not measured — ${escape(missingReason(prefix+'judged'))}</p></div>`;
    const pairs=state.billingData?.quality?.[variant]?.pairs;
    const content=Array.from({length:20},(_,i)=>{
      const result=pairs?pairs[i]?.same_facts:i<passed.value?true:i<judged.value?false:null;
      const cls=result===true?'dot-pass':result===false?'dot-fail':'dot-empty';
      return `<g><title>${escape(pairs?.[i]?.chat_id || 'Aggregate count')}: ${escape(result===true?'same facts':result===false?'different facts':'not judged')}${pairs?.[i]?.reason?' · '+escape(pairs[i].reason):''}</title><circle class="${cls}" cx="${10+i*20}" cy="14" r="7"/>${result===false?`<path class="dot-cross" d="M${6+i*20} 10 l8 8 m0 -8 l-8 8"/>`:''}</g>`;
    }).join('');
    return `<div class="dot-strip"><h4>${title} ${metric(prefix+'passed')} / ${metric(prefix+'judged')} judged</h4>${svg(`${content}<path class="threshold" d="M360 1 V27"/>`,'Twenty paired checks; reference line at eighteen of twenty','0 0 402 30','quality-chart')}<p class="hint">18-of-20 quality line${pairs?' · dots retain recorded pair order.':' · aggregate counts; individual verdict records unavailable.'}</p></div>`;
  }
  function readableClaim(id='') {
    const speed=id.match(/^speed\/([^/]+)\/(.+)$/);
    if(speed) {
      const metricName={ttft_s:'Time to first visible token',latency_s:'Complete reply time',output_tokens_per_s:'Token throughput'}[speed[1]] || speed[1].replaceAll('_',' ');
      return `${metricName} · ${speed[2].replaceAll('_',' ')}`;
    }
    return id.replace(/^baseline\//,'Baseline / ').replace(/^ratios\//,'Native-to-English ratio / ').replaceAll('_',' ').replaceAll('/',' · ');
  }
  function droppedReason(c) {
    if(String(c.reason).replaceAll("'",'').replaceAll('"','')===c.id) return c.id.startsWith('speed/output_tokens_per_s/') ? 'No supported throughput observation; reasoning usage cannot be separated.' : 'The checker could not recompute this statistic from its source records.';
    return String(c.reason || 'No rejection reason supplied.').replaceAll(c.id,readableClaim(c.id));
  }
  function renderFix(f,index) {
    const label={english_system:'Keep system instructions in English',answer_cap:'Cap answer length',model_switch:'Change the model'}[f.lever] || f.lever;
    const fields=f.fields || {},saving=fields.saving_usd,after=fields.after_monthly_usd;
    const today=claimValue(state.billingData?.headline?.monthly_usd),cost=claimValue(after),extent=Math.max(today||1,cost||0);
    const graph=finite(today)&&finite(cost)?svg(`<path class="chart-rule" d="M0 25 H620"/><rect class="today-bar" x="0" y="5" width="${today/extent*600}" height="12"/><path class="waterfall-link" d="M${today/extent*600} 17 V45 H${cost/extent*600}"/><rect class="${f.group==='would_cost_more'?'tax-bar':'after-bar'}" x="0" y="45" width="${cost/extent*600}" height="14"/>`,'Independent alternative: today monthly cost to this fix after-cost','0 0 640 75','waterfall-chart'):'';
    return `<article class="fix ${f.tested?'tested':'estimate'}"><div class="fix-heading"><div><h3>${escape(label)}${f.tokenizer?` · ${escape(f.tokenizer)}`:''}</h3>${fixStatus(f.tested && state.report.quality_interpretation?.includes('inconclusive') ? 'inconclusive' : f.status)} ${f.tested?tag('Tested experiment','good'):''}${f.model_label?tag(f.model_label.includes('stand-in')?'STAND-IN':f.model_label):''}</div><div class="fix-money">${saving?metric(saving):metric(f.claim_id)}<small>${f.group==='would_cost_more'?'negative saving / month':'saving / month'}${fields.saving_percent?' · '+metric(fields.saving_percent):''}</small></div></div>${graph}<div class="fix-costs"><span>Today ${billMetric('monthly_usd')}</span><span>After this fix ${after?metric(after):'<span class="muted">not measured — '+escape(f.comparison_reason || 'No comparable after-cost.')+'</span>'}</span></div><p>${escape(f.reason || f.basis || 'No reason supplied.')}</p>${f.reason && f.basis?`<p>${escape(f.basis)}</p>`:''}${f.tested?`<div class="quality-line">${dotStrip('aa','A/A floor')}${dotStrip('ab','A/B change')}</div><p class="interpretation">${escape(state.report.quality_interpretation || state.report.quality_status || 'Quality interpretation not supplied.')}</p><p class="hint">${escape(f.model_label || '')} · ${escape(state.report.experiment?.models?.changed || state.report.jobs?.request?.hosted_model || 'Hosted model name not recorded')} · reply-time change: ${metric('speed/latency_s/paired_difference')}</p>`:'<p class="hint">Quality and reply-time change: not tested for this estimate.</p>'}</article>`;
  }
  function renderFixes() {
    const fixes=state.billingData?.fixes || list(state.report.fixes).map(f=>({...f,tested:!!f.experiment_evidence_ids?.length,group:claimValue(f.claim_id)<0?'would_cost_more':'not_measured'}));
    const positives=fixes.filter(f=>f.group!=='would_cost_more'),negatives=fixes.filter(f=>f.group==='would_cost_more');
    return `<section class="panel report-wide"><p class="eyebrow">Which change is worth making?</p><h2>The fix ladder.</h2><p class="rate-note">${escape(rateNote())}</p><p class="hint">Independent alternatives to today. Each after-cost applies one change; the savings are never added together. Dashed entries are estimates.</p>${positives.map(renderFix).join('') || '<p class="empty">No checked saving is available.</p>'}${negatives.length?`<section class="would-cost-more"><h3>Would cost more</h3><p class="hint">These negative savings increase the monthly bill.</p>${negatives.map(renderFix).join('')}</section>`:''}</section>`;
  }
  function renderModels() {
    return `<section class="panel report-wide"><p class="eyebrow">What if the model changes?</p><h2>Compare the same conversations.</h2><p class="hint">Measured tokenizer counts with each verified provider quote. Output quality is not implied by a cheaper tokenizer.</p><div class="model-table-wrap"><table class="model-table"><thead><tr><th scope="col">Tokenizer / provider</th><th scope="col">Cost / conversation</th><th scope="col">Native / English tokens</th><th scope="col">Lone byte or partial character</th></tr></thead><tbody>${list(state.billingData?.models).map(m=>`<tr><th scope="row">${escape(m.tokenizer)}${m.tokenizer===state.billingData.tokenizer?' '+tag('In use','good'):''}<small>${escape(m.price?.provider || 'No verified price')} · ${escape(m.price?.fetched_at || '')}</small></th><td>${m.fields.per_conversation_usd?metric(m.fields.per_conversation_usd):'<span class="muted">no verified price</span>'}</td><td>${metric(m.fields.token_multiplier,'ratio')}</td><td>${m.fields.lone_byte_share?metric(m.fields.lone_byte_share,'share'):'<span class="muted">not measured — '+escape(m.lone_byte_reason || 'No valid fragment measurements.')+'</span>'}</td></tr>`).join('') || '<tr><td colspan="4">not measured — no billing evidence for model comparison.</td></tr>'}</tbody></table></div><p class="rate-note">${escape(rateNote())}</p><button type="button" data-screen="tokens">Inspect the token boundaries →</button></section>`;
  }
  function renderWhatIf() {
    const ready=!!state.billingData?.headline?.monthly_usd;
    const volume=state.scenario.volume ?? claimValue(state.billingData?.headline?.monthly_chats) ?? 100000;
    return `<section class="panel what-if report-wide"><div class="toolbar"><div><p class="eyebrow">What-if, not measured</p><h2>Change the assumptions.</h2></div><button type="button" id="reset-what-if">Reset to recorded values</button></div><p class="hint">Reprices the same measured content counts. It does not generate replies or predict quality, speed or cache discounts.</p><div class="what-if-controls"><label for="what-if-volume">Conversations per month <input id="what-if-volume" type="range" min="1000" max="1000000" step="1000" value="${volume}" ${ready?'':'disabled'}><output for="what-if-volume">${number(volume,0)}</output></label><label for="what-if-input">Input price multiplier <input id="what-if-input" type="range" min="0.1" max="3" step="0.1" value="${state.scenario.input}" ${ready?'':'disabled'}><output for="what-if-input">${number(state.scenario.input)}×</output></label><label for="what-if-output">Output price multiplier <input id="what-if-output" type="range" min="0.1" max="3" step="0.1" value="${state.scenario.output}" ${ready?'':'disabled'}><output for="what-if-output">${number(state.scenario.output)}×</output></label></div><div id="what-if-result"></div><p class="rate-note">${escape(rateNote())}</p></section>`;
  }
  function updateWhatIf() {
    const b=state.billingData;if(!b?.headline?.monthly_usd){$('#what-if-result').innerHTML='<p class="empty">not measured — checked token counts and prices are required.</p>';return;}
    const h=b.headline,volume=state.scenario.volume ?? claimValue(h.monthly_chats),input=claimValue(h.input_price_usd)*state.scenario.input,output=claimValue(h.output_price_usd)*state.scenario.output;
    const cost=volume*(claimValue(h.input_per_conversation)*input+claimValue(h.output_per_conversation)*output)/1000000;
    const original=claimValue(h.monthly_usd);
    state.scenarioReceipt={status:'what-if, not measured',formula:'volume × (measured input per conversation × assumed input USD price + measured output per conversation × assumed output USD price) / 1,000,000',inputs:{volume,input_tokens_per_conversation:claimValue(h.input_per_conversation),output_tokens_per_conversation:claimValue(h.output_per_conversation),assumed_input_price_usd:input,assumed_output_price_usd:output},monthly_usd:cost,recorded_monthly_usd:original,source_claims:h,conversion:rate()};
    $('#what-if-result').innerHTML=`<div class="scenario-total"><span>What-if monthly cost</span><strong><button type="button" class="metric" data-scenario-record>${escape(money(cost))}</button></strong><span>Change from recorded cost ${escape(money(cost-original))}</span></div><p class="hint">${number(volume,0)} conversations × (measured input / conversation × ${escape(money(input))} + measured output / conversation × ${escape(money(output))}) / 1,000,000.</p><div class="scenario-savings">${list(b.fixes).filter(f=>f.fields.after_monthly_usd).map(f=>{
      const fields=f.fields,keys=['after_input_per_conversation','after_output_per_conversation','after_input_price_usd','after_output_price_usd'];
      if(!keys.every(k=>finite(claimValue(fields[k])))) return `<p>${escape(f.lever)} saving: not measured — no checked input/output split for this alternative.</p>`;
      const after=volume*(claimValue(fields.after_input_per_conversation)*claimValue(fields.after_input_price_usd)*state.scenario.input+claimValue(fields.after_output_per_conversation)*claimValue(fields.after_output_price_usd)*state.scenario.output)/1000000;
      return `<p>${escape(f.tokenizer || f.lever)} · what-if saving <strong>${escape(money(cost-after))}</strong></p>`;
    }).join('')}</div>`;
  }
  function renderSpeed() {
    const model=state.report.experiment?.models || {},label=state.report.experiment?.model_label || 'Hosting relationship not supplied';
    return `<section class="panel"><p class="eyebrow">What happens to reply time?</p><div class="toolbar"><h2>Timing, with its limits.</h2>${tag(state.report.speed_status || 'not measured','warm')}</div>${['ttft_s','latency_s'].map(key=>`<h3>${key==='ttft_s'?'First visible token':'Complete reply'}</h3><div class="speed-row">${['original','changed'].map(side=>`<div><p class="hint">${side==='original'?'Original':'Changed'} · <strong>${escape(model[side] || state.report.jobs?.request?.hosted_model || 'Model name not recorded')}</strong> · ${escape(label)}</p><p class="speed-number">${metric(`speed/${key}/${side}_median`)}</p><p class="hint">Observed spread ${metric(`speed/${key}/${side}_min`)} – ${metric(`speed/${key}/${side}_max`)}</p></div>`).join('')}</div>`).join('')}<p class="hint">Throughput: ${escape(state.report.throughput_status || 'not measured')}</p></section>`;
  }
  function renderMarkovian() {
    const extent=Math.max(1,...list(state.report.markovian_runs).map(run=>Math.abs(claimValue(run.claim_prefix+'net_tokens') || 0)));
    return `<section class="panel"><p class="eyebrow">The investigation’s own token ledger</p><h2>Compression can cost tokens, too.</h2>${list(state.report.markovian_runs).map(run=>{
      const id=run.claim_prefix+'net_tokens',value=claimValue(id),width=Math.abs(value || 0)/extent*280;
      return `<div class="markovian-row"><span>${escape(run.token_label)} · recorded run <code>${escape(run.claim_prefix)}</code></span><span>${metric(id,'signed')} · ${metric(run.claim_prefix+'net_percent','signed')}</span>${finite(value)?svg(`<path class="chart-rule" d="M320 0 V36 M10 18 H630"/><rect class="${value<0?'tax-bar':'after-bar'}" x="${value<0?320-width:320}" y="${value<0?19:4}" width="${width}" height="13"/>`,'Signed compression accounting: negative is below zero; positive is above','0 0 640 36','signed-chart'):''}</div>`;
    }).join('') || '<p class="empty">not measured — no compression runs supplied.</p>'}<p class="hint">Reference history-replay counterfactual, not an independently measured second execution.</p></section>`;
  }
  function renderReport() {
    const r=state.report;if(!r)return;attachBilling();
    $('#report').dataset.reportId=r.id;$('#report').dataset.billingStatus=state.billingData?'checked':state.billingReason && state.billingReason!=='Billing evidence is loading.'?'not measured':'loading';
    const language={te:'Telugu',hi:'Hindi'}[state.billingData?.language || state.companies.find(c=>c.company===r.company)?.language] || 'native-language';
    const lead=state.billingData?.headline?.system_cost_share || (state.tokenizer?`baseline/${state.tokenizer}/system_prompt_cost_share`:null);
    const headline=state.claims.has(lead)?`Your ${escape(language)} system prompt is ${metric(lead,'share')} of the money: it is sent again with every reply.`:escape(r.top_finding || 'The checked bill is not available yet.');
    const priceNote=claimValue(state.billingData?.headline?.output_price_usd)>claimValue(state.billingData?.headline?.input_price_usd)?' Answers cost more per token at this quoted price.':'';
    const fields=[['monthly_usd','Monthly cost'],['per_1000_conversations_usd','Per 1,000 conversations'],['per_reply_usd','Per reply'],['language_tax_usd','Language tax / month']];
    $('#report-content').innerHTML=`<section class="report-hero"><div class="report-meta"><p class="eyebrow">${escape(names[r.company] || r.company || 'Billing report')} / ${escape(state.billingData?.tokenizer || state.tokenizer || 'Tokenizer not supplied')}</p>${tag(r.status || 'Status not supplied')}${tag(state.mode==='saved'?'Recorded verdicts':'Verified source view','good')}</div><h1 id="report-title">${headline}</h1><p class="hint">${escape(r.partial_reason || 'Quoted provider content-cost scenario. Native review remains pending.')}${escape(priceNote)}</p><p class="rate-note">Base quote: ${escape(r.quoted_price?.provider || 'provider not recorded')} · fetched ${escape(r.quoted_price?.fetched_at || 'not supplied')}</p><div class="headline-strip">${fields.map(([key,label])=>`<div class="headline-cell ${key==='language_tax_usd'?'tax-cell':''}"><span>${label}</span><strong>${billMetric(key)}</strong>${key==='language_tax_usd'?`<small>${billMetric('cost_multiplier','cost-ratio')} what the same content costs in English</small>`:''}</div>`).join('')}<div class="headline-cell"><span>Billed tokens / English</span><strong>${billMetric('token_multiplier','ratio')}</strong>${state.billingData?.headline?.token_multiplier?svg(`<path class="chart-tax" stroke-width="4" d="M2 6 H150"/><path class="chart-evidence" stroke-width="4" d="M2 17 H${2+148/Math.max(1,claimValue(state.billingData.headline.token_multiplier))}"/>`,'Native billed token ratio compared with English at one','0 0 160 24','multiplier-chart'):''}<small>English ×1.0 · same content</small></div></div><p class="rate-note">${escape(rateNote())}</p><div class="actions"><button type="button" id="download-report">Download report JSON</button><button type="button" data-screen="investigation">Open case file →</button></div><p class="hint">Run <code>${escape(r.id)}</code></p></section>${renderComposition()}${renderStaircase()}${renderFixes()}${renderModels()}${renderWhatIf()}<div class="report-grid">${renderSpeed()}${renderRatios()}</div><section class="panel report-wide trust-line"><p class="eyebrow">Trust and review</p><h2>What survived the check?</h2><p>Recorded claims checked ${metric('billing/trust/reported_checked')} · claims dropped ${metric('billing/trust/reported_dropped')}</p><p>${tag('Native review: '+(r.review_status || 'not supplied'))}</p><p class="hint">Each displayed figure opens its receipt. Dropped claims retain their reason and no value.</p><ul class="reason-list">${list(r.dropped_claims).map((c,i)=>`<li><button type="button" class="metric" data-dropped="${i}">${escape(readableClaim(c.id))}</button><br>${escape(droppedReason(c))}</li>`).join('') || '<li>No dropped claims listed.</li>'}</ul></section>${renderMarkovian()}<details class="limitations"><summary>Read the accounting limits</summary><ul class="reason-list">${[...list(r.limitations),...list(state.billingData?.limitations)].map(item=>`<li>${escape(item)}</li>`).join('')}</ul></details><section class="panel"><h2>Claim ledger</h2><details><summary>Browse every recorded and checked claim</summary><div class="claim-list">${[...state.claims.values()].map(c=>`<div><span>${escape(readableClaim(c.id))}</span>${metric(c.id)}</div>`).join('')}</div></details></section>`;
    updateWhatIf();
    window.dispatchEvent(new Event('polytoken:report'));
  }
  async function inspectTokens() {
    const text=$('#token-text').value;if(!text.trim())return;
    const generation=state.generation,sequence=++state.tokenSequence;
    const models=state.billingData?.models || baselineTokenizers().map(tokenizer=>({tokenizer}));
    $('#token-status').textContent='Reading local tokenizer files. No model requests or downloads.';
    $('#token-rows').innerHTML='';state.tokenResults=new Map();
    for(const model of models) {
      try {
        const {data}=await fetchJSON('/tokens?'+new URLSearchParams({text,tokenizer:model.tokenizer}));
        if(generation!==state.generation || sequence!==state.tokenSequence)return;
        state.tokenResults.set(model.tokenizer,data);
      }catch(error){state.tokenResults.set(model.tokenizer,{ok:false,reason:error.message});}
      renderTokens();
    }
    if(generation===state.generation && sequence===state.tokenSequence) $('#token-status').textContent='Local inspection complete. Hatched cells show UTF-8 hex bytes grouped under their source character. Original token IDs and text remain in the receipt.';
  }
  function tokenCells(row) {
    const groups=[];
    for(const piece of list(row.pieces)) {
      const previous=groups.at(-1);
      if(previous && piece.kind!=='gap' && piece.tokenizer_start<previous.end) {
        previous.pieces.push(piece);previous.end=Math.max(previous.end,piece.tokenizer_end);
      } else groups.push({start:piece.tokenizer_start ?? piece.start,end:piece.tokenizer_end ?? piece.end,pieces:[piece]});
    }
    const cell=p=>`<span class="token-piece ${p.fragment?'fragment':''} ${p.kind==='gap'?'gap':''}" title="${escape('Token ID: '+p.id+'; source span: '+p.tokenizer_start+'–'+p.tokenizer_end)}">${escape(p.fragment?(p.byte_hex || 'byte unavailable'):(p.text || p.raw))}</span>`;
    return groups.map(g=>g.pieces.some(p=>p.fragment)?`<span class="byte-group"><span class="byte-character">${escape(Array.from(row.text).slice(g.start,g.end).join(''))}</span><span class="byte-cells">${g.pieces.map(cell).join('')}</span></span>`:g.pieces.map(cell).join('')).join('');
  }
  function renderTokens() {
    $('#token-rows').innerHTML=[...state.tokenResults.entries()].map(([spec,row])=>`<section class="token-row"><div class="toolbar"><h2>${escape(spec)}</h2>${tag(row.ok?'Measured locally':'Not measured',row.ok?'good':'warm')}</div>${row.ok?`<div class="token-pieces" lang="${escape(state.billingData?.language || 'und')}">${tokenCells(row)}</div><div class="token-stats"><button type="button" class="metric" data-token-record="${escape(spec)}">${number(row.count,0)} tokens</button><button type="button" class="metric" data-token-record="${escape(spec)}">${number(row.tokens_per_word)} tokens / whitespace word</button><button type="button" class="metric" data-token-record="${escape(spec)}">${finite(row.lone_byte_share)?new Intl.NumberFormat('en-IN',{style:'percent',maximumFractionDigits:1}).format(row.lone_byte_share):'not measured'} lone byte / partial character</button></div><p class="hint">${escape(row.boundary_note || '')}</p>`:`<p class="muted">${escape(row.reason || 'Local tokenizer unavailable.')}</p>`}</section>`).join('');
  }
  function openDropped(index) {
    const row=list(state.report?.dropped_claims)[index];if(!row)return;state.back='report';state.evidenceView++;
    $('#back-evidence').textContent='← Back to report';$('#evidence-content').innerHTML=`<section class="panel"><p class="eyebrow">Dropped claim / receipt</p><h2>${escape(readableClaim(row.id))}</h2>${tag('Dropped','failed')}<p>${escape(droppedReason(row))}</p><h3>Original checker record</h3><pre>${escape(JSON.stringify(row,null,2))}</pre><p class="hint">Run ${escape(state.runId)}</p></section>`;show('evidence');
  }
  function openTokenRecord(spec) {
    const row=state.tokenResults.get(spec);if(!row)return;state.back='tokens';state.evidenceView++;
    $('#back-evidence').textContent='← Back to token strip';$('#evidence-content').innerHTML=`<section class="panel"><p class="eyebrow">Local measurement / receipt</p><h2>${escape(spec)}</h2>${tag('Verified encoding','good')}<p>IDs are checked against a second encoding; display pieces are checked to reproduce the complete input.</p><pre>${escape(JSON.stringify(row,null,2))}</pre></section>`;show('evidence');
  }
  function formula(claim) {
    const id=claim.id;
    if(claim.recompute?.formula)return claim.recompute.formula;
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
    $('#evidence-content').innerHTML=`<section class="panel"><p class="eyebrow">${claim?'Checked claim':'Recorded observation'}</p><h2>${escape(claim?.text || evidenceId)}</h2>${claim?`<p class="lead-metric">${escape(format(claim,claim.id.endsWith('_share')?'share':undefined))}</p>${['USD','INR'].includes(claim.unit)?`<p class="rate-note">${escape(rateNote())}</p>`:''}<code>${escape(claim.id)}</code><div class="formula">${escape(formula(claim))}</div><details><summary>Exact checked claim</summary><pre>${escape(JSON.stringify(claim,null,2))}</pre></details><h3>Formula inputs</h3><pre>${escape(JSON.stringify(claim.recompute || {reason:'No recipe supplied'},null,2))}</pre>`:''}<p class="hint">Report / investigation run: <code>${escape(state.runId || 'not supplied')}</code></p></section><div id="raw-evidence"><p class="empty">Loading recorded evidence…</p></div>`;
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
      const compressed=file.name.endsWith('.gz');
      const text=compressed?await new Response(file.stream().pipeThrough(new DecompressionStream('gzip'))).text():await file.text();
      if(file.name.replace(/\.gz$/,'').endsWith('.jsonl')) records.push(...text.split(/\r?\n/).filter(line=>line.trim()).map(line=>JSON.parse(line)));
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
    notice();show('report');window.dispatchEvent(new Event('polytoken:import'));
  }
  document.addEventListener('click',event=>{
    const button=event.target.closest('button');
    if(!button || button.disabled) return;
    if(button.dataset.screen) {show(button.dataset.screen);if(button.dataset.screen==='tokens' && !state.tokenResults.size)inspectTokens();}
    else if(button.dataset.company) {state.company=button.dataset.company;renderCompanies();}
    else if(button.id==='currency-source') {state.back=state.screen;state.evidenceView++;$('#back-evidence').textContent='← Back';$('#evidence-content').innerHTML=`<section class="panel"><p class="eyebrow">Display currency / receipt</p><h2>${escape(state.currency)}</h2><div class="formula">Canonical USD amount × sourced units per USD</div><pre>${escape(JSON.stringify(rate(),null,2))}</pre></section>`;show('evidence');}
    else if(button.hasAttribute('data-scenario-record')) {state.back='report';state.evidenceView++;$('#back-evidence').textContent='← Back to report';$('#evidence-content').innerHTML=`<section class="panel"><p class="eyebrow">What-if / receipt</p><h2>Scenario, not a measurement</h2><pre>${escape(JSON.stringify(state.scenarioReceipt,null,2))}</pre><div class="actions">${['input_per_conversation','output_per_conversation','input_price_usd','output_price_usd','monthly_chats'].map(key=>`<button type="button" data-claim="${escape(state.billingData?.headline?.[key])}">${escape(key.replaceAll('_',' '))} source</button>`).join('')}</div></section>`;show('evidence');}
    else if(button.hasAttribute('data-dropped')) openDropped(Number(button.dataset.dropped));
    else if(button.dataset.tokenRecord) openTokenRecord(button.dataset.tokenRecord);
    else if(button.id==='reset-what-if'){state.scenario={volume:null,input:1,output:1};renderReport();$('#reset-what-if').focus();}
    else if(button.id==='token-native' || button.id==='token-english') {$('#token-text').value=state.billingData?.default_text?.[button.id==='token-native'?'native':'english'] || '';inspectTokens();}
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
  document.addEventListener('input',event=>{
    if(event.target.id.startsWith('what-if-')) {
      const key={"what-if-volume":'volume',"what-if-input":'input',"what-if-output":'output'}[event.target.id];
      if(key) {state.scenario[key]=Number(event.target.value);event.target.nextElementSibling.textContent=number(state.scenario[key])+(key==='volume'?'':'×');updateWhatIf();}
    }
  });
  $('#token-form').addEventListener('submit',event=>{event.preventDefault();inspectTokens();});
  document.addEventListener('change',event=>{
    if(event.target.id==='currency') {state.currency=event.target.value;try{localStorage.setItem('polytoken.currency',state.currency);}catch{}$('#currency-source').textContent=rateNote();if(state.report)renderReport();}
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
    finally{state.posting=false;$('#investigate').disabled=!state.company || state.demo;}
  });
  window.addEventListener('beforeunload',stopStream);
  window.polyConsole={state,show,resetRun,setReport,renderInvestigation,renderReport,fetchJSON,metric,format,escape,notice,inspectTokens,connectEvents,stopStream,openEvidence,enableViews};
  loadCompanies();loadCurrencies();
})();
