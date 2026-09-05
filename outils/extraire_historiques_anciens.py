#!/usr/bin/env python3
"""Extract archived official tables without currency conversion or frequency changes.
Optional dependencies: openpyxl and beautifulsoup4. No network calls.
"""
from pathlib import Path
import csv
import hashlib
import json
import math
import re
import openpyxl
from bs4 import BeautifulSoup
ROOT = Path(__file__).resolve().parents[1] / 'historiques_anciens'

def write_series(key, rows, unit, frequency, source, source_file, **extra):
    assert rows and all(math.isfinite(v) and v > 0 for _, v in rows)
    indices = [int(d) if frequency == 'A' else int(d[:4])*12+int(d[5:]) for d, _ in rows]
    assert all(b-a == 1 for a,b in zip(indices, indices[1:])), key
    target = ROOT / (key+'.csv')
    with target.open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f);writer.writerow(['year' if frequency == 'A' else 'date','price']);writer.writerows(rows)
    return dict(key=key, file=target.name, unit=unit, currency='USD', frequency=frequency,
                source=source, sourceFile=source_file, start=rows[0][0], end=rows[-1][0], count=len(rows),
                sha256=hashlib.sha256(target.read_bytes()).hexdigest(), rows=[dict(date=d,price=v) for d,v in rows], **extra)

def main():
    catalog=[]
    for asset, name, end in [('or','gold',2022),('argent','silver',2021),('cuivre','copper',2020)]:
        filename=f'ds140-{name}-{end}.xlsx'
        rows=list(openpyxl.load_workbook(ROOT/filename,data_only=True).active.values)
        col=rows[4].index('Unit value ($/t)')
        data=[(str(r[0]),r[col]) for r in rows[5:] if isinstance(r[0],int) and isinstance(r[col],(int,float))]
        catalog.append(write_series('usgs_'+asset,data,'USD / tonne','A','USGS DS140',filename,asset=asset,
            measure='Annual nominal unit value; see embedded workbook methodology.'))
    filename='CMO-Historical-Data-Monthly-2026.xlsx'
    book=openpyxl.load_workbook(ROOT/filename,data_only=True);rows=list(book['Monthly Prices'].values)
    for asset,name,unit in [('or','Gold','USD / once troy'),('argent','Silver','USD / once troy'),('cuivre','Copper','USD / tonne'),('brent','Crude oil, Brent','USD / baril')]:
        col=rows[4].index(name)
        data=[(r[0].replace('M','-'),r[col]) for r in rows[6:] if isinstance(r[0],str) and re.fullmatch(r'\d{4}M\d{2}',r[0]) and isinstance(r[col],(int,float))]
        catalog.append(write_series('wb_'+asset,data,unit,'M','World Bank Pink Sheet',filename,asset=asset,sourceColumn=name))
    descriptions=[' | '.join(str(v) for v in r if v is not None) for r in book['Description'].values]
    (ROOT/'worldbank_definitions.txt').write_text('\n'.join(descriptions),encoding='utf-8')
    soup=BeautifulSoup((ROOT/'eia-petrole-annuel.html').read_text(),'html.parser');data=[]
    for tr in soup.find_all('tr'):
        cells=[td.get_text(' ',strip=True) for td in tr.find_all('td',recursive=False)]
        if len(cells)!=11 or not re.fullmatch(r"\d{4}'s",cells[0]):continue
        decade=int(cells[0][:4])
        for i,value in enumerate(cells[1:]):
            if re.fullmatch(r'\d+(?:\.\d+)?',value):data.append((str(decade+i),float(value)))
    catalog.append(write_series('eia_petrole_us',data,'USD / baril','A','EIA F000000__3','eia-petrole-annuel.html',asset='petrole_us',measure='U.S. crude oil first purchase price; not Brent.'))
    package={'format':'observatoire-historical-research-v1','retrievedAt':'2026-09-05','series':catalog}
    (ROOT/'catalogue.json').write_text(json.dumps(package,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for s in catalog:print(s['key'],s['start'],s['end'],s['count'],s['frequency'],s['unit'])

if __name__=='__main__':main()
