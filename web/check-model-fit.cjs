/* Real offline API proof: no mocked reports and no provider calls. */
const {chromium}=require('playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),images=path.join(root,'docs/images'),origin='http://127.0.0.1:8000';
(async()=>{
 const browser=await chromium.launch({headless:true});
 const context=await browser.newContext({viewport:{width:1600,height:1050},colorScheme:'dark'});
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',r=>{assert.equal(new URL(r.request().url()).origin,origin);return r.continue();});
 const response=await context.request.get(origin+'/model-fits');assert.equal(response.status(),200);
 const fits=await response.json();assert.equal(fits.length,4);
 for(const r of fits){assert.equal(r.model_fit.models.length,8);assert.equal(r.model_fit.tokenizer_fit_only.length,4);assert.ok(r.claims.every(c=>c.verified));if(r.model_fit.profile.channel==='voice')assert.equal(r.model_fit.recommendation,null);}
 await page.goto(origin);await page.locator('.fit-company').nth(3).waitFor({timeout:90000});
 const noOverflow=async()=>assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'No page overflow');
 const contrast=async()=>{
  const bad=await page.evaluate(()=>{
   const lum=c=>{const m=c.match(/[\d.]+/g);return m.slice(0,3).map(Number).map(n=>n/255).map(n=>n<=.04045?n/12.92:((n+.055)/1.055)**2.4).reduce((s,n,i)=>s+n*[.2126,.7152,.0722][i],0);};
   return [...document.querySelectorAll('#ask h1,#ask h2,#ask h3,#ask .hint,#ask .eyebrow,#ask .fit-status,#ask .fit-metric,#model-fit h1,#model-fit h2,#model-fit .hint,#model-fit .tag,#model-fit .fit-metric')].filter(e=>e.getClientRects().length&&!e.closest('[hidden]')).flatMap(e=>{let p=e,bg;while(p){bg=getComputedStyle(p).backgroundColor;if(bg!=='rgba(0, 0, 0, 0)'&&bg!=='transparent')break;p=p.parentElement;}if(!p)return[];const a=lum(getComputedStyle(e).color),b=lum(bg),ratio=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);return ratio<4.5?[{text:e.textContent.slice(0,50),ratio}]:[];});
  });assert.deepEqual(bad,[],'Text contrast >= 4.5:1');
 };
 let shots=0;
 for(const [width,height,size] of [[1600,1050,'desktop'],[390,844,'mobile']]){
  await page.setViewportSize({width,height});
  for(const theme of ['dark','light']){
   await page.locator('.rail [data-screen=settings]').click();await page.locator('#theme').selectOption(theme);
   await page.locator('.rail [data-screen=ask]').click();await noOverflow();await contrast();
   await page.screenshot({path:path.join(images,`model_fit_companies_${size}_${theme}.png`)});shots++;
   for(const r of fits){
    await page.locator(`.fit-company[data-fit-company=${r.company}] [data-fit-open]`).click();
    await page.waitForFunction(id=>window.polyConsole.state.report?.id===id,r.id,{timeout:90000});
    await page.locator('#model-fit:not([hidden]) .fit-ranking tbody tr').nth(7).waitFor();
    assert.equal(await page.locator('.run-tabs button').first().textContent(),'Model fit');
    assert.equal(await page.locator('.fit-ranking tbody tr').count(),8);
    const m=r.model_fit.models[0],cl=r.claims.find(c=>c.id===m.cost_claim);
    assert.equal(await page.locator('.fit-ranking tbody tr').first().locator('td').first().innerText(),'$'+cl.value.toFixed(5));
    if(r.model_fit.profile.channel==='voice')assert.match(await page.locator('.fit-recommendation').innerText(),/No model has verified latency/);
    await noOverflow();await contrast();
    await page.screenshot({path:path.join(images,`model_fit_${r.company}_${size}_${theme}.png`)});shots++;
    await page.locator('[data-console-tab=activity]').click();
    assert.ok(await page.locator('#service-map .service-state').allTextContents().then(a=>a.some(t=>/\d+ ms/.test(t))),'New replay contains measured timings');
    await page.locator('[data-console-tab=fit]').click();
    await page.locator('.fit-ranking tbody tr').first().locator('[data-claim]').first().click();
    await page.locator('#raw-evidence article').first().waitFor({timeout:90000});
    assert.match(await page.locator('#evidence').innerText(),/model_fit/);
    await page.locator('.rail [data-screen=ask]').click();
   }
  }
 }
 // Narrow reflow and keyboard entry remain usable.
 await page.setViewportSize({width:320,height:700});await noOverflow();
 await page.locator('.fit-open').first().focus();await page.keyboard.press('Enter');
 await page.locator('#model-fit:not([hidden]) .fit-ranking').waitFor();await noOverflow();
 await page.keyboard.press('Alt+2');assert.equal(await page.locator('#investigation').isVisible(),true);
 await page.keyboard.press('Alt+1');assert.equal(await page.locator('#model-fit').isVisible(),true);
 assert.deepEqual(errors,[]);await context.close();
 const videoContext=await browser.newContext({viewport:{width:1600,height:1050},colorScheme:'dark',recordVideo:{dir:path.join(images,'.model-fit-recording'),size:{width:1600,height:1050}}});
 const v=await videoContext.newPage();await v.route('**/*',r=>{assert.equal(new URL(r.request().url()).origin,origin);return r.continue();});
 await v.goto(origin);await v.locator('.fit-company').nth(3).waitFor({timeout:90000});await v.waitForTimeout(2500);
 for(const company of ['samudra','raitu','swara','paisa']){
  await v.locator(`.fit-company[data-fit-company=${company}] [data-fit-open]`).click();
  await v.waitForFunction(c=>window.polyConsole.state.report?.company===c,company,{timeout:90000});
  await v.locator('#model-fit:not([hidden]) .fit-ranking').waitFor();await v.waitForTimeout(2500);
  if(company==='samudra'){
   await v.locator('[data-console-tab=activity]').click();await v.locator('#replay-position').fill('0');await v.locator('#replay-speed').selectOption('16');await v.locator('#replay-play').click();
   await v.waitForFunction(()=>document.querySelector('#run-status').textContent==='Complete',null,{timeout:90000});
   await v.locator('[data-console-tab=fit]').click();
   await v.locator('.fit-ranking tbody tr').first().locator('[data-claim]').first().click();await v.locator('#raw-evidence article').first().waitFor();await v.waitForTimeout(2500);
  }
  await v.locator('.rail [data-screen=ask]').click();
 }
 const video=v.video();await videoContext.close();await video.saveAs(path.join(images,'model_fit_replay.webm'));fs.rmSync(path.join(images,'.model-fit-recording'),{recursive:true,force:true});
 const record={event:'model_fit_browser_validation',timestamp:new Date().toISOString(),ok:true,screenshots:shots,companies:fits.map(r=>r.company),run_ids:fits.map(r=>r.id),checks:['four companies','eight models each','four unpriced families','checked costs','voice abstention','evidence receipts','fresh timings','dark/light contrast','320px reflow','keyboard navigation','no external requests','no page errors'],recording:'docs/images/model_fit_replay.webm'};
 fs.appendFileSync(path.join(root,'logs/sample/model_fit_validation.jsonl'),JSON.stringify(record)+'\n');console.log(JSON.stringify(record));await browser.close();
})().catch(e=>{console.error(e);process.exit(1);});
