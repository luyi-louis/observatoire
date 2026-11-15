#!/usr/bin/env python3
"""Embed the complete INSEE history (mises_a_jour/historique_complet.json) in the standalone HTML.

Same transformation as installHistory() in the page: DATA[key] = rows,
META[key] = the series without its rows, plus the package's retrievedAt.
No network access, no dependency: run outils/actualiser_cours.py first to collect.
"""
import argparse
import importlib.util
import json
import math
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location('collector', Path(__file__).with_name('actualiser_cours.py'))
collector = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(collector)
MONTH = re.compile(r'\d{4}-(0[1-9]|1[0-2])')


def validate(package):
    """Refuse anything the page itself would refuse: format, series, units, months, prices, gaps."""
    if not isinstance(package, dict) or package.get('format') != 'observatoire-insee-v1':
        raise ValueError('Format de collecte non reconnu (observatoire-insee-v1 attendu).')
    if not isinstance(package.get('retrievedAt'), str) or not isinstance(package.get('series'), dict):
        raise ValueError('Collecte sans date de récupération ou sans séries.')
    if set(package['series']) != set(collector.SOURCES):
        raise ValueError('Les quatre séries or, argent, brent et cuivre sont exigées ensemble.')
    for key, spec in collector.SOURCES.items():
        item = package['series'][key]
        if item.get('idbank') != spec['id'] or item.get('unit') != spec['unit']:
            raise ValueError(f'Série {key} : identifiant INSEE ou unité différent du catalogue.')
        rows = item.get('rows')
        if not isinstance(rows, list) or len(rows) < 2:
            raise ValueError(f'Série {key} : historique insuffisant.')
        for row in rows:
            price = row.get('price')
            if (not MONTH.fullmatch(str(row.get('date', ''))) or isinstance(price, bool)
                    or not isinstance(price, (int, float)) or not math.isfinite(price) or price <= 0):
                raise ValueError(f'Série {key} : observation invalide ({row.get("date")}).')
        indices = [int(r['date'][:4]) * 12 + int(r['date'][5:]) for r in rows]
        if any(b - a != 1 for a, b in zip(indices, indices[1:])):
            raise ValueError(f'Série {key} : mois manquant, dupliqué ou désordonné.')
    return package


def js_literal(value):
    # Same escaping as the translation embed: no '</script>' can close the block early.
    return (json.dumps(value, ensure_ascii=False, separators=(',', ':'))
            .replace('<', '\\u003c').replace('\u2028', '\\u2028').replace('\u2029', '\\u2029'))


def build(html_path=ROOT / 'Observatoire.html', source=ROOT / 'mises_a_jour' / 'historique_complet.json', check=False):
    package = validate(json.loads(Path(source).read_text(encoding='utf-8')))
    data, meta = {}, {}
    for key in collector.SOURCES:
        item = package['series'][key]
        data[key] = item['rows']
        meta[key] = {k: v for k, v in item.items() if k != 'rows'}
        meta[key]['retrievedAt'] = package['retrievedAt']
    lines = Path(html_path).read_text(encoding='utf-8').split('\n')
    targets = {'const DATA=': 'const DATA=' + js_literal(data) + ';',
               'const META=': 'const META=' + js_literal(meta) + ';'}
    for prefix, replacement in targets.items():
        found = [i for i, line in enumerate(lines) if line.startswith(prefix)]
        if len(found) != 1:
            raise ValueError(f'Ligne « {prefix} » absente ou dupliquée dans le HTML.')
        if check:
            if lines[found[0]] != replacement:
                raise ValueError('Les cours intégrés au HTML ne sont pas ceux de la dernière collecte. '
                                 'Lancer outils/integrer_cours.py.')
        else:
            lines[found[0]] = replacement
    if not check:
        Path(html_path).write_text('\n'.join(lines), encoding='utf-8')
    return {key: (len(rows), rows[0]['date'], rows[-1]['date']) for key, rows in data.items()}, package['retrievedAt']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--check', action='store_true', help='Vérifier sans écrire.')
    args = parser.parse_args()
    try:
        summary, retrieved = build(check=args.check)
        for key, (count, first, last) in summary.items():
            print(f'{key} : {count} mois, {first} → {last}')
        print(f'OK : collecte du {retrieved} ' + ('déjà intégrée.' if args.check else 'intégrée au HTML autonome.'))
    except (ValueError, OSError) as exc:
        parser.exit(1, str(exc) + '\n')
