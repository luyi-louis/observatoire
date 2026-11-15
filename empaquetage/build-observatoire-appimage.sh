#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
#  build-observatoire-appimage.sh — Observatoire → une AppImage Linux portable.
#  version 1.0.0 (2026-11-15)
#
#  Usage : ./build-observatoire-appimage.sh                 # → dist/Observatoire-v<version>-x86_64.AppImage
#          ./build-observatoire-appimage.sh --install       # + entrée de menu (sans root)
#          ./build-observatoire-appimage.sh --uninstall     # retire l'entrée de menu
#          PRODUCT_VERSION=0.3.0 ./build-observatoire-appimage.sh
#          NW_FLAVOR=sdk ./build-observatoire-appimage.sh   # avec DevTools, pour sonder
#
#  Livraison : l'AppImage livrable (saveur normal) est aussi COPIÉE dans le
#  dossier Téléchargements (xdg-user-dir DOWNLOAD), par livrer-telechargements.sh
#  de la chaîne d'empaquetage voisine (LIVRAISON_SH=<chemin> pour un autre) :
#  copie vérifiée par cmp, un ancien fichier différent est gardé sous
#  <nom>-avant-<date>. Script absent (clone ailleurs) : on le dit, sans livrer.
#
#  Chaîne NW.js classique (NW.js v0.113.0, runtime AppImage type-2 épinglé,
#  --no-sandbox, StartupWMClass) : une fenêtre
#  NW.js affiche Observatoire.html, déjà autonome. Une seule différence : le
#  bouton de collecte INSEE a besoin du service Python local. AppRun le démarre
#  donc avec le python3 du système (bibliothèque standard seulement), et écrit
#  les collectes hors de l'image, en lecture seule :
#      ${XDG_DATA_HOME:-~/.local/share}/observatoire/mises_a_jour/
#  Sans python3 (≥ 3.9), la fenêtre ouvre la copie embarquée hors ligne : tous
#  les historiques, calculs et exports restent disponibles, et l'import d'une
#  collecte JSON aussi.
#
#  Réseau : seulement si un cache manque (runtime NW.js, runtime AppImage,
#  appimagetool). Ils sont cherchés dans cache/ (ignoré par git : on peut y
#  poser des liens vers des caches existants), puis dans $SHARED_PACKAGING/cache
#  et $SHARED_PACKAGING/tools si cette variable est posée, jamais modifiés ;
#  sinon téléchargés une fois dans cache/, et vérifiés par leur SHA-256.
# ══════════════════════════════════════════════════════════════════════════════
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
DIST="${DIST:-$HERE/dist}"
APPNAME="Observatoire"
LOWER="observatoire"

# La version du LIVRABLE : écrite ici seulement.
PRODUCT_VERSION="${PRODUCT_VERSION:-0.2.0}"
FLAVOR="${NW_FLAVOR:-normal}"
NW_VERSION="v0.113.0"

# Empreintes épinglées.
declare -A NW_SHA=(
  [normal]="1963d6dfa40eaeec11e8158fbf8787d765bb1ffd0dbab572433ccbc519c7d17d"
  [sdk]="340e7c6b9fdc0426b5a96fea0df5b93ad671b4e0544dc056fe3227e8b722292d"
)
AIRUNTIME_SHA="1cc49bcf1e2ccd593c379adb17c9f85a36d619088296504de95b1d06215aebbf"
AIRUNTIME_URL="https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-x86_64"
AITOOL_URL="https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
SHARED="${SHARED_PACKAGING:-}"
CACHE="${CACHE:-$HERE/cache}"   # réglable, comme DIST : la console de la chaîne les veut hors du dépôt

BIN="$HOME/.local/bin"
APPS="$HOME/.local/share/applications"
ICONS="$HOME/.local/share/icons/hicolor/256x256/apps"
USERDATA="${XDG_DATA_HOME:-$HOME/.local/share}/observatoire"

say(){ printf '\n\033[1;32m▸ %s\033[0m\n' "$*"; }
die(){ printf '\n\033[1;31m✗ %s\033[0m\n' "$*" >&2; exit 1; }

# ── --uninstall : avant tout contrôle, pour marcher même sans dist/ ──────────
if [ "${1:-}" = "--uninstall" ]; then
  rm -f "$BIN/${APPNAME}.AppImage" "$APPS/${LOWER}.desktop" "$ICONS/${LOWER}.png"
  update-desktop-database "$APPS" >/dev/null 2>&1 || true
  gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true
  echo "▸ Entrée de menu retirée."
  # Les collectes sont des données de l'utilisateur : elles ne s'effacent pas d'office.
  [ -d "$USERDATA" ] && echo "  Collectes conservées : $USERDATA (à supprimer à la main si on le souhaite)."
  exit 0
