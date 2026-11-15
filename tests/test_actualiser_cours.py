import importlib.util
from pathlib import Path
import tempfile
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock
import unittest
import xml.etree.ElementTree as ET

path = Path(__file__).resolve().parents[1] / 'outils' / 'actualiser_cours.py'
spec = importlib.util.spec_from_file_location('collector', path)
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)

def fixture():
    root = ET.Element('StructureSpecificData')
    for item in collector.SOURCES.values():
        s = ET.SubElement(root, 'Series', IDBANK=item['id'], FREQ='M', UNIT_MEASURE=item['sourceUnit'],
                          UNIT_MULT='0', TITLE_FR=item['term'], LAST_UPDATE='2026-08-25')
        for date, value in [('2026-01', '100'), ('2026-02', '110'), ('2026-03', '')]:
            ET.SubElement(s, 'Obs', TIME_PERIOD=date, OBS_VALUE=value, OBS_STATUS='A')
    return root

def daily(first, last, price=lambda day: 100 + day.day):
    day, out = first, []
    while day <= last:
        out.append((day, price(day)))
        day += timedelta(days=1)
    return out

def bitstamp_page(candles, pair='BTC/USD'):
    return json.dumps({'data': {'pair': pair, 'ohlc': [
        {'timestamp': str(int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp())),
         'open': '1', 'high': '1', 'low': '1', 'close': f'{v}', 'volume': '1'} for d, v in candles]}}).encode()

NOW = datetime(2026, 4, 10, 12, tzinfo=timezone.utc)
DAYS = daily(datetime(2026, 1, 15), datetime(2026, 4, 10))

