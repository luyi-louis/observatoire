// Optional DOM integration test: see locales/README.md.
const {JSDOM}=require(process.env.JSDOM_PATH || 'jsdom');
const fs=require('node:fs'),assert=require('node:assert/strict');
const html=fs.readFileSync(require('node:path').join(__dirname,'..','Observatoire.html'),'utf8');let blob;
const dom=new JSDOM(html,{runScripts:'dangerously',url:'http://127.0.0.1:8765',beforeParse(w){
 w.ResizeObserver=class{observe(){}};Object.defineProperty(w.HTMLElement.prototype,'clientWidth',{get(){return 1120}});
 w.URL.createObjectURL=b=>{blob=b;return 'blob:test'};w.URL.revokeObjectURL=()=>{};w.Blob=Blob;
 w.HTMLAnchorElement.prototype.click=function(){};
}});
const w=dom.window,$=id=>w.document.getElementById(id),run=s=>w.eval(s);
const EMBEDDED=run('DATA.or.length');
assert.ok($('languageSelect').options.length>=3);
assert.ok([...$('languageSelect').options].some(o=>o.value==='ru'&&o.textContent==='Русский'));
assert.equal($('start').value,'1900');assert.equal($('seriesSelect').value,'usgs_or');
$('seriesSelect').value='insee_or';$('seriesSelect').dispatchEvent(new w.Event('change'));
const dataBefore=run('JSON.stringify(DATA)');
$('start').value='2022-01';$('end').value='2025-12';$('rsiPeriod').value=7;run('render();showPage("method");setLanguage("en")');
assert.equal(w.document.documentElement.lang,'en');
assert.equal(w.localStorage.getItem('observatoire.language'),'en');
assert.equal($('methodTab').textContent,'Settings & calculation methods');
assert.equal($('methodPage').hidden,false);assert.equal($('start').value,'2022-01');assert.equal($('rsiPeriod').value,'7');
assert.ok($('m-adf').textContent.includes('The null hypothesis'));
assert.equal(run('JSON.stringify(DATA)'),dataBefore);
run('showPage("analysis")');assert.ok($('price').textContent.includes('Gold — monthly prices'));assert.ok($('price').textContent.includes('USD / troy oz'));
assert.ok($('momentum').textContent.includes('RSI · 7 months'));
assert.equal(run('fmt(1234.5)'), '1,234.50');
run('exportFigure("price")');
(async()=>{
 const svg=await blob.text();assert.ok(svg.includes('Gold — monthly prices'));assert.ok(!svg.includes('cours mensuel'));
 if(process.env.SVG_PREVIEW)fs.writeFileSync(process.env.SVG_PREVIEW,svg);
 // Existing error messages are retranslated, not merely future errors.
 run(`try{parseCSV('date,price\\n2020-01,0\\n2020-02,10')}catch(e){setError('importError',e)}`);
 assert.ok($('importError').textContent.startsWith('Row 2:'));
 run('setLanguage("fr")');assert.ok($('importError').textContent.startsWith('Ligne 2'));
 // Russian translates existing state as well as the scientific SVG output.
 run('setLanguage("ru")');
 assert.equal(w.document.documentElement.lang,'ru');
 assert.equal(w.localStorage.getItem('observatoire.language'),'ru');
 assert.equal($('methodTab').textContent,'Настройки и методика расчёта');
 assert.ok($('m-adf').textContent.includes('Нулевая гипотеза'));
 assert.ok($('importError').textContent.startsWith('Строка 2:'));
 assert.equal(run('fmt(1234.5)'), '1\u00a0234,50');
 assert.equal($('start').value,'2022-01');assert.equal(run('JSON.stringify(DATA)'),dataBefore);
 assert.ok($('price').textContent.includes('Золото — месячные цены'));
 run('exportFigure("price")');const russianSvg=await blob.text();
 assert.ok(russianSvg.includes('Дата [год]'));assert.ok(!russianSvg.includes('Gold —'));
 if(process.env.RU_SVG_PREVIEW)fs.writeFileSync(process.env.RU_SVG_PREVIEW,russianSvg);
 run('setLanguage("fr")');

 // Official package preview, status and applied state survive language changes.
 run(`window.testPack={format:'observatoire-insee-v1',retrievedAt:'2026-09-05T08:00:00Z',series:Object.fromEntries(Object.entries(OFFICIAL_IDS).map(([k,id])=>[k,{idbank:id,unit:OFFICIAL_UNITS[k],rows:[{date:'2026-01',price:100},{date:'2026-02',price:110}]}]))};previewOfficial(testPack);showPage('sources');`);
 $('applyOfficial').click();assert.equal($('applyOfficial').disabled,true);run('setLanguage("en")');assert.equal($('applyOfficial').disabled,true);assert.ok($('updateStatus').textContent.startsWith('The complete histories (INSEE and bitcoin)'));
 assert.ok($('provenance').textContent.includes('USD / barrel'));
 // Filtering and a partial update never truncate saved history; restoring restores revisions.
 assert.equal(run('DATA.or.length'),EMBEDDED);
 assert.equal(JSON.parse(w.localStorage.getItem('observatoire.history.v1')).series.or.rows[0].date,'1990-01');
 run("setRange(1);testPack.retrievedAt='2027-01-01T00:00:00Z';previewOfficial(testPack)");$('applyOfficial').click();
 assert.equal(run("DATA.or.find(r=>r.date==='2026-01').price"),100);
 run("DATA.or=[];restoreHistory()");
 assert.equal(run('DATA.or.length'),EMBEDDED);assert.equal(run("DATA.or.find(r=>r.date==='2026-01').price"),100);
 // A fresh page restores the complete saved history, including revised prices.
 const savedHistory=w.localStorage.getItem('observatoire.history.v1');
 const reloaded=new JSDOM(html,{runScripts:'dangerously',url:'http://127.0.0.1:8765',beforeParse(other){
  other.ResizeObserver=class{observe(){}};
  other.localStorage.setItem('observatoire.history.v1',savedHistory);
 }});
 assert.equal(reloaded.window.eval('DATA.or.length'),EMBEDDED);
 assert.equal(reloaded.window.eval("DATA.or.find(r=>r.date==='2026-01').price"),100);
 assert.equal(reloaded.window.document.getElementById('start').value,'1900');
 reloaded.window.close();
 // Archived annual series remain annual in standalone downloads and translate fully.
 run("showPage('sources');setLanguage('en')");
 assert.equal($('archiveSelect').options.length,8);
 $('archiveSelect').value='usgs_or';$('archiveSelect').dispatchEvent(new w.Event('change'));
 assert.ok($('archiveDetail').textContent.includes('1900 → 2022'));
 assert.ok($('archiveDetail').textContent.includes('Annual'));
 $('archiveDownload').click();const archiveCSV=await blob.text();
 assert.ok(archiveCSV.startsWith('year,price\n1900,609000\n'));
 assert.equal(archiveCSV.trim().split('\n').length,124);
 run("setLanguage('ru')");assert.equal($('archiveSelect').value,'usgs_or');
 assert.ok($('archiveDetail').textContent.includes('Годовые данные'));
 assert.equal($('sourcesPage').contains($('archiveSelect')),true);
 // Analysis exports identify the displayed mass unit; archived originals stay unchanged.
 run("asset='or';chosenSeries.or='usgs_or';goldMassUnit='gram';setRange(0);showPage('analysis')");
 $('exportBtn').click();const gramCSV=await blob.text();
 assert.ok(gramCSV.startsWith('source;frequency;unit;date;price;'));
 assert.ok(gramCSV.includes('"usgs_or";"A";"USD / gramme";"1900";"0,609"'));
 assert.ok($('price').textContent.includes('USD / грамм'));
 run("chosenSeries.or='insee_or';goldMassUnit='ounce';setRange(0)");
 // Help tab: one card per indicator, opened from the tabs or from the "?" of each chart.
 run("setLanguage('fr')");assert.equal(w.document.querySelectorAll('#helpPage .help-card').length,9);
 $('helpTab').click();assert.equal($('helpPage').hidden,false);assert.equal($('analysisPage').hidden,true);
 assert.ok($('h-rsi').textContent.includes('RSI = 100 − 100 / (1 + RS)'));
 assert.ok($('helpPage').querySelector('.intro').textContent.includes('«\u00a0Paramètres & méthode de calcul\u00a0»'));
 run("showPage('analysis')");w.document.querySelector('[data-help="momentum"]').click();
 assert.equal($('helpPage').hidden,false);assert.equal(w.document.activeElement.id,'h-rsi');
 run("showPage('analysis');momentum='macd';render()");w.document.querySelector('[data-help="momentum"]').click();assert.equal(w.document.activeElement.id,'h-macd');
 w.document.querySelector('#h-macd .help-more').dispatchEvent(new w.MouseEvent('click',{bubbles:true,cancelable:true}));assert.equal($('methodPage').hidden,false);
 run("setLanguage('en')");assert.equal($('helpTab').textContent,'Help');assert.ok($('h-macd').textContent.includes('MACD = EMA12 − EMA26'));
 run("setLanguage('ru')");assert.equal($('helpTab').textContent,'Справка');assert.equal($('themeSelect').options[2].textContent,'Тёмная');
 run("momentum='rsi';setLanguage('fr');showPage('analysis')");
 // Dark theme: tokens and chart palette follow the choice; the exported SVG keeps the light figure palette.
 $('themeSelect').value='dark';$('themeSelect').dispatchEvent(new w.Event('change'));
 assert.equal(w.document.documentElement.dataset.theme,'dark');assert.equal(w.localStorage.getItem('observatoire.theme'),'dark');
 assert.equal(run('SCI===SCI_DARK'),true);assert.ok($('price').innerHTML.includes('fill="#171f1c"'));
 run('exportFigure("price")');const darkExport=await blob.text();
 assert.ok(darkExport.includes('fill="white"'));assert.ok(!darkExport.includes('#171f1c'));
 assert.ok($('price').innerHTML.includes('fill="#171f1c"'));
 $('themeSelect').value='auto';$('themeSelect').dispatchEvent(new w.Event('change'));
 assert.equal(w.document.documentElement.dataset.theme,undefined);assert.equal(run('SCI===SCI_LIGHT'),true);
 // Free ratio: any numerator and denominator, unit deduced; bitcoin is an asset of its own.
 run("setLanguage('fr');showPage('analysis')");
 assert.deepEqual([...$('assets').children].map(b=>b.textContent).slice(-2),['Bitcoin','Ratio']);
 [...$('assets').children].at(-1).click();
 assert.equal($('ratioControls').hidden,false);assert.equal($('seriesSelect').hidden,true);
 assert.equal($('ratioNum').value,'insee_or');assert.equal($('ratioDen').value,'insee_argent');
 $('ratioDen').value='bitstamp_bitcoin';$('ratioDen').dispatchEvent(new w.Event('change'));
 assert.ok($('priceTitle').textContent.startsWith('Or / Bitcoin · bitcoin / once troy'));
 assert.ok($('price').textContent.includes('Ratio Or / Bitcoin [bitcoin / once troy]'));
 assert.match($('metrics').querySelector('.value').textContent,/^0,0\d{3}$/);
 $('ratioSwap').click();assert.ok($('priceTitle').textContent.startsWith('Bitcoin / Or · once troy / bitcoin'));
 run("setLanguage('en')");assert.ok($('priceTitle').textContent.startsWith('Bitcoin / Gold · troy oz / bitcoin'));
 run("setLanguage('fr')");$('ratioNum').value='usgs_or';$('ratioNum').dispatchEvent(new w.Event('change'));
 assert.ok($('status').textContent.startsWith('Les deux séries du ratio'));assert.equal($('ratioControls').hidden,false);
 run("setLanguage('ru')");assert.ok($('status').textContent.startsWith('У двух рядов отношения'));
 run("setLanguage('fr');ratioPair.num='insee_or';ratioPair.den='insee_argent';asset='or';nav();setRange(0)");
 assert.equal($('ratioControls').hidden,true);assert.equal($('seriesSelect').hidden,false);
 // The registry accepts further complete locales without a fixed language switch.
 run(`I18N_CATALOGS.es={...I18N_CATALOGS.en,label:'Test language',locale:'es-ES',messages:Object.fromEntries(Object.entries(I18N_CATALOGS.en.messages).map(([k,v])=>[k,'⟦'+v+'⟧']))};setLanguage('es');`);
 assert.equal(w.document.documentElement.lang,'es');assert.ok($('methodTab').textContent.startsWith('⟦'));
 assert.ok($('updateStatus').textContent.startsWith('⟦'));
 run('showPage("analysis")');assert.ok($('price').textContent.includes('⟦Price ['));
 console.log('OK: DOM FR/EN/RU, complete guide, figures, numeric locale, errors, imports, unchanged state, SVG export, help tab, dark theme and an additional language.');w.close();
})().catch(e=>{console.error(e);process.exitCode=1;w.close()});
