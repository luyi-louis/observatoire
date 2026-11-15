#!/usr/bin/env python3
"""Collecte INSEE (et bitcoin chez Bitstamp) à la demande ; bibliothèque standard Python uniquement."""
import argparse
import calendar
from datetime import datetime, timezone
import hashlib
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import math
from pathlib import Path
import re
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
API = 'https://bdm.insee.fr/series/sdmx/data/SERIES_BDM/'
SOURCES = {
    'or': {'id': '010002061', 'name': 'Or', 'unit': 'USD / once troy', 'sourceUnit': 'USD', 'factor': 1, 'term': 'or'},
    'argent': {'id': '010002043', 'name': 'Argent', 'unit': 'USD / once troy', 'sourceUnit': 'CENT_US', 'factor': .01, 'term': 'argent'},
    'brent': {'id': '010002077', 'name': 'Brent', 'unit': 'USD / baril', 'sourceUnit': 'USD', 'factor': 1, 'term': 'brent'},
    'cuivre': {'id': '010002052', 'name': 'Cuivre', 'unit': 'USD / tonne', 'sourceUnit': 'USD', 'factor': 1, 'term': 'cuivre'},
}
MAX_BYTES = 10_000_000
USER_AGENT = 'Observatoire-local/1.0 (monthly data research)'

# Bitcoin: no statistical agency publishes it. Bitstamp's public market API gives daily BTC/USD candles
# since 2011-08-18; one month = arithmetic mean of the daily closes (00:00 UTC) of a complete calendar month.
BITSTAMP_API = 'https://www.bitstamp.net/api/v2/ohlc/btcusd/'
BITSTAMP_FIRST_DAY = 1312156800  # 2011-08-01 00:00 UTC, before the first quote
DAY = 86400
MARKET_SOURCES = {
    'bitcoin': {'market': 'bitstamp:btcusd', 'pair': 'BTC/USD', 'name': 'Bitcoin', 'unit': 'USD / bitcoin',
                'source': 'Bitstamp', 'sourceUrl': 'https://www.bitstamp.net/api/',
                'title': 'Bitcoin · BTC/USD Bitstamp · moyenne mensuelle des clôtures quotidiennes (00:00 UTC)'},
}

def parse_sdmx(raw):
    if len(raw) > MAX_BYTES or b'<!DOCTYPE' in raw.upper() or b'<!ENTITY' in raw.upper():
        raise ValueError('Document XML trop volumineux ou non autorisé.')
    root = ET.fromstring(raw)
    nodes = [node for node in root.iter() if node.tag.split('}')[-1] == 'Series']
    result = {}
    for key, spec in SOURCES.items():
        matches = [n for n in nodes if n.get('IDBANK') == spec['id']]
        if len(matches) != 1:
            raise ValueError(f"Série {spec['id']} absente ou dupliquée dans la réponse.")
        node = matches[0]
        title = node.get('TITLE_FR', '')
        if (node.get('FREQ') != 'M' or node.get('UNIT_MEASURE') != spec['sourceUnit']
                or node.get('UNIT_MULT') != '0' or spec['term'] not in title.lower()):
            raise ValueError(f"Métadonnées inattendues pour {key} : unité, fréquence ou intitulé modifié.")
        if re.search(r'arr[eê]t[eé]e', title, re.I):
            raise ValueError(f'Série {key} arrêtée : vérifier son remplacement sur le site INSEE.')
        dated, skipped, seen = [], [], set()
        for obs in node:
            if obs.tag.split('}')[-1] != 'Obs':
                continue
            date = obs.get('TIME_PERIOD', '')
            if not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', date) or date in seen:
                raise ValueError(f'Mois invalide ou dupliqué pour {key} : {date}.')
            seen.add(date)
            value = obs.get('OBS_VALUE', '').strip()
            if value in ('', 'NaN') or obs.get('OBS_STATUS') == 'O':
                skipped.append(date)
                continue
            price = float(value) * spec['factor']
            if not math.isfinite(price) or price <= 0:
                raise ValueError(f'Prix invalide pour {key} en {date}.')
            dated.append({'date': date, 'price': round(price, 10), 'status': obs.get('OBS_STATUS', '')})
        dated.sort(key=lambda r: r['date'])
        if len(dated) < 2:
            raise ValueError(f'Historique insuffisant pour {key}.')
        indices = [int(r['date'][:4]) * 12 + int(r['date'][5:]) for r in dated]
        if any(b-a != 1 for a,b in zip(indices, indices[1:])):
            raise ValueError(f'Lacune interne dans la série {key} ; aucune interpolation automatique.')
        result[key] = {'name': spec['name'], 'idbank': spec['id'], 'unit': spec['unit'],
                       'sourceUnit': spec['sourceUnit'], 'conversionFactor': spec['factor'],
                       'title': title, 'source': 'INSEE BDM',
                       'sourceUrl': 'https://www.insee.fr/fr/statistiques/serie/' + spec['id'],
                       'publishedAt': node.get('LAST_UPDATE', ''), 'skippedMonths': skipped, 'rows': dated}
    return result

