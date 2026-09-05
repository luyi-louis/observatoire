# Historiques anciens — sources anglophones

Fichiers téléchargés et vérifiés le 5 septembre 2026. Ils sont archivés avec leurs devises, unités et fréquences d’origine. Aucune conversion monétaire, interpolation mensuelle ni fusion avec l’INSEE n’a été effectuée. Les huit séries sont incorporées au HTML et chargées automatiquement à chaque ouverture, hors ligne. Dans **Analyse**, le sélecteur choisit uniquement la courbe affichée : les métaux USGS depuis 1900 et le pétrole EIA depuis 1859 sont sélectionnés par défaut. Les CSV restent exportables comme copies des données.

| Fichier CSV | Période observée | Fréquence | Mesure / unité publiée |
| --- | --- | --- | --- |
| `usgs_or.csv` | 1900–2022 (123 points) | Annuelle | Valeur unitaire nominale, USD / tonne métrique |
| `usgs_argent.csv` | 1900–2021 (122 points) | Annuelle | Valeur unitaire nominale, USD / tonne métrique |
| `usgs_cuivre.csv` | 1900–2020 (121 points) | Annuelle | Valeur unitaire nominale, USD / tonne métrique |
| `eia_petrole_us.csv` | 1859–2025 (167 points) | Annuelle | Prix du premier achat de pétrole brut américain, USD / baril |
| `wb_or.csv` | 1960-01–2025-12 (792 points) | Mensuelle | Colonne Gold, USD / once troy |
| `wb_argent.csv` | 1960-01–2025-12 (792 points) | Mensuelle | Colonne Silver, USD / once troy |
| `wb_cuivre.csv` | 1960-01–2025-12 (792 points) | Mensuelle | Colonne Copper, USD / tonne métrique |
| `wb_brent.csv` | 1960-01–2025-12 (792 points) | Mensuelle | Colonne Crude oil, Brent, USD / baril — voir réserve ci-dessous |

Les fichiers annuels ont les colonnes `year,price` et les mensuels `date,price`. Le calculateur utilise la fréquence de la courbe sélectionnée : un pas annuel reste annuel, un pas mensuel reste mensuel. Les fenêtres SMA, EMA, RSI et Bollinger sont exprimées dans cette fréquence ; le facteur de volatilité est √1 pour une série annuelle, √12 pour une série mensuelle. Aucune valeur annuelle n’est répétée sur douze mois. Les points annuels sont positionnés au milieu de l’année uniquement pour leur représentation graphique. Rendements et drawdowns calculés sur les moyennes annuelles ne décrivent pas les fluctuations internes à l’année. L’import de CSV personnels reste limité aux séries mensuelles ; les historiques annuels intégrés sont analysables sans import.

## Métaux : USGS Data Series 140

