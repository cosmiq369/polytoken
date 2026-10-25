/* Model-fit views render checked claim values; ranking and decisions come from replayed evidence. */
'use strict';
(() => {
 const a=window.polyConsole,s=a.state,esc=a.escape,$=q=>document.querySelector(q);
 const names={samudra:'Samudra Telecom',swara:'Swara Care',raitu:'Raitu Mitra',paisa:'Paisa Saathi'};
 const labels={native_script:'Native script',romanized:'Romanized',code_mixed:'Code-mixed',unknown:'Unclassified'};
 let comparisons=[];
 const short=model=>String(model || '').split('/').at(-1);
 const checked=(claims,id)=>claims.find(c=>c.id===id && c.verified===true && Number.isFinite(c.value) && c.evidence_ids?.length);
 const value=(claims,id)=>checked(claims,id)?.value;
 function metric(claims,id,format='number',run=null){
  const cl=checked(claims,id);if(!cl)return '<span class="muted">Not measured</span>';
  const text=format==='share'?(cl.value*100).toFixed(1)+'%':format==='usd'?a.money(cl.value):format==='ratio'?cl.value.toFixed(2)+'×':new Intl.NumberFormat('en-IN',{maximumFractionDigits:2}).format(cl.value);
  return `<button class="metric fit-metric" ${run?`data-fit-evidence="${esc(run)}" data-fit-claim="${esc(id)}"`:`data-claim="${esc(id)}"`} title="Open checked source and formula">${esc(text)}</button>`;
 }
 function derived(claims,ids,text,run){
  if(!ids.every(id=>checked(claims,id)))return '<span class="muted">Not measured</span>';
  return `<button class="metric fit-metric" ${run?`data-fit-evidence="${esc(run)}" data-fit-claim="${esc(ids[0])}"`:`data-claim="${esc(ids[0])}"`} title="${esc(ids.join(' · '))}">${esc(text)}</button>`;
 }
 function monthly(claims,row,run){
  const ids=[row.cost_claim,'profile/monthly_conversations'];
  return derived(claims,ids,a.money(value(claims,ids[0])*value(claims,ids[1])/1000),run);
 }
 function multiple(claims,row,best,run){
  const n=value(claims,row.cost_claim),d=value(claims,best.cost_claim);
  return d>0?derived(claims,[row.cost_claim,best.cost_claim],(n/d).toFixed(2)+'×',run):'Not measured';
 }
 function headline(fit,claims){
  const r=fit.lowest_unit_price,b=fit.cost_candidate;
  if(!r || !b || !checked(claims,r.ratio_claim) || !checked(claims,r.cost_claim) || !checked(claims,b.cost_claim))return '';
  const script=(fit.profile.language==='te'?'Telugu':'Hindi')+' '+labels[fit.profile.dominant_script].toLowerCase();
  return `<p class="fit-insight">${r.model!==b.model?'Cheapest per token is not cheapest for your users:':'The lowest unit price also wins on this measured workload:'} ${esc(short(r.model))} quotes the lowest price but needs ${metric(claims,r.ratio_claim,'ratio')} English tokens on your ${esc(script)} traffic. ${multiple(claims,r,b)} the best fit’s content cost.</p><p class="hint">Unit price compares equal input/output token baskets. <a href="${esc(r.source_url)}" target="_blank" rel="noreferrer">Checked quote source ↗</a></p>`;
 }
 function mix(claims,run){
  return `<div class="script-mixture" aria-label="Measured user-turn script mix">${Object.keys(labels).map(k=>{const v=value(claims,'profile/'+k+'_share');return Number.isFinite(v)&&v>0?`<span class="mix-${k}" style="flex-grow:${v}" title="${labels[k]} ${(100*v).toFixed(1)}%"></span>`:'';}).join('')}</div><div class="mix-key">${Object.keys(labels).filter(k=>value(claims,'profile/'+k+'_share')>0).map(k=>`<span><i class="mix-${k}" aria-hidden="true"></i>${labels[k]} ${metric(claims,'profile/'+k+'_share','share',run)}</span>`).join('')}</div>`;
 }
 function recommendation(fit,claims,run,compact=false){
  const r=compact?fit.cost_candidate:(fit.recommendation || fit.cost_candidate);
  if(!r)return '<p>No verified price is available. Compare tokenizer fit below.</p>';
  return `<div class="fit-choice"><p class="eyebrow">${fit.recommendation?'Cost recommendation · quality to verify':'Cost candidate · voice latency unverified'}</p><h${compact?'3':'2'}>${esc(short(r.model))}</h${compact?'3':'2'}><p class="fit-price">${monthly(claims,r,run)} <span>/ month at ${metric(claims,'profile/monthly_conversations','number',run)} conversations</span></p><p class="hint">${metric(claims,r.cost_claim,'usd',run)} / 1,000 conversations · ${esc(r.provider)}</p><p class="fit-status">${esc(fit.status)}</p>${compact?'':`<p>${esc(r.reason)}</p><p>On this workload: ${metric(claims,r.ratio_claim,'ratio',run)} the billed tokens of its English pair.</p><p class="hint">Quote fetched ${esc(r.fetched_at)} · <a href="${esc(r.source_url)}" target="_blank" rel="noreferrer">Price source ↗</a></p>`}</div>`;
 }
 function renderCompanies(){
  $('#company-fit-grid').innerHTML=comparisons.length?comparisons.map(r=>{const f=r.model_fit;return `<article class="fit-company" data-fit-company="${esc(r.company)}"><div class="fit-company-heading"><p class="eyebrow">${esc(f.profile.channel)} · ${f.profile.language==='te'?'Telugu':'Hindi'}</p><h2>${esc(names[r.company] || f.profile.display_name || r.company)}</h2><p>${esc(f.profile.role)}</p></div>${mix(r.claims,r.id)}<div class="fit-shape"><span>${metric(r.claims,'profile/turns_per_conversation','number',r.id)}<small>turns / conversation</small></span><span>${metric(r.claims,'profile/answer_billed_share','share',r.id)}<small>new answer token share</small></span></div><div class="fit-cost-pair"><div>${recommendation(f,r.claims,r.id,true)}</div><div><p class="eyebrow">Cheapest per token</p><h3>${esc(short(f.lowest_unit_price?.model))}</h3>${f.lowest_unit_price?monthly(r.claims,f.lowest_unit_price,r.id):'Not measured'}<p class="hint">/ month · ${f.lowest_unit_price?multiple(r.claims,f.lowest_unit_price,f.cost_candidate,r.id):''} the best fit</p><p class="hint">${f.lowest_unit_price?metric(r.claims,f.lowest_unit_price.cost_claim,'usd',r.id):''} / 1,000 conversations</p></div></div><p class="hint">${esc(a.rateNote())}</p><button class="fit-open" data-fit-open="${esc(r.id)}">Inspect model fit ↗</button></article>`;}).join(''):'<p class="panel">No checked model-fit runs are saved yet. Start an investigation below or import a report with its evidence.</p>';
 }
 function render(){
  const fit=s.report?.model_fit,claims=[...s.claims.values()];
  if(!fit || !fit.claim_ids?.every(id=>checked(claims,id))){$('#model-fit-content').innerHTML='<p class="eyebrow">Model fit</p><h1 id="model-fit-title">Waiting for checked workload evidence</h1><p>Open a completed model-fit run, or follow Activity while this investigation runs. Older archives do not contain the new profile and model ranking.</p>';return;}
  const f=fit.profile;
  const alternatives=[['Runner-up',fit.runner_up],['Avoid tokenizer penalty',fit.avoid]];
  $('#model-fit-content').innerHTML=`<div class="fit-header"><div><p class="eyebrow">${esc(names[f.company] || f.display_name || f.company)} · ${esc(f.channel)} · pending native review</p><h1 id="model-fit-title">The model that fits this workload</h1><p>${esc(f.role)}</p>${headline(fit,claims)}<p class="hint">${esc(a.rateNote())}</p></div><span class="tag">Checked evidence · ${f.company.startsWith('upload_')?'uploaded workload':'fictional company'}</span></div><div class="fit-main-grid"><section class="panel workload-profile"><p class="eyebrow">What users send</p><h2>The workload, in its own words.</h2>${mix(claims)}<div class="fit-profile-stats"><div><span>Sample conversations</span>${metric(claims,'profile/conversations')}</div><div><span>Turns per conversation</span>${metric(claims,'profile/turns_per_conversation')}</div><div><span>New answer token share</span>${metric(claims,'profile/answer_billed_share','share')}</div><div><span>Recognized English terms</span>${metric(claims,'profile/english_terms_share','share')}</div><div><span>Monthly conversations</span>${metric(claims,'profile/monthly_conversations')}</div><div><span>Full-reply target</span><span>${metric(claims,'profile/latency_target_s')} seconds</span></div></div><p class="hint">Current model: ${esc(f.current_model)}.</p><details><summary>How the profile is measured</summary><p>${esc(f.classifier)}</p><p>${esc(f.answer_share_basis)}</p></details></section><section class="panel fit-recommendation">${recommendation(fit,claims)}</section></div><section class="panel fit-ranking"><p class="eyebrow">Same conversations · each model's measured tokenizer</p><h2>Ranked by content cost</h2><p class="hint">Cheapest verified provider quote for each model. Monthly = checked cost per 1,000 × checked company volume / 1,000. × best fit = checked model cost / lowest checked cost. Content-cost estimates exclude templates and unpublished cache discounts. Quality: verify on your sample.</p><div class="model-table-wrap"><table><thead><tr><th>Model / provider</th><th>${esc(s.currency)} / month at volume</th><th>× the best fit</th><th>Billed tokens / English</th><th>Latency fit</th></tr></thead><tbody>${fit.models.map((m,i)=>`<tr><th><span class="rank-number">${i+1}</span>${esc(short(m.model))}<small>${esc(m.provider)}</small></th><td>${monthly(claims,m)}<small>${metric(claims,m.cost_claim,'usd')} / 1,000 conversations</small></td><td>${multiple(claims,m,fit.cost_candidate)}</td><td>${metric(claims,m.ratio_claim,'ratio')}</td><td><span class="tag ${m.latency==='unverified'?'':'good'}">${esc(m.latency)}</span>${m.latency_claim?metric(claims,m.latency_claim):''}</td></tr>`).join('')}</tbody></table></div><details><summary>All verified provider quotes</summary><ul>${fit.provider_quotes.map(m=>`<li>${esc(m.model)} · ${esc(m.provider)} · ${monthly(claims,m)} / month · ${metric(claims,m.cost_claim,'usd')} / 1,000 conversations · <a href="${esc(m.source_url)}" target="_blank" rel="noreferrer">dated source</a></li>`).join('')}</ul></details></section><div class="fit-alternatives">${alternatives.map(([label,r])=>r?`<section class="panel"><p class="eyebrow">${label}</p><h2>${esc(short(r.model))}</h2><p>${monthly(claims,r)} / month · ${multiple(claims,r,fit.cost_candidate)} the best fit</p><p>${metric(claims,r.cost_claim,'usd')} / 1,000 conversations · ${metric(claims,r.ratio_claim,'ratio')} tokens / English</p><p>${esc(r.reason)}</p><p class="hint">Quality: ${esc(r.quality)} · latency: ${esc(r.latency)}</p></section>`:'').join('')}</div><section class="panel"><h2>Tokenizer fit only</h2><p>No verified price is available for these measured families.</p><div class="fit-tokenizers">${fit.tokenizer_fit_only.map(r=>`<div><strong>${esc(short(r.tokenizer))}</strong>${metric(claims,r.ratio_claim,'ratio')}<small>tokens / English</small></div>`).join('')}</div></section><section class="panel"><h2>What still needs testing</h2><p>${esc(fit.serving_note)}</p><ul>${fit.limitations.map(x=>`<li>${esc(x)}</li>`).join('')}</ul><p>Further levers: answer length, history length and caching eligibility. Savings and quality must be tested before deployment.</p></section>`;
 }
 async function openCompleted(id,claim){
  a.notice('Loading checked model fit…');
  try{const {data}=await a.fetchJSON(`/investigations/${encodeURIComponent(id)}/replay`);a.loadCompleted(data);a.notice();if(claim)a.openEvidence(claim);}
  catch(error){a.notice(error.message);}
 }
 document.addEventListener('click',event=>{const b=event.target.closest('button');if(!b)return;if(b.dataset.fitOpen)openCompleted(b.dataset.fitOpen);if(b.dataset.fitEvidence)openCompleted(b.dataset.fitEvidence,b.dataset.fitClaim);if(b.dataset.consoleTab==='fit')render();});
 window.addEventListener('polytoken:currency',()=>{render();renderCompanies();});
 window.addEventListener('polytoken:report',render);window.addEventListener('polytoken:reset',render);
 window.addEventListener('polytoken:screen',e=>{if(e.detail==='model-fit')render();});
 a.fetchJSON('/model-fits').then(({data})=>{comparisons=Array.isArray(data)?data:[];renderCompanies();}).catch(()=>{$('#company-fit-grid').innerHTML='<p class="panel">Checked comparison unavailable. Open a saved run to inspect its evidence.</p>';});
 render();
})();