def collect():
    url = API + '+'.join(s['id'] for s in SOURCES.values())
    request = urllib.request.Request(url, headers={
        'Accept': 'application/vnd.sdmx.structurespecificdata+xml;version=2.1',
        'User-Agent': USER_AGENT})
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise ValueError(f'Réponse INSEE inattendue : HTTP {response.status}.')
        raw = response.read(MAX_BYTES + 1)
    series = parse_sdmx(raw)
    package = {'format': 'observatoire-insee-v1', 'retrievedAt': datetime.now(timezone.utc).isoformat(),
               'requestUrl': url, 'sha256': hashlib.sha256(raw).hexdigest(), 'series': series}
    for item in series.values():
        for row in item['rows']:
            row['retrievedAt'] = package['retrievedAt']
    return package, raw

def parse_bitstamp(pages, now):
    """Daily BTC/USD closes → monthly means of the complete calendar months before `now` (UTC)."""
    closes = {}
    for raw in pages:
        if len(raw) > MAX_BYTES:
            raise ValueError('Réponse Bitstamp trop volumineuse.')
        try:
            data = json.loads(raw)['data']
            candles = data['ohlc']
        except (ValueError, KeyError, TypeError):
            raise ValueError('Réponse Bitstamp illisible.') from None
        if data.get('pair') != MARKET_SOURCES['bitcoin']['pair'] or not isinstance(candles, list):
            raise ValueError('Réponse Bitstamp inattendue : paire ou format modifié.')
        for candle in candles:
            try:
                stamp, close = int(candle['timestamp']), float(candle['close'])
            except (KeyError, TypeError, ValueError):
                raise ValueError('Cotation Bitstamp illisible.') from None
            if stamp % DAY or not math.isfinite(close) or close <= 0:
                raise ValueError('Cotation Bitstamp invalide (jour ou prix).')
            if closes.setdefault(stamp, close) != close:
                raise ValueError('Cotation Bitstamp dupliquée et contradictoire.')
    stamps = sorted(closes)
    if any(b - a != DAY for a, b in zip(stamps, stamps[1:])):
        raise ValueError('Jour manquant dans l’historique Bitstamp ; aucune interpolation automatique.')
    by_month = {}
    for stamp in stamps:
        by_month.setdefault(datetime.fromtimestamp(stamp, timezone.utc).strftime('%Y-%m'), []).append(closes[stamp])
    current = now.astimezone(timezone.utc).strftime('%Y-%m')
    rows = [{'date': month, 'price': round(math.fsum(values) / len(values), 6), 'days': len(values)}
            for month, values in sorted(by_month.items())
            # The first month (partial) and the month in progress are left out.
            if month < current and len(values) == calendar.monthrange(int(month[:4]), int(month[5:]))[1]]
    if len(rows) < 2:
        raise ValueError('Historique Bitstamp insuffisant.')
    spec = MARKET_SOURCES['bitcoin']
    return {'name': spec['name'], 'market': spec['market'], 'pair': spec['pair'], 'unit': spec['unit'],
            'title': spec['title'], 'source': spec['source'], 'sourceUrl': spec['sourceUrl'],
            'lastQuote': datetime.fromtimestamp(stamps[-1], timezone.utc).strftime('%Y-%m-%d'),
            'skippedMonths': [], 'rows': rows}


