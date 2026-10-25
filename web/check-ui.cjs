/* Development-only offline browser checks; not loaded by the page. No npm/build step. */
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '..');
const samples = path.join(root, 'logs/sample');
const readJSON = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const readLines = file => fs.readFileSync(file, 'utf8').trim().split('\n').map(JSON.parse);
const samudraPath = path.join(samples, 'agent_samudra_v2_report.json');
const samudra = readJSON(samudraPath);
const events = readLines(path.join(samples, 'agent_samudra_v2.jsonl')).filter(e=>e.investigation_id===samudra.id);
const worlds = ['agent_world_events.jsonl','agent_v2_world_events.jsonl'].flatMap(file=>readLines(path.join(samples,file)).map(row=>row.world_event));
const world = new Map(worlds.map(e=>[e.event_id,e]));
const companies = ['samudra','swara'].map(company=>worlds.find(e=>e.payload?.config?.company===company)?.payload.config).filter(Boolean).map(c=>Object.fromEntries(['company','language','model_in_use','monthly_chats','latency_target_s'].map(k=>[k,c[k]])));
function reportFiles(dir) {
  return fs.readdirSync(dir,{withFileTypes:true}).flatMap(item=>item.isDirectory()?reportFiles(path.join(dir,item.name)):/^agent_.*_report\.json$/.test(item.name)?[path.join(dir,item.name)]:[]);
}
(async()=>{
  const browser = await chromium.launch({headless:true});
  try {
    const page = await browser.newPage({viewport:{width:1440,height:1040},colorScheme:'light'});
    const errors=[];page.on('pageerror',error=>errors.push(error.message));
    let posted=null, finishReport=false, companiesFail=false, postFail=false;
    const served=[];
    await page.route('**/*', async route=>{
      const url=new URL(route.request().url());
      assert.equal(url.origin,'http://polytoken.test','No external resources or providers are permitted');
      served.push(url.pathname);
      const respond=(data,status=200)=>route.fulfill({status,contentType:'application/json',body:JSON.stringify(data)});
      if(url.pathname==='/companies') return respond(companiesFail?{detail:'Test company lookup unavailable'}:companies,companiesFail?503:200);
      if(url.pathname==='/investigations' && route.request().method()==='POST') {
        posted=route.request().postDataJSON();return respond(postFail?{detail:'Test queue unavailable'}:{id:samudra.id},postFail?503:202);
      }
      if(url.pathname.endsWith('/events')) {
        // Replay actual recorded frames through native EventSource, including IDs.
        const cut=events.findIndex(e=>e.event==='experiment_progress');
        const rows=events.slice(0,cut+1);
        return route.fulfill({status:200,contentType:'text/event-stream',body:rows.map((row,i)=>`id: ${i}\nevent: ${row.event}\ndata: ${JSON.stringify(row)}\n\n`).join('')});
      }
      if(url.pathname.endsWith('/report')) return respond(finishReport?samudra:{...samudra,status:'running',jobs:{...samudra.jobs,status:'running'}},finishReport?200:202);
      if(url.pathname.startsWith('/evidence/')) {
        const evidence=world.get(decodeURIComponent(url.pathname.slice('/evidence/'.length)));
        return respond(evidence || {detail:'Evidence not found'},evidence?200:404);
      }
      const filename={'/':'index.html','/app.js':'app.js','/styles.css':'styles.css'}[url.pathname];
      if(!filename) return route.fulfill({status:404,body:'Not found'});
      return route.fulfill({path:path.join(__dirname,filename),contentType:filename.endsWith('.js')?'application/javascript':filename.endsWith('.css')?'text/css':'text/html'});
    });
    await page.goto('http://polytoken.test/');
    await page.locator('.company-card').first().waitFor();
    const importReport=async(file)=>{
      await page.getByRole('button',{name:'1 Ask',exact:true}).click();
      await page.locator('#saved-files').setInputFiles(file);
      await page.locator('#report:not([hidden]) #report-title').waitFor();
    };
    const importObject=async(report)=>importReport({name:'test-report.json',mimeType:'application/json',buffer:Buffer.from(JSON.stringify(report))});
    const noOverflow=async()=>assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth),false,'Page overflows horizontally');
    const checkContrast=async()=>{
      const failures=await page.evaluate(()=>{
        const rgb=color=>color.match(/[\d.]+/g).slice(0,3).map(Number);
        const luminance=color=>rgb(color).map(n=>n/255).map(n=>n<=.04045?n/12.92:((n+.055)/1.055)**2.4).reduce((sum,n,i)=>sum+n*[.2126,.7152,.0722][i],0);
        return [...document.querySelectorAll('nav [aria-current],.screen:not([hidden]) h1,.screen:not([hidden]) .hint,.screen:not([hidden]) .eyebrow,.screen:not([hidden]) .tag,.screen:not([hidden]) .metric:not(.missing)')].filter(el=>el.getClientRects().length).flatMap(el=>{
          let parent=el,bg;while(parent){bg=getComputedStyle(parent).backgroundColor;if(bg!=='rgba(0, 0, 0, 0)' && bg!=='transparent')break;parent=parent.parentElement;}
          if(!parent)return [];
          const a=luminance(getComputedStyle(el).color),b=luminance(bg),ratio=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);
          return ratio<4.5?[{text:el.textContent.slice(0,60),ratio}]:[];
        });
      });
      assert.deepEqual(failures,[],'Visible text must meet 4.5:1 contrast');
    };
    const fixtures=reportFiles(samples);assert.ok(fixtures.length);
    for(const file of fixtures) {
      await importReport(file);
      const text=await page.locator('#report').innerText();
      assert.ok(!/\b(?:undefined|NaN|Infinity)\b/.test(text),file);
      await page.locator('#ratio-part').selectOption('user');
      await page.locator('#ratio-part').selectOption('assistant');
      await page.locator('#ratio-part').selectOption('system_prompt');
      await page.getByRole('button',{name:'Transcript',exact:true}).click();
      assert.match(await page.locator('#report').innerText(),/Transcript totals have no checked claims/);
      await page.getByRole('button',{name:'Billed',exact:true}).click();
      await noOverflow();
    }
    // Absent, unverified and explicitly dropped values cannot leak into the ledger.
    const source=samudra.claims[0];
    await importObject({id:'test-partial',status:'partial',partial_reason:'Test budget exhausted',claims:[{...source,id:'unverified',value:987654321,verified:false},{...source,id:'dropped',value:987654321}],dropped_claims:[{id:'dropped',reason:'Test checker rejection'}],top_finding:'<img src=x onerror="window.injected=true">',unknown_future_field:{anything:true}});
    assert.ok(!(await page.locator('#report').innerText()).includes('987654321'));
    assert.equal(await page.locator('#report img').count(),0);
    assert.equal(await page.evaluate(()=>window.injected),undefined);
    await importObject({id:'startup-failure',status:'partial',partial_reason:'startup failed: TestError',claims:[],dropped_claims:[]});
    assert.match(await page.locator('#report').innerText(),/startup failed: TestError/);
    // A/A support is optional and must not invent an old report's floor.
    await importReport(samudraPath);
    assert.match(await page.locator('#report').innerText(),/This report has no checked A\/A control/);
    const aa={...samudra,id:'test-aa',quality_interpretation:'Test A/A interpretation',claims:[...samudra.claims,{...source,id:'quality/aa/passed',value:17},{...source,id:'quality/aa/judged',value:20}],fixes:samudra.fixes.map(f=>f.experiment_evidence_ids?{...f,status:'inconclusive; native review pending'}:f)};
    await importObject(aa);
    assert.match(await page.locator('.quality-line').innerText(),/A\/A floor: 17 \/ 20/);
    assert.match(await page.locator('#report').innerText(),/Inconclusive/);
    // Import must be atomic on malformed input, and missing evidence must be explicit.
    await importReport(samudraPath);
    await page.locator('#report .lead-metric button').click();
    await page.getByText('Raw evidence not loaded.',{exact:false}).first().waitFor();
    await page.getByRole('button',{name:'1 Ask',exact:true}).click();
    await page.locator('#saved-files').setInputFiles({name:'bad.json',mimeType:'application/json',buffer:Buffer.from('{')});
    await page.locator('#notice:not([hidden])').waitFor();
    await page.getByRole('button',{name:'3 Report',exact:true}).click();
    assert.match(await page.locator('#report').innerText(),new RegExp(samudra.id));
    // Screenshots contain only the saved Samudra report, recorded events and source evidence.
    await importReport([samudraPath,path.join(samples,'agent_samudra_v2.jsonl'),path.join(samples,'agent_world_events.jsonl'),path.join(samples,'agent_v2_world_events.jsonl')]);
    const capture=async name=>{if(process.argv.includes('--screenshots')) await page.screenshot({path:path.join(samples,`ui_${name}.png`),fullPage:true});};
    await capture('report');
    const net=samudra.claims.find(c=>c.id.endsWith('/net_tokens')&&c.value<0);
    if(net) assert.match(await page.locator('#report').innerText(),new RegExp(new Intl.NumberFormat('en-IN').format(net.value)));
    await page.locator('#report .lead-metric button').click();
    await page.locator('#raw-evidence article').first().waitFor();
    await page.locator('#raw-evidence').getByText('Join bot_config, chats and latest token counts',{exact:true}).first().waitFor();
    await page.getByText('Raw rows or call record',{exact:true}).first().click();
    await capture('evidence');
    await page.getByRole('button',{name:'2 Investigate',exact:true}).click();
    assert.equal(await page.locator('.timeline li').count(),9);
    assert.match(await page.locator('#experiment-progress').innerText(),/done.*failed.*total/);
    assert.ok(!(await page.locator('#evidence-cards').innerText()).includes('[object Object]'));
    assert.ok(await page.locator('.evidence-card').first().evaluate(el=>el.querySelector('.preview').getBoundingClientRect().height>0 && el.querySelector('small').getBoundingClientRect().bottom<=el.getBoundingClientRect().bottom),'Evidence card content must fit inside its border');
    await capture('investigation');
    await page.getByRole('button',{name:'1 Ask',exact:true}).click();
    await capture('ask');
    // Responsive checks for every screen in both media themes.
    await page.setViewportSize({width:390,height:844});
    for(const theme of ['light','dark']) {
      await page.emulateMedia({colorScheme:theme,reducedMotion:'reduce'});
      for(const view of ['1 Ask','2 Investigate','3 Report']) {
        await page.getByRole('button',{name:view,exact:true}).click();await noOverflow();await checkContrast();
      }
      await page.locator('#report .lead-metric button').click();await page.locator('#raw-evidence article').first().waitFor();await noOverflow();
      if(theme==='dark') await capture('evidence_mobile_dark');
    }
    await page.emulateMedia({colorScheme:'light'});
    await page.getByRole('button',{name:'3 Report',exact:true}).click();await capture('report_mobile');
    // Real native EventSource replay + POST overrides + polling from running to complete.
    await page.getByRole('button',{name:'1 Ask',exact:true}).click();
    await page.locator('#monthly-chats').fill('120000');await page.locator('#latency-target').fill('2.5');
    await page.locator('#investigate').click();
    await page.locator('#investigation:not([hidden]) .timeline .running').waitFor();
    await page.waitForFunction(()=>document.querySelector('#experiment-progress').textContent.includes('done ·'));
    assert.deepEqual({company:posted.company,monthly_chats:posted.monthly_chats,latency_target_s:posted.latency_target_s},{company:'samudra',monthly_chats:120000,latency_target_s:2.5});
    assert.equal(await page.locator('.timeline .running').count(),1);
    const evidenceCards=await page.locator('.evidence-card').count();
    finishReport=true;
    await page.waitForFunction(()=>document.querySelector('#stream-status').textContent.includes('Investigation complete'),{},{timeout:15000});
    assert.equal(await page.locator('.evidence-card').count(),evidenceCards,'Reconnect replay must not duplicate evidence');
    await page.locator('.evidence-card').first().click();await page.locator('#raw-evidence article').first().waitFor();
    // Unavailable companies and failed submission have usable recovery states.
    companiesFail=true;await page.reload();await page.locator('#retry-companies:not([hidden])').waitFor();
    assert.equal(await page.locator('#investigate').isDisabled(),true);
    companiesFail=false;await page.locator('#retry-companies').click();await page.locator('.company-card').first().waitFor();
    postFail=true;await page.locator('#investigate').click();await page.locator('#notice:not([hidden])').waitFor();
    assert.equal(await page.locator('#investigate').isEnabled(),true);
    assert.match(await page.locator('#notice').innerText(),/Test queue unavailable/);
    assert.deepEqual(errors,[]);
    console.log(`UI checks passed: ${fixtures.length} saved reports; static assets, native SSE, POST, polling, A/A, dropped claims, partial reports, escaping, archive evidence, 390px light/dark, recovery. Chromium ${browser.version()}`);
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
