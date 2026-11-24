"""Single-page version of the organizer summary, in Spanish and English.

Writes output/preview/index.html with its styles inline and copies the figures and videos it
shows to output/preview/assets/. The folder opens from disk and can be hosted as it is. The
text, numbers and diagrams are the ones of the Quarto site (site/_organizer.py).

Usage: uv run python scripts/make_preview.py
"""

import re
import shutil
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
OUT = ROOT / "output" / "preview"
sys.path.insert(0, str(SITE))

import _organizer  # noqa: E402

PAGES = {"es": SITE / "index.qmd", "en": SITE / "en.qmd"}
FONTS = ("https://fonts.googleapis.com/css2?family=Orbitron:wght@600;800&family=Cinzel:wght@600"
         "&family=Source+Sans+3:ital,wght@0,400;0,600;0,700;1,400&display=swap")
SCRIPT = """
const sections = document.querySelectorAll("main");
const buttons = document.querySelectorAll(".lang button");
function show(lang) {
  sections.forEach((s) => { s.hidden = s.id !== lang; });
  buttons.forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.lang === lang)));
  document.querySelectorAll("video").forEach((v) => v.pause());
  document.documentElement.lang = lang;
}
function fromHash() { return location.hash === "#en" ? "en" : "es"; }
buttons.forEach((b) => b.addEventListener("click", () => {
  location.hash = b.dataset.lang;
  show(b.dataset.lang);
}));
window.addEventListener("hashchange", () => show(fromHash()));
show(fromHash());
"""


def front_matter(path: Path) -> dict:
    """Title and subtitle of a site page. A Quarto span such as [Orus Fest]{.red} becomes
    an HTML span."""
    meta = yaml.safe_load(path.read_text(encoding="utf-8").split("---")[1])
    return {k: re.sub(r"\[([^\]]+)\]\{\.(\w+)\}", r'<span class="\2">\1</span>', str(v))
            for k, v in meta.items()}


def plain(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html)


def copy_assets(body: str) -> None:
    for rel in sorted(set(re.findall(r'(?:src|poster)="(assets/[^"]+)"', body))):
        folder = "animations" if rel.startswith("assets/video/") else "figures"
        target = OUT / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "output" / folder / Path(rel).name, target)


def main():
    text = yaml.safe_load((SITE / "_text.yaml").read_text(encoding="utf-8"))
    sections = []
    for lang, page in PAGES.items():
        meta = front_matter(page)
        hidden = "" if lang == "es" else " hidden"
        sections.append(
            f'<main id="{lang}" lang="{lang}"{hidden}>\n<h1>{meta["title"]}</h1>\n'
            f'<p class="subtitle">{meta["subtitle"]}</p>\n{_organizer.render_html(lang)}'
            f'<p class="more">{text["preview_note"][lang]}</p>\n</main>')
    body = "\n".join(sections)
    site_cfg = yaml.safe_load((SITE / "_quarto.yml").read_text(encoding="utf-8"))["website"]
    title = site_cfg["title"]
    page = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<meta name="description" content="{plain(front_matter(PAGES["es"])["subtitle"])}">
<link rel="icon" type="image/svg+xml" href="favicon.svg">
<link rel="stylesheet" href="{FONTS}">
<style>
{(SITE / "_preview.css").read_text(encoding="utf-8")}</style>
</head>
<body>
<header class="top">
<span class="brand">{title}</span>
<nav class="lang" aria-label="Idioma / Language">
<button type="button" data-lang="es" aria-pressed="true">Español</button>
<button type="button" data-lang="en" aria-pressed="false">English</button>
</nav>
</header>
{body}
<footer>{site_cfg["page-footer"]["left"]}</footer>
<script>{SCRIPT}</script>
</body>
</html>
"""
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "index.html").write_text(page, encoding="utf-8")
    copy_assets(body)
    shutil.copy2(SITE / "favicon.svg", OUT / "favicon.svg")
    print("preview written to", OUT)


if __name__ == "__main__":
    main()
