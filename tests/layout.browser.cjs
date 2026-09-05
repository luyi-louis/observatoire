// Optional: PLAYWRIGHT_PATH=/path/to/playwright PLAYWRIGHT_BROWSERS_PATH=/path/to/browsers node tests/layout.browser.cjs
const {chromium}=require(process.env.PLAYWRIGHT_PATH||'playwright');
const {pathToFileURL}=require('node:url'),path=require('node:path'),assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1200}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(pathToFileURL(path.join(__dirname,'..','Observatoire.html')).href);
  await page.locator('#price .plot-frame').waitFor();
  assert.equal(await page.locator('#seriesSelect').inputValue(),'usgs_or');
  assert.equal(await page.locator('#start').inputValue(),'1900');
  assert.ok((await page.locator('#seriesMeaning').textContent()).includes('Engelhard'));
  assert.ok((await page.locator('#riskInfo').textContent()).includes('√1'));
  assert.ok((await page.locator('#price desc').textContent()).includes('pondération'));
  await page.locator('#seriesSelect').selectOption('wb_or');
  assert.equal(await page.locator('#start').inputValue(),'1960-01');
  await page.locator('#seriesSelect').selectOption('usgs_or');
  const [price,momentum,risk]=await page.locator('.graph-layout .chartcard').evaluateAll(es=>es.map(e=>{const r=e.getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height}}));
  assert.equal(price.y,momentum.y);assert.equal(momentum.x,risk.x);assert.ok(price.x<momentum.x);
  assert.ok(Math.abs(price.y+price.h-risk.y-risk.h)<2);
  assert.equal(await page.locator('.plot-frame').count(),3);
  for(const id of ['momentum','risk'])assert.equal(await page.locator('#'+id+' path').first().getAttribute('stroke'),'#000000');
  await page.locator('#sma').uncheck();assert.equal(await page.locator('#price path').first().getAttribute('stroke'),'#000000');
  await page.locator('#languageSelect').selectOption('ru');
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth-innerWidth),0);
  await page.locator('#sourcesTab').click();assert.equal(await page.locator('#archiveSelect option').count(),8);
  assert.deepEqual(errors,[]);
  console.log('OK : disposition sur deux colonnes, cadres, courbes noires, russe, mobile et archives autonomes.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
