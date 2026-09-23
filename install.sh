#!/usr/bin/env bash
# Install webapp-maker from source: copies the app to ~/.local/share/webapp-maker,
# installs its only dependency (PySide6/Qt6), and adds an app-menu entry + icon.
# Usage: ./install.sh [--uninstall]      (no sudo needed)
set -euo pipefail

SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_DIR="$HOME/.local/share/webapp-maker"
BINDIR="$HOME/.local/bin"
APPSDIR="$HOME/.local/share/applications"
ICONSDIR="$HOME/.local/share/icons"

refresh_db() {
    update-desktop-database "$APPSDIR" 2>/dev/null || true
}

if [ "${1:-}" = "--uninstall" ] || [ "${1:-}" = "uninstall" ]; then
    rm -rf "$APP_DIR" "$BINDIR/webapp-maker" \
        "$APPSDIR/webapp-maker.desktop" "$ICONSDIR/webapp-maker.svg"
    refresh_db
    echo "Uninstalled."
    exit 0
fi

echo "-> copying app to $APP_DIR"
mkdir -p "$APP_DIR"
cp "$SRC_DIR/main.py" "$SRC_DIR/pyproject.toml" "$APP_DIR/"
[ -f "$SRC_DIR/uv.lock" ] && cp "$SRC_DIR/uv.lock" "$APP_DIR/"

echo "-> installing dependency (PySide6)"
if command -v uv >/dev/null 2>&1; then
    (cd "$APP_DIR" && uv sync --quiet)
    PY="$APP_DIR/.venv/bin/python"
else
    command -v python3 >/dev/null 2>&1 || { echo "error: need python3 (or uv)" >&2; exit 1; }
    if [ ! -x "$APP_DIR/.venv/bin/python" ]; then
        python3 -m venv "$APP_DIR/.venv" || {
            echo "error: venv creation failed (Debian/Ubuntu: sudo apt install python3-venv)" >&2
            exit 1
        }
    fi
    "$APP_DIR/.venv/bin/pip" install --quiet PySide6
    PY="$APP_DIR/.venv/bin/python"
fi
"$PY" -c "import PySide6" || { echo "error: PySide6 install failed" >&2; exit 1; }

echo "-> installing launcher, menu entry, icon"
mkdir -p "$BINDIR" "$APPSDIR" "$ICONSDIR"
cat > "$BINDIR/webapp-maker" <<EOF
#!/usr/bin/env bash
exec "$APP_DIR/.venv/bin/python" "$APP_DIR/main.py" "\$@"
EOF
chmod 755 "$BINDIR/webapp-maker"

ICON_REF="web-browser"
if [ -f "$SRC_DIR/icon.svg" ]; then
    install -m644 "$SRC_DIR/icon.svg" "$ICONSDIR/webapp-maker.svg"
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
echo "Installed. Find 'WebApp Maker' in your app menu (or run: webapp-maker)."
