import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('translations',ROOT/'outils/integrer_traductions.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class TranslationTests(unittest.TestCase):
    def test_embedded_catalogues_current(self):
        languages,keys=module.build(check=True)
        self.assertGreaterEqual(languages,2)
        self.assertGreaterEqual(keys,355)

    def fixture(self,directory):
        for code in ['fr','en']:
            (directory/f'{code}.json').write_text((ROOT/f'locales/{code}.json').read_text())
        return json.loads((directory/'en.json').read_text())

    def test_third_language(self):
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp);catalogue=self.fixture(directory)
            catalogue.update(label='Test language',locale='es-ES')
            (directory/'es.json').write_text(json.dumps(catalogue))
            self.assertEqual(len(module.validate_catalogues(directory)),3)

    def test_missing_translation_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp);catalogue=self.fixture(directory)
            del catalogue['messages']['html.001']
            (directory/'en.json').write_text(json.dumps(catalogue))
            with self.assertRaisesRegex(ValueError,'missing keys'):module.validate_catalogues(directory)

    def test_bad_placeholder_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp);catalogue=self.fixture(directory)
            catalogue['messages']['chart.volLegend']='Volatility {wrong} months'
            (directory/'en.json').write_text(json.dumps(catalogue))
            with self.assertRaisesRegex(ValueError,'placeholders'):module.validate_catalogues(directory)

    def test_unsafe_html_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp);catalogue=self.fixture(directory)
            catalogue['messages']['html.001']='<img src=x onerror="alert(1)">'
            (directory/'en.json').write_text(json.dumps(catalogue))
            with self.assertRaisesRegex(ValueError,'markup'):module.validate_catalogues(directory)

if __name__=='__main__':unittest.main()