Sources officielles : [or](https://www.usgs.gov/media/files/gold-historical-statistics-data-series-140), [argent](https://www.usgs.gov/media/files/silver-historical-statistics-data-series-140), [cuivre](https://www.usgs.gov/media/files/copper-historical-statistics-data-series-140). Les trois classeurs `.xlsx` originaux sont conservés, y compris leurs documents méthodologiques incorporés. La colonne extraite est exactement **Unit value ($/t)**, et non **Unit value (98$/t)** : il s’agit de dollars courants, pas de dollars constants de 1998.

La méthodologie incorporée du classeur or décrit une estimation fondée sur le prix mondial moyen jusqu’en 1967, puis sur les cotations moyennes Engelhard à partir de 1968. Celle du cuivre utilise le prix producteur américain moyen annuel. Ces définitions ne sont pas identiques à un fixing londonien mensuel ni au prix LME. Les notes texte de l’or et du cuivre ont été extraites des documents Word incorporés ; le passage relatif à la valeur unitaire de l’argent est également extrait dans `ds140-silver-2021.notes.txt`, depuis le document Word binaire incorporé.

## Mensuel : Banque mondiale, Pink Sheet

[Catalogue officiel](https://www.worldbank.org/en/research/commodity-markets) et [page du document](https://thedocs.worldbank.org/en/doc/18675f1d1639c7a34d463f59263ba0a2-0050012025/worldbank-commodities-price-data-the-pink-sheet). Les définitions de la feuille `Description` sont archivées dans `worldbank_definitions.txt`.

Le fichier extrait est `CMO-Historical-Data-Monthly-2026.xlsx`, nommé selon l’année du téléchargement. Ses observations s’arrêtent en décembre 2025 ; son en-tête indique « Updated on January 06, 2025 », information incohérente avec cette dernière observation. Nous retenons les dates des lignes pour la couverture, sans présenter cet en-tête comme une date de publication fiable. Le premier classeur téléchargé via une ancienne URL, arrêté en décembre 2024, est conservé séparément mais n’est pas utilisé pour les CSV.

L’or est décrit comme le fixing londonien de l’après-midi ; le cuivre comme le prix de règlement LME grade A. Pour l’argent, la documentation précise Handy & Harman avant juillet 1976 et de l’argent non raffiné avant 1962 : ces ruptures doivent être prises en compte dans une comparaison de long terme.

**La colonne nommée « Brent » contient des valeurs dès 1960, mais cela ne démontre pas l’existence d’un prix de marché du Brent à cette date.** Le champ n’est entré en production qu’en 1976 selon [Shell](https://www.shell.co.uk/about-us/sustainability/decommissioning/brent-field-decommissioning/the-brent-story). La feuille de description consultée ne précise pas la construction de la partie ancienne. Cette colonne est donc conservée telle que publiée et séparée de l’INSEE ; sa partie antérieure à 1976 doit être documentée avant tout raccord.

## Pétrole ancien : EIA

[Table officielle EIA](https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?f=a&n=pet&s=f000000__3), série `F000000__3`, fréquence annuelle. La page HTML brute est conservée avec son empreinte. L’extracteur lit les lignes de décennies, leurs dix colonnes annuelles et les seules cellules numériques ; il contrôle ensuite l’absence de trous et de doublons.

Il s’agit de pétrole américain, **pas de Brent**. Cela permet une étude du pétrole dès le XIXe siècle, à condition de conserver l’identité de cette série. Une courbe pétrole de longue durée assemblant plusieurs références devrait documenter chaque changement de référence.

## Traçabilité et reproduction

`sources.json` contient les URL de téléchargement, les dates de récupération et les SHA-256 des sources. `catalogue.json` contient les huit séries extraites, leurs périodes, unités, fréquences et empreintes CSV. Les originaux restent disponibles pour vérifier une observation ou une définition.

Pour reproduire les extractions hors ligne depuis les archives :

```bash
python3 outils/extraire_historiques_anciens.py
```

Dépendances propres à cet extracteur : `openpyxl` et `beautifulsoup4`. Le collecteur INSEE reste indépendant et n’utilise que la bibliothèque standard. Les anciennes données ne sont pas automatiquement actualisées par le bouton INSEE : une nouvelle édition doit être archivée et contrôlée avec les mêmes définitions avant de remplacer une extraction. Les archives actuelles restent conservées.

## Sens des observations annuelles USGS

Une ligne représente une **valeur moyenne de l’année**, pas une cotation du 31 décembre. Pour l’or, la valeur unitaire est estimée à partir de prix moyens (marché mondial jusqu’en 1967, Engelhard ensuite). Pour l’argent, la note définit une valeur moyenne par tonne de métal d’une pureté minimale de 99,9 %. Pour le cuivre, elle cite explicitement le prix producteur américain moyen annuel. Les colonnes sont exprimées en dollars courants par tonne métrique. Les notes consultées ne décrivent pas complètement le calendrier des cotations ni leur pondération : on ne peut pas affirmer que chaque observation est une moyenne arithmétique de tous les jours de l’année. Les prix producteurs, fixings, estimations de valeur unitaire et prix de premier achat sont conservés comme des mesures distinctes.

## Affichage de l’or

Les colonnes USGS en USD/t sont conservées à l’identique. Dans l’analyse, l’or est affiché en USD par once troy par défaut, ou en USD par gramme au choix. La conversion par once est `prix_USD_t × 31,1034768 / 1 000 000` ; par gramme `prix_USD_t / 1 000 000`. Les sources déjà par once sont divisées par 31,1034768 pour l’affichage au gramme. Les valeurs d’origine, la fréquence et la devise restent intactes. Voir la définition de l’once troy chez [Royal Mint](https://www.royalmint.com/faqs/bullion/what-is-a-troy-ounce/) et les [conversions de métaux précieux du NIST](https://www.nist.gov/system/files/documents/2017/05/09/Precious-Metals-Conversion-Information-march2015.pdf).
