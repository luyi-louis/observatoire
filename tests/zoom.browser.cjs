const {chromium}=require(process.env.PLAYWRIGHT_PATH||'playwright');
const {pathToFileURL}=require('node:url'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{const browser=await chromium.launch();try{
 const p=await browser.newPage({viewport:{width:1440,height:1300}}),errors=[];p.on('pageerror',e=>errors.push(e.message));
 await p.goto(pathToFileURL(path.join(__dirname,'..','Observatoire.html')).href);
 assert.equal(await p.locator('#goldUnit').inputValue(),'ounce');
 const ounce=await p.evaluate(()=>visible[0].price);assert.ok(Math.abs(ounce-609000*31.1034768/1e6)<1e-12);
 const dataBefore=await p.evaluate(()=>JSON.stringify(EARLY_HISTORIES));
 await p.locator('#goldUnit').selectOption('gram');const gram=await p.evaluate(()=>visible[0].price);assert.ok(Math.abs(ounce/gram-31.1034768)<1e-12);
 assert.ok((await p.locator('#priceTitle').textContent()).includes('gramme'));
 await p.locator('#goldUnit').selectOption('ounce');
 const domains=()=>p.evaluate(()=>Object.fromEntries(['price','momentum','risk'].map(id=>[id,{x:JSON.parse(document.getElementById(id).dataset.xDomain),y:JSON.parse(document.getElementById(id).dataset.yDomain)}])));
 const span=a=>a[1]-a[0];
 async function wheel(id){await p.locator('#'+id).scrollIntoViewIfNeeded();const r=await p.locator('#'+id+' .plot-frame').boundingBox();await p.mouse.move(r.x+r.width*.6,r.y+r.height*.5);await p.mouse.wheel(0,-300);await p.waitForTimeout(150)}
 const original=await domains();await wheel('price');let after=await domains();
 for(const id of ['price','momentum','risk']){assert.ok(span(after[id].x)<span(original[id].x));assert.deepEqual(after[id].y,original[id].y)}
 assert.deepEqual(after.price.x,after.risk.x);
 await p.locator('#zoomReset').click();await p.locator('#zoomSync').click();await p.locator('[data-zoom-axis="y"]').click();await wheel('risk');after=await domains();
 assert.deepEqual(after.price,original.price);assert.deepEqual(after.momentum,original.momentum);assert.deepEqual(after.risk.x,original.risk.x);assert.ok(span(after.risk.y)<span(original.risk.y));
 await p.locator('#zoomReset').click();await p.locator('[data-zoom-axis="xy"]').click();
 await p.locator('#price').scrollIntoViewIfNeeded();const r=await p.locator('#price .plot-frame').boundingBox();
 await p.mouse.move(r.x+r.width*.2,r.y+r.height*.2);await p.mouse.down();await p.mouse.move(r.x+r.width*.8,r.y+r.height*.8,{steps:5});await p.mouse.up();after=await domains();
 assert.ok(span(after.price.x)<span(original.price.x));assert.ok(span(after.price.y)<span(original.price.y));assert.deepEqual(after.risk,original.risk);
 await p.locator('#languageSelect').selectOption('en');assert.deepEqual((await domains()).price,after.price);
 await p.locator('#zoomReset').click();await p.locator('#scale').selectOption('log');await p.locator('[data-zoom-axis="y"]').click();await wheel('price');after=await domains();assert.ok(after.price.y[0]>0);
 await p.locator('#zoomSync').click();const normalized=await p.evaluate(()=>JSON.stringify(zoomWindows));assert.ok(normalized);after=await domains();assert.ok(after.price.y[0]>0);
 assert.equal(await p.evaluate(()=>JSON.stringify(EARLY_HISTORIES)),dataBefore);
 assert.equal(await p.evaluate(()=>visible.length),123);
 await p.locator('#zoomReset').click();await p.locator('.graph-layout').screenshot({path:'/tmp/gold-ounce-zoom.png'});
 assert.deepEqual(errors,[]);console.log('OK : conversion once/gramme, zoom X/Y/XY, synchronisation, sélection, logarithme, traduction et données intactes.');
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
