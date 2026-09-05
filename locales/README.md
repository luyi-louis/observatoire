# Langues de l’application

Le sélecteur **Langue / Language / Язык** traduit toute l’interface en français, anglais ou russe, les guides pédagogiques, les sources, les attributs d’accessibilité, les messages applicatifs, les figures et leurs exports SVG. Il conserve les données, la période, les réglages et l’onglet actif. La préférence est mémorisée localement lorsque le navigateur autorise le stockage.

Les catalogues sont intégrés à `Observatoire.html` : le fichier reste autonome, sans connexion ni chargement JSON externe. Le serveur de collecte continue à servir ce même fichier.

## Ajouter une langue supplémentaire

1. Copier `en.json` vers le code de la langue, par exemple `es.json`.
2. Modifier `label` (nom natif affiché dans le sélecteur), `locale` (format régional BCP 47, par exemple `es-ES`) et `direction` (`ltr` ou `rtl`).
3. Traduire **toutes** les valeurs de `messages`, y compris les guides `html.*`, les formules avec mots, les unités `unit.*`, les textes de graphes `chart.*` et les erreurs `error.*`.
4. Conserver les clés, les paramètres `{months}`, `{asset}`, etc., les liens de source et le balisage en ligne. L’ordre des paramètres peut changer selon la grammaire de la langue.
5. Depuis la racine du projet, exécuter :

```bash
python3 outils/integrer_traductions.py
```

La nouvelle langue apparaît automatiquement dans le sélecteur. Aucun `if (langue === ...)` ni changement du code de l’interface n’est nécessaire. Il faut vérifier visuellement la traduction, surtout pour des textes plus longs ou une écriture de droite à gauche ; le sens du document est configurable, mais les figures conservent leurs axes scientifiques orientés de gauche à droite.

Pour contrôler sans modifier le HTML :

```bash
python3 outils/integrer_traductions.py --check
```

Le contrôle refuse les clés absentes ou supplémentaires, les messages vides, les paramètres incohérents, les balises non autorisées et les changements de liens. Il ne peut pas juger la qualité linguistique : la relecture humaine reste nécessaire.

## Modifier ou ajouter un texte

Les clés `html.001` à `html.247` sont des identifiants stables : ne pas les renuméroter. Leur valeur française fournit le contexte de traduction. Les autres clés sont regroupées par usage (`chart`, `error`, `source`, etc.).

Pour un nouveau contenu statique, ajouter la même clé dans tous les catalogues, puis utiliser `data-i18n="cle"` pour du texte ou `data-i18n-html="cle"` pour du texte enrichi. Ne jamais placer ce dernier attribut sur un élément contenant un contrôle interactif. Les attributs `data-i18n-aria-label` et `data-i18n-placeholder` prennent également une clé.

Pour un contenu dynamique : `t('cle', {months: 12})`. Les paramètres ne se traduisent pas par concaténation de fragments de phrase. Pour un message affiché durablement : `setMessage('idElement', 'cle', params)`. Pour une erreur : `throw new I18nError('error.cle', params)`, puis `setError(...)`. Une valeur de paramètre peut être une fonction pour recalculer sa traduction lors d’un changement de langue.

Les chaînes enrichies sont validées lors de l’intégration et proviennent des catalogues locaux du projet. Les valeurs de données sont échappées avant toute insertion dans le HTML ou le SVG.

## Formats et éléments conservés

Les nombres suivent le format régional choisi. Les CSV exportés conservent les noms de colonnes techniques, le séparateur point-virgule et les dates ISO `AAAA-MM`, mais utilisent le séparateur décimal régional. Les axes temporels scientifiques gardent leurs graduations ISO et leurs intitulés traduits. Les dates de collecte lisibles suivent la langue et affichent UTC.

Les identifiants de série, noms de fichiers, commandes, liens et unités canoniques du protocole JSON ne changent pas. Les unités reconnues sont traduites à l’affichage seulement. Un texte libre fourni par l’utilisateur, un intitulé brut archivé de fournisseur ou une page externe ne sont pas traduits automatiquement. Les fenêtres natives de choix de fichiers et de dates suivent la langue du navigateur ou du système.

## Tests

Depuis la racine :

```bash
node tests/observatoire.test.cjs
python3 -m unittest discover -s tests -p 'test_*.py'
```

Le test DOM optionnel utilise jsdom 26 (uniquement pour le développement, aucune dépendance à l’exécution de l’application) :

```bash
npm install --prefix /tmp/observatoire-i18n-test --ignore-scripts --no-audit --no-fund jsdom@26
JSDOM_PATH=/tmp/observatoire-i18n-test/node_modules/jsdom node tests/i18n.dom.cjs
```

Il vérifie les basculements FR → EN → RU → FR, le guide ADF complet, les textes des figures et leur SVG exporté, les formats numériques, les erreurs déjà présentes, la prévisualisation et l’application des collectes, la conservation de l’état et une langue supplémentaire simulée. La langue simulée sert au test et n’est pas livrée comme traduction.
