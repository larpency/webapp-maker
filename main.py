"""WebApp Maker - insanely simple URL -> web app installer (Python + Qt6).

UI: [ url field ] [ Install ] [ Delete ]

Install creates ~/.local/share/applications/webapp-<slug>.desktop that
opens the URL in a separate Chromium app window:
    chromium --app="<url>" --user-data-dir="~/.local/share/webapps/<slug>"

Delete removes that .desktop file (+ icon + isolated profile).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

# --- Qt imports (PySide6 preferred, PyQt6 fallback; both are Qt6) ---
try:  # PySide6 first
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QApplication,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )
except ImportError:  # fallback to PyQt6
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import (
        QApplication,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMessageBox,
        QPushButton,
        QVBoxLayout,
        QWidget,
    )


# ---------------------------------------------------------------- core logic

APPS_DIR = Path.home() / ".local" / "share" / "applications"
ICONS_DIR = Path.home() / ".local" / "share" / "icons"
PROFILES_DIR = Path.home() / ".local" / "share" / "webapps"

# Chromium-family browsers that support `--app=` SSB windows, in order.
APP_MODE_BROWSERS = [
    "chromium",
    "chromium-browser",
    "google-chrome",
    "google-chrome-stable",
    "brave-browser",
    "brave",
    "microsoft-edge",
    "microsoft-edge-stable",
    "opera",
    "vivaldi",
    "vivaldi-stable",
]


def normalize_url(raw: str) -> str:
    """'youtube.com' -> 'https://youtube.com'. Raises ValueError if empty."""
    raw = raw.strip()
    if not raw:
        raise ValueError("Paste a URL first.")
    if "://" not in raw:
        raw = "https://" + raw
    parsed = urllib.parse.urlparse(raw)
    if not parsed.netloc:
        raise ValueError(f"Not a valid URL: {raw!r}")
    return raw


def _parse_netloc(url: str) -> str:
    """Extract netloc, tolerating bare domains like 'youtube.com'."""
    u = url.strip()
    if "://" not in u:
        u = "https://" + u
    return urllib.parse.urlparse(u).netloc.lower()


def slug_from_url(url: str) -> str:
    """'https://www.youtube.com/watch?v=x' -> 'youtube-com' (filename-safe)."""
    netloc = _parse_netloc(url)
    netloc = netloc.split("@")[-1]  # strip userinfo
    netloc = netloc.split(":")[0]  # strip port
    if netloc.startswith("www."):
        netloc = netloc[4:]
    slug = netloc.replace(".", "-").replace("_", "-")
    slug = "".join(c if c.isalnum() or c == "-" else "-" for c in slug)
    slug = "-".join(filter(None, slug.split("-")))
    return slug or "webapp"


# Brand-cased names keyed by base domain label (lowercase, no TLD).
KNOWN_BRANDS = {
    "github": "GitHub",
    "gitlab": "GitLab",
    "bitbucket": "Bitbucket",
    "stackoverflow": "Stack Overflow",
    "stackexchange": "Stack Exchange",
    "youtube": "YouTube",
    "youtu": "YouTube",
    "linkedin": "LinkedIn",
    "facebook": "Facebook",
    "instagram": "Instagram",
    "tiktok": "TikTok",
    "twitter": "X",
    "x": "X",
    "reddit": "Reddit",
    "twitch": "Twitch",
    "vimeo": "Vimeo",
    "netflix": "Netflix",
    "spotify": "Spotify",
    "soundcloud": "SoundCloud",
    "discord": "Discord",
    "slack": "Slack",
    "telegram": "Telegram",
    "whatsapp": "WhatsApp",
    "messenger": "Messenger",
    "signal": "Signal",
    "google": "Google",
    "gmail": "Gmail",
    "microsoft": "Microsoft",
    "outlook": "Outlook",
    "office": "Microsoft 365",
    "onedrive": "OneDrive",
    "icloud": "iCloud",
    "apple": "Apple",
    "amazon": "Amazon",
    "aws": "AWS",
    "ebay": "eBay",
    "aliexpress": "AliExpress",
    "etsy": "Etsy",
    "notion": "Notion",
    "figma": "Figma",
    "canva": "Canva",
    "dropbox": "Dropbox",
    "trello": "Trello",
    "asana": "Asana",
    "jira": "Jira",
    "confluence": "Confluence",
    "wordpress": "WordPress",
    "medium": "Medium",
    "substack": "Substack",
    "hackernews": "Hacker News",
    "ycombinator": "Y Combinator",
    "openai": "OpenAI",
    "chatgpt": "ChatGPT",
    "claude": "Claude",
    "anthropic": "Anthropic",
    "gemini": "Gemini",
    "copilot": "Copilot",
    "deepseek": "DeepSeek",
    "mistral": "Mistral",
    "perplexity": "Perplexity",
    "duckduckgo": "DuckDuckGo",
    "brave": "Brave",
    "firefox": "Firefox",
    "mozilla": "Mozilla",
    "chromium": "Chromium",
    "pinterest": "Pinterest",
    "tumblr": "Tumblr",
    "quora": "Quora",
    "wikipedia": "Wikipedia",
    "archive": "Internet Archive",
    "cloudflare": "Cloudflare",
    "vercel": "Vercel",
    "netlify": "Netlify",
    "heroku": "Heroku",
    "digitalocean": "DigitalOcean",
    "linode": "Linode",
    "hetzner": "Hetzner",
    "ovh": "OVH",
    "proton": "Proton",
    "protonmail": "Proton Mail",
    "tutanota": "Tuta",
    "fastmail": "Fastmail",
    "zoom": "Zoom",
    "teams": "Teams",
    "meet": "Google Meet",
    "webex": "Webex",
    "skype": "Skype",
    "drive": "Google Drive",
    "docs": "Google Docs",
    "sheets": "Google Sheets",
    "slides": "Google Slides",
    "calendar": "Google Calendar",
    "photos": "Google Photos",
    "maps": "Google Maps",
    "translate": "Google Translate",
    "news": "Google News",
    "play": "Google Play",
    "classroom": "Google Classroom",
    "mail": "Gmail",
    "mdn": "MDN",
    "dev": "Dev",
    "devto": "DEV",
    "codepen": "CodePen",
    "codesandbox": "CodeSandbox",
    "replit": "Replit",
    "huggingface": "Hugging Face",
    "kaggle": "Kaggle",
    "colab": "Colab",
    "overleaf": "Overleaf",
    "zotero": "Zotero",
    "coursera": "Coursera",
    "udemy": "Udemy",
    "edx": "edX",
    "khanacademy": "Khan Academy",
    "duolingo": "Duolingo",
    "booking": "Booking",
    "airbnb": "Airbnb",
    "uber": "Uber",
    "lyft": "Lyft",
    "doordash": "DoorDash",
    "steam": "Steam",
    "epicgames": "Epic Games",
    "gog": "GOG",
    "itch": "itch.io",
    "nexusmods": "Nexus Mods",
    "bandcamp": "Bandcamp",
    "deezer": "Deezer",
    "tidal": "Tidal",
    "lastfm": "Last.fm",
    "imdb": "IMDb",
    "rottentomatoes": "Rotten Tomatoes",
    "letterboxd": "Letterboxd",
    "goodreads": "Goodreads",
    "nytimes": "NYTimes",
    "bbc": "BBC",
    "theguardian": "The Guardian",
    "verge": "The Verge",
    "arstechnica": "Ars Technica",
    "techcrunch": "TechCrunch",
    "wired": "Wired",
    "codeberg": "Codeberg",
    "sourcehut": "SourceHut",
    "docker": "Docker Hub",
    "npmjs": "npm",
    "pypi": "PyPI",
    "crates": "crates.io",
    "packagist": "Packagist",
    "rubygems": "RubyGems",
    "archlinux": "Arch Linux",
    "debian": "Debian",
    "ubuntu": "Ubuntu",
    "fedora": "Fedora",
    "nixos": "NixOS",
    "kernel": "Kernel",
    "python": "Python",
    "rust": "Rust",
    "golang": "Go",
    "nodejs": "Node.js",
    "typescript": "TypeScript",
    "react": "React",
    "vue": "Vue",
    "angular": "Angular",
    "svelte": "Svelte",
    "tailwindcss": "Tailwind CSS",
    "nextjs": "Next.js",
    "vk": "VK",
    "yandex": "Yandex",
    "dzen": "Dzen",
    "ok": "OK",
}

# Full hostnames with dedicated names (checked before base-label lookup).
FULL_DOMAIN_NAMES = {
    "mail.google.com": "Gmail",
    "drive.google.com": "Google Drive",
    "docs.google.com": "Google Docs",
    "sheets.google.com": "Google Sheets",
    "slides.google.com": "Google Slides",
    "calendar.google.com": "Google Calendar",
    "meet.google.com": "Google Meet",
    "chat.google.com": "Google Chat",
    "classroom.google.com": "Google Classroom",
    "photos.google.com": "Google Photos",
    "maps.google.com": "Google Maps",
    "translate.google.com": "Google Translate",
    "news.google.com": "Google News",
    "play.google.com": "Google Play",
    "music.youtube.com": "YouTube Music",
    "studio.youtube.com": "YouTube Studio",
    "chat.openai.com": "ChatGPT",
    "chatgpt.com": "ChatGPT",
    "claude.ai": "Claude",
    "gemini.google.com": "Gemini",
    "copilot.microsoft.com": "Copilot",
    "teams.microsoft.com": "Teams",
    "outlook.live.com": "Outlook",
    "outlook.office.com": "Outlook",
    "news.ycombinator.com": "Hacker News",
}

# Second parts of two-level public suffixes (co.uk, com.au, ...).
_TWO_LEVEL_SUFFIXES = frozenset(
    {"co", "com", "net", "org", "gov", "edu", "ac", "ne", "or", "go", "mil"}
)


def display_name_from_url(url: str) -> str:
    """'github.com' -> 'GitHub', 'https://www.youtube.com/...' -> 'YouTube'.

    Uses the registrable domain's base label (no TLD, no www) plus a
    brand-casing table. Unknown sites fall back to Title Case.
    """
    netloc = _parse_netloc(url)
    netloc = netloc.split("@")[-1].split(":")[0]
    if netloc.startswith("www."):
        netloc = netloc[4:]
    if not netloc:
        return url.strip() or "WebApp"

    # Full-domain specials first (Google subsites, AI chats, ...).
    full = netloc
    if full in FULL_DOMAIN_NAMES:
        return FULL_DOMAIN_NAMES[full]

    base = _base_label(netloc)
    if base in KNOWN_BRANDS:
        return KNOWN_BRANDS[base]
    return _fallback_title(base)


def _base_label(netloc: str) -> str:
    """'mail.google.com' -> 'google', 'sub.example.co.uk' -> 'example'."""
    parts = [p for p in netloc.split(".") if p]
    if not parts:
        return netloc
    if len(parts) == 1:
        return parts[0]
    # Two-level public suffixes like co.uk / com.au: base is 3rd from end.
    if (
        len(parts) >= 3
        and len(parts[-1]) == 2
        and parts[-2] in _TWO_LEVEL_SUFFIXES
    ):
        return parts[-3]
    return parts[-2]


def _fallback_title(base: str) -> str:
    words = base.replace("_", " ").replace("-", " ").split()
    if not words:
        return "WebApp"
    return " ".join(w[:1].upper() + w[1:] for w in words)


def desktop_path_for_url(url: str) -> Path:
    return APPS_DIR / f"webapp-{slug_from_url(url)}.desktop"


def find_browser() -> str | None:
    """Return first available Chromium-family browser binary, else None."""
    for name in APP_MODE_BROWSERS:
        if shutil.which(name):
            return name
    return None


def fetch_icon(url: str, slug: str) -> str:
    """Try to download a favicon, return Icon= value for .desktop. Fallback: 'web-browser'."""
    netloc = urllib.parse.urlparse(url).netloc
    candidates = [
        f"https://www.google.com/s2/favicons?domain={netloc}&sz=128",
        f"https://{netloc}/favicon.ico",
    ]
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    for src in candidates:
        try:
            dest = ICONS_DIR / f"webapp-{slug}.png"
            req = urllib.request.Request(src, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=10) as r, open(dest, "wb") as f:
                shutil.copyfileobj(r, f)
            if dest.stat().st_size > 0:
                return str(dest)
            dest.unlink(missing_ok=True)
        except Exception:
            continue
    return "web-browser"


def build_desktop_content(url: str, name: str, slug: str, icon: str) -> str:
    browser = find_browser()
    if browser:
        profile = PROFILES_DIR / slug
        # .desktop Exec does NOT do shell expansion, so use absolute paths.
        exe = shutil.which(browser) or browser
        exec_line = f'{exe} --app="{url}" --user-data-dir="{profile}" --class="webapp-{slug}"'
    else:
        exec_line = f"xdg-open {url}"
    return (
        "[Desktop Entry]\n"
        "Version=1.0\n"
        "Type=Application\n"
        f"Name={name}\n"
        f"Comment={url}\n"
        f"Exec={exec_line}\n"
        f"Icon={icon}\n"
        "Terminal=false\n"
        "Categories=Network;WebBrowser;\n"
        f"StartupWMClass=webapp-{slug}\n"
    )


def install_webapp(raw_url: str) -> Path:
    """Create the .desktop launcher. Returns its path."""
    url = normalize_url(raw_url)
    slug = slug_from_url(url)
    name = display_name_from_url(url)
    APPS_DIR.mkdir(parents=True, exist_ok=True)
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    icon = fetch_icon(url, slug)
    desktop_file = APPS_DIR / f"webapp-{slug}.desktop"
    desktop_file.write_text(
        build_desktop_content(url, name, slug, icon), encoding="utf-8"
    )
    os.chmod(desktop_file, 0o755)
    # Refresh launcher DB if available; ignore failures.
    try:
        subprocess.run(
            ["update-desktop-database", str(APPS_DIR)],
            capture_output=True,
            timeout=10,
        )
    except Exception:
        pass
    return desktop_file


def delete_webapp(raw_url: str) -> bool:
    """Remove launcher (+ icon + isolated profile). Returns True if something was removed."""
    url = normalize_url(raw_url)
    slug = slug_from_url(url)
    removed = False
    desktop_file = APPS_DIR / f"webapp-{slug}.desktop"
    if desktop_file.exists():
        desktop_file.unlink()
        removed = True
    for icon in (ICONS_DIR / f"webapp-{slug}.png", ICONS_DIR / f"webapp-{slug}.svg"):
        if icon.exists():
            icon.unlink()
            removed = True
    profile = PROFILES_DIR / slug
    if profile.exists():
        shutil.rmtree(profile, ignore_errors=True)
        removed = True
    try:
        subprocess.run(
            ["update-desktop-database", str(APPS_DIR)],
            capture_output=True,
            timeout=10,
        )
    except Exception:
        pass
    return removed


# ---------------------------------------------------------------- Qt UI


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("WebApp Maker")
        self.setFixedSize(400, 150)

        layout = QVBoxLayout(self)

        self.url_field = QLineEdit(self)
        self.url_field.setPlaceholderText("paste url, e.g. youtube.com")
        self.url_field.setClearButtonEnabled(True)
        self.url_field.returnPressed.connect(self.on_install)
        layout.addWidget(self.url_field)

        row = QHBoxLayout()
        self.install_btn = QPushButton("Install", self)
        self.delete_btn = QPushButton("Delete", self)
        self.install_btn.clicked.connect(self.on_install)
        self.delete_btn.clicked.connect(self.on_delete)
        row.addWidget(self.install_btn)
        row.addWidget(self.delete_btn)
        layout.addLayout(row)

        self.status = QLabel("", self)
        self.status.setWordWrap(True)
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status)

    def on_install(self) -> None:
        raw = self.url_field.text()
        try:
            path = install_webapp(raw)
        except ValueError as e:
            self.status.setText(str(e))
            QMessageBox.warning(self, "WebApp Maker", str(e))
            return
        except Exception as e:  # noqa: BLE001
            self.status.setText(f"Install failed: {e}")
            QMessageBox.critical(self, "WebApp Maker", f"Install failed:\n{e}")
            return
        self.status.setText(f"Installed → {path.name}")
        QMessageBox.information(self, "WebApp Maker", f"Installed:\n{path}")

    def on_delete(self) -> None:
        raw = self.url_field.text()
        try:
            removed = delete_webapp(raw)
        except ValueError as e:
            self.status.setText(str(e))
            QMessageBox.warning(self, "WebApp Maker", str(e))
            return
        except Exception as e:  # noqa: BLE001
            self.status.setText(f"Delete failed: {e}")
            QMessageBox.critical(self, "WebApp Maker", f"Delete failed:\n{e}")
            return
        if removed:
            self.status.setText("Deleted.")
            QMessageBox.information(self, "WebApp Maker", "Web app deleted.")
        else:
            self.status.setText("No web app found for that URL.")
            QMessageBox.information(
                self, "WebApp Maker", "No web app found for that URL."
            )


def _ensure_system_qt_plugins() -> None:
    """Let pip-bundled Qt find distro style/platformtheme plugins.

    PySide6 wheels ship their own Qt which only knows Windows/Fusion,
    so QT_STYLE_OVERRIDE=Darkly (or Breeze/kvantum) is ignored with:
        "invalid style override ... Available styles: Windows, Fusion"
    If the distro ships matching Qt6 plugins (e.g. /usr/lib/qt6/plugins
    with darkly6.so, breeze6.so), expose them via QT_PLUGIN_PATH before
    QApplication is constructed so the app uses real system Qt colors.
    No-op when those dirs don't exist. We never force a style ourselves.
    """
    candidates = (
        "/usr/lib/qt6/plugins",
        "/usr/lib64/qt6/plugins",
        "/usr/lib/x86_64-linux-gnu/qt6/plugins",
    )
    existing = os.environ.get("QT_PLUGIN_PATH", "")
    paths = [p for p in existing.split(os.pathsep) if p]
    for cand in candidates:
        if os.path.isdir(cand) and cand not in paths:
            paths.insert(0, cand)
    if paths != ([p for p in existing.split(os.pathsep) if p] if existing else []):
        os.environ["QT_PLUGIN_PATH"] = os.pathsep.join(paths)


def _run_cli(argv: list[str]) -> int | None:
    """Handle --install/--delete/--name. Returns an exit code, or None to start the GUI."""
    import argparse

    parser = argparse.ArgumentParser(
        prog="webapp-maker",
        description="Turn a URL into a desktop web app (no args opens the Qt GUI).",
    )
    parser.add_argument("--install", metavar="URL", help="install a web app for URL and exit")
    parser.add_argument("--delete", metavar="URL", help="delete the web app for URL and exit")
    parser.add_argument("--name", metavar="URL", help="print the app name for URL and exit")
    args = parser.parse_args(argv)
    if args.name is not None:
        try:
            print(display_name_from_url(normalize_url(args.name)))
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        return 0
    if args.install is not None:
        try:
            print(install_webapp(args.install))
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        return 0
    if args.delete is not None:
        try:
            removed = delete_webapp(args.delete)
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        print("Deleted." if removed else "No web app found for that URL.")
        return 0 if removed else 1
    return None


def main() -> None:
    code = _run_cli(sys.argv[1:])
    if code is not None:
        sys.exit(code)
    _ensure_system_qt_plugins()
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
