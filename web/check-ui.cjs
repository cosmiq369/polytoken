/* Offline browser contract checks. Production code has no Playwright dependency. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require('playwright');
const root=path.resolve(__dirname,'..'),samples=path.join(root,'logs/sample');
const readJSON=file=>JSON.parse(fs.readFileSync(file,'utf8'));
const lines=file=>fs.readFileSync(file,'utf8').trim().split('\n').map(JSON.parse);
const samudraPath=path.join(samples,'agent_samudra_v3_report.json'),samudra=readJSON(samudraPath);
const events=lines(path.join(samples,'agent_samudra_v3.jsonl')).filter(e=>e.investigation_id===samudra.id);
const world=new Map(['agent_world_events.jsonl','agent_v2_world_events.jsonl','agent_v3_world_events.jsonl'].flatMap(file=>lines(path.join(samples,file)).map(row=>[row.world_event.event_id,row.world_event])));
const companies=['samudra','swara'].map(c=>[...world.values()].filter(e=>e.payload?.config?.company===c).at(-1)?.payload.config).filter(Boolean).map(c=>Object.fromEntries(['company','language','model_in_use','monthly_chats','latency_target_s'].map(k=>[k,c[k]])));
const fixtureRoot=process.env.UI_BILLING_FIXTURES || path.join(root,'.cache/ui-browser-fixtures');
const index=readJSON(path.join(fixtureRoot,'index.json')),tokenFixtures=readJSON(path.join(fixtureRoot,'tokens.json'));
const recordedCurrencies=readJSON(path.join(fixtureRoot,'currencies.json'));
const currencies={...recordedCurrencies,rates:[...recordedCurrencies.rates,{...recordedCurrencies.rates[1],currency:'EUR',per_usd:.9,source:'Test-only future currency row'}]};
function reportFiles(dir){return fs.readdirSync(dir,{withFileTypes:true}).flatMap(item=>item.isDirectory()?reportFiles(path.join(dir,item.name)):/^agent_.*_report\.json$/.test(item.name)?[path.join(dir,item.name)]:[]);}
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1040},colorScheme:'light'});
  const errors=[];page.on('pageerror',error=>errors.push(error.message));
  let companiesFail=false,postFail=false,posted=null,finishReport=false,billingUnavailable=false,billingOverride=null;
  const tokenRequests=[];
  await page.route('**/*',async route=>{
   const url=new URL(route.request().url());assert.equal(url.origin,'http://polytoken.test','No external origins allowed');
   const respond=(data,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(data)});
   if(url.pathname==='/companies')return respond(companiesFail?{detail:'Test company lookup unavailable'}:companies,companiesFail?503:200);
   if(url.pathname==='/currencies')return respond(currencies);
   if(url.pathname==='/tokens'){
    const text=url.searchParams.get('text'),spec=url.searchParams.get('tokenizer');tokenRequests.push([text,spec]);
    return respond(tokenFixtures[text+'\n'+spec] || {ok:false,reason:'No local test measurement for this text; no download attempted.'});
   }
   if(url.pathname.endsWith('/billing')){
    const id=url.pathname.split('/')[2];
    if(billingOverride && billingOverride.id===id)return respond(billingOverride);
    return respond(!billingUnavailable && index[id]?readJSON(index[id]):{id,status:'not measured',reason:'Test archived billing evidence unavailable',claims:[]});
   }
   if(url.pathname==='/investigations' && route.request().method()==='POST'){
    posted=route.request().postDataJSON();return respond(postFail?{detail:'Test queue unavailable'}:{id:samudra.id},postFail?503:202);
   }
   if(url.pathname.endsWith('/events')){
    const cut=events.findIndex(e=>e.event==='experiment_progress');
    return route.fulfill({status:200,contentType:'text/event-stream',body:events.slice(0,cut+1).map((e,i)=>`id: ${i}\nevent: ${e.event}\ndata: ${JSON.stringify(e)}\n\n`).join('')});
   }
   if(url.pathname.endsWith('/report'))return respond(finishReport?samudra:{...samudra,status:'running',jobs:{...samudra.jobs,status:'running'}},finishReport?200:202);
   if(url.pathname.startsWith('/evidence/')){const e=world.get(decodeURIComponent(url.pathname.slice(10)));return respond(e || {detail:'Evidence not found'},e?200:404);}
   const filename={'/':'index.html','/app.js':'app.js','/styles.css':'styles.css','/console.css':'console.css','/console.js':'console.js'}[url.pathname];
   return filename?route.fulfill({path:path.join(__dirname,filename),contentType:filename.endsWith('.js')?'application/javascript':filename.endsWith('.css')?'text/css':'text/html'}):route.fulfill({status:404,body:'Not found'});
  });
  await page.goto('http://polytoken.test/');await page.locator('.company-card').first().waitFor();
  const tab=async name=>page.locator(`[data-console-tab="${name}"]`).click();
  const bill=async name=>{await tab('billing');await page.locator(`[data-bill-tab="${name}"]`).click();};
  const importReport=async(file,id)=>{
   await page.locator('.rail [data-screen=ask]').click();await page.locator('#saved-files').setInputFiles(file);
   await page.locator('#report:not([hidden]) #report-title').waitFor();
   if(id)await page.waitForFunction(id=>document.querySelector('#report').dataset.reportId===id && document.querySelector('#report').dataset.billingStatus!=='loading',id,{timeout:20000});
  };
  const importObject=async obj=>importReport({name:'test-report.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(obj))},obj.id);
  const noOverflow=async()=>assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth),false,'Horizontal page overflow');
  const contrast=async()=>{
   const failures=await page.evaluate(()=>{
    const rgb=c=>c.match(/[\d.]+/g).slice(0,3).map(Number),lum=c=>rgb(c).map(n=>n/255).map(n=>n<=.04045?n/12.92:((n+.055)/1.055)**2.4).reduce((s,n,i)=>s+n*[.2126,.7152,.0722][i],0);
    return [...document.querySelectorAll('nav [aria-current],.screen:not([hidden]) h1,.screen:not([hidden]) .hint,.screen:not([hidden]) .eyebrow,.screen:not([hidden]) .tag,.screen:not([hidden]) .metric:not(.missing),.screen:not([hidden]) .rate-note')].filter(e=>e.getClientRects().length).flatMap(e=>{
     let p=e,bg;while(p){bg=getComputedStyle(p).backgroundColor;if(bg!=='rgba(0, 0, 0, 0)' && bg!=='transparent')break;p=p.parentElement;}if(!p)return[];
     const a=lum(getComputedStyle(e).color),b=lum(bg),r=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);return r<4.5?[{text:e.textContent.slice(0,60),ratio:r}]:[];
    });
   });assert.deepEqual(failures,[],'Visible text contrast must be at least 4.5:1');
  };
  const fixtures=reportFiles(samples);
  for(const file of fixtures){
   const report=readJSON(file);await importReport(file,report.id);
   assert.ok(!/\b(?:undefined|NaN|Infinity)\b/.test(await page.locator('#report').innerText()),file);
   await tab('quality');await page.locator('#ratio-part').selectOption('system_prompt');
   assert.equal(await page.locator('.interval').count(),0,'Degenerate system-prompt intervals must be suppressed');
   assert.match(await page.locator('.ratio-section').innerText(),/One system prompt per company/);
   await page.locator('#ratio-part').selectOption('user');
   const relevant=report.claims.filter(c=>/^ratios\/.+\/user\/ci_low$/.test(c.id));
   const nonzero=relevant.filter(c=>report.claims.find(h=>h.id===c.id.replace('/ci_low','/ci_high'))?.value>c.value);
   assert.equal(await page.locator('.interval').count(),nonzero.length);
   await tab('quality');await page.locator('#ratio-part').selectOption('system_prompt');
   await bill('composition');await page.getByRole('button',{name:'Transcript',exact:true}).click();
   if(index[report.id] && readJSON(index[report.id]).status==='checked')assert.match(await page.locator('#report').innerText(),/No history replay/);
   await page.getByRole('button',{name:'Billed',exact:true}).click();await noOverflow();
   // Every negative checked fix belongs in the cost-increase group, never the saving group.
   const view=index[report.id]?readJSON(index[report.id]):null;
   for(const f of view?.fixes || [])if(f.group==='would_cost_more'){
    const selector=`[data-claim="${f.fields.saving_usd}"]`;
    assert.equal(await page.locator('.would-cost-more '+selector).count(),1);
    assert.equal(await page.locator('.fix:not(.would-cost-more .fix) '+selector).count(),0);
   }
  }
  await importReport(samudraPath,samudra.id);
  assert.match(await page.locator('#report-title').innerText(),/Your Telugu system prompt/);
  assert.ok(!(await page.locator('#report-title').innerText()).includes('system_prompt'));
  assert.equal(await page.locator('.model-table tbody tr').count(),8);
  assert.match(await page.locator('.model-table').innerText(),/no verified price/i);
  assert.match(await page.locator('.speed-row').first().innerText(),/openai\/gpt-oss-20b/);
  assert.match(await page.locator('.speed-row').first().innerText(),/stand-in/);
  assert.ok(!(await page.locator('.trust-line').innerText()).includes('speed/output_tokens_per_s/'));
  const legacyPath=path.join(samples,'agent_samudra_v2_report.json');await importReport(legacyPath,readJSON(legacyPath).id);
  await tab('evidence');await page.locator('#evidence-ledger [data-dropped]').first().click();assert.match(await page.locator('#evidence').innerText(),/speed\/output_tokens_per_s/);
  await page.locator('#back-evidence').click();
  await importReport(samudraPath,samudra.id);
  // Currency conversion is explicit, precise, and remembered after reload.
  assert.equal(await page.locator('#currency').inputValue(),'INR');
  await page.locator('#currency').selectOption('USD');
  const usdText=await page.locator('.headline-cell').first().innerText();assert.match(usdText,/\$116\.02/);
  await page.locator('#currency').selectOption('INR');assert.match(await page.locator('.headline-cell').first().innerText(),/11,015\.34/);
  assert.match(await page.locator('#currency-source').innerText(),/FBIL.*2026-10-23/);
  await page.locator('#currency-source').click();assert.match(await page.locator('#evidence').innerText(),/94\.9432/);await page.locator('#back-evidence').click();
  await page.reload();await page.locator('.company-card').first().waitFor();await page.waitForFunction(()=>document.querySelector('#currency').value==='INR');
  await page.locator('#currency').selectOption('EUR');await importReport(samudraPath,samudra.id);assert.match(await page.locator('.headline-cell').first().innerText(),/104\.42/);
  await page.locator('#currency').selectOption('USD');
  // Only the explicitly labelled what-if panel changes when inputs change.
  const recorded=await page.locator('.headline-cell').first().innerText();
  await bill('scenario');
  const scenarioBefore=await page.locator('#what-if-result').innerText();
  await page.locator('#what-if-input').evaluate(el=>{el.value='2';el.dispatchEvent(new Event('input',{bubbles:true}));});
  assert.notEqual(await page.locator('#what-if-result').innerText(),scenarioBefore);
  assert.equal((await page.locator('.headline-cell').first().innerText()).replace(/\s/g,''),recorded.replace(/\s/g,''));
  await page.locator('[data-scenario-record]').click();assert.match(await page.locator('#evidence').innerText(),/Scenario, not a measurement/);assert.match(await page.locator('#evidence').innerText(),/assumed_input_price_usd/);await page.locator('#back-evidence').click();
  await page.locator('#reset-what-if').click();assert.equal(await page.locator('#what-if-result').innerText(),scenarioBefore);
  await tab('quality');assert.match(await page.locator('.quality-line').innerText(),/A\/A floor 7 \/ 20 judged/);
  await tab('quality');assert.match(await page.locator('.quality-line').innerText(),/A\/B change 3 \/ 20 judged/);
  assert.match(await page.locator('.fix.tested .fix-heading').innerText(),/Inconclusive/i);
  assert.match(await page.locator('.interpretation').innerText(),/the bar cannot be met by this judge and stand-in model/);
  assert.match(await page.locator('#report-title').innerText(),/of the money/);
  assert.match(await page.locator('.composition-grid').innerText(),/of billed tokens/);
  assert.match(await page.locator('.tax-cell').innerText(),/what the same content costs in English/);
  assert.ok(!(await page.locator('#report').innerText()).includes('820.65%'));
  for(const fix of await page.locator('.fix.estimate').all()) assert.equal(await fix.getByText('Untested estimate',{exact:true}).count(),1);
  // Optional A/A and A/B rows use recorded pair order, null verdicts stay unjudged.
  const source=samudra.claims[0],view=readJSON(index[samudra.id]),aaId='test-aa';
  const synthetic={...samudra,id:aaId,quality_interpretation:'Test A/A floor is inconclusive',claims:[...samudra.claims.filter(c=>!c.id.startsWith('quality/aa/')),{...source,id:'quality/aa/passed',value:17},{...source,id:'quality/aa/judged',value:20}],fixes:samudra.fixes.map(f=>f.experiment_evidence_ids?{...f,status:'inconclusive; native review pending'}:f)};
  billingOverride={...view,id:aaId,quality:{...view.quality,aa:{pairs:Array.from({length:20},(_,i)=>({chat_id:'test-'+i,same_facts:i<17,reason:'Test-only verdict'}))}},fixes:view.fixes.map(f=>f.tested?{...f,status:'inconclusive; native review pending'}:f)};
  await importObject(synthetic);assert.match(await page.locator('.quality-line').innerText(),/A\/A floor 17 \/ 20 judged/);assert.equal(await page.locator('.quality-line .threshold').count(),2);assert.match(await page.locator('.quality-line').innerText(),/18-of-20/);
  billingOverride=null;
  const zlib=require('node:zlib');await importReport([{name:'report.json',mimeType:'application/json',buffer:fs.readFileSync(samudraPath)},{name:'evidence.jsonl.gz',mimeType:'application/gzip',buffer:zlib.gzipSync(JSON.stringify({world_event:world.values().next().value})+'\n')}],samudra.id);
  assert.equal(await page.locator('#notice').isVisible(),false);
  // Source escaping, missing values, dropped claims, malformed imports.
  await importObject({id:'test-partial',status:'partial',partial_reason:'Test budget exhausted',claims:[{...source,id:'unverified',value:987654321,verified:false},{...source,id:'dropped',value:987654321}],dropped_claims:[{id:'dropped',reason:'Test checker rejection'}],top_finding:'<img src=x onerror="window.injected=true">',unknown_future_field:{anything:true}});
  assert.ok(!(await page.locator('#report').innerText()).includes('987654321'));assert.equal(await page.locator('#report img').count(),0);assert.equal(await page.evaluate(()=>window.injected),undefined);
  billingUnavailable=true;await importReport(samudraPath,samudra.id);await page.locator('#report-title .metric').click();await page.getByText('Raw evidence not loaded.',{exact:false}).first().waitFor();
  await page.locator('.rail [data-screen=ask]').click();await page.locator('#saved-files').setInputFiles({name:'bad.json',mimeType:'application/json',buffer:Buffer.from('{')});await page.locator('#notice:not([hidden])').waitFor();
  billingUnavailable=false;
  await page.locator('#currency').selectOption('INR');
  // Screenshots use the saved Samudra report and actual cached tokenizer outputs.
  await importReport([samudraPath,path.join(samples,'agent_samudra_v3.jsonl'),path.join(samples,'agent_world_events.jsonl'),path.join(samples,'agent_v2_world_events.jsonl'),path.join(samples,'agent_v3_world_events.jsonl')],samudra.id);
  await page.locator('[data-console-tab=tokens]').click();await page.waitForFunction(()=>document.querySelector('#token-status').textContent.startsWith('Local inspection complete'));
  assert.equal(await page.locator('.token-row').count(),8);
  const successful=Object.values(tokenFixtures).filter(r=>r.ok);
  successful.forEach(row=>assert.equal(row.pieces.map(p=>p.text).join(''),row.text));
  if(successful.some(r=>r.fragments>0)){assert.ok(await page.locator('.token-piece.fragment').count()>0);for(const cell of await page.locator('.token-piece.fragment').all())assert.match(await cell.innerText(),/^[0-9A-F]{2}( [0-9A-F]{2})*$/);assert.ok(await page.locator('.byte-character').count()>0);}
  await page.locator('#token-english').click();await page.waitForFunction(()=>document.querySelector('#token-status').textContent.startsWith('Local inspection complete'));
  assert.ok(tokenRequests.some(([text])=>text===view.default_text.english));
  await page.locator('#token-native').click();await page.waitForFunction(()=>document.querySelector('#token-status').textContent.startsWith('Local inspection complete'));
  // Desktop and 390px, light and dark: all five screens, no page overflow, text contrast.
  for(const [width,height,size] of [[1440,1040,'desktop'],[390,844,'mobile']]){
   await page.setViewportSize({width,height});
   for(const theme of ['light','dark']){
    await page.emulateMedia({colorScheme:theme,reducedMotion:'reduce'});
    for(const [screen,name] of [['ask','1 Ask'],['investigation','2 Investigate'],['report','3 Report'],['tokens','4 Token strip'],['evidence',null]]){
     if(name)await page.locator({'1 Ask':'.rail [data-screen=ask]','2 Investigate':'[data-console-tab=activity]','3 Report':'[data-console-tab=overview]','4 Token strip':'[data-console-tab=tokens]'}[name]).click();
     else{await page.locator('[data-console-tab=overview]').click();await page.locator('#report-title .metric').click();await page.locator('#raw-evidence article').first().waitFor();await page.locator('#raw-evidence').getByText('Raw rows or call record',{exact:true}).first().click();}
     await noOverflow();await contrast();
     if(process.argv.includes('--screenshots')) {await page.screenshot({path:path.join(samples,`ui_5b_${screen}_${size}_${theme}.png`),fullPage:true});if(screen==='report' && size==='desktop' && theme==='light')await page.screenshot({path:path.join(samples,'ui_5b_report_summary.png'),fullPage:false});}
    }
   }
  }
  await page.emulateMedia({colorScheme:'light'});
  // Live EventSource replay, duplicate protection, POST and final report polling.
  await page.locator('.rail [data-screen=ask]').click();await page.locator('#monthly-chats').fill('120000');await page.locator('#latency-target').fill('2.5');await page.locator('#investigate').click();
  await page.locator('#investigation:not([hidden]) .timeline .running').waitFor({state:'attached'});await page.waitForFunction(()=>document.querySelector('#experiment-progress').textContent.includes('done ·'));
  assert.deepEqual({company:posted.company,monthly_chats:posted.monthly_chats,latency_target_s:posted.latency_target_s},{company:'samudra',monthly_chats:120000,latency_target_s:2.5});
  const evidenceCount=await page.locator('.evidence-card').count();finishReport=true;
  await page.waitForFunction(()=>document.querySelector('#stream-status').textContent.includes('Investigation complete'),{},{timeout:20000});assert.equal(await page.locator('.evidence-card').count(),evidenceCount);
  companiesFail=true;await page.reload();await page.locator('#retry-companies:not([hidden])').waitFor();assert.equal(await page.locator('#investigate').isDisabled(),true);
  companiesFail=false;await page.locator('#retry-companies').click();await page.locator('.company-card').first().waitFor();postFail=true;await page.locator('#investigate').click();await page.locator('#notice:not([hidden])').waitFor();assert.equal(await page.locator('#investigate').isEnabled(),true);
  assert.deepEqual(errors,[]);
  console.log(`UI checks passed: ${fixtures.length} saved reports; USD/INR persistence; signed fix grouping; non-zero intervals; readable dropped claims; billing and token receipts; 20-screen matrix; 390px light/dark contrast; what-if reset; optional A/A dots; native SSE; failure recovery. Chromium ${browser.version()}`);
 }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
