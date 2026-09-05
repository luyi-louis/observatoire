#!/usr/bin/env python3
"""Collecte INSEE à la demande ; bibliothèque standard Python uniquement."""
import argparse
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
        'User-Agent': 'Observatoire-local/1.0 (monthly data research)'})
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
    merged['previousRetrieval'] = previous.get('retrievedAt')
    return merged


def collect_preserving_history(directory):
    current, raw = collect()
    cache = Path(directory) / 'historique_complet.json'
    previous = json.loads(cache.read_text(encoding='utf-8')) if cache.exists() else None
    return merge_packages(previous, current), raw


def archive(package, raw, directory):
    # Nouveau dossier à chaque collecte : les fichiers d'origine restent intacts.
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    target = Path(directory) / stamp
    target.mkdir(parents=True, exist_ok=False)
    (target / 'source-insee.xml').write_bytes(raw)
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
    except (ValueError, ET.ParseError, OSError) as exc:
        print(f'Échec de collecte : {exc}', file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
