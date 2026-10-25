/* Checks fresh launcher success, actionable stale-server failure, and architecture navigation. */
const {chromium}=require('playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..'),origin=process.env.POLYTOKEN_TEST_ORIGIN || 'http://127.0.0.1:8011';
(async()=>{
 const browser=await chromium.launch({headless:true});
 const page=await browser.newPage({viewport:{width:1920,height:1080},colorScheme:'dark'});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 page.on('request',r=>assert.equal(new URL(r.url()).origin,origin));
 try{
  await page.goto(origin);await page.locator('.rail [data-screen=launcher]').click();
  await page.locator('#candidate-models input').first().waitFor();
  assert.ok(await page.locator('#candidate-models input').count()>1);
  await page.locator('#launch-source').selectOption('raitu');await page.locator('#investigate').click();
  await page.locator('#replay-controls:not([hidden])').waitFor();
  assert.match(await page.locator('#replay-controls').innerText(),/Replay of a saved run/);
  const run=await page.evaluate(()=>window.polyConsole.state.runId);
  await page.getByRole('button',{name:'How it works',exact:true}).first().click();
  await page.locator('#how-it-works:not([hidden])').waitFor();
  assert.match(await page.locator('#how-it-works').innerText(),/in-repo Python implementations against a pinned reference specification/i);
  for(const theme of ['dark','light']){
   await page.evaluate(theme=>document.documentElement.dataset.theme=theme,theme);
   assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
   await page.screenshot({path:path.join(root,`docs/images/how_it_works_${theme}.png`)});
  }
  await page.locator('[data-console-tab=activity]').click();
  assert.equal(await page.evaluate(()=>window.polyConsole.state.runId),run);
  await page.locator('.rail [data-screen=how-it-works]').click();
  assert.equal(await page.locator('#how-it-works').isVisible(),true);
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false);
  // Deliberately simulate an old server without this endpoint; never mock the successful launch.
  await page.route('**/launcher/options',r=>r.fulfill({status:404,contentType:'application/json',body:'{"detail":"Not Found"}'}));
  await page.reload();await page.locator('.rail [data-screen=launcher]').click();
  await page.waitForFunction(()=>document.querySelector('#launcher-mode').textContent.includes('Restart the server: it may be an older process'));
  assert.equal(await page.locator('#investigate').isDisabled(),true);assert.deepEqual(errors,[]);
  fs.appendFileSync(path.join(root,'logs/sample/architecture_validation.jsonl'),JSON.stringify({event:'architecture_and_launcher_browser_validation',ok:true,timestamp:new Date().toISOString(),origin,checks:['fresh demo models load','Run starts original Raitu replay','info and sidebar navigation','run survives architecture view','1920x1080 light/dark','390px overflow','stale endpoint recovery message and disabled Run'],external_requests:0})+'\n');
  console.log('Architecture and launcher checks passed');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
