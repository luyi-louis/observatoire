# Observatoire

Ouvrir **Observatoire.html** dans un navigateur récent, par double-clic. Ce fichier contient l’interface, les calculs et les historiques annuels anciens USGS/EIA, les historiques mensuels Banque mondiale et les quatre historiques INSEE vérifiés : aucun serveur, installation ou accès Internet nécessaire. Il peut être copié seul sur un autre ordinateur.

Les historiques anciens sont chargés automatiquement et affichés par défaut : métaux dès 1900, pétrole américain dès 1859. Choisir un actif, une courbe source et une période, activer les moyennes mobiles ou Bollinger, puis explorer les graphiques au survol ou au toucher. Les vues RSI/MACD et volatilité/drawdown sont commutables. L’échelle propose cours, base 100 et axe logarithmique. L’onglet **Aide** consacre une fiche à chaque indicateur (moyennes mobiles, Bollinger, RSI, MACD, volatilité, drawdown, rendement annualisé, base 100 et axe logarithmique, ratio or/argent) : ce qu’il mesure, sa définition, comment le lire et ses limites, sans prérequis en finance. Le bouton « ? » de chaque graphe ouvre directement la fiche de ce qui est affiché. L’onglet « Paramètres & méthode de calcul » rassemble les réglages et un guide pédagogique adapté du document LaTeX : formules, interprétations, exemples et conventions de calcul. Son sommaire donne accès aux huit chapitres. Les onglets sont aussi accessibles au clavier (flèches, Début et Fin).

« Importer un CSV » remplace une série ou ajoute une série personnelle pour la session. Format : `date,prix`, dates `AAAA-MM`, prix positifs, un point par mois sans lacune. Le point-virgule et les décimales françaises sont acceptés. Les imports ne sont pas conservés après rechargement. « Exporter » télécharge les valeurs et indicateurs de la période visible.

Les CSV initiaux remontaient déjà à 1990 et restent intacts. Le CSV cuivre initial duplique l’or ; la série intégrée utilise désormais les cours officiels du cuivre. Les unités sont explicites et l’argent est converti en dollars par once troy pour le ratio. Les archives ZIP initiales ne sont pas raccordées aux séries. Le test ADF du script Python n’est pas repris.

Validation des calculs et du lecteur CSV : `node tests/observatoire.test.cjs`.

D’après le travail de Louis Tomczyk et contributeurs, sous licence CC BY-SA 4.0. Cette adaptation ajoute une interface HTML autonome et initialise les indicateurs sur l’historique antérieur à la période affichée.

## Sources et actualisation

L’onglet **Sources & mise à jour** propose les liens officiels, les unités, la provenance et la collecte à la demande. Pour activer le bouton de collecte, lancer `python3 outils/actualiser_cours.py --serve`, puis ouvrir **http://127.0.0.1:8765**. Le serveur local utilise l’API publique INSEE et archive ses réponses ; il ne modifie pas les CSV initiaux.

Le HTML ouvert seul accepte les collectes JSON produites par `python3 outils/actualiser_cours.py`. La collecte demande tout l’historique disponible, sans limite de dates. La fusion prévisualisée conserve les mois anciens, ajoute les nouveaux et tient compte des révisions. Le collecteur maintient `mises_a_jour/historique_complet.json` et garde chaque archive datée. Les historiques appliqués sont aussi sauvegardés dans le navigateur lorsque son stockage est disponible ; conserver le JSON complet comme sauvegarde portable. Les graphes affichent tout l’historique par défaut : réduire la période affichée ne supprime aucune donnée.

Voir [Sources et méthode de mise à jour](SOURCES_ET_MISE_A_JOUR.md) pour le catalogue exact, l’import manuel des exports INSEE, l’architecture de collecte et l’ajout d’un extracteur pour un autre site.

## Conventions des figures

Les graphes suivent le tutoriel « How to — Make graphs » de Louis Tomczyk : fond blanc, axes nommés et unités explicites, graduations majeures et mineures, légendes permanentes, styles de traits distincts et panneaux utilisant les mêmes bornes temporelles. Sur grand écran, le cours occupe la colonne gauche sur deux lignes ; momentum et risque sont empilés à droite. Sur mobile, les trois panneaux se suivent verticalement. Chaque zone de tracé est encadrée sur ses quatre côtés ; une courbe seule est noire. La grille temporelle majeure tombe tous les cinq ans, la mineure tous les ans, indépendamment du zoom. Les observations sont représentées par des cercles ; les SMA sont tiretées, les EMA en traits mixtes. Les familles SMA/EMA sont sélectionnées séparément pour limiter la superposition. Les bandes de Bollinger sont une enveloppe de dispersion des prix, pas des barres d’erreur sur les observations.

