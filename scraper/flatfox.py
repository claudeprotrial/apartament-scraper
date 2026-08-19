"""Adaptor pentru flatfox.ch — portal imobiliar elvetian cu API public JSON.

De ce flatfox: homegate.ch, immoscout24.ch, immowelt.de si immobilienscout24.de
sunt in spatele protectiei anti-bot (DataDome / Akamai) si returneaza 403.
willhaben.at interzice explicit scraping-ul in robots.txt.
flatfox.ch expune /api/v1/public-listing/ fara autentificare si acopera toata
Elvetia, inclusiv cantonul Berna, cu texte germane complete.

API-ul ignora parametrii de filtrare, deci descarcam tot indexul o data
(~35.000 anunturi, cache local) si filtram/clasificam local.
"""

import gzip
import json
import os
import time
import urllib.error
import urllib.request

BASE = "https://flatfox.ch"
API = BASE + "/api/v1/public-listing/"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
PAGE_SIZE = 100  # maximul acceptat de API


def _request(url, timeout=45, binary=False, tries=4, pause=0.3, accept=None, with_url=False):
    """GET cu retry si backoff. Returneaza bytes sau dict JSON.

    `Accept-Language: de-CH` este esential — fara el API-ul genereaza
    titlurile (`short_title`, `pitch_title`, ...) in engleza.
    """
    headers = {
        "User-Agent": UA,
        "Accept-Encoding": "gzip",
        "Accept": accept or ("*/*" if binary else "application/json"),
        "Accept-Language": "de-CH,de;q=0.9",
    }
    last = None
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read()
                if resp.headers.get("Content-Encoding") == "gzip":
                    raw = gzip.decompress(raw)
                time.sleep(pause)  # politete fata de server
                out = raw if binary else json.loads(raw.decode("utf-8"))
                return (out, resp.url) if with_url else out
        except (urllib.error.URLError, urllib.error.HTTPError, OSError, ValueError) as exc:
            last = exc
            if attempt < tries - 1:
                time.sleep(2 * (attempt + 1))
    raise RuntimeError("cerere esuata dupa %d incercari: %s (%s)" % (tries, url, last))


def harvest_index(cache_path, refresh=False, progress=None):
    """Descarca (sau citeste din cache) intregul index de anunturi."""
    if os.path.exists(cache_path) and not refresh:
        with open(cache_path, encoding="utf-8") as fh:
            return json.load(fh)

    listings = []
    offset = 0
    total = None
    while True:
        url = "%s?limit=%d&offset=%d&ordering=pk&expand=images" % (API, PAGE_SIZE, offset)
        data = _request(url)
        if total is None:
            total = data.get("count", 0)
            if progress:
                progress("index flatfox: %d anunturi de parcurs" % total)
        results = data.get("results") or []
        if not results:
            break
        listings.extend(results)
        offset += PAGE_SIZE
        if progress and offset % 2000 == 0:
            progress("  descarcat %d / %d" % (len(listings), total))
        if offset > total + PAGE_SIZE:
            break

    os.makedirs(os.path.dirname(cache_path) or ".", exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as fh:
        json.dump(listings, fh, ensure_ascii=False)
    return listings


def listing_url(listing):
    """URL public al anuntului.

    Folosim `short_url` (/<pk>/), care redirecteaza spre varianta germana
    canonica. Campul `url` vine cu prefix /en/, iar simpla inlocuire cu /de/
    da 404 — segmentul german difera dupa tipul obiectului (wohnung, gewerbe...).
    """
    return BASE + (listing.get("short_url") or listing.get("url") or "")


def image_urls(listing, max_images=12):
    """URL-urile imaginilor la rezolutie maxima, in ordinea din anunt."""
    imgs = listing.get("images") or []
    if imgs and not isinstance(imgs[0], dict):
        return []  # doar ID-uri, fara expand=images
    ordered = sorted(imgs, key=lambda i: i.get("ordering") or 0)
    out = []
    for img in ordered[:max_images]:
        path = img.get("url")
        if not path:
            continue
        # Unele anunturi dau cale relativa (/media/...), altele URL absolut
        # spre CDN (https://cdn.flatfox.ch/...).
        url = path if path.startswith("http") else BASE + path
        out.append((url, img.get("caption") or "", img.get("width"), img.get("height")))
    return out


def fetch_image(url):
    return _request(url, timeout=60, binary=True, tries=3, pause=0.1)


def fetch_page_html(listing):
    """Pagina HTML publica a anuntului — pentru forma de prezentare vizuala.

    Returneaza (html_bytes, url_final_dupa_redirect) sau (None, url).
    """
    url = listing_url(listing)
    try:
        html, final = _request(
            url, timeout=40, binary=True, tries=2,
            accept="text/html,application/xhtml+xml", with_url=True,
        )
        return html, final
    except RuntimeError:
        return None, url
