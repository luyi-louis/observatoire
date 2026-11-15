import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('embed', ROOT / 'outils/integrer_cours.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def package():
    return json.loads((ROOT / 'mises_a_jour/historique_complet.json').read_text(encoding='utf-8'))


class EmbedTests(unittest.TestCase):
    def test_embedded_prices_are_latest_collection(self):
        summary, _ = module.build(check=True)
        self.assertEqual(list(summary), ['or', 'argent', 'brent', 'cuivre', 'bitcoin'])
        self.assertTrue(all(summary[k][1] == '1990-01' for k in ['or', 'argent', 'brent', 'cuivre']))
        self.assertEqual(summary['bitcoin'][1], '2011-09')

    def test_rebuild_is_idempotent(self):
        with tempfile.TemporaryDirectory() as temp:
            copy = Path(temp) / 'page.html'
            copy.write_text((ROOT / 'Observatoire.html').read_text(encoding='utf-8'), encoding='utf-8')
            before = copy.read_bytes()
            module.build(html_path=copy)
            self.assertEqual(copy.read_bytes(), before)

    def test_meta_matches_page_install_history(self):
        p = package()
        line = next(l for l in (ROOT / 'Observatoire.html').read_text(encoding='utf-8').split('\n')
                    if l.startswith('const META='))
        meta = json.loads(line[len('const META='):-1])
        self.assertEqual(meta['or']['retrievedAt'], p['retrievedAt'])
        self.assertNotIn('rows', meta['or'])

    def test_rejections(self):
        for mutation, message in [
                (lambda p: p['series'].pop('cuivre'), 'quatre séries'),
                (lambda p: p['series']['argent'].update(unit='cents'), 'unité'),
                (lambda p: p['series']['or']['rows'].pop(5), 'mois manquant'),
                (lambda p: p['series']['brent']['rows'][0].update(price=-1), 'observation invalide'),
                (lambda p: p.update(format='autre'), 'Format'),
                (lambda p: p['series']['bitcoin'].update(unit='EUR / bitcoin'), 'marché ou unité'),
                (lambda p: p['series']['bitcoin']['rows'].pop(3), 'mois manquant'),
                (lambda p: p['series'].update(ether=p['series']['bitcoin']), 'Série inconnue')]:
            p = package()
            mutation(p)
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                module.validate(p)

    def test_bitcoin_is_optional(self):
        p = package()
        p['series'].pop('bitcoin')
        self.assertEqual(module.series_keys(module.validate(p)), ['or', 'argent', 'brent', 'cuivre'])

    def test_script_closing_tag_is_escaped(self):
        self.assertNotIn('</', module.js_literal({'title': '</script><b>'}))


if __name__ == '__main__':
    unittest.main()
