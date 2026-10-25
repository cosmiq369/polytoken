/* Real offline app, no mocked data. Magenta/cyan slates give exact trim boundaries. */
const {chromium}=require('playwright'),fs=require('fs'),path=require('path'),assert=require('assert/strict');
const root=path.resolve(__dirname,'../..'),out=path.join(root,'docs/video/screen'),origin='http://127.0.0.1:8000';
const scenes=JSON.parse(fs.readFileSync(path.join(root,'docs/video/scenes.json'))),only=process.argv[2];
const native='నేను దీవి ప్లాన్ వాడుతున్నాను. బిల్లులో ఖర్చు అర్థం కాలేదు.',mixed='Nenu Deevi plan use chestunna. Bill lo charge ardham kaledu.';
const log=r=>fs.appendFileSync(path.join(root,'logs/sample/video_production.jsonl'),JSON.stringify({timestamp:new Date().toISOString(),...r})+'\n');
(async()=>{const b=await chromium.launch({headless:true});
for(const scene of scenes){if(only&&only!==scene.id)continue;
 const ctx=await b.newContext({viewport:{width:1920,height:1080},colorScheme:'dark',recordVideo:{dir:out,size:{width:1920,height:1080}}});
 await ctx.addInitScript(()=>{localStorage.setItem('polytoken.theme','dark');localStorage.setItem('polytoken.currency','INR');document.addEventListener('DOMContentLoaded',()=>{const cursor=document.createElement('div');cursor.id='video-pointer';cursor.style.cssText='position:fixed;left:1750px;top:110px;width:30px;height:30px;border:2px solid #f4c466;border-radius:50%;background:#f4c46633;pointer-events:none;z-index:99999;transform:translate(-50%,-50%);box-shadow:0 0 0 5px #f4c46615';document.body.append(cursor);document.addEventListener('mousemove',e=>{cursor.style.left=e.clientX+'px';cursor.style.top=e.clientY+'px'});document.addEventListener('mousedown',()=>cursor.style.background='#f4c46699');document.addEventListener('mouseup',()=>cursor.style.background='#f4c46633');});});
 const p=await ctx.newPage(),errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.route('**/*',r=>{assert.equal(new URL(r.request().url()).origin,origin);return r.continue()});
 await p.goto(origin);await p.locator('.fit-company').nth(3).waitFor({timeout:90000});
 const move=async l=>{const box=await l.boundingBox();assert.ok(box);await p.mouse.move(box.x+Math.min(box.width*.5,200),box.y+Math.min(box.height*.5,80),{steps:24});};
 const click=async sel=>{let l=typeof sel==='string'?p.locator(sel):sel;await move(l);await p.waitForTimeout(180);await l.click();};
 const smooth=async l=>{await l.evaluate(el=>{const main=document.querySelector('#main');const offset=el.getBoundingClientRect().top-main.getBoundingClientRect().top;main.scrollTo({top:main.scrollTop+offset-45,behavior:'smooth'})});await p.waitForTimeout(850);};
 const top=async()=>{await p.locator('#main').evaluate(el=>el.scrollTo({top:0,behavior:'smooth'}));await p.waitForTimeout(850)};
 const openFit=async()=>{await p.locator('.fit-company[data-fit-company=raitu] [data-fit-open]').click();await p.waitForFunction(()=>window.polyConsole.state.report?.company==='raitu',null,{timeout:90000});await p.locator('#model-fit:not([hidden]) .fit-ranking').waitFor();await p.locator('#replay-speed').selectOption('2');};
 const tab=async t=>click(`[data-console-tab=${t}]`);
 const card=spec=>p.locator('.token-row').filter({has:p.locator('h2',{hasText:spec})});
 if(!['s01','s05','s07'].includes(scene.id))await openFit();
 if(scene.id==='s02'){
  await p.locator('[data-console-tab=tokens]').click();await p.locator('#token-text').fill(native);await p.locator('#token-form button[type=submit]').click();await p.waitForFunction(()=>document.querySelector('#token-status').textContent.startsWith('Local inspection complete'),null,{timeout:90000});
  assert.match(await card('unsloth/Llama-3.2-3B-Instruct').innerText(),/102 tokens/);assert.match(await card('sarvamai/sarvam-1').innerText(),/17 tokens/);await smooth(card('unsloth/Llama-3.2-3B-Instruct'));
 }
 if(scene.id==='s03'){await p.locator('[data-console-tab=activity]').click();await p.locator('#replay-position').fill('0');await top();}
 if(scene.id==='s06'){
  await p.locator('.fit-ranking tbody tr').first().locator('[data-claim]').first().click();await p.locator('#raw-evidence article').first().waitFor({timeout:90000});assert.match(await p.locator('.formula').innerText(),/billed input tokens.*sample conversations/);await top();
 }
 const slide=async n=>{const uri='data:image/png;base64,'+fs.readFileSync(path.join(root,`docs/deck/slides/slide-${String(n).padStart(2,'0')}.png`)).toString('base64');await p.evaluate(src=>{let el=document.getElementById('video-slide');if(!el){el=document.createElement('img');el.id='video-slide';el.style.cssText='position:fixed;inset:0;width:100vw;height:100vh;z-index:90000;object-fit:contain;background:#15171c';document.body.append(el)}el.src=src;},uri);};
 if(scene.id==='s07')await slide(9);
 const mark=async color=>{await p.evaluate(color=>{let e=document.createElement('div');e.id='sync-slate';e.style.cssText=`position:fixed;inset:0;z-index:999999;background:${color}`;document.body.append(e)},color);await p.waitForTimeout(450);await p.locator('#sync-slate').evaluate(e=>e.remove());};
 await mark('#ff00ff');const start=Date.now();
 const at=async(sec,fn)=>{await p.waitForTimeout(Math.max(0,sec*1000-(Date.now()-start)));await fn()};
 if(scene.id==='s01'){
  await at(1,()=>move(p.locator('.fit-company[data-fit-company=samudra] .fit-cost-pair .fit-metric').first()));
  await at(5,()=>smooth(p.locator('.fit-company[data-fit-company=raitu]')));
  await at(8,()=>move(p.locator('.fit-company[data-fit-company=raitu] .fit-cost-pair .fit-metric').first()));
  await at(scene.duration-4,()=>slide(1));
 }
 if(scene.id==='s02'){
  await at(1,()=>move(card('unsloth/Llama-3.2-3B-Instruct').locator('.token-stats')));
  await at(7.5,()=>smooth(card('sarvamai/sarvam-1')));await at(8.5,()=>move(card('sarvamai/sarvam-1').locator('.token-stats')));
  await at(12,async()=>{await top();await click('#token-text');await p.locator('#token-text').fill(mixed);await click('#token-form button[type=submit]');});
  await p.waitForFunction(()=>document.querySelector('#token-status').textContent.startsWith('Local inspection complete'),null,{timeout:90000});
  await smooth(card('unsloth/Llama-3.2-3B-Instruct'));assert.match(await card('unsloth/Llama-3.2-3B-Instruct').innerText(),/19 tokens/);await move(card('unsloth/Llama-3.2-3B-Instruct').locator('.token-stats'));
 }
 if(scene.id==='s03'){
  await at(.8,()=>click('#replay-play'));await at(3,()=>smooth(p.locator('.circuit-panel')));
  await at(6,()=>move(p.locator('[data-node=company]')));await at(10,()=>move(p.locator('[data-node=nvidia]')));
  await at(14,()=>tab('trace'));await at(15,()=>click(p.locator('.trace-step>summary').first()));
  await at(22,()=>tab('activity'));await smooth(p.locator('.circuit-panel'));
  await at(25,()=>move(p.locator('[data-node=world]')));await at(29,()=>move(p.locator('[data-node=checker]')));
 }
 if(scene.id==='s04'){
  await at(1,()=>move(p.locator('.workload-profile .script-mixture'))).catch(async()=>move(p.locator('.workload-profile')));
  await at(7,()=>smooth(p.locator('.fit-ranking')));const llama=p.locator('.fit-ranking tbody tr').filter({hasText:'Llama-3.1-8B-Instruct'});
  await at(10,()=>move(llama.locator('td').nth(2)));await at(14,()=>move(llama.locator('td').nth(1)));
  await at(18,()=>move(p.locator('.fit-ranking tbody tr').first().locator('td').first()));
  await at(23,top);await at(26,()=>move(p.locator('.fit-recommendation')));
 }
 if(scene.id==='s05'){
  await at(1,()=>move(p.locator('.fit-company[data-fit-company=samudra] .fit-cost-pair'))).catch(async()=>move(p.locator('.fit-company[data-fit-company=samudra]')));
  await at(6,()=>move(p.locator('.fit-company[data-fit-company=swara] .fit-cost-pair .fit-metric').first()));
  await at(9,()=>smooth(p.locator('.fit-company[data-fit-company=raitu]')));
  await at(12,()=>move(p.locator('.fit-company[data-fit-company=paisa] .fit-cost-pair .fit-metric').first()));
  await at(16,()=>move(p.locator('.fit-company[data-fit-company=raitu] .fit-cost-pair .fit-metric').first()));
 }
 if(scene.id==='s06'){
  await at(1,()=>move(p.locator('.formula')));await at(5,()=>smooth(p.locator('#raw-evidence article').first()));
  await at(7,()=>move(p.locator('#raw-evidence article').first().locator('dd').nth(1)));
  await at(12,()=>tab('evidence'));
 }
 if(scene.id==='s07')await at(scene.duration-5,()=>slide(1));
 const elapsed=(Date.now()-start)/1000;assert.ok(elapsed<scene.duration,`${scene.id} actions ${elapsed} exceed duration ${scene.duration}`);
 await p.waitForTimeout((scene.duration-elapsed)*1000);await mark('#00ffff');
 assert.deepEqual(errors,[]);const v=p.video();await ctx.close();await v.saveAs(path.join(out,scene.id+'-raw.webm'));fs.unlinkSync(await v.path());
 log({event:'scene_recorded',scene:scene.id,ok:true,width:1920,height:1080,theme:'dark',currency:'INR',replay_speed:2,target_duration:scene.duration,errors});console.log(scene.id+' recorded',scene.duration.toFixed(2)+'s');
}
await b.close();})().catch(e=>{console.error(e);process.exit(1)});
