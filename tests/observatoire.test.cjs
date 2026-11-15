// Exécution : node tests/observatoire.test.cjs
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '..', 'Observatoire.html'), 'utf8');
const source = html.split('<script>')[1].split('</script>')[0];
// Les fonctions sont testées indépendamment du navigateur.
const context = vm.createContext({});
vm.runInContext(source.slice(0, source.indexOf("$('importBtn').onclick")), context);
const run = code => vm.runInContext(code, context);
// Embedded snapshot: whatever the last collection, four aligned monthly series from 1990-01.
const EMBEDDED=run('DATA.or.length'),LAST=run('DATA.or.at(-1).date');
const NEXT=run(`(()=>{const m=monthIndex(${JSON.stringify(LAST)})+1;return String(Math.floor(m/12))+'-'+String(m%12+1).padStart(2,'0')})()`);
assert.ok(EMBEDDED>=439);assert.equal(run('DATA.or[0].date'),'1990-01');
for (const k of ['argent','brent','cuivre']) assert.equal(run(`DATA.${k}.length`),EMBEDDED);
assert.equal(run("parseCSV('date;prix\\n2020-02;12,5\\n2020-01;10,0')[0].price"), 10);
assert.equal(run('parseCSV(\'"Période";"Valeur"\\n"2020-01";"10"\\n"2020-02";"11"\').length'), 2);
for (const csv of ['date,prix\n2020-01,10\n2020-03,12','date,prix\n2020-01,10\n2020-01,12','date,prix\n2020-01,-1\n2020-02,12','date,prix\n2020-13,10\n2020-02,12']) {
  assert.throws(() => run(`parseCSV(${JSON.stringify(csv)})`));
}
run(`const rising=Array.from({length:40},(_,i)=>({date:String(2020+Math.floor(i/12))+'-'+String(i%12+1).padStart(2,'0'),price:100*1.01**i}));const calc=calculate(rising,14,20,12);`);
assert.equal(run('calc[13].rsi'), null);
assert.equal(run('calc[14].rsi'), 100);
assert.equal(run('calc[10].s12'), null);
assert.ok(Math.abs(run('calc[11].s12') - run('avg(rising.slice(0,12).map(r=>r.price))')) < 1e-10);
assert.ok(Math.abs(run('calc[20].vol')) < 1e-10);
assert.equal(run('calc[18].upper'), null);
assert.ok(run('calc[19].upper > calc[19].mid && calc[19].lower < calc[19].mid'));
assert.equal(run('calculate(rising.map(r=>({...r,price:100})),14,20,12)[20].rsi'), 50);
assert.equal(run('calculate(rising.map((r,i)=>({...r,price:100-i})),14,20,12)[20].rsi'), 0);
assert.equal(run("monthIndex('2026-01')-monthIndex('2020-01')"), 72);
assert.equal(run("asset='ratio';getRows().length"), EMBEDDED);
assert.ok(!/<script[^>]+src=|<link[^>]+href=/i.test(html), 'Aucune dépendance distante');
console.log('OK : données, CSV, validation, SMA, RSI, Bollinger, volatilité, ratio et autonomie.');
// Le chargement d'une collecte exige les quatre séries et des unités cohérentes.
run(`const packageFixture={format:'observatoire-insee-v1',retrievedAt:'2026-09-05T00:00:00Z',series:Object.fromEntries(Object.entries(OFFICIAL_IDS).map(([k,id])=>[k,{idbank:id,unit:OFFICIAL_UNITS[k],rows:[{date:'2026-01',price:100},{date:'2026-02',price:110}]}]))};`);
assert.equal(run('validateOfficial(packageFixture).series.or.rows.length'), 2);
for (const mutation of ["delete p.series.or", "p.series.argent.unit='cents'", "p.series.or.rows[1].date='2026-04'", "p.series.or.rows[0].price=-1", "p.series.or.idbank='000000000'"]) {
  assert.throws(() => run(`(()=>{const p=JSON.parse(JSON.stringify(packageFixture));${mutation};return validateOfficial(p)})()`));
}
assert.equal(run('DATA.or.length'), EMBEDDED, 'La validation ne remplace pas les données');
console.log('OK : validation des collectes officielles et conservation des données en cas d’erreur.');
// Les domaines scientifiques conservent zéro et les contraintes de chaque indicateur.
assert.ok(run('axisDomain([100,110],{zero:true}).lo === 0'));
assert.ok(run('axisDomain([-25,-2],{zero:true,max:0}).hi === 0'));
assert.ok(run('axisDomain([100,110],{log:true}).lo > 0'));
assert.ok(run('axisDomain([0,0],{min:0,zero:true}).hi > 0'));
assert.ok(run('linearTicks(0,10).values.includes(0)'));
assert.ok(run('linearTicks(0,.01).values.every(Number.isFinite)'));
assert.equal(run("timeTicks(monthIndex('2021-01'),monthIndex('2026-01'),260).values.length"),1);
assert.equal(run("timeTicks(monthIndex('1990-01'),monthIndex('2026-07'),260).step"),60);
assert.equal(run("timeTicks(monthIndex('1990-01'),monthIndex('2026-07'),260).minor.length"),29);
assert.ok(!html.includes('<canvas'), 'Figures vectorielles SVG');
console.log('OK : graduations, domaines linéaires/logarithmiques et figures SVG.');