def collect_market(now=None):
    """Bitcoin from Bitstamp. A failure is reported, not raised: the INSEE update must not depend on it."""
    now = now or datetime.now(timezone.utc)
    pages, start = [], BITSTAMP_FIRST_DAY
    try:
        while start <= now.timestamp():
            if len(pages) >= 40:
                raise ValueError('pagination Bitstamp anormalement longue')
            request = urllib.request.Request(f'{BITSTAMP_API}?step={DAY}&limit=1000&start={start}',
                                             headers={'Accept': 'application/json', 'User-Agent': USER_AGENT})
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.status != 200:
                    raise ValueError(f'HTTP {response.status}')
                raw = response.read(MAX_BYTES + 1)
            pages.append(raw)
            try:
                candles = json.loads(raw)['data']['ohlc']
                # A page covers 1000 days from `start`, even before the first quote: advance from what came back.
                start = int(candles[-1]['timestamp']) + DAY if candles else start + 1000 * DAY
            except (ValueError, KeyError, TypeError, IndexError):
                raise ValueError('réponse Bitstamp illisible') from None
        series = parse_bitstamp(pages, now)
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return {}, {}, [f'bitcoin : {exc}']
    raws = {f'source-bitstamp-{i:02d}.json': raw for i, raw in enumerate(pages)}
    # The raw pages stay in the local archive (not versioned); their digest makes the monthly means checkable.
    series.update(requestUrl=f'{BITSTAMP_API}?step={DAY}&limit=1000&start=<jour>', pages=len(pages),
                  sha256=hashlib.sha256(b''.join(pages)).hexdigest())
    return {'bitcoin': series}, raws, []


def _union(key, old, new, previous, current):
    by_date = {}
    old_rows = [dict(r, retrievedAt=r.get('retrievedAt', previous.get('retrievedAt'))) for r in old['rows']]
    new_rows = [dict(r, retrievedAt=r.get('retrievedAt', current.get('retrievedAt'))) for r in new['rows']]
    for item in old_rows + new_rows:
        date, price = item.get('date', ''), item.get('price')
        if (not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', date)
                or not isinstance(price, (int, float)) or isinstance(price, bool)
                or not math.isfinite(price) or price <= 0):
            raise ValueError(f'Observation invalide dans le cache : {key}.')
        by_date[date] = item
    new_dates = {r['date'] for r in new['rows']}
    new['retainedMonths'] = sorted(set(by_date) - new_dates)
    new['rows'] = [by_date[date] for date in sorted(by_date)]
    indices = [int(r['date'][:4])*12+int(r['date'][5:]) for r in new['rows']]
    if any(b-a != 1 for a,b in zip(indices,indices[1:])):
        raise ValueError(f'Lacune après fusion de l’historique : {key}.')


def merge_packages(previous, current):
    """Union by month for the same INSEE series and canonical unit only."""
    merged = json.loads(json.dumps(current))
    if previous is None:
        return merged
    if (not isinstance(previous, dict) or previous.get('format') != 'observatoire-insee-v1'
            or not isinstance(previous.get('series'), dict)
            or any(not isinstance(previous['series'].get(k), dict)
                   or not isinstance(previous['series'][k].get('rows'), list) for k in SOURCES)):
        raise ValueError('Format du cache historique non reconnu.')
    for key, spec in SOURCES.items():
        old, new = previous['series'][key], merged['series'][key]
        if any(item.get('idbank') != spec['id'] or item.get('unit') != spec['unit'] for item in [old, new]):
            raise ValueError(f'Historique incompatible pour {key} : source ou unité différente.')
        _union(key, old, new, previous, current)
    # Optional market series: absent from older caches, or not collected this time (source unreachable).
    for key, spec in MARKET_SOURCES.items():
        old, new = previous['series'].get(key), merged['series'].get(key)
        for item in [old, new]:
            if item is not None and (not isinstance(item, dict) or not isinstance(item.get('rows'), list)
                                     or item.get('market') != spec['market'] or item.get('unit') != spec['unit']):
                raise ValueError(f'Historique incompatible pour {key} : source ou unité différente.')
        if old is None:
            continue
        if new is None:
            kept = json.loads(json.dumps(old))
            kept['rows'] = [dict(r, retrievedAt=r.get('retrievedAt', previous.get('retrievedAt'))) for r in kept['rows']]
            kept['retainedMonths'] = [r.get('date') for r in kept['rows']]
            merged['series'][key] = kept
        else:
            _union(key, old, new, previous, current)
    merged['previousRetrieval'] = previous.get('retrievedAt')
    return merged


