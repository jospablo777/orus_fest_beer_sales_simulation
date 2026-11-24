"""Quarto pre-render step: copy figures, videos and docs into the site folder and write
the organizer pages.

Figures and videos come from output/figures and output/animations. The docs in docs/ are
copied to site/_generated/ with their cross-links rewritten to the site pages. The organizer
pages (Spanish and English) are written to site/_generated/ from site/_text.yaml and the
simulation outputs.
"""

import os
import re
import shutil
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent
ROOT = SITE.parent

PAGES = {"METHODS.md": "methods", "ASSUMPTIONS.md": "assumptions",
         "LITERATURE_REVIEW.md": "literature"}


def copy_dir(src: Path, dst: Path, pattern: str):
    dst.mkdir(parents=True, exist_ok=True)
    for f in src.glob(pattern):
        target = dst / f.name
        if not target.exists() or target.stat().st_mtime < f.stat().st_mtime:
            shutil.copy2(f, target)


def copy_docs():
    out = SITE / "_generated"
    out.mkdir(exist_ok=True)
    for name, page in PAGES.items():
        text = (ROOT / "docs" / name).read_text(encoding="utf-8")
        text = re.sub(r"^# .*\n+", "", text, count=1)          # the page title comes from the .qmd
        for other, other_page in PAGES.items():
            text = text.replace(f"]({other})", f"]({other_page}.qmd)")
        (out / f"{page}.md").write_text(text, encoding="utf-8")


def write_organizer_pages():
    """Needs output/runs, which is not committed. Without it the committed pages stay."""
    if not (ROOT / "output" / "runs" / "scenario_metrics.csv").exists():
        return
    sys.path.insert(0, str(SITE))
    import _organizer
    for lang in ("es", "en"):
        (SITE / "_generated" / f"organizer_{lang}.md").write_text(
            _organizer.render(lang, "summary"), encoding="utf-8")
        (SITE / "_generated" / f"evidence_{lang}.md").write_text(
            _organizer.render(lang, "evidence"), encoding="utf-8")


def write_build_line():
    """site/_variables.yml with the short commit and the build date, shown in the footer.
    The publishing workflow sets GITHUB_SHA; locally the checked-out commit is used."""
    import datetime
    import subprocess
    sha = os.environ.get("GITHUB_SHA", "")[:7]
    if not sha:
        try:
            sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                                 capture_output=True, text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            sha = "local"
    day = datetime.date.today().isoformat()
    (SITE / "_variables.yml").write_text(f'build: "{sha} · {day}"\n', encoding="utf-8")


def main():
    # Quarto runs this step on every render; steps whose inputs are missing are skipped.
    if (ROOT / "output" / "figures").exists():
        copy_dir(ROOT / "output" / "figures", SITE / "assets" / "figures", "*.png")
    if (ROOT / "output" / "animations").exists():
        for pattern in ("*.mp4", "*.jpg"):
            copy_dir(ROOT / "output" / "animations", SITE / "assets" / "video", pattern)
    copy_docs()
    write_organizer_pages()
    write_build_line()
    if os.environ.get("QUARTO_PROJECT_RENDER_ALL"):
        print("assets and docs synced to", SITE)


if __name__ == "__main__":
    main()
