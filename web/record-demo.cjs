/* Real local UI run. No request interception and no synthetic responses. */
const fs=require('node:fs'),path=require('node:path');
const {chromium}=require('playwright');
const root=path.resolve(__dirname,'..'),out=path.join(root,'docs/images'),sample=path.join(root,'logs/sample');
fs.mkdirSync(out,{recursive:true});
const progress=data=>fs.writeFileSync(path.join(root,'.cache/demo-progress.json'),JSON.stringify({...data,at:new Date().toISOString()}));
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1040},colorScheme:'light',reducedMotion:'reduce'});
  await page.goto('http://127.0.0.1:8000/');await page.locator('.company-card').first().waitFor({timeout:30000});
  await page.locator('[data-company="samudra"]').click();
  await page.screenshot({path:path.join(out,'demo_ask.png'),fullPage:true});
  let report,events,id;
  if(process.argv.includes('--capture-existing')){
   report=JSON.parse(fs.readFileSync(path.join(sample,'demo_samudra_report.json'),'utf8'));id=report.id;
   events=fs.readFileSync(path.join(sample,'demo_samudra.jsonl'),'utf8').trim().split('\n').map(JSON.parse);
   await page.locator('#saved-files').setInputFiles(['demo_samudra_report.json','demo_samudra.jsonl','demo_samudra_world_events.jsonl.gz'].map(f=>path.join(sample,f)));
   await page.locator('#report:not([hidden]) #report-title').waitFor({timeout:60000});
  }else{
   if(fs.existsSync(path.join(sample,'demo_samudra_report.json')))throw Error('Demo archive already exists; use --capture-existing to refresh screenshots without a new investigation.');
  const started=page.waitForResponse(r=>r.url().endsWith('/investigations') && r.request().method()==='POST');
  await page.locator('#investigate').click();({id}=await (await started).json());
  progress({id,status:'running'});console.log('Demo started',id);
  const eventResponse=await fetch(`http://127.0.0.1:8000/investigations/${id}/events`);
  const eventPromise=eventResponse.text();
  await page.locator('#investigation:not([hidden])').waitFor();
  await page.screenshot({path:path.join(out,'demo_investigation_running.png'),fullPage:true});
  const deadline=Date.now()+37*60*1000;
  while(Date.now()<deadline){
   const response=await fetch(`http://127.0.0.1:8000/investigations/${id}/report`);
   const value=await response.json();
   progress({id,status:value.status || 'starting',job_status:value.jobs?.status});
   if(response.status===200 && ['complete','partial'].includes(value.status)){report=value;break;}
   await new Promise(resolve=>setTimeout(resolve,2500));
  }
  if(!report)throw Error('Demo exceeded the reasoning and background deadlines');
  events=(await eventPromise).split('\n').filter(line=>line.startsWith('data: ')).map(line=>JSON.parse(line.slice(6)));
  fs.writeFileSync(path.join(sample,'demo_samudra.jsonl'),events.map(e=>JSON.stringify(e)).join('\n')+'\n');
  fs.writeFileSync(path.join(sample,'demo_samudra_report.json'),JSON.stringify(report,null,2)+'\n');
  }
  await page.waitForFunction(()=>document.querySelector('[data-screen="report"]').disabled===false);
  await page.getByRole('button',{name:'3 Report',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#report').dataset.billingStatus!=='loading',null,{timeout:60000});
  await page.screenshot({path:path.join(out,'demo_report.png'),fullPage:true});
  await page.screenshot({path:path.join(out,'demo_report_summary.png'),fullPage:false});
  await page.getByRole('button',{name:'2 Investigate',exact:true}).click();
  await page.screenshot({path:path.join(out,'demo_investigation.png'),fullPage:true});
  await page.getByRole('button',{name:'4 Token strip',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('#token-status').textContent.startsWith('Local inspection complete'),null,{timeout:120000});
  await page.screenshot({path:path.join(out,'demo_tokens.png'),fullPage:true});
  await page.getByRole('button',{name:'3 Report',exact:true}).click();
  await page.locator('#report-title .metric').click();await page.locator('#raw-evidence article').first().waitFor({timeout:60000});
  await page.screenshot({path:path.join(out,'demo_evidence.png'),fullPage:true});
  progress({id,status:report.status,done:true,quality:report.quality_interpretation,event_count:events.length});
  console.log(JSON.stringify({id,status:report.status,events:events.length,quality:report.quality_interpretation}));
 }finally{await browser.close();}
})().catch(error=>{console.error(error);progress({status:'failed',error:error.message});process.exitCode=1;});
