/* Structured launches and a bounded read-only question surface. */
'use strict';
(()=>{
 const a=window.polyConsole,s=a.state,$=q=>document.querySelector(q),esc=a.escape;
 const names={samudra:'Samudra Telecom',swara:'Swara Care',raitu:'Raitu Mitra',paisa:'Paisa Saathi'};
 const industries={samudra:'Telecom customer service',swara:'Healthcare support',raitu:'Agriculture support',paisa:'Financial services support'};
 const suggestions=['Why this model?','Why not the cheapest model?','How does script mix affect cost?','Is quality verified?','Where does this number come from?'];
 const scope='Ask about saved model choices, quoted costs at another volume, company comparisons, script mix, quality, evidence, assumptions or verification. No new research or model calls.';
 let options=null,runs=[],samples=[],answerVersion=0;
 const answers=new Map();
 function sourceChanged(prefill=true){
  const sample=$('#launch-source').value,upload=sample==='upload';$('#upload-fields').hidden=!upload;$('#sample-file').required=upload;
  if(prefill && !upload){
   const c=options?.samples.find(c=>c.company===sample) || s.companies.find(c=>c.company===sample);
   $('#company-name').value=names[sample];$('#industry').value=industries[sample];$('#language').value=c?.language || (['samudra','raitu'].includes(sample)?'te':'hi');$('#channel').value=c?.channel || (['swara','raitu'].includes(sample)?'voice':'chat');if(c?.monthly_chats)$('#monthly-chats').value=c.monthly_chats;if(c?.latency_target_s)$('#latency-target').value=c.latency_target_s;
  }
  $('#launcher-mode').textContent=options?.demo?(upload?'Live mode needed. Uploaded data cannot run in demo mode.':'Replay of a saved run. Uses its original company, models and volume; edits above do not change the saved findings.'):'Live mode: new measurements and a bounded investigation require configured Zetaris, cached tokenizers and NVIDIA. Full uploaded-data integration is not yet verified.';
 }
 $('#launch-source').addEventListener('change',()=>sourceChanged());
 document.addEventListener('click',e=>{const b=e.target.closest('[data-company]');if(b){$('#launch-source').value=b.dataset.company;sourceChanged();a.show('launcher');}});
 $('#ask-form').addEventListener('submit',async e=>{
  e.preventDefault();if(s.posting || !options)return;
  const error=$('#launcher-error');error.hidden=true;
  try{
   const sample=$('#launch-source').value;
   const launch={name:$('#company-name').value.trim(),industry:$('#industry').value.trim(),channel:$('#channel').value,language:$('#language').value,monthly_chats:Number($('#monthly-chats').value),currency:$('#launch-currency').value,latency_target_s:Number($('#latency-target').value),system_prompt:$('#system-prompt').value,candidate_models:[...document.querySelectorAll('#candidate-models input:checked')].map(el=>el.value)};
   if(!launch.candidate_models.length)throw new Error('Select at least one candidate model.');
   if(sample==='upload'){
    if(options.demo)throw new Error('Live mode needed. Uploaded data cannot run in demo mode.');
    const file=$('#sample-file').files[0];if(!file)throw new Error('Choose a JSONL or CSV file.');
    if(file.size>options.max_bytes)throw new Error('Sample exceeds the one MiB limit.');
    if(!/\.(jsonl|csv)$/i.test(file.name))throw new Error('Use a .jsonl or .csv file.');
    launch.filename=file.name;launch.content=await file.text();
   }else launch.sample=sample;
   s.posting=true;$('#investigate').disabled=true;
   const {data}=await a.fetchJSON('/investigations',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({company:sample==='upload'?'new':sample,launch})});
   if(typeof data.id!=='string')throw new Error('No investigation identifier was returned.');
   s.company=sample==='upload'?launch.name:sample;s.launchName=launch.name;
   $('#currency').value=launch.currency;$('#currency').dispatchEvent(new Event('change',{bubbles:true}));
   await a.openLaunched(data);
  }catch(ex){error.textContent=ex.message;error.hidden=false;a.notice('Could not start the investigation: '+ex.message);}
  finally{s.posting=false;$('#investigate').disabled=false;}
 });
 function askPanel(id,companyPage){
  const target=$('#'+id);
  target.innerHTML=`<p class="eyebrow">Read-only / saved evidence</p><h2>Ask the evidence</h2>${companyPage?`<div class="ask-context"><label>Run to ask about<select class="ask-run"></select></label><label>Compare with<select class="ask-compare"></select></label></div>`:''}<div class="ask-chips">${suggestions.map(q=>`<button type="button" data-question="${esc(q)}">${esc(q)}</button>`).join('')}</div><form><label>Question<input class="evidence-question" maxlength="1000" required placeholder="Why not the cheapest model?"></label><button type="submit">Ask evidence</button></form><p class="hint">${scope}</p><div class="ask-answer" role="status"></div>`;
  target.querySelectorAll('[data-question]').forEach(b=>b.addEventListener('click',()=>{target.querySelector('input').value=b.dataset.question;target.querySelector('form').requestSubmit();}));
  target.querySelector('form').addEventListener('submit',async e=>{
   e.preventDefault();const version=++answerVersion,answer=target.querySelector('.ask-answer'),id=companyPage?target.querySelector('.ask-run').value:s.runId;
   if(!id){answer.textContent='Open a saved model-fit run first.';return;}
   const question=target.querySelector('input').value;
   let compare_id=companyPage?target.querySelector('.ask-compare').value:null;
   // Resolve explicitly named comparisons from saved runs only.
   if(!compare_id && /compar/i.test(question))compare_id=runs.find(r=>r.id!==id && question.toLowerCase().includes(r.company))?.id || runs.find(r=>r.id!==id)?.id;
   answer.textContent='Checking the stored evidence…';
   try{
    const {data}=await a.fetchJSON(`/investigations/${encodeURIComponent(id)}/ask`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question,compare_id:compare_id || null})});
    if(version!==answerVersion)return;
    const key=id+':'+version;answers.set(key,data);
    answer.innerHTML=`<p>${esc(data.answer)}</p><div class="ask-facts">${data.facts.map((f,i)=>`<article><span>${esc(f.label)}</span><strong>${esc(new Intl.NumberFormat('en-IN',{maximumFractionDigits:4}).format(f.claim.value))}${f.claim.unit==='USD'?' USD':f.claim.unit==='ratio'?' × / share':''}</strong><button class="ask-evidence-chip" data-answer="${esc(key)}" data-fact="${i}">Checked evidence ↗</button></article>`).join('')}</div>`;
   }catch(ex){answer.textContent='Evidence answer unavailable: '+ex.message;}
  });
 }
 askPanel('companies-ask',true);askPanel('run-ask',false);
 function receipt(data,fact){
  s.back=s.screen;s.evidenceView++;$('#back-evidence').textContent='← Back';
  $('#evidence-content').innerHTML=`<section class="panel"><p class="eyebrow">Checked claim / saved evidence</p><h2>${esc(fact.label)}</h2><pre>${esc(JSON.stringify(fact.claim,null,2))}</pre><h3>Authenticated sources</h3>${fact.claim.evidence_ids.map(id=>`<details><summary>${esc(id)}</summary><pre>${esc(JSON.stringify(data.evidence.find(e=>e.event_id===id),null,2))}</pre></details>`).join('')}</section>`;a.show('evidence');
 }
 document.addEventListener('click',e=>{const b=e.target.closest('[data-answer]');if(b){const data=answers.get(b.dataset.answer);receipt(data,data.facts[Number(b.dataset.fact)]);}});
 window.addEventListener('polytoken:screen',e=>{$('#run-ask').hidden=!s.report || !['model-fit','report','evidence-index','investigation'].includes(e.detail);});
 window.addEventListener('polytoken:reset',()=>{answerVersion++;$('#run-ask .ask-answer').textContent='';$('#run-ask').hidden=true;});
 window.addEventListener('polytoken:report',()=>{$('#run-ask').hidden=!['model-fit','report','evidence-index','investigation'].includes(s.screen);});
 function tokenSample(compare=false){
  const chosen=samples.find(x=>x.variant===$('#token-sample').value);if(!chosen)return;
  $('#token-review').textContent=chosen.review_status.toUpperCase()+': '+chosen.review_note;
  $('#token-text').value=chosen.text;s.tokenSequence++;s.tokenResults=new Map(chosen.models.map(m=>[m.tokenizer,{...m.record,claims:m.claims,evidence_ids:m.claims[0].evidence_ids,provenance:m.evidence[0].provenance}]));a.renderTokens();
  $('#token-status').textContent='Recorded encodings, recomputed from authenticated token receipts. No new tokenizer or model call. Ratios are conditional on the unreviewed translations.';
  const rows=compare?samples:[chosen];
  const specs=[...new Set(rows.flatMap(x=>x.models.map(m=>m.tokenizer)))];
  $('#token-comparison').innerHTML=`<p><strong>Paired English baseline:</strong> ${esc(chosen.english)}</p><div class="token-pair-table"><table><thead><tr><th>Tokenizer</th>${rows.map(x=>`<th>${esc(x.variant==='native'?'Telugu script':'Tenglish')} tokens / English</th>`).join('')}</tr></thead><tbody>${specs.map(spec=>`<tr><th>${esc(spec)}</th>${rows.map(x=>{const m=x.models.find(m=>m.tokenizer===spec);if(!m)return '<td>Not measured</td>';const vals=Object.fromEntries(m.claims.map(c=>[c.id,c.value]));const key='token:'+x.variant+':'+spec;answers.set(key,{evidence:m.evidence,facts:[{label:x.label+' / English',claim:m.claims.find(c=>c.id==='token_pair/ratio')}]});return `<td><button data-answer="${esc(key)}" data-fact="0">${vals['token_pair/native_tokens']} / ${vals['token_pair/english_tokens']} · ${vals['token_pair/ratio'].toFixed(2)}× ↗</button></td>`;}).join('')}</tr>`).join('')}</tbody></table></div>`;
 }
 $('#token-sample').addEventListener('change',()=>tokenSample());$('#use-token-sample').addEventListener('click',()=>tokenSample());$('#compare-token-samples').addEventListener('click',()=>tokenSample(true));
 window.addEventListener('polytoken:screen',e=>{if(e.detail==='tokens' && !$('#token-text').value && samples.length)tokenSample();});
 a.fetchJSON('/token-samples').then(({data})=>{samples=data;$('#token-review').textContent=data[0]?.review_note || 'No authenticated sample receipts available.';}).catch(()=>{$('#token-review').textContent='Saved sample evidence unavailable.';});
 a.fetchJSON('/model-fits').then(({data})=>{runs=data;const opts=runs.map(r=>`<option value="${esc(r.id)}">${esc(names[r.company] || r.company)}</option>`).join('');$('#companies-ask .ask-run').innerHTML=opts;$('#companies-ask .ask-compare').innerHTML='<option value="">Choose for comparison</option>'+opts;const r=runs.find(r=>r.company==='raitu');if(r)$('#companies-ask .ask-run').value=r.id;}).catch(()=>{});
 a.fetchJSON('/launcher/options').then(({data})=>{options=data;$('#candidate-models').innerHTML=data.models.map(m=>`<label><input type="checkbox" value="${esc(m)}" checked>${esc(m)}</label>`).join('');$('#investigate').disabled=false;sourceChanged();}).catch(()=>{$('#launcher-mode').textContent='Launcher options unavailable. Reload after checking the local server.';$('#investigate').disabled=true;});
})();
