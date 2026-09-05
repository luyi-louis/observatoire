# Observatoire

Application HTML autonome pour explorer les historiques de l’or, de l’argent,
du cuivre et du pétrole, avec une présentation scientifique des graphiques.

**[Télécharger le projet](https://github.com/luyi-louis/observatoire/archive/refs/heads/main.zip)**,
décompresser puis ouvrir **[Observatoire.html](Observatoire.html)** dans un navigateur.
L’application fonctionne hors ligne, sans installation ni dépendance distante.

- Historiques intégrés : métaux dès **1900**, pétrole américain dès **1859**,
  séries mensuelles Banque mondiale dès **1960** et INSEE dès **1990**.
- Sources sélectionnables, avec leurs unités, fréquences et définitions explicites.
  Les séries annuelles et mensuelles restent distinctes ; le pétrole américain
  historique n’est pas assimilé au Brent.
- SMA, EMA, Bollinger, RSI, MACD, volatilité et drawdown ; guide pédagogique
  et paramètres de calcul dans un onglet dédié.
- Graphiques vectoriels, zoom X/Y/X+Y synchronisable, export SVG et CSV.
  L’or s’affiche par once troy ou par gramme.
- Interface intégralement disponible en **français, anglais et russe**.
- Actualisation INSEE à la demande avec conservation de l’historique.

## Documentation

- [Utilisation de l’application](LISEZMOI.md)
- [Sources officielles et actualisation](SOURCES_ET_MISE_A_JOUR.md)
- [Provenance et définition des historiques anciens](historiques_anciens/README.md)
- [Ajouter ou modifier une langue](locales/README.md)
- [Document pédagogique LaTeX](tex/main.tex)

Pour utiliser la collecte INSEE depuis l’interface, lancer :

```sh
python3 outils/actualiser_cours.py --serve
```

Puis ouvrir <http://127.0.0.1:8765>. L’accès Internet est nécessaire à la collecte,
mais pas à l’analyse des données déjà intégrées.

## Vérification

Les vérifications de base nécessitent Node.js et Python 3 :

```sh
node tests/observatoire.test.cjs
python3 -m unittest discover -s tests -p 'test_*.py'
python3 outils/integrer_traductions.py --check
```

Les tests de navigateur et de DOM sont décrits dans les fichiers de `tests/` et
dans la [documentation des traductions](locales/README.md).

## Attribution

D’après le travail de **Louis Tomczyk et contributeurs**, sous
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
Cette adaptation ajoute l’application HTML autonome, les historiques documentés,
la collecte, les traductions et les interactions graphiques. Les données tierces
conservent leur provenance et les conditions de leurs fournisseurs, référencés
dans la documentation des sources.
