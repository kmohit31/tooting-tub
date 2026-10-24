#!/usr/bin/env python3
"""Build the CrazyGames upload: dist/crazygames/ and dist/tooting-tub-crazygames.zip.

Takes index.html, adds the CrazyGames SDK, and bundles the fonts and PeerJS next to it
so the game loads from relative paths only. Run from the repo root: python3 build-crazygames.py
"""
import re
import shutil
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "dist" / "crazygames"
ZIP = ROOT / "dist" / "tooting-tub-crazygames.zip"
SDK_TAG = '<script src="https://sdk.crazygames.com/crazygames-sdk-v3.js"></script>'
PEERJS_URL = "https://cdnjs.cloudflare.com/ajax/libs/peerjs/1.5.4/peerjs.min.js"
# A modern browser user agent makes Google Fonts answer with woff2 files.
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read()


def bundle_fonts(html):
    m = re.search(r'<link rel="stylesheet" href="(https://fonts\.googleapis\.com/[^"]+)">', html)
    if not m:
        return html
    css = fetch(m.group(1).replace("&amp;", "&")).decode()
    # keep only the latin subset; the game has no other scripts
    blocks = re.findall(r"/\* latin \*/\s*(@font-face\s*{[^}]+})", css)
    (OUT / "fonts").mkdir(parents=True, exist_ok=True)
    local = []
    for n, block in enumerate(blocks):
        url = re.search(r"url\((https://[^)]+\.woff2)\)", block).group(1)
        name = f"font-{n}.woff2"
        (OUT / "fonts" / name).write_bytes(fetch(url))
        local.append(block.replace(url, f"fonts/{name}"))
    (OUT / "fonts.css").write_text("\n".join(local) + "\n")
    html = html.replace(m.group(0), '<link rel="stylesheet" href="fonts.css">')
    return re.sub(r'<link rel="preconnect"[^>]*>\n', "", html)


def main():
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir(parents=True)
    html = (ROOT / "index.html").read_text()
    html = bundle_fonts(html)
    (OUT / "peerjs.min.js").write_bytes(fetch(PEERJS_URL))
    html = html.replace(f'<script src="{PEERJS_URL}"></script>', f'{SDK_TAG}\n<script src="peerjs.min.js"></script>')
    assert SDK_TAG in html, "PeerJS script tag not found; SDK was not added"
    (OUT / "index.html").write_text(html)

    ZIP.unlink(missing_ok=True)
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(OUT.rglob("*")):
            if f.is_file():
                z.write(f, f.relative_to(OUT))
    files = [f for f in OUT.rglob("*") if f.is_file()]
    print(f"{len(files)} files, {sum(f.stat().st_size for f in files) / 1024:.0f} KB -> {ZIP.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
