/* Record the real offline app at 1x wall-clock speed; replay is explicitly 2x. */
const {chromium}=require('playwright'),fs=require('fs'),path=require('path'),assert=require('assert/strict');
const root=path.resolve(__dirname,'../..'),out=path.join(root,'docs/video/screen'),origin=process.env.POLYTOKEN_VIDEO_ORIGIN||'http://127.0.0.1:8011';
const scenes=JSON.parse(fs.readFileSync(path.join(root,'docs/video/scenes.json'))),only=process.argv[2];
const read=n=>fs.readFileSync(path.join(root,'docs/video',n),'utf8');
const log=r=>fs.appendFileSync(path.join(root,'logs/sample/video_production.jsonl'),JSON.stringify({timestamp:new Date().toISOString(),...r})+'\n');
(async()=>{const b=await chromium.launch({headless:true});
for(const scene of scenes){if(only&&only!==scene.id)continue;
 const ctx=await b.newContext({viewport:{width:1920,height:1080},colorScheme:'dark',recordVideo:{dir:out,size:{width:1920,height:1080}}});
 await ctx.addInitScript(()=>{localStorage.setItem('polytoken.theme','dark');localStorage.setItem('polytoken.currency','INR');document.addEventListener('DOMContentLoaded',()=>{const cursor=document.createElement('div');cursor.id='video-pointer';cursor.style.cssText='position:fixed;left:1750px;top:110px;width:30px;height:30px;border:2px solid #f4c466;border-radius:50%;background:#f4c46633;pointer-events:none;z-index:99999;transform:translate(-50%,-50%);box-shadow:0 0 0 5px #f4c46615';document.body.append(cursor);document.addEventListener('mousemove',e=>{cursor.style.left=e.clientX+'px';cursor.style.top=e.clientY+'px'});});});
 const p=await ctx.newPage(),errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.route('**/*',r=>{assert.equal(new URL(r.request().url()).origin,origin);return r.continue()});
 await p.goto(origin);await p.locator('.fit-company').nth(3).waitFor({timeout:90000});
 const move=async l=>{const box=await l.boundingBox();assert.ok(box);await p.mouse.move(box.x+Math.min(box.width*.5,200),box.y+Math.min(box.height*.5,80),{steps:24});};
 const click=async sel=>{let l=typeof sel==='string'?p.locator(sel):sel;await move(l);await l.click();};
 const smooth=async l=>{await l.evaluate(el=>{const main=document.querySelector('#main');main.scrollTo({top:main.scrollTop+el.getBoundingClientRect().top-main.getBoundingClientRect().top-25,behavior:'smooth'})});await p.waitForTimeout(650);};
 const openFit=async()=>{await p.locator('.fit-company[data-fit-company=raitu] [data-fit-open]').click();await p.locator('#model-fit:not([hidden]) .fit-ranking').waitFor();await p.locator('#replay-speed').selectOption('2');};
 const tab=async t=>click(`[data-console-tab=${t}]`);
 const card=()=>p.locator('.token-row').filter({has:p.locator('h2',{hasText:'unsloth/Llama-3.2-3B-Instruct'})});
 const ratio=()=>p.locator('#token-comparison tr').filter({hasText:'unsloth/Llama-3.2-3B-Instruct'});
 const slide=async n=>{const uri='data:image/png;base64,'+fs.readFileSync(path.join(root,`docs/deck/slides/slide-${String(n).padStart(2,'0')}.png`)).toString('base64');await p.evaluate(src=>{let el=document.createElement('img');el.id='video-slide';el.style.cssText='position:fixed;inset:0;width:100vw;height:100vh;z-index:90000;object-fit:contain;background:#15171c;transition:opacity .4s';el.src=src;document.body.append(el)},uri);};
 const terminal=async(title,text)=>p.evaluate(({title,text})=>{let e=document.getElementById('terminal-capture');if(!e){e=document.createElement('section');e.id='terminal-capture';e.style.cssText='position:fixed;inset:0;background:#15171c;color:#f1f2f5;padding:90px 100px;z-index:90000;font:28px/1.55 monospace;box-sizing:border-box';document.body.append(e)}e.replaceChildren();let h=document.createElement('div');h.style.cssText='font:20px Arial;color:#a5bbff;letter-spacing:2px;margin-bottom:50px';h.textContent=title;let pre=document.createElement('pre');pre.style.cssText='white-space:pre-wrap;font:inherit';pre.textContent=text;e.append(h,pre)}, {title,text});
 if(['s04','s05','s07'].includes(scene.id))await openFit();
 if(scene.id==='s01')await slide(1);
 if(scene.id==='s02')await terminal('RECORDED LOCAL TERMINAL SESSION · FRESH CLONE', '$ git clone --local --no-hardlinks . .cache/video-setup-clone\nCloning into \'.cache/video-setup-clone\'...\ndone.\n\n$ cd .cache/video-setup-clone');
 if(scene.id==='s03'){await p.locator('.rail [data-screen=launcher]').click();await p.locator('#candidate-models input').first().waitFor();}
 if(scene.id==='s04')await smooth(p.locator('.workload-profile'));
 if(scene.id==='s05'){await tab('tokens');await p.locator('#use-token-sample').click();await smooth(p.locator('.token-samples'));}
 if(scene.id==='s06')await smooth(p.locator('.fit-company[data-fit-company=samudra] .fit-cost-pair'));
 if(scene.id==='s07'){await p.locator('.fit-ranking tbody tr').first().locator('[data-claim]').first().click();await p.locator('#raw-evidence article').first().waitFor();await smooth(p.locator('.formula'));}
 if(scene.id==='s08')await slide(12);
 const mark=async color=>{await p.evaluate(color=>{let e=document.createElement('div');e.id='sync-slate';e.style.cssText=`position:fixed;inset:0;z-index:999999;background:${color}`;document.body.append(e)},color);await p.waitForTimeout(450);await p.locator('#sync-slate').evaluate(e=>e.remove());};
 console.log(scene.id+' ready');await mark('#ff00ff');const start=Date.now();
 const at=async(sec,fn)=>{await p.waitForTimeout(Math.max(0,sec*1000-(Date.now()-start)));await fn()};
 const shot=async name=>p.screenshot({path:path.join(root,'docs/video',name+'.png')});
 if(scene.id==='s01'){
  await at(4,async()=>{await p.locator('#video-slide').evaluate(e=>e.style.opacity='0');await p.waitForTimeout(400);await p.locator('#video-slide').evaluate(e=>e.remove())});
  await at(8,()=>move(p.locator('.fit-company[data-fit-company=samudra] .fit-cost-pair')));
  await at(14,()=>smooth(p.locator('.fit-company[data-fit-company=raitu]')));
  await at(19,()=>move(p.locator('.fit-company[data-fit-company=raitu] .fit-cost-pair')));
 }
 if(scene.id==='s02'){
  await at(3,()=>terminal('PROMPT FOR YOUR CODING AGENT', 'Run skills/polytoken-setup/SKILL.md\n\nInterview me about demo or live mode, then guide setup.\n\nCanonical setup skill in the cloned repository.'));
  await at(7,()=>terminal('RECORDED LOCAL TERMINAL SESSION · INSTALLED FRESH CLONE','$ polytoken doctor --port 8012\n\n'+read('setup-doctor.txt')));
  await at(14,()=>terminal('RECORDED LOCAL TERMINAL SESSION · DEMO NEEDS NO KEY','$ polytoken serve --demo --port 8013\n\n'+read('setup-serve.txt')));
 }
 if(scene.id==='s03'){
  await at(1,()=>p.locator('#launch-source').selectOption('raitu'));
  await at(2,async()=>{await click('#company-name');await p.locator('#company-name').fill('');await p.locator('#company-name').pressSequentially('Raitu Mitra',{delay:85})});
  await at(4,()=>move(p.locator('#channel')));
  await at(5,async()=>{await click('#monthly-chats');await p.locator('#monthly-chats').fill('');await p.locator('#monthly-chats').pressSequentially('80000',{delay:150})});
  await at(7,()=>move(p.locator('#launch-source')));
  await at(8.5,()=>click('#investigate'));await p.locator('#replay-controls:not([hidden])').waitFor();
  await p.locator('#replay-speed').selectOption('2');
  await at(11,()=>smooth(p.locator('.circuit-panel')));
  await at(13,async()=>{await click('#replay-play');await click('.rail [data-screen=how-it-works]')});await shot('architecture-recording');
  await at(21,async()=>{await tab('activity');await click('#replay-play')});
  await at(23,()=>smooth(p.locator('.circuit-panel')));
 }
 if(scene.id==='s04'){
  await at(1,()=>move(p.locator('.script-mixture').last()));
  await at(4,()=>smooth(p.locator('.fit-ranking')));
  const llama=p.locator('.fit-ranking tbody tr').filter({hasText:'Llama-3.1-8B-Instruct'});
  await at(5,()=>move(llama.locator('th')));await at(8,()=>move(llama.locator('td').nth(2)));
  await at(11,()=>smooth(p.locator('.fit-recommendation')));
  await at(12,()=>move(p.locator('.fit-recommendation h2')));
  await at(15,()=>smooth(p.locator('.fit-ranking')));
  await at(16,()=>move(p.locator('.fit-ranking tbody tr').first().locator('td').first()));
  await at(18,()=>move(llama.locator('td').first()));
  await at(20,()=>move(llama.locator('td').nth(1)));
  await at(22,()=>move(p.locator('.fit-ranking > .hint')));
  assert.match(await p.locator('.fit-ranking > .hint').innerText(),/Quality: verify on your sample/);
  await shot('s04-quality-and-cost');
 }
 if(scene.id==='s05'){
  await at(2,()=>smooth(card()));await at(3,()=>move(card().locator('.token-pieces')));
  await at(7,()=>smooth(ratio()));await at(8,()=>move(ratio().locator('button')));assert.match(await ratio().innerText(),/6.00×/);
  await at(11,()=>smooth(p.locator('.token-samples')));
  await at(12,()=>p.locator('#token-sample').selectOption('tenglish'));
  await at(13,()=>smooth(ratio()));await at(14,()=>move(ratio().locator('button')));assert.match(await ratio().innerText(),/1.12×/);
  await at(17,()=>smooth(card()));await at(19,()=>move(card().locator('.token-pieces')));
 }
 if(scene.id==='s06'){
  await at(1,()=>move(p.locator('.fit-company[data-fit-company=samudra] .fit-cost-pair')));
  await at(4,()=>smooth(p.locator('.fit-company[data-fit-company=raitu] .fit-cost-pair')));
  await at(7,()=>smooth(p.locator('#companies-ask')));
  await at(9,()=>click('#companies-ask [data-question="Why not the cheapest model?"]'));
  await p.waitForFunction(()=>document.querySelector('#companies-ask .ask-answer').textContent.includes('Llama'));
  await smooth(p.locator('#companies-ask .ask-answer'));
  await at(14,()=>click('#companies-ask [data-question="Is quality verified?"]'));
  await at(17,async()=>{await p.locator('#companies-ask .evidence-question').fill('What will the stock market do tomorrow?');await click('#companies-ask button[type=submit]')});
  await at(19,()=>smooth(p.locator('#companies-ask .ask-answer')));await shot('s06-refusal');
 }
 if(scene.id==='s07'){
  await at(1,()=>move(p.locator('.formula')));
  await at(4,()=>smooth(p.locator('#raw-evidence article').first()));
  await at(9,()=>terminal('RECORDED TEST OUTPUT · PINNED METERLESS CONFORMANCE', '$ pytest -q tests/meterless/test_conformance_*.py\n    -k "not indic_stable_ids"\n\n'+read('conformance.txt')+'\n29 pinned reference checks + one additional Indic-script test.\nThe additional test also passes in the full suite.'));
 }
 const elapsed=(Date.now()-start)/1000;assert.ok(elapsed<scene.duration,`${scene.id} actions ${elapsed} exceed duration ${scene.duration}`);
 await p.waitForTimeout((scene.duration-elapsed)*1000);await mark('#00ffff');assert.deepEqual(errors,[]);
 const v=p.video();await ctx.close();await v.saveAs(path.join(out,scene.id+'-raw.webm'));fs.unlinkSync(await v.path());
 log({event:'scene_recorded',scene:scene.id,ok:true,width:1920,height:1080,theme:'dark',currency:'INR',replay_speed:2,target_duration:scene.duration,quality_label_hold_s:scene.id==='s04'?scene.duration-22:null,errors});console.log(scene.id+' recorded',scene.duration.toFixed(2)+'s');
}
await b.close();})().catch(e=>{console.error(e);process.exit(1)});
