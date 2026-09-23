#!/usr/bin/env bash
# Install webapp-maker: binary -> ~/.local/bin, plus an app-menu entry + icon.
# Usage: ./install.sh [--uninstall]
# Uses ./webapp-maker if present, else ./dist/webapp-maker (repo checkout).
set -euo pipefail

SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_SRC="$SRC_DIR/webapp-maker"
[ -f "$BIN_SRC" ] || BIN_SRC="$SRC_DIR/dist/webapp-maker"
ICON_SRC="$SRC_DIR/icon.svg"

BINDIR="$HOME/.local/bin"
APPSDIR="$HOME/.local/share/applications"
ICONSDIR="$HOME/.local/share/icons"

refresh_db() {
    update-desktop-database "$APPSDIR" 2>/dev/null || true
}

if [ "${1:-}" = "--uninstall" ] || [ "${1:-}" = "uninstall" ]; then
    rm -f "$BINDIR/webapp-maker" "$APPSDIR/webapp-maker.desktop" "$ICONSDIR/webapp-maker.svg"
    refresh_db
    echo "Uninstalled."
    exit 0
fi

[ -f "$BIN_SRC" ] || { echo "error: webapp-maker binary not found next to install.sh" >&2; exit 1; }

mkdir -p "$BINDIR" "$APPSDIR" "$ICONSDIR"
install -m755 "$BIN_SRC" "$BINDIR/webapp-maker"

ICON_REF="web-browser"
if [ -f "$ICON_SRC" ]; then
    install -m644 "$ICON_SRC" "$ICONSDIR/webapp-maker.svg"
    ICON_REF="webapp-maker"
fi

cat > "$APPSDIR/webapp-maker.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=WebApp Maker
Comment=Turn any URL into a desktop web app
Exec=$BINDIR/webapp-maker
Icon=$ICON_REF
Terminal=false
Categories=Network;WebBrowser;
EOF
chmod 755 "$APPSDIR/webapp-maker.desktop"
refresh_db
echo "Installed. Find 'WebApp Maker' in your app menu."