// A shorter update preserves both ends; an older JSON cannot undo newer prices.
assert.equal(run('mergeOfficialHistory(packageFixture).series.or.rows.length'),EMBEDDED);
assert.equal(run('mergeOfficialHistory(packageFixture).series.or.rows[0].date'),'1990-01');
assert.equal(run('mergeOfficialHistory(packageFixture).series.or.rows.at(-1).date'),LAST);
assert.equal(run("mergeOfficialHistory(packageFixture).series.or.rows.find(r=>r.date==='2026-01').price"),run("DATA.or.find(r=>r.date==='2026-01').price"));
run("packageFixture.retrievedAt='2027-01-01T00:00:00Z'");
assert.equal(run("mergeOfficialHistory(packageFixture).series.or.rows.find(r=>r.date==='2026-01').price"),100);
run("const originalMeta=META.or;META.or={name:'Or',unit:'unité source'}");
assert.throws(()=>run('mergeOfficialHistory(packageFixture)'));
run('META.or=originalMeta');
assert.equal(run('DATA.or.length'),EMBEDDED);
console.log('OK : historique conservé, révisions récentes et refus de raccord incompatible.');

// An earlier published month and a new last month extend rather than crop the history.
run(`const extended={format:'observatoire-insee-v1',retrievedAt:'2027-01-01T00:00:00Z',series:Object.fromEntries(Object.entries(OFFICIAL_IDS).map(([k,id])=>[k,{idbank:id,unit:OFFICIAL_UNITS[k],rows:[{date:'1989-12',price:90},...DATA[k],{date:'${NEXT}',price:120}]}]))};`);
assert.equal(run('mergeOfficialHistory(extended).series.or.rows.length'),EMBEDDED+2);
assert.equal(run('mergeOfficialHistory(extended).series.or.rows[0].date'),'1989-12');
assert.equal(run('mergeOfficialHistory(extended).series.or.rows.at(-1).date'),NEXT);
// All original historical observations are immediately available, without importing files.
run("asset='or'");
assert.equal(run('getRows()[0].date'),'1900');
assert.equal(run('getRows().length'),123);
assert.equal(run('annualAnalysis()'),true);
assert.equal(run('EARLY_HISTORIES.length'),8);
run("asset='argent'");assert.equal(run('getRows()[0].date'),'1900');
run("asset='cuivre'");assert.equal(run('getRows()[0].date'),'1900');
run("asset='brent'");assert.equal(run('getRows()[0].date'),'1859');assert.equal(run('currentSeries().asset'),'petrole_us');
run("asset='or';chosenSeries.or='wb_or'");assert.equal(run('getRows()[0].date'),'1960-01');assert.equal(run('annualAnalysis()'),false);
run("chosenSeries.or='insee_or'");assert.equal(run('getRows()[0].date'),'1990-01');
// Same observed returns: annual standard deviation has no monthly sqrt(12) multiplier.
run(`const annualFixture=[100,120,108,140,125].map((price,i)=>({date:String(1900+i),price}));const yearly=calculate(annualFixture,2,2,2,1);const monthlyFactor=calculate(annualFixture,2,2,2,12);`);
assert.ok(Math.abs(run('monthlyFactor[4].vol/yearly[4].vol')-Math.sqrt(12))<1e-12);
assert.equal(run('yearly.length'),5,'Annual observations are never expanded into months');
assert.equal(run('yearly[0].date'),'1900');
console.log('OK : chargement automatique des historiques anciens et calculs selon leur fréquence.');
// Mass conversions affect displayed prices, never the original observations or currency.
run("asset='or';chosenSeries.or='usgs_or';goldMassUnit='ounce'");
assert.ok(Math.abs(run('getRows()[0].price')-609000*31.1034768/1e6)<1e-12);
assert.equal(run('displaySeries().unit'),'USD / once troy');
assert.equal(run('currentSeries().rows[0].price'),609000);
run("goldMassUnit='gram'");assert.equal(run('getRows()[0].price'),.609);
run("chosenSeries.or='wb_or';goldMassUnit='ounce'");assert.equal(run('getRows()[0].price'),35.27);
run("goldMassUnit='gram'");assert.ok(Math.abs(run('getRows()[0].price')-35.27/31.1034768)<1e-12);
assert.equal(run('currentSeries().rows[0].price'),35.27);
// Zoom intervals remain ordered and bounded, and zoom out cannot discard the full range.
assert.equal(run('JSON.stringify(scaleWindow([0,1],.5,.5))'),'[0.25,0.75]');
assert.equal(run('JSON.stringify(scaleWindow([0,1],.5,2))'),'[0,1]');
assert.ok(run('boundedWindow(-10,10)[0]===0 && boundedWindow(-10,10)[1]===1'));
assert.ok(run('boundedWindow(.5,.5)[1]>boundedWindow(.5,.5)[0]'));
console.log('OK : conversions de masse réversibles et fenêtres de zoom bornées.');
// Bitcoin (Bitstamp) and the free ratio A / B: any two series of the same frequency, unit deduced.
assert.equal(run('DATA.bitcoin[0].date'),'2011-09');assert.equal(run('META.bitcoin.unit'),'USD / bitcoin');
assert.ok(run("allSeries().some(s=>s.key==='bitstamp_bitcoin'&&s.asset==='bitcoin')"));
run("asset='ratio';ratioPair.num='insee_or';ratioPair.den='bitstamp_bitcoin'");
assert.equal(run('ratioUnit()'),'bitcoin / once troy');
assert.equal(run('getRows()[0].date'),'2011-09');assert.equal(run('getRows().at(-1).date'),LAST);
assert.ok(Math.abs(run('getRows()[0].price')-run("DATA.or.find(r=>r.date==='2011-09').price/DATA.bitcoin[0].price"))<1e-12);
run("ratioPair.num='insee_cuivre'");assert.equal(run('ratioUnit()'),'bitcoin / tonne');
run("ratioPair.num='bitstamp_bitcoin';ratioPair.den='insee_argent'");assert.equal(run('ratioUnit()'),'once troy / bitcoin');
run("ratioPair.num='usgs_or';ratioPair.den='usgs_argent'");assert.equal(run('ratioUnit()'),'1');assert.equal(run('annualAnalysis()'),true);
assert.equal(run('getRows()[0].date'),'1900');assert.equal(run('getRows().at(-1).date'),'2021');
run("ratioPair.den='insee_argent'");assert.equal(run('getRows().length'),0,'Annual and monthly series are never mixed');
run("ratioPair.num='wb_or';ratioPair.den='wb_argent'");assert.equal(run('getRows()[0].date'),'1960-01');assert.equal(run('ratioUnit()'),'1');
run("ratioPair.num='disparu';ratioPair.den='disparu'");assert.equal(run("ratioOperands().num.key+'/'+ratioOperands().den.key"),'insee_or/insee_argent');
// A collected bitcoin series is optional, but checked when present.
run(`packageFixture.series.bitcoin={market:'bitstamp:btcusd',unit:'USD / bitcoin',rows:[{date:'2026-01',price:90000},{date:'2026-02',price:95000}]}`);
assert.equal(run('validateOfficial(packageFixture).series.bitcoin.source'),'Bitstamp');
for (const mutation of ["p.series.bitcoin.unit='EUR / bitcoin'", "p.series.bitcoin.market='kraken:xbtusd'", "p.series.bitcoin.rows[1].date='2026-04'", "p.series.bitcoin.rows[0].price=0"]) {
  assert.throws(() => run(`(()=>{const p=JSON.parse(JSON.stringify(packageFixture));${mutation};return validateOfficial(p)})()`));
}
assert.equal(run('mergeOfficialHistory(packageFixture).series.bitcoin.rows[0].date'),'2011-09');
assert.equal(run("JSON.stringify(validateOfficial({...packageFixture,warnings:['bitcoin : hors ligne']}).warnings)"),'["bitcoin : hors ligne"]');
run('delete packageFixture.series.bitcoin');
console.log('OK : bitcoin, ratio libre entre deux séries de même fréquence et unité déduite.');
