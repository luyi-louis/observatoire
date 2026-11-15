# Observatoire

Application HTML autonome pour explorer les historiques de l’or, de l’argent,
du cuivre, du pétrole et du bitcoin, et le ratio entre deux d’entre eux, avec une
présentation scientifique des graphiques.

**[Télécharger le projet](https://github.com/luyi-louis/observatoire/archive/refs/heads/main.zip)**,
décompresser puis ouvrir **[Observatoire.html](Observatoire.html)** dans un navigateur.
L’application fonctionne hors ligne, sans installation ni dépendance distante.

- Historiques intégrés : métaux dès **1900**, pétrole américain dès **1859**,
  séries mensuelles Banque mondiale dès **1960** et INSEE dès **1990** ;
  bitcoin mensuel dès **2011** (moyennes des clôtures quotidiennes Bitstamp).
- **Ratio libre** entre deux séries quelconques de même fréquence (or / argent,
  or / bitcoin, cuivre / bitcoin…), avec son unité déduite (bitcoins par once…).
- Sources sélectionnables, avec leurs unités, fréquences et définitions explicites.
  Les séries annuelles et mensuelles restent distinctes ; le pétrole américain
  historique n’est pas assimilé au Brent.
- SMA, EMA, Bollinger, RSI, MACD, volatilité et drawdown ; un onglet **Aide**
  (une fiche par indicateur : définition, lecture, limites), un bouton « ? »
  sur chaque graphe, puis le guide pédagogique et les paramètres de calcul.
- Graphiques vectoriels, zoom X/Y/X+Y synchronisable, export SVG et CSV.
  L’or s’affiche par once troy ou par gramme.
- Interface intégralement disponible en **français, anglais et russe**,
  en thème clair ou **sombre** (ou celui du système).
- Actualisation INSEE et bitcoin à la demande avec conservation de l’historique.

## Documentation

- [Utilisation de l’application](LISEZMOI.md)
- [Sources officielles et actualisation](SOURCES_ET_MISE_A_JOUR.md)
- [Provenance et définition des historiques anciens](historiques_anciens/README.md)
- [Ajouter ou modifier une langue](locales/README.md)
- [AppImage Linux](empaquetage/README.md)
- [Document pédagogique LaTeX](tex/main.tex)

Sous Linux, `empaquetage/build-observatoire-appimage.sh` en fait une **AppImage** :
un seul fichier, double-clic, collecte INSEE comprise si `python3` est présent.

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
python3 outils/integrer_cours.py --check
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
