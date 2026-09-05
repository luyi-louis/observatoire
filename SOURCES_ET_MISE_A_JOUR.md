# Sources et mise à jour des cours

Documentation vérifiée le 5 septembre 2026. L’onglet **Sources & mise à jour** contient également le guide et les commandes, afin de rester utilisable dans le HTML autonome.

## Catalogue retenu

| Actif | Fiche officielle INSEE | Unité de la source | Unité après collecte |
| --- | --- | --- | --- |
| Or | [010002061](https://www.insee.fr/fr/statistiques/serie/010002061) | USD par once | USD par once troy |
| Argent | [010002043](https://www.insee.fr/fr/statistiques/serie/010002043) | Cents US par once troy | USD par once troy, division par 100 |
| Brent | [010002077](https://www.insee.fr/fr/statistiques/serie/010002077) | USD par baril | Identique |
| Cuivre | [010002052](https://www.insee.fr/fr/statistiques/serie/010002052) | USD par tonne | Identique |

Le collecteur utilise des séries mensuelles diffusées par l’INSEE, pas un flux de cotations instantanées. La date de consultation, la date de publication et le dernier mois observé sont trois informations distinctes. Certaines valeurs historiques peuvent être révisées.

Chercher une nouvelle série dans le [catalogue INSEE](https://www.insee.fr/fr/information/2411675), puis vérifier sa fiche : identifiant, unité, fréquence, prix/indice, comptant/terme, méthode et éventuel arrêt de série. Les archives locales 010002091 et 010002094 sont des indices en euros base 2010 et ne correspondent pas aux séries de prix du tableau. Le CSV cuivre initial du dossier duplique l’or ; il n’est pas utilisé comme base de raccord par le collecteur.

Pour vérifier la référence de marché : [LBMA / ICE Benchmark Administration](https://www.ice.com/iba/lbma-precious-metals), [portail historique LBMA](https://portal.lbma.org.uk/), [cuivre LME](https://www.lme.com/en/Metals/Non-ferrous/LME-Copper), [Brent mensuel EIA](https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=RBRTE&f=M). Les accès et licences de ces organismes sont distincts. Un prix comptant ne doit pas être raccordé automatiquement à un contrat à terme, ni un prix à un indice.

## Utiliser le bouton dans l’application

Prérequis : Python 3.9 ou plus récent et une connexion Internet pour la collecte ; aucune bibliothèque externe.

Depuis le dossier du projet :

```bash
python3 outils/actualiser_cours.py --serve
```

Ouvrir **http://127.0.0.1:8765**, puis **Sources & mise à jour → Rechercher les dernières données**. Examiner les périodes et les différences affichées, puis cliquer sur **Utiliser ces données**. L’opération fusionne les quatre historiques ensemble, en conservant tous les mois déjà présents ; le ratio est recalculé avec des unités compatibles. Les CSV et le HTML sur disque ne sont pas écrasés.

Le serveur écoute uniquement sur la boucle locale. Ctrl+C l’arrête. Pour changer de port : `--port 8766`, puis utiliser l’adresse affichée dans le terminal. Il ne faut pas lancer un simple `python3 -m http.server` : ce dernier ne fournit pas le point d’accès de collecte.

## Utiliser uniquement le HTML autonome

Collecter en ligne de commande :

```bash
python3 outils/actualiser_cours.py
```

Un dossier daté est créé sous `mises_a_jour/`, avec :

- `source-insee.xml` : réponse brute de l’API ;
- `cours-insee.json` : historiques complets normalisés et provenance.

Le fichier `mises_a_jour/historique_complet.json` conserve également la dernière fusion complète. Chaque collecte repart de ce cache et ajoute les mois reçus ; les valeurs des mois communs sont actualisées. Les archives datées restent intactes, même en cas de révision. Conserver ce dossier lors du transfert du projet.

Ouvrir le HTML par double-clic, puis **Sources & mise à jour → Importer une collecte JSON** et sélectionner le second fichier. La prévisualisation et l’application des données fonctionnent hors ligne.

**Conserver la collecte JSON** télécharge également la collecte prévisualisée depuis l’interface. Les historiques INSEE appliqués sont sauvegardés dans le stockage du navigateur et restaurés au rechargement. Ce stockage dépend du navigateur et de l’adresse utilisée ; il peut être indisponible pour un fichier local ou effacé. Un message signale un échec de sauvegarde. Le JSON complet reste la sauvegarde portable à conserver. Le JSON n’est pas une sauvegarde des réglages ou des séries CSV personnelles.

Le bouton de collecte directe nécessite le service Python local : les restrictions de lecture entre sites des navigateurs ne permettent pas de garantir une collecte distante depuis un simple fichier HTML.

## Télécharger manuellement

Sur la fiche INSEE, télécharger le CSV/ZIP et extraire `valeurs_mensuelles.csv`. L’import CSV reconnaît le préambule INSEE (Libellé, idBank, dernière mise à jour, Période). Les mois sans valeur aux extrémités sont ignorés ; une lacune interne est refusée. Sélectionner l’actif et renseigner l’unité telle que publiée.

**Cet import manuel ne convertit pas les unités.** Une série argent en cents ne doit pas être comparée à de l’or en dollars sans conversion. Préférer la collecte JSON fournie pour obtenir les quatre séries normalisées ensemble. Les imports de CSV simples `date,prix` restent possibles.

## Méthode de collecte et d’extraction

L’INSEE documente son [service SDMX public](https://www.insee.fr/fr/information/2862759). Le collecteur effectue une requête HTTPS avec négociation du format SDMX StructureSpecific 2.1 :

```text
https://bdm.insee.fr/series/sdmx/data/SERIES_BDM/010002061+010002043+010002077+010002052
```

Il valide l’identifiant de chaque série, la fréquence mensuelle, le libellé attendu, `UNIT_MEASURE` et `UNIT_MULT`. Il contrôle dates, unicité, valeurs finies strictement positives et continuité. Les observations manquantes en bordure sont recensées dans `skippedMonths`. Il n’interpole pas les mois et n’assemble pas de fournisseurs différents.

Il demande tout l’historique disponible, sans `startPeriod`, `endPeriod` ni `lastNObservations` : une éventuelle extension antérieure à 1990 sera récupérée. Les CSV initiaux remontaient déjà à 1990 ; cette profondeur est conservée. La vue initiale affiche tout l’historique, et les filtres du graphe ne limitent jamais la collecte ni la sauvegarde.

Le collecteur conserve les mois absents d’une nouvelle réponse et applique les révisions aux mois communs. Dans l’application, la fusion exige la même série INSEE et la même unité ; pour chaque mois commun, la date de collecte la plus récente prévaut, afin qu’un ancien JSON ne fasse pas régresser les valeurs. Les mois conservés sont listés dans `retainedMonths`. Un import CSV de provenance différente ne peut être remplacé par une collecte plus courte : l’application refuse de supprimer ses mois non couverts. Aucun raccord arbitraire ni interpolation n’est effectué. Le prévisualiseur compare les valeurs avec les séries actuellement en mémoire ; ces écarts ne constituent pas tous des révisions officielles, car les CSV initiaux peuvent avoir une provenance ou une unité différente.

La réponse brute est archivée avec son empreinte SHA-256 dans le manifeste JSON, ainsi que l’URL, l’heure UTC de collecte, la publication indiquée par l’INSEE, les unités et le facteur de conversion. Le JSON fusionné peut aussi contenir des observations de collectes précédentes : l’empreinte porte uniquement sur la dernière réponse XML brute, et non sur l’ensemble fusionné. Cette empreinte permet de comparer le XML archivé ; elle ne constitue pas une signature de l’INSEE ni une authentification d’un JSON importé.

Un délai réseau de 30 secondes et une limite de réponse de 10 Mo bornent la collecte. Il n’y a pas de tâche planifiée, ni de boucle de tentatives : chaque collecte résulte d’une commande ou d’un clic. En cas d’erreur, rien n’est appliqué dans l’interface. Les archives de test de développement sont distinctes des données du projet.

## Ajouter un fournisseur ou un scraper

Le catalogue fixe `SOURCES` et l’adaptateur `parse_sdmx` se trouvent dans `outils/actualiser_cours.py`. L’interface valide aussi les identifiants et unités avec `OFFICIAL_IDS` et `OFFICIAL_UNITS`. Un changement de série exige de modifier ces deux catalogues après vérification des métadonnées ; une autre API exige un adaptateur et un format d’import explicitement validé.

Pour un site sans API ou export utilisable :

1. Vérifier les conditions d’accès, les règles robots.txt et la disponibilité publique du tableau ; ne pas contourner un accès authentifié ou payant.
2. Utiliser une URL fixe et un extracteur propre à la source. Repérer le tableau par ses en-têtes et unités plutôt que par sa seule position dans la page.
3. Conserver une réponse de référence et tester le parseur sur celle-ci ; un changement de structure doit produire une erreur, pas des prix plausibles mais incorrects.
4. Déclarer la fréquence, la devise, l’unité et le type de prix. Ne pas intégrer une série quotidienne dans les calculs mensuels sans définir explicitement une agrégation (moyenne ou clôture mensuelle).
5. Réutiliser les contrôles, la provenance et la prévisualisation, avec des téléchargements limités et à la demande.

Aucun scraper de pages LBMA, LME ou EIA n’est activé dans cette version. L’adaptateur INSEE est implémenté et testé sur le service réel.

## Validation

```bash
node tests/observatoire.test.cjs
python3 -m unittest discover -s tests -p 'test_*.py'
```

Le 5 septembre 2026, le collecteur et son point d’accès HTTP local ont récupéré les quatre séries : 439 observations chacune, de janvier 1990 à juillet 2026. Ce résultat est une vérification ponctuelle, pas une garantie de disponibilité future.

## Sources anciennes anglophones

Les fichiers vérifiés, leurs CSV et les définitions sont décrits dans [Historiques anciens](historiques_anciens/README.md). L’interface charge les huit séries automatiquement et permet de les analyser hors ligne, à leur fréquence d’origine. Le sélecteur change uniquement la courbe affichée. Une copie CSV reste exportable. Les séries annuelles et les références de marché différentes sont conservées séparément, sans conversion de devise ni raccord automatique. La collecte INSEE ne modifie pas ces archives.