class CollectorTests(unittest.TestCase):
    def parse(self, root):
        return collector.parse_sdmx(ET.tostring(root))

    def test_units_and_missing_edge(self):
        data = self.parse(fixture())
        self.assertEqual(data['argent']['rows'][0]['price'], 1)
        self.assertEqual(data['or']['rows'][0]['price'], 100)
        self.assertEqual(data['argent']['unit'], 'USD / once troy')
        self.assertEqual(data['or']['skippedMonths'], ['2026-03'])

    def test_refuse_changed_metadata(self):
        for attr, value in [('FREQ', 'D'), ('UNIT_MEASURE', 'EUROS'), ('UNIT_MULT', '3'), ('TITLE_FR', 'Or - Série arrêtée')]:
            root = fixture()
            root[0].set(attr, value)
            with self.subTest(attr=attr), self.assertRaises(ValueError):
                self.parse(root)

    def test_refuse_partial_response(self):
        root = fixture()
        root.remove(root[1])
        with self.assertRaises(ValueError):
            self.parse(root)

    def test_invalid_price(self):
        for value in ['0', '-1', 'inf', 'not-a-number']:
            root = fixture()
            root[0][0].set('OBS_VALUE', value)
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.parse(root)

    def test_gap_duplicate(self):
        for date in ['2026-01', '2026-04']:
            root = fixture()
            root[0][1].set('TIME_PERIOD', date)
            with self.assertRaises(ValueError):
                self.parse(root)

    def test_raw_archive_and_package(self):
        with tempfile.TemporaryDirectory() as directory:
            one = collector.archive({'format': 'test'}, b'<source/>', directory)
            two = collector.archive({'format': 'test'}, b'<source/>', directory)
            self.assertNotEqual(one, two)
            self.assertEqual((one / 'source-insee.xml').read_bytes(), b'<source/>')
            self.assertTrue((one / 'cours-insee.json').exists())

    def package(self):
        return {'format': 'observatoire-insee-v1', 'retrievedAt': '2026-09-05T00:00:00Z',
                'series': self.parse(fixture())}

    def test_shorter_update_retains_history_and_revisions(self):
        old, new = self.package(), self.package()
        for item in old['series'].values():
            item['rows'].insert(0, {'date': '2025-12', 'price': 90})
            item['rows'].append({'date': '2026-03', 'price': 120})
        new['series']['or']['rows'][0]['price'] = 101
        merged = collector.merge_packages(old, new)
        self.assertEqual(len(merged['series']['or']['rows']), 4)
        self.assertEqual(merged['series']['or']['rows'][1]['price'], 101)
        self.assertEqual(merged['series']['or']['retainedMonths'], ['2025-12', '2026-03'])
        self.assertEqual(old['series']['or']['rows'][1]['price'], 100)
        bad = self.package()
        bad['series']['or']['unit'] = 'EUR'
        with self.assertRaises(ValueError):
            collector.merge_packages(bad, new)

    def test_collect_requests_all_dates(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.read.return_value = ET.tostring(fixture())
        with patch.object(collector.urllib.request, 'urlopen', return_value=response) as request:
            collector.collect()
        self.assertNotIn('?', request.call_args.args[0].full_url)

    def test_complete_cache_used_across_collections(self):
        old, new = self.package(), self.package()
        for item in old['series'].values():
            item['rows'].insert(0, {'date': '2025-12', 'price': 90})
        with tempfile.TemporaryDirectory() as directory:
            first = collector.archive(old, b'old', directory)
            with patch.object(collector, 'collect', return_value=(new, b'new')), \
                    patch.object(collector, 'collect_market', return_value=({}, {}, [])):
                merged, raw = collector.collect_preserving_history(directory)
            collector.archive(merged, raw, directory)
            cache = json.loads((Path(directory)/'historique_complet.json').read_text())
            self.assertEqual(cache['series']['or']['rows'][0]['date'], '2025-12')
            self.assertEqual((first/'source-insee.xml').read_bytes(), b'old')

    # ── Bitcoin (Bitstamp) ──────────────────────────────────────────────────────
    def test_bitstamp_monthly_means_of_complete_months(self):
        series = collector.parse_bitstamp([bitstamp_page(DAYS)], NOW)
        # January is partial (from the 15th), April is in progress: only February and March remain.
        self.assertEqual([r['date'] for r in series['rows']], ['2026-02', '2026-03'])
        self.assertEqual(series['rows'][0]['days'], 28)
        self.assertAlmostEqual(series['rows'][0]['price'], 100 + 14.5)
        self.assertAlmostEqual(series['rows'][1]['price'], 100 + 16)
        self.assertEqual((series['unit'], series['market'], series['lastQuote']), ('USD / bitcoin', 'bitstamp:btcusd', '2026-04-10'))

    def test_bitstamp_refusals(self):
        gap = [d for d in DAYS if d[0] != datetime(2026, 2, 10)]
        contradictory = DAYS + [(DAYS[40][0], 1)]
        for label, pages in [('jour manquant', [bitstamp_page(gap)]), ('paire', [bitstamp_page(DAYS, 'ETH/USD')]),
                             ('prix nul', [bitstamp_page(DAYS[:-1] + [(DAYS[-1][0], 0)])]),
                             ('doublon contradictoire', [bitstamp_page(contradictory)]), ('illisible', [b'<html/>']),
                             ('trop court', [bitstamp_page(DAYS[:40])])]:
            with self.subTest(label), self.assertRaises(ValueError):
                collector.parse_bitstamp(pages, NOW)

    def test_bitstamp_paginates_from_the_first_quote_to_now(self):
        def answer(request, timeout):
            start = int(request.full_url.rsplit('start=', 1)[1])
            response = MagicMock()
            response.__enter__.return_value, response.status = response, 200
            response.read.return_value = bitstamp_page(
                [(d, v) for d, v in DAYS if start <= datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() < start + 1000 * 86400][:30])
            return response
        with patch.object(collector.urllib.request, 'urlopen', side_effect=answer) as request:
            series, raws, warnings = collector.collect_market(NOW)
        self.assertEqual(warnings, [])
        self.assertEqual([r['date'] for r in series['bitcoin']['rows']], ['2026-02', '2026-03'])
        self.assertEqual(len(raws), request.call_count)
        self.assertTrue(all('step=86400&limit=1000&start=' in c.args[0].full_url for c in request.call_args_list))

    def test_bitstamp_failure_is_reported_not_raised(self):
        with patch.object(collector.urllib.request, 'urlopen', side_effect=collector.urllib.error.URLError('hors ligne')):
            self.assertEqual(collector.collect_market(NOW)[:2], ({}, {}))
            self.assertIn('bitcoin', collector.collect_market(NOW)[2][0])

    def test_bitcoin_kept_when_not_collected_and_raw_pages_archived(self):
        bitcoin = collector.parse_bitstamp([bitstamp_page(DAYS)], NOW)
        old, new = self.package(), self.package()
        old['series']['bitcoin'] = bitcoin
        merged = collector.merge_packages(old, new)
        self.assertEqual([r['date'] for r in merged['series']['bitcoin']['rows']], ['2026-02', '2026-03'])
        self.assertEqual(merged['series']['bitcoin']['retainedMonths'], ['2026-02', '2026-03'])
        self.assertNotIn('bitcoin', collector.merge_packages(self.package(), self.package())['series'])
        old['series']['bitcoin']['unit'] = 'EUR / bitcoin'
        with self.assertRaises(ValueError):
            collector.merge_packages(old, new)
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(collector, 'collect', return_value=(self.package(), b'<insee/>')), \
                    patch.object(collector, 'collect_market', return_value=({'bitcoin': bitcoin}, {'source-bitstamp-00.json': b'{}'}, [])):
                merged, raws = collector.collect_preserving_history(directory)
            target = collector.archive(merged, raws, directory)
            self.assertEqual((target / 'source-bitstamp-00.json').read_bytes(), b'{}')
            self.assertEqual((target / 'source-insee.xml').read_bytes(), b'<insee/>')
            self.assertTrue(all(r['retrievedAt'] == merged['retrievedAt'] for r in merged['series']['bitcoin']['rows']))

    def test_reject_entities(self):
        with self.assertRaises(ValueError):
            collector.parse_sdmx(b'<!DOCTYPE x><x/>')

if __name__ == '__main__':
    unittest.main()
