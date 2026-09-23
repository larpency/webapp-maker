# WebApp Maker

Insanely simple Python + Qt6 utility to turn any URL into a desktop web app.

UI: a URL field + `Install` + `Delete`.

- **Install** creates `~/.local/share/applications/webapp-<slug>.desktop`
  that opens the URL in its own Chromium app window:
  `chromium --app="<url>" --user-data-dir="~/.local/share/webapps/<slug>"`
- **Delete** removes that launcher (+ icon + isolated profile).

## Download (no install needed)

Grab `webapp-maker` from the [Releases](../../releases) page, then:

```bash
chmod +x webapp-maker
./webapp-maker
```

Linux only. Requires Chromium (or Chrome/Brave/Edge) for `--app` windows;
falls back to `xdg-open` otherwise.

## Run from source

```bash
uv sync        # creates .venv and installs PySide6 (Qt6)
uv run main.py
```

Requires Python 3.10+.

Headless / scriptable (no GUI):

```bash
uv run main.py --install github.com
uv run main.py --delete github.com
uv run main.py --name github.com   # -> GitHub
```

## Build the binary yourself

```bash
uv run --with pyinstaller pyinstaller --onefile --name webapp-maker main.py
./dist/webapp-maker --name github.com   # smoke test -> GitHub
```

One file, ~90 MB, no Python/pip needed to run it.
Pushing a `v*` tag builds it automatically via `.github/workflows/release.yml`
and attaches it to the GitHub Release.

## Upload to GitHub

```bash
git init
git add .
git commit -m "webapp maker"
gh repo create webapp-maker --public --source=. --push
git tag v0.1.0 && git push --tags   # triggers the binary build
```

## System Qt colors

The app sets no style/stylesheet of its own — it uses whatever Qt style
your system specifies (`QT_STYLE_OVERRIDE`, e.g. Darkly/Breeze/kvantum).
Since the PySide6 wheel bundles its own Qt (which alone only knows
Windows/Fusion), `main.py` prepends `/usr/lib/qt6/plugins` to
`QT_PLUGIN_PATH` when that dir exists, so the bundled Qt can load your
distro's system styles and platform themes. No config needed.