fi
DO_INSTALL=0
[ "${1:-}" = "--install" ] && DO_INSTALL=1
case "$FLAVOR" in normal|sdk) ;; *) die "NW_FLAVOR=$FLAVOR inconnu (normal | sdk)";; esac

# Livraison dans Téléchargements : le dossier est cherché AVANT de compiler,
# pour l'apprendre en une seconde. La variante sdk, de débogage, n'est jamais livrée.
LIVRAISON_SH="${LIVRAISON_SH:-$(dirname "$ROOT")/chaine-empaquetage/packaging/livrer-telechargements.sh}"
LIVRER=0
if [ "$FLAVOR" = "normal" ]; then
  if [ -f "$LIVRAISON_SH" ]; then
    # shellcheck source=/dev/null
    . "$LIVRAISON_SH"
    DL="$(telechargements_dir)" || die "dossier Téléchargements introuvable (DOWNLOADS_DIR=<dossier> pour en imposer un)"
    LIVRER=1
  else
    printf '\n\033[1;33m! livrer-telechargements.sh introuvable : %s\033[0m\n' "$LIVRAISON_SH"
    echo "  L'AppImage restera dans $DIST seulement."
  fi
fi

# Un fichier : le premier cache existant, sinon téléchargé dans cache/.
fetch(){ # nom, url, sha256 attendu (vide = non vérifié)
  local name="$1" url="$2" sha="$3" found=""
  local dirs=("$CACHE"); [ -n "$SHARED" ] && dirs+=("$SHARED/cache" "$SHARED/tools")
  for dir in "${dirs[@]}"; do
    [ -f "$dir/$name" ] && { found="$dir/$name"; break; }
  done
  if [ -z "$found" ]; then
    mkdir -p "$CACHE"
    echo "    téléchargement : $url" >&2
    curl -L --fail --progress-bar -o "$CACHE/$name.part" "$url" || { rm -f "$CACHE/$name.part"; die "téléchargement impossible : $url"; }
    mv "$CACHE/$name.part" "$CACHE/$name"; found="$CACHE/$name"
  fi
  if [ -n "$sha" ]; then
    local got; got="$(sha256sum "$found" | awk '{print $1}')"
    [ "$got" = "$sha" ] || die "empreinte inattendue pour $found
    attendu : $sha
    obtenu  : $got"
  fi
  printf '%s' "$found"
}

# ── 0. La page livrée doit être cohérente avec ses sources ───────────────────
say "Contrôle de la page"
python3 -B "$ROOT/outils/integrer_cours.py" --check | tail -1 \
  || die "Observatoire.html n'intègre pas la dernière collecte : lancer python3 outils/integrer_cours.py"
python3 -B "$ROOT/outils/integrer_traductions.py" --check \
  || die "traductions non intégrées : lancer python3 outils/integrer_traductions.py"

# ── 1. Runtimes ─────────────────────────────────────────────────────────────
say "Runtimes (NW.js $NW_VERSION $FLAVOR, AppImage type-2, appimagetool)"
if [ "$FLAVOR" = "sdk" ]; then NWPKG="nwjs-sdk-${NW_VERSION}-linux-x64"; else NWPKG="nwjs-${NW_VERSION}-linux-x64"; fi
NWTAR="$(fetch "$NWPKG.tar.gz" "https://dl.nwjs.io/${NW_VERSION}/$NWPKG.tar.gz" "${NW_SHA[$FLAVOR]}")"
AIRUNTIME="$(fetch appimage-runtime-x86_64 "$AIRUNTIME_URL" "$AIRUNTIME_SHA")"
AITOOL="$(fetch appimagetool-x86_64.AppImage "$AITOOL_URL" "")"
[ -x "$AITOOL" ] || chmod +x "$AITOOL"
echo "    $NWTAR"; echo "    $AIRUNTIME"; echo "    $AITOOL"

# ── 2. Icône ─────────────────────────────────────────────────────────────────
say "Icône"
ART="$DIST/icone"
python3 -B "$HERE/gen-icone.py" "$ART" >/dev/null

