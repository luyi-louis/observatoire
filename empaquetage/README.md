# AppImage Linux

Un seul fichier, sans installation ni droits administrateur : une fenêtre
NW.js qui affiche `Observatoire.html`.

```bash
./empaquetage/build-observatoire-appimage.sh             # → empaquetage/dist/Observatoire-v0.1.0-x86_64.AppImage
./empaquetage/build-observatoire-appimage.sh --install   # + entrée dans le menu des applications
./empaquetage/build-observatoire-appimage.sh --uninstall # retire l'entrée (garde les collectes)
```

`PRODUCT_VERSION=0.2.0` change la version du livrable, écrite dans le script
seulement. `NW_FLAVOR=sdk` construit une variante avec DevTools, nommée
`…-sdk-…`, qui sert uniquement aux vérifications automatiques.

## Ce que fait l'AppImage au lancement

1. Si `python3` (3.9 ou plus récent) est présent, elle démarre le collecteur
   INSEE local (`outils/actualiser_cours.py --serve`) sur `127.0.0.1:8765`
   (8766 à 8769 si ce port est pris), puis la fenêtre ouvre la page servie par
   lui : le bouton **Rechercher les dernières données** fonctionne.
2. Les collectes sont écrites hors de l'image, qui est en lecture seule :
   `~/.local/share/observatoire/mises_a_jour/` (ou `$XDG_DATA_HOME/observatoire/`).
   Le premier lancement y copie l'historique embarqué ; chaque collecte s'y
   fusionne ensuite, comme dans le dépôt. Journal : `serveur.log`, à côté.
3. Sans `python3`, la fenêtre ouvre la copie embarquée hors ligne : historiques,
   calculs, exports et import d'une collecte JSON restent disponibles.
4. À la fermeture de la fenêtre, le collecteur s'arrête.

## Construction

Le script refuse de construire si `Observatoire.html` n'intègre pas la dernière
collecte (`outils/integrer_cours.py --check`) ou les traductions courantes.

NW.js v0.113.0 et le runtime AppImage type-2 sont épinglés par empreinte
SHA-256. Ils sont téléchargés une fois dans `empaquetage/cache/`, ou lus dans
`$SHARED_PACKAGING/cache` si cette variable désigne un cache existant (des liens
symboliques posés dans `empaquetage/cache/` font aussi l’affaire). Les livrables
vont dans `empaquetage/dist/`. Ces deux dossiers sont ignorés par git.

Un poste sans FUSE refuse de monter une AppImage : `sudo apt install libfuse2`.