def collect_preserving_history(directory):
    current, raw = collect()
    market, market_raw, warnings = collect_market()
    for item in market.values():
        for row in item['rows']:
            row['retrievedAt'] = current['retrievedAt']
    current['series'].update(market)
    if warnings:
        current['warnings'] = warnings
    cache = Path(directory) / 'historique_complet.json'
    previous = json.loads(cache.read_text(encoding='utf-8')) if cache.exists() else None
    return merge_packages(previous, current), {'source-insee.xml': raw, **market_raw}


def archive(package, raw, directory):
    # Nouveau dossier à chaque collecte : les fichiers d'origine restent intacts.
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    target = Path(directory) / stamp
    target.mkdir(parents=True, exist_ok=False)
    for name, content in ({'source-insee.xml': raw} if isinstance(raw, bytes) else raw).items():
        (target / name).write_bytes(content)
    payload = json.dumps(package, ensure_ascii=False, indent=2)
    (target / 'cours-insee.json').write_text(payload, encoding='utf-8')
    # Atomic replacement of the complete cache, after the dated archive is written.
    temporary = Path(directory) / (stamp + '.tmp')
    temporary.write_text(payload, encoding='utf-8')
    temporary.replace(Path(directory) / 'historique_complet.json')
    return target

def serve(port, directory):
    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, data, content_type='application/json; charset=utf-8'):
            if not isinstance(data, bytes):
                data = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(data)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.end_headers()
            self.wfile.write(data)

        def valid_host(self):
            return self.headers.get('Host') == f'127.0.0.1:{self.server.server_port}'

        def do_GET(self):
            if not self.valid_host():
                return self.reply(403, {'error': 'Hôte non autorisé.'})
            if self.path in ('/', '/Observatoire.html'):
                return self.reply(200, (ROOT/'Observatoire.html').read_bytes(), 'text/html; charset=utf-8')
            self.reply(404, {'error': 'Ressource inconnue.'})

        def do_POST(self):
            expected = f'http://127.0.0.1:{self.server.server_port}'
            if (not self.valid_host() or self.headers.get('Origin') != expected
                    or self.headers.get('X-Observatoire') != 'update'):
                return self.reply(403, {'error': 'Ouvrez l’application depuis l’adresse locale affichée par le serveur.'})
            if self.path != '/api/update':
                return self.reply(404, {'error': 'Ressource inconnue.'})
            try:
                package, raw = collect_preserving_history(directory)
                archive(package, raw, directory)
                self.reply(200, package)
            except (ValueError, ET.ParseError, OSError) as exc:
                self.reply(502, {'error': f'Collecte impossible : {exc}. Les séries actuelles sont conservées.'})

    server = HTTPServer(('127.0.0.1', port), Handler)
    print(f'Ouvrir http://127.0.0.1:{server.server_port} — Ctrl+C pour arrêter.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--serve', action='store_true', help='Ouvrir un serveur local pour le bouton de mise à jour HTML.')
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--output', type=Path, default=ROOT/'mises_a_jour', help='Dossier des archives de collecte.')
    args = parser.parse_args()
    if args.serve:
        serve(args.port, args.output)
        return
    try:
        package, raw = collect_preserving_history(args.output)
        target = archive(package, raw, args.output)
        print(f'Collecte validée : {target / "cours-insee.json"}')
        for key, item in package['series'].items():
            print(f"{key} : {len(item['rows'])} mois, {item['rows'][0]['date']} → {item['rows'][-1]['date']}, {item['unit']}")
        for warning in package.get('warnings', []):
            print(f'Non actualisé (historique conservé) : {warning}', file=sys.stderr)
    except (ValueError, ET.ParseError, OSError) as exc:
        print(f'Échec de collecte : {exc}', file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