# ── 3. package.nw : la fenêtre, déterministe ─────────────────────────────────
say "package.nw"
WORK="$DIST/_work-$FLAVOR"
rm -rf "$WORK"; mkdir -p "$WORK/stage" "$WORK/nw"
cp "$ROOT/Observatoire.html" "$HERE/lanceur.html" "$WORK/stage/"
cp "$ART/icon-256.png" "$WORK/stage/icon.png"
python3 -B - "$HERE/app-manifest.json" "$WORK/stage/package.json" "$PRODUCT_VERSION" <<'PY'
import json, sys
manifest = json.load(open(sys.argv[1], encoding='utf-8'))
manifest['version'] = sys.argv[3]
json.dump(manifest, open(sys.argv[2], 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
PY
SOURCE_DATE_EPOCH="${SOURCE_DATE_EPOCH:-$(git -C "$ROOT" log -1 --format=%ct 2>/dev/null || echo 315532800)}"
find "$WORK/stage" -exec touch -d "@$SOURCE_DATE_EPOCH" {} +
chmod 644 "$WORK/stage"/*
( cd "$WORK/stage" && find . -mindepth 1 | LC_ALL=C sort | zip -q -X -@ "$WORK/package.nw" )

# ── 4. AppDir ────────────────────────────────────────────────────────────────
say "AppDir"
APPDIR="$WORK/AppDir"
SHARE="$APPDIR/usr/share/$LOWER"
mkdir -p "$APPDIR/usr/bin" "$SHARE/outils" "$SHARE/mises_a_jour" "$APPDIR/usr/share/icons/hicolor/256x256/apps"
tar -xzf "$NWTAR" -C "$WORK/nw"
cp -r "$WORK/nw/$NWPKG/." "$APPDIR/usr/bin/"
mv "$APPDIR/usr/bin/nw" "$APPDIR/usr/bin/$APPNAME"
cp "$WORK/package.nw" "$APPDIR/usr/bin/package.nw"
printf '%s\n' "$PRODUCT_VERSION" > "$APPDIR/usr/bin/VERSION.txt"
# Le service de collecte : la page qu'il sert, le collecteur et l'historique de départ.
cp "$ROOT/Observatoire.html" "$SHARE/"
cp "$ROOT/outils/actualiser_cours.py" "$SHARE/outils/"
cp "$ROOT/mises_a_jour/historique_complet.json" "$SHARE/mises_a_jour/"
cp "$ART/icon-256.png" "$APPDIR/${LOWER}.png"
cp "$ART/icon-256.png" "$APPDIR/usr/share/icons/hicolor/256x256/apps/${LOWER}.png"

cat > "$APPDIR/AppRun" <<EOF
#!/bin/sh
# Observatoire $PRODUCT_VERSION — démarre le collecteur INSEE local si python3 ≥ 3.9
# est présent, puis la fenêtre NW.js ; arrête le collecteur à la fermeture.
HERE="\$(dirname "\$(readlink -f "\$0")")"
SHARE="\$HERE/usr/share/$LOWER"
DATA="\${XDG_DATA_HOME:-\$HOME/.local/share}/$LOWER"
SERVER_PID=""
trap '[ -n "\$SERVER_PID" ] && kill "\$SERVER_PID" 2>/dev/null' EXIT INT TERM
if command -v python3 >/dev/null 2>&1 && python3 -B -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>/dev/null \\
   && mkdir -p "\$DATA/mises_a_jour" 2>/dev/null; then
  # L'historique de départ n'est copié qu'une fois : ensuite, chaque collecte s'y fusionne.
  [ -f "\$DATA/mises_a_jour/historique_complet.json" ] \\
    || cp "\$SHARE/mises_a_jour/historique_complet.json" "\$DATA/mises_a_jour/" 2>/dev/null
  # Port fixe de préférence : le stockage du navigateur dépend de l'adresse.
  # SO_REUSEADDR comme HTTPServer : un port en TIME_WAIT après la fermeture
  # précédente reste le bon, sinon langue et collectes appliquées seraient perdues.
  for PORT in 8765 8766 8767 8768 8769; do
    python3 -B -c 'import socket,sys; s=socket.socket(); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1); s.bind(("127.0.0.1", int(sys.argv[1])))' "\$PORT" 2>/dev/null || continue
    python3 -B "\$SHARE/outils/actualiser_cours.py" --serve --port "\$PORT" --output "\$DATA/mises_a_jour" >"\$DATA/serveur.log" 2>&1 &
    SERVER_PID=\$!
    i=0
    while [ \$i -lt 50 ] && kill -0 "\$SERVER_PID" 2>/dev/null; do
      if python3 -B -c 'import socket,sys; socket.create_connection(("127.0.0.1", int(sys.argv[1])), .2).close()' "\$PORT" 2>/dev/null; then
        OBSERVATOIRE_PORT="\$PORT"; export OBSERVATOIRE_PORT; break
      fi
      sleep 0.1; i=\$((i+1))
    done
    [ -n "\${OBSERVATOIRE_PORT:-}" ] && break
    kill "\$SERVER_PID" 2>/dev/null; SERVER_PID=""
  done
fi
# --no-sandbox : le bac à sable Chromium exige un binaire setuid root, ce qu'une
# AppImage portable par utilisateur ne peut pas fournir (pratique NW.js/Electron).
"\$HERE/usr/bin/$APPNAME" --no-sandbox --class=$APPNAME "\$@"
EOF
chmod +x "$APPDIR/AppRun"

cat > "$APPDIR/${LOWER}.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Observatoire
GenericName=Analyse des cours des matières premières
Comment=Or, argent, cuivre et pétrole : historiques, moyennes mobiles, RSI, MACD, volatilité
Exec=$APPNAME
Icon=$LOWER
Categories=Office;Finance;
Keywords=or;argent;cuivre;pétrole;Brent;cours;INSEE;RSI;MACD;gold;silver;copper;oil;
StartupNotify=true
# Doit égaler le --class= passé par AppRun, sinon la barre des tâches perd l'icône.
StartupWMClass=$APPNAME
Terminal=false
EOF

# ── 5. Empaquetage ───────────────────────────────────────────────────────────
say "AppImage"
SUFFIX=""; [ "$FLAVOR" = "normal" ] || SUFFIX="-$FLAVOR"
OUT="$DIST/${APPNAME}-v${PRODUCT_VERSION}${SUFFIX}-x86_64.AppImage"
rm -f "$OUT"
# --runtime-file passe par un chemin RELATIF : appimagetool rejette un chemin non
# ASCII dans cette option (« Invalid byte sequence »), et celui du dépôt contient « ’ ».
( cd "$(dirname "$AIRUNTIME")" && ARCH=x86_64 "$AITOOL" --appimage-extract-and-run --no-appstream \
    --runtime-file "./$(basename "$AIRUNTIME")" "$APPDIR" "$OUT" ) >"$WORK/appimagetool.log" 2>&1 \
  || { tail -20 "$WORK/appimagetool.log"; die "appimagetool a échoué (journal : $WORK/appimagetool.log)"; }
chmod +x "$OUT"
rm -rf "$WORK"
say "FAIT — $(du -h "$OUT" | cut -f1)"
echo "  → $OUT"
if [ "$LIVRER" = "1" ]; then
  livrer_telechargements "$OUT" || die "livraison dans $DL en échec (l'AppImage est intacte dans $DIST)"
  echo "  LIVRÉ → $LIVRE"
  [ -z "$LIVRE_AVANT" ] || echo "  ancienne version gardée → $LIVRE_AVANT"
fi

# ── 6. Intégration au bureau (par utilisateur, sans root) ────────────────────
if [ "$DO_INSTALL" = "1" ]; then
  [ "$FLAVOR" = "normal" ] || die "--install n'installe que la saveur livrable (normal)."
  say "Ajout au menu (sans root)"
  mkdir -p "$BIN" "$APPS" "$ICONS"
  install -m 755 "$OUT" "$BIN/${APPNAME}.AppImage"
  install -m 644 "$ART/icon-256.png" "$ICONS/${LOWER}.png"
  # Même entrée que celle de l'image, mais Exec vise la COPIE installée.
  cat >"$APPS/${LOWER}.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Observatoire
GenericName=Analyse des cours des matières premières
Comment=Or, argent, cuivre et pétrole : historiques, moyennes mobiles, RSI, MACD, volatilité
Exec=$BIN/${APPNAME}.AppImage
Icon=$LOWER
Categories=Office;Finance;
Keywords=or;argent;cuivre;pétrole;Brent;cours;INSEE;RSI;MACD;gold;silver;copper;oil;
StartupNotify=true
StartupWMClass=$APPNAME
Terminal=false
EOF
  update-desktop-database "$APPS" >/dev/null 2>&1 || true
  gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" >/dev/null 2>&1 || true
  echo "  Installée : touche Super, puis « Observatoire »."
  echo "  Pour la retirer : $0 --uninstall"
fi
