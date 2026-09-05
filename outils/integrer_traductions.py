#!/usr/bin/env python3
"""Validate locale catalogues and embed them in the standalone HTML. No dependencies."""
import argparse
from html.parser import HTMLParser
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
START = '/* I18N_CATALOGS_START */'
END = '/* I18N_CATALOGS_END */'

class InlineMarkup(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.stack = []
    def handle_starttag(self, tag, attrs):
        if tag not in {'b','i','sub','sup','br','code','cite','a'}:
            raise ValueError('Unexpected translation markup: '+tag)
        for name, value in attrs:
            if tag != 'a' or name not in {'href','rel','target'}:
                raise ValueError('Unexpected translation attribute: '+name)
            if name == 'href':
                if not value.startswith(('https://','http://127.0.0.1:')):
                    raise ValueError('Unexpected translation URL: '+value)
                self.links.append(value)
        if tag != 'br': self.stack.append(tag)
    def handle_endtag(self, tag):
        if tag == 'br': return
        if not self.stack or self.stack.pop() != tag:
            raise ValueError('Unbalanced translation markup: '+tag)
    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag != 'br': self.handle_endtag(tag)

def validate_catalogues(directory):
    catalogues = {p.stem: json.loads(p.read_text(encoding='utf-8')) for p in sorted(directory.glob('*.json'))}
    if not {'fr','en'} <= catalogues.keys():
        raise ValueError('French and English catalogues are required.')
    reference = catalogues['fr']['messages']
    for code, catalogue in catalogues.items():
        if not re.fullmatch(r'[a-z]{2,3}(?:-[A-Za-z0-9]{2,8})*', code):
            raise ValueError('Invalid language code: '+code)
        if any(not isinstance(catalogue.get(k), str) or not catalogue[k] for k in ['label','locale','direction']):
            raise ValueError(code+': label, locale and direction are required.')
        if catalogue['direction'] not in ['ltr','rtl']:
            raise ValueError(code+': invalid text direction.')
        messages = catalogue.get('messages', {})
        if messages.keys() != reference.keys():
            raise ValueError(f'{code}: missing keys {sorted(reference.keys()-messages.keys())}; extra keys {sorted(messages.keys()-reference.keys())}')
        for key, value in messages.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f'{code}/{key}: empty translation.')
            if set(re.findall(r'\{(\w+)\}', value)) != set(re.findall(r'\{(\w+)\}', reference[key])):
                raise ValueError(f'{code}/{key}: mismatching placeholders.')
            parser, original = InlineMarkup(), InlineMarkup()
            parser.feed(value); original.feed(reference[key])
            if parser.stack or original.stack or sorted(parser.links) != sorted(original.links):
                raise ValueError(f'{code}/{key}: unbalanced markup or changed links.')
    # French first; all additional languages appear automatically in the selector.
    return {code:catalogues[code] for code in ['fr','en',*sorted(catalogues.keys()-{'fr','en'})]}

def build(html_path=ROOT/'Observatoire.html', directory=ROOT/'locales', check=False):
    catalogues = validate_catalogues(directory)
    html = html_path.read_text(encoding='utf-8')
    if html.count(START)!=1 or html.count(END)!=1:
        raise ValueError('Translation embed markers are missing or duplicated.')
    keys = catalogues['fr']['messages'].keys()
    static_keys = re.findall(r'data-i18n(?:-html|-aria-label|-placeholder)?="([^"]+)"', html)
    dynamic_keys = re.findall(r"\b(?:t|I18nError)\('([\w.]+)'", html.split(END)[1])
    dynamic_keys=[k for k in dynamic_keys if not k.endswith('.')]
    if set(static_keys+dynamic_keys)-keys:
        raise ValueError('Unknown translation keys: '+str(set(static_keys+dynamic_keys)-keys))
    payload=json.dumps(catalogues,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('\u2028','\\u2028').replace('\u2029','\\u2029')
    embedded='\nconst I18N_CATALOGS='+payload+';\n'
    before,tail=html.split(START);old,after=tail.split(END)
    if check:
        if old!=embedded:raise ValueError('Embedded catalogues are stale. Run outils/integrer_traductions.py.')
    else:
        html_path.write_text(before+START+embedded+END+after,encoding='utf-8')
    return len(catalogues),len(keys)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    try:
        languages,keys=build(check=args.check)
        print(f'OK: {languages} languages, {keys} keys each; standalone HTML '+('checked.' if args.check else 'updated.'))
    except (ValueError, OSError) as exc:
        parser.exit(1,str(exc)+'\n')
