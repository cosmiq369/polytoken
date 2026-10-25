/* Capture the real offline API: no mocked replies, no provider generation. */
const {chromium}=require('playwright');const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),images=path.join(root,'docs/images');
(async()=>{
 const browser=await chromium.launch({headless:true});
 const context=await browser.newContext({viewport:{width:1280,height:950},colorScheme:'dark'});
 const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('**/*',route=>{assert.equal(new URL(route.request().url()).origin,'http://127.0.0.1:8000','Recording must stay on the offline local server');return route.continue();});
 await page.goto('http://127.0.0.1:8000');await page.locator('#demo-run').click();await page.locator('#replay-controls:not([hidden])').waitFor({timeout:90000});
 await page.locator('#replay-position').fill('1000');await page.waitForFunction(()=>document.querySelector('#report').dataset.billingStatus==='checked',null,{timeout:90000});
 const run=await page.locator('#console-run-id').textContent();const tab=async name=>page.locator(`[data-console-tab=${name}]`).click();
 for(const [width,height,size] of [[1280,950,'desktop'],[390,844,'mobile']]){
  await page.setViewportSize({width,height});
  for(const theme of ['dark','light']){
   await page.locator('.rail [data-screen=settings]').click();await page.locator('#theme').selectOption(theme);
   for(const view of ['settings','companies','history','activity','trace','overview','billing','quality','evidence','tokens']){
    if(view==='settings')await page.locator('.rail [data-screen=settings]').click();else if(view==='companies')await page.locator('.rail [data-screen=ask]').click();else if(view==='history')await page.locator('.rail [data-screen=history]').click();else await tab(view);
    if(view==='tokens')await page.waitForFunction(()=>document.querySelector('#token-status').textContent.startsWith('Local inspection complete'),null,{timeout:90000});
    if(view==='trace'){const d=page.locator('.trace-step').first();if(await d.getAttribute('open')===null)await d.locator('summary').first().click();}
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,view+' overflow');
    await page.screenshot({path:path.join(images,`console_${view}_${size}_${theme}.png`),fullPage:true});
   }
   await tab('billing');for(const sub of ['replay','models','scenario','compression']){await page.locator(`[data-bill-tab=${sub}]`).click();await page.screenshot({path:path.join(images,`console_billing_${sub}_${size}_${theme}.png`),fullPage:true});}
   await tab('overview');await page.locator('#report-title .metric').click();await page.locator('#raw-evidence article').first().waitFor();await page.screenshot({path:path.join(images,`console_receipt_${size}_${theme}.png`),fullPage:true});
   await tab('activity');await page.locator('#toggle-events').click();await page.screenshot({path:path.join(images,`console_events_${size}_${theme}.png`),fullPage:true});await page.locator('#toggle-events').click();
  }
 }
 assert.deepEqual(errors,[]);await context.close();
 const vc=await browser.newContext({viewport:{width:1280,height:900},colorScheme:'dark',recordVideo:{dir:path.join(images,'.recording'),size:{width:1280,height:900}}});
 const v=await vc.newPage();await v.route('**/*',route=>{assert.equal(new URL(route.request().url()).origin,'http://127.0.0.1:8000');return route.continue();});
 await v.goto('http://127.0.0.1:8000');await v.locator('#demo-run').click();await v.locator('#replay-controls:not([hidden])').waitFor({timeout:90000});await v.locator('#replay-speed').selectOption('4');
 await v.waitForFunction(()=>document.querySelector('#run-status').textContent==='Complete');await v.waitForFunction(()=>document.querySelector('#report').dataset.billingStatus==='checked',null,{timeout:90000});
 for(const view of ['trace','overview','billing','quality','evidence','tokens']){await v.locator(`[data-console-tab=${view}]`).click();if(view==='trace')await v.locator('.trace-step>summary').first().click();await v.waitForTimeout(8500);}
 await v.locator('[data-console-tab=activity]').click();await v.locator('#toggle-events').click();await v.waitForTimeout(5000);
 const video=v.video();await vc.close();await video.saveAs(path.join(images,'console_replay.webm'));fs.rmSync(path.join(images,'.recording'),{recursive:true,force:true});
 fs.appendFileSync(path.join(root,'logs/sample/console_validation.jsonl'),JSON.stringify({event:'console_proof_captured',timestamp:new Date().toISOString(),ok:true,run_id:run,screenshots:64,replay_speed:4,recording:'docs/images/console_replay.webm',note:'Original 34-second saved replay at 4x, followed by result inspection. Legacy logs disclose missing call timings.'})+'\n');
 console.log('Captured 64 console screenshots and console_replay.webm from the real offline API.');await browser.close();
})().catch(e=>{console.error(e);process.exit(1);});
