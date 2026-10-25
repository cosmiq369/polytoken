/* Offline console acceptance checks and reproducible proof capture. */
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {chromium}=require('playwright');
const root=path.resolve(__dirname,'..'),sample=path.join(root,'logs/sample'),fixtures=process.env.UI_BILLING_FIXTURES || path.join(root,'.cache/ui-browser-fixtures');
const read=p=>JSON.parse(fs.readFileSync(p,'utf8')),lines=p=>fs.readFileSync(p,'utf8').trim().split('\n').map(JSON.parse);
const report=read(path.join(sample,'agent_samudra_v3_report.json')),events=lines(path.join(sample,'agent_samudra_v3.jsonl')).filter(e=>e.investigation_id===report.id),index=read(path.join(fixtures,'index.json'));
const swara=read(path.join(sample,'agent_swara_v3_report.json')),swaraEvents=lines(path.join(sample,'agent_swara_v3.jsonl')).filter(e=>e.investigation_id===swara.id);
const billing=read(index[report.id]),tokens=read(path.join(fixtures,'tokens.json')),currencies=read(path.join(fixtures,'currencies.json'));
const proof=process.argv.includes('--proof'),images=path.join(root,'docs/images');
const start=Date.parse(events[0].timestamp),end=Date.parse(events.at(-1).timestamp);
const fakeEvents=[
 {event:'step_started',step:'measure',span_id:'step-measure'},
 {event:'tool_started',step:'measure',span_id:'test-tool',service:'tools',name:'measure',input:{company:'Test fixture'}},
 {event:'sql_started',step:'measure',span_id:'test-sql',parent_id:'test-tool',service:'measurements',name:'Zetaris SQL',input:{query:'SELECT test_fixture'}},
 {event:'budget',step:'measure',sql:1,nemotron:1,judge:0,hosted:0,duration_s:1,ceilings:{sql:60,nemotron:25,judge:45,hosted:70,duration_s:360}},
 {event:'finding',step:'measure',text:'Unchecked observation 999999 INR'},
].map((e,i)=>({...e,timestamp:new Date(Date.now()+i).toISOString(),investigation_id:'live-fake'}));
(async()=>{
 const browser=await chromium.launch({headless:true});const errors=[];let stopped=false;
 const context=await browser.newContext({viewport:{width:1280,height:950},colorScheme:'dark'});
 async function routePage(page){page.on('pageerror',e=>errors.push(e.message));await page.route('**/*',async route=>{
  const url=new URL(route.request().url());assert.equal(url.origin,'http://polytoken.test','No external network requests');
  const json=(data,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(data)});
  if(url.pathname==='/console/config')return json({demo:false});
  if(url.pathname==='/launcher/options')return json({demo:false,models:['fixture/model'],samples:[{company:'samudra',language:'te',channel:'chat',monthly_chats:200000}],max_bytes:1048576});
  if(url.pathname==='/token-samples')return json([]);
  if(url.pathname==='/model-fits')return json([]);
  if(url.pathname==='/companies')return json([{company:'samudra',language:'te',model_in_use:billing.tokenizer,monthly_chats:100000},{company:'swara',language:'hi'}]);
  if(url.pathname==='/currencies')return json(currencies);
  if(url.pathname==='/investigations' && route.request().method()==='GET')return json([{id:report.id,company:'samudra',status:'complete',saved:true,demo:true},{id:swara.id,company:'swara',status:'complete',saved:true}]);
  if(url.pathname==='/investigations' && route.request().method()==='POST'){stopped=false;return json({id:'live-fake'},202);}
  if(url.pathname.endsWith('/replay'))return json(url.pathname.includes(swara.id)?{report:swara,events:swaraEvents,evidence:[],legacy:true}:{report,events,evidence:[],legacy:true});
  if(url.pathname.endsWith('/billing'))return json(billing);
  if(url.pathname.endsWith('/stop')){stopped=true;return json({id:'live-fake',status:'stopping'},202);}
  if(url.pathname.endsWith('/events'))return route.fulfill({contentType:'text/event-stream',body:fakeEvents.map((e,i)=>`id: ${i}\nevent: ${e.event}\ndata: ${JSON.stringify(e)}\n\n`).join('')});
  if(url.pathname.endsWith('/report'))return json(stopped?{id:'live-fake',status:'partial',claims:[],dropped_claims:[],partial_reason:'Stopped by user'}:{detail:'Investigation is running'},stopped?200:202);
  if(url.pathname==='/tokens')return json(tokens[url.searchParams.get('text')+'\n'+url.searchParams.get('tokenizer')] || {ok:false,reason:'Test fixture unavailable'});
  if(url.pathname.startsWith('/evidence/'))return json({detail:'Raw archive not loaded in this fixture'},404);
  const filename={'/':'index.html','/launcher.js':'launcher.js','/model-fit.js':'model-fit.js','/app.js':'app.js','/styles.css':'styles.css','/console.js':'console.js','/console.css':'console.css'}[url.pathname];
  return filename?route.fulfill({path:path.join(__dirname,filename),contentType:filename.endsWith('.js')?'application/javascript':filename.endsWith('.css')?'text/css':'text/html'}):route.fulfill({status:404,body:'Not found'});
 });}
 const page=await context.newPage();await routePage(page);
 const tab=async name=>page.locator(`[data-console-tab=${name}]`).click();
 const seek=async value=>page.locator('#replay-position').fill(String(value));
 const noOverflow=async()=>assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'No page overflow');
 const contrast=async()=>{
  const bad=await page.evaluate(()=>{
   const lum=c=>{const m=c.match(/[\d.]+/g);if(!m)return 0;return m.slice(0,3).map(Number).map(n=>n/255).map(n=>n<=.04045?n/12.92:((n+.055)/1.055)**2.4).reduce((s,n,i)=>s+n*[.2126,.7152,.0722][i],0);};
   return [...document.querySelectorAll('button:not(:disabled),h1,h2,.hint,.tag,.span-duration,.eyebrow,.planner-why,.service-state,.stage-item strong,.stage-item small,.work-copy p,.phase-label,.verified-counter')].filter(e=>e.getClientRects().length && !e.closest('[hidden]')).flatMap(e=>{if(e instanceof SVGElement)return [];let p=e,bg;while(p){bg=getComputedStyle(p).backgroundColor;if(bg!=='rgba(0, 0, 0, 0)' && bg!=='transparent')break;p=p.parentElement;}if(!p)return [];const a=lum(getComputedStyle(e).color),b=lum(bg),ratio=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);return ratio<4.5?[{text:e.textContent.slice(0,50),ratio}]:[];});
  });assert.deepEqual(bad,[],'Text contrast >= 4.5:1');
 };
 await page.goto('http://polytoken.test');await page.locator('#demo-run').click();await page.locator('#replay-controls:not([hidden])').waitFor();
 await seek(0);assert.equal(await page.locator('[data-console-tab=billing]').isDisabled(),true);assert.equal(await page.locator('[data-console-tab=quality]').isDisabled(),true);assert.equal(await page.locator('#run-status').textContent(),'Queued');assert.equal(await page.locator('.finding-card').count(),0);
 await page.locator('#replay-play').click();await page.waitForFunction(()=>document.querySelector('#elapsed').textContent!=='00:00');assert.equal(await page.locator('#run-status').textContent(),'Running');await page.locator('#replay-play').click();
 // Recorded legacy observations light in order without inventing physical latency.
 for(const [type,node] of [['tool_called','tools'],['evidence_added','world']]){const e=events.find((e,i)=>e.event===type && Date.parse(events[i+1]?.timestamp)>Date.parse(e.timestamp)),fraction=(Date.parse(e.timestamp)-start+.1)/(end-start)*1000;await page.locator('#replay-position').evaluate((el,value)=>{el.value=value;el.dispatchEvent(new Event('input',{bubbles:true}));},fraction);assert.equal(await page.locator(`[data-edge=${node}].observed`).count(),1,'Recorded edges illuminate in event order');}
 await seek(700);assert.equal(await page.locator('.finding-card').count(),0,'Legacy findings withheld until final checked report');
 await seek(1000);await page.waitForFunction(()=>document.querySelector('#report').dataset.billingStatus==='checked');assert.equal(await page.locator('#run-status').textContent(),'Complete');assert.ok(await page.locator('.finding-card[data-verified=true]').count()>0);
 assert.match(await page.locator('#current-work h2').textContent(),/quality needs review/);
 for(const currency of ['USD','INR']){await page.locator('#currency').selectOption(currency);assert.equal(await page.locator('.finding-unit').first().textContent(),currency);assert.match(await page.locator('.finding-card .metric').first().textContent(),currency==='INR'?/₹/:/\$/);}
 await seek(0);assert.equal(await page.locator('.finding-card').count(),0,'Scrub backwards clears future findings');await seek(1000);await page.waitForFunction(()=>document.querySelector('#report').dataset.billingStatus==='checked');
 await page.keyboard.press('Alt+4');assert.equal(await page.locator('#report').isVisible(),true);await page.keyboard.press('Alt+9');assert.equal(await page.locator('#event-console').isVisible(),true);await page.keyboard.press('Alt+9');
 for(const name of ['overview','billing','quality','evidence','tokens','trace','activity']){await tab(name);await noOverflow();}
 await page.locator('.rail [data-screen=launcher]').click();await page.locator('#investigate').click();await page.locator('[data-edge=measurements].active').waitFor();
 if(await page.locator('[data-trace-step=measure]').getAttribute('open')===null)await page.locator('[data-trace-step=measure]>summary').click();await page.locator('[data-span=test-tool]>summary').click();
 assert.equal(await page.locator('[data-span=test-tool] [data-span=test-sql][data-parent=test-tool]').count(),1);
 await page.locator('[data-span=test-tool]>summary').focus();await page.evaluate(()=>window.dispatchEvent(new Event('polytoken:update')));assert.equal(await page.locator('[data-span=test-tool]>summary').evaluate(el=>el===document.activeElement),true,'Event updates preserve trace keyboard focus');
 assert.equal(await page.locator('.finding-card').count(),0,'Unchecked observations never become findings');assert.ok(!(await page.locator('.planner-why').innerText()).includes('999999'));
 await page.locator('#stop-run').click();await page.waitForFunction(()=>document.querySelector('#run-status').textContent==='Partial');assert.equal(stopped,true);
 await page.locator('.rail [data-screen=ask]').click();await page.locator('#demo-run').click();await page.locator('#replay-controls:not([hidden])').waitFor();await seek(1000);await page.waitForFunction(()=>document.querySelector('#report').dataset.billingStatus==='checked');
 // Regression for the user's Swara screenshot: earlier experiment events must not mask quality work.
 await page.locator(`#run-history [data-run="${swara.id}"]`).click();
 await page.waitForFunction(id=>document.querySelector('#console-run-id').textContent===id,swara.id);
 const swaraDuration=Date.parse(swaraEvents.at(-1).timestamp)-Date.parse(swaraEvents[0].timestamp);
 await seek(Math.round(127000/swaraDuration*1000));
 assert.equal(await page.locator('#run-status').textContent(),'Running');
 assert.equal(await page.locator('.stage-item[aria-current=step]').getAttribute('data-stage'),'judge');
 assert.match(await page.locator('#current-work h2').textContent(),/meaning survives/);
 assert.equal(await page.locator(`#run-history [data-run="${swara.id}"] .tag`).textContent(),'complete','Replay does not rewrite saved history status');
 // The desktop rail and mobile navigation stay fixed while the content actually moves.
 for(const width of [1280,1024,768,640,390,320]){
  await page.setViewportSize({width,height:900});await tab('activity');
  const rail=await page.locator('.rail nav').boundingBox(),run=await page.locator('.run-bar').boundingBox();
  await page.locator('#main').evaluate(el=>el.scrollTop=el.scrollHeight);
  assert.ok(await page.locator('#main').evaluate(el=>el.scrollTop)>0,'Main content scrolls');
  assert.deepEqual(await page.locator('.rail nav').boundingBox(),rail,'Navigation stays in place');
  assert.deepEqual(await page.locator('.run-bar').boundingBox(),run,'Run controls stay in place');
  assert.equal(await page.evaluate(()=>scrollY),0,'Document does not move');
  await noOverflow();await tab('activity');
  if(width<=900){const active=await page.locator('.stage-item[aria-current=step]').boundingBox(),path=await page.locator('#stage-path').boundingBox();assert.ok(active.x>=path.x && active.x+active.width<=path.x+path.width+1,'Current stage is visible without hunting horizontally');}
 }
 await page.setViewportSize({width:1280,height:950});
 await page.locator('[data-stage=judge]').focus();await page.keyboard.press('Enter');
 assert.equal(await page.locator('[data-trace-step=judge]').getAttribute('open'),'');
 assert.equal(await page.locator('[data-trace-step=judge]>summary').evaluate(el=>el===document.activeElement),true,'Stage navigation moves keyboard focus to trace');
 // A 640×475 CSS viewport is the reflow space of a 1280×950 window at 200% browser zoom.
 await page.setViewportSize({width:640,height:475});await tab('activity');await noOverflow();
 assert.ok((await page.locator('#main').boundingBox()).height>100,'Content remains usable at zoom-equivalent reflow');
 await page.setViewportSize({width:1280,height:950});
 await page.emulateMedia({reducedMotion:'reduce'});
 assert.equal(await page.locator('.stage-item').first().evaluate(el=>getComputedStyle(el).animationName),'none');
 await page.locator('.rail [data-screen=ask]').click();await page.locator('#demo-run').click();
 await page.waitForFunction(id=>document.querySelector('#console-run-id').textContent===id,report.id);
 await seek(1000);await page.waitForFunction(()=>document.querySelector('#report').dataset.billingStatus==='checked');
 // Both themes, desktop and 390px; every run view and workspace view.
 for(const [width,height,size] of [[1280,950,'desktop'],[390,844,'mobile']]){
  await page.setViewportSize({width,height});
  for(const theme of ['dark','light']){
   await page.locator('.rail [data-screen=settings]').click();await page.locator('#theme').selectOption(theme);
   for(const view of ['settings','companies','history','activity','trace','overview','billing','quality','evidence','tokens']){
    if(view==='settings')await page.locator('.rail [data-screen=settings]').click();
    else if(view==='companies')await page.locator('.rail [data-screen=ask]').click();
    else if(view==='history')await page.locator('.rail [data-screen=history]').click();
    else await tab(view);
    if(view==='tokens')await page.waitForFunction(()=>document.querySelector('#token-status').textContent.startsWith('Local inspection complete'));
    if(view==='trace'){const first=page.locator('.trace-step').first();if(!await first.getAttribute('open'))await first.locator('summary').first().click();}
    await noOverflow();await contrast();
    if(proof)await page.screenshot({path:path.join(images,`console_${view}_${size}_${theme}.png`),fullPage:true});
   }
   if(proof){await tab('billing');for(const name of ['replay','models','scenario','compression']){await page.locator(`[data-bill-tab=${name}]`).click();await page.screenshot({path:path.join(images,`console_billing_${name}_${size}_${theme}.png`),fullPage:true});}await tab('overview');await page.locator('#report-title .metric').click();await page.screenshot({path:path.join(images,`console_receipt_${size}_${theme}.png`),fullPage:true});await tab('activity');await page.locator('#toggle-events').click();await page.screenshot({path:path.join(images,`console_events_${size}_${theme}.png`),fullPage:true});await page.locator('#toggle-events').click();}
  }
 }
 assert.deepEqual(errors,[]);
 if(proof){
  const videoContext=await browser.newContext({viewport:{width:1280,height:900},colorScheme:'dark',recordVideo:{dir:path.join(images,'.recording'),size:{width:1280,height:900}}});
  const v=await videoContext.newPage();await routePage(v);await v.goto('http://polytoken.test');await v.locator('#demo-run').click();await v.locator('#replay-controls:not([hidden])').waitFor();await v.locator('#replay-speed').selectOption('4');
  await v.waitForFunction(()=>document.querySelector('#run-status').textContent==='Complete');await v.waitForFunction(()=>document.querySelector('#report').dataset.billingStatus==='checked');
  // A complete original-time 4× replay, followed by a guided result inspection.
  for(const name of ['trace','overview','billing','quality','evidence','tokens']){await v.locator(`[data-console-tab=${name}]`).click();if(name==='trace')await v.locator('.trace-step>summary').first().click();await v.waitForTimeout(9000);}
  await v.locator('[data-console-tab=activity]').click();await v.locator('#toggle-events').click();await v.waitForTimeout(5000);
  const video=v.video();await videoContext.close();await video.saveAs(path.join(images,'console_replay.webm'));fs.rmSync(path.join(images,'.recording'),{recursive:true,force:true});
 }
 fs.mkdirSync(path.join(root,'logs/sample'),{recursive:true});fs.appendFileSync(path.join(root,'logs/sample/console_validation.jsonl'),JSON.stringify({event:'console_browser_validation',timestamp:new Date().toISOString(),ok:true,proof,recorded_run:report.id,checks:['replay status and timer','scrub removes future claims','legacy timing disclosure','nested SQL spans','live fake stop','verified-only findings','all tabs','dark/light 1280/390 no overflow','4.5:1 contrast','Swara current quality stage','fixed navigation while content scrolls 320–1280px','mobile current stage visibility','keyboard stage-to-trace focus','200% zoom-equivalent reflow','reduced motion'],browser:browser.version()})+'\n');
 console.log('Console checks passed: replay, scrub, timer, nested spans, active edges, fake live Stop, verified findings, tabs, theme matrix, contrast, Swara current stage, fixed navigation, mobile stage visibility, keyboard focus, zoom, reduced motion.');await browser.close();
})().catch(e=>{console.error(e);process.exit(1);});