Les valeurs positives peuvent être affichées sur un véritable axe logarithmique, en conservant leurs unités. L’échelle linéaire du cours inclut zéro par défaut, avec une option « Plage des données ». Le RSI garde ses bornes 0–100 ; volatilité et drawdown conservent leur origine. L’écart MACD–signal est tracé en courbe, et les repères 0, 30 et 70 sont annotés là où ils s’appliquent.

La disposition est resserrée : aucun titre visible ni rappel de source sous les graphes, les axes Y identifient la grandeur et son unité. Les légendes sont à l’intérieur des cadres, dans le coin qui croise le moins de segments de données. Chaque bouton **SVG** exporte cette figure compacte avec ses axes et sa légende ; le titre, la période et la provenance sont conservés dans les métadonnées accessibles du SVG. Le bouton **CSV** exporte les valeurs numériques. Aucune incertitude de mesure ni régression n’est ajoutée sans données qui la justifient.

## Thème clair ou sombre

Le sélecteur **Thème** propose Auto (celui du système, par défaut), Clair ou Sombre ; le choix est mémorisé. En sombre, les graphes changent de palette à l’écran, mais les SVG exportés gardent toujours la palette claire des figures (fond blanc, courbe seule noire) décrite ci-dessus.

## Langues

Le sélecteur **Langue / Language / Язык** permet de basculer intégralement entre français, anglais et russe, y compris la documentation, les graphes et les messages applicatifs. Le choix est mémorisé et conserve la session d’analyse.

Les traductions sont centralisées dans `locales/fr.json`, `locales/en.json` et `locales/ru.json`, puis intégrées au HTML autonome. Voir [Ajouter ou modifier une langue](locales/README.md) pour la procédure complète : un catalogue supplémentaire suffit pour proposer une langue supplémentaire.

## Historiques anciens

Huit historiques anciens sont chargés systématiquement, conservés dans le HTML autonome et dans [historiques_anciens](historiques_anciens/README.md) : métaux USGS annuels dès 1900, pétrole américain EIA annuel dès 1859 et quatre colonnes Banque mondiale mensuelles dès 1960. Les unités et devises publiées sont conservées. Ces archives restent distinctes des séries INSEE ; le calculateur respecte leur fréquence annuelle ou mensuelle. Le choix de courbe change l’affichage, jamais le chargement des données. La définition de chaque mesure annuelle est affichée au-dessus des graphes.

## Unité de l’or et zoom

L’or est affiché par **once troy** par défaut, pour les trois fournisseurs. Le sélecteur permet de passer au **gramme**. Les observations USGS restent archivées en USD par tonne ; seule leur représentation et les calculs associés sont convertis. La transformation utilise 1 once troy = 31,1034768 g et 1 tonne métrique = 1 000 000 g. Il n’y a aucune conversion monétaire. Les axes, infobulles, moyennes, MACD et export CSV suivent l’unité choisie ; le CSV d’analyse indique aussi la source, la fréquence et l’unité. Les exports des archives originales gardent les unités publiées.

La barre **Zoom** propose **X**, **Y** et **X+Y**. La molette agrandit/réduit autour du pointeur ; glisser dans le cadre sélectionne une zone, également sur écran tactile. Le bouton **Synchroniser les graphes** active ou désactive la synchronisation. X partage les mêmes dates ; Y partage une fraction de chaque domaine vertical, et non des valeurs numériques entre unités différentes. Sur un axe logarithmique, le zoom vertical est calculé dans l’espace logarithmique.

Le double-clic réinitialise le graphe (tous les graphes si synchronisés). **Réinitialiser le zoom** restaure les trois domaines. La période sélectionnée, les observations et les statistiques ne sont pas modifiées par le zoom ; les SVG exportent la vue courante. Changer d’actif, de source, d’unité, de période ou de définition d’indicateur réinitialise le zoom ; changer de langue conserve la vue. Les grilles X restent espacées de cinq ans et d’un an.
