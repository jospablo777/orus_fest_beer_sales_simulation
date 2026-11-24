"""Checks the length of the Spanish summary page.

Words: running text of site/index.qmd as counted by site/_organizer.py (running_words), at
most MAX_WORDS. Height: the rendered page in site/_site at 390 px wide, at most MAX_HEIGHT
pixels, measured with headless Chrome (path in the CHROME variable or the macOS default).
Usage: uv run python scripts/check_summary.py   (after ./scripts/render_site.sh)
"""

import http.server
import os
import re
import subprocess
import sys
import tempfile
import threading
from functools import partial
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "site"))

import _organizer  # noqa: E402

MAX_WORDS = 300
MAX_HEIGHT = 7000
WIDTH = 390
CHROME = os.environ.get("CHROME",
                        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
WRAPPER = """<html><body style="margin:0"><iframe id="f" src="/{page}" width="{w}"
height="800" style="border:0"></iframe><script>
document.getElementById("f").addEventListener("load", function () {{
  var d = this.contentDocument;
  setTimeout(function () {{
    document.title = "H=" + d.documentElement.scrollHeight;
  }}, 1500);
}});
</script></body></html>"""


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def page_height(page: str = "index.html") -> int:
    site = ROOT / "site" / "_site"
    with tempfile.TemporaryDirectory() as tmp:
        wrap = Path(tmp) / "wrap.html"
        wrap.write_text(WRAPPER.format(page=page, w=WIDTH), encoding="utf-8")
        handler = partial(QuietHandler, directory=str(site))
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        port = server.server_address[1]
        (site / "_check_wrap.html").write_text(wrap.read_text(encoding="utf-8"),
                                               encoding="utf-8")
        try:
            out = subprocess.run([CHROME, "--headless=new", "--disable-gpu",
                                  "--virtual-time-budget=15000", "--window-size=600,1000",
                                  "--dump-dom", f"http://127.0.0.1:{port}/_check_wrap.html"],
                                 capture_output=True, text=True, timeout=120).stdout
        finally:
            (site / "_check_wrap.html").unlink(missing_ok=True)
            server.shutdown()
    m = re.search(r"<title>H=(\d+)</title>", out)
    if not m:
        raise RuntimeError("could not measure the page height")
    return int(m.group(1))


def main():
    words = _organizer.running_words("es")
    height = page_height()
    print(f"Spanish summary: {words} words of running text (limit {MAX_WORDS}); "
          f"{height} px tall at {WIDTH} px wide (limit {MAX_HEIGHT})")
    if words > MAX_WORDS or height > MAX_HEIGHT:
        sys.exit(1)


if __name__ == "__main__":
    main()
