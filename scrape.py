#!/usr/bin/env python3
"""Scraper de anunturi imobiliare (CH) pentru construirea unei baze de date
de prezentari — limbaj, formulari, imagini si forme de prezentare.

Prioritate: spatii de INCHIRIAT pentru praxis / birou / gewerbe, cu accent pe
regiunea Berna. Locuintele sunt colectate doar secundar.

Utilizare:
    python3 scrape.py                      # 100 anunturi, implicit
    python3 scrape.py --limit 200          # mai multe anunturi
    python3 scrape.py --refresh            # reia indexul de la server
    python3 scrape.py --max-images 20      # mai multe poze per anunt
    python3 scrape.py --wohnen 5           # cate locuinte sa includa
    python3 scrape.py --no-html            # fara snapshot HTML al paginii
"""

import argparse
import csv
import datetime as dt
import json
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from scraper import classify as C
from scraper import flatfox, render

CACHE = os.path.join(HERE, ".cache", "flatfox_raw.json")
OUTDIR = os.path.join(HERE, "anunturi")


def log(msg):
    print(msg, flush=True)


def select(listings, limit, max_wohnen, max_altele=0):
    """Alege cele mai bune `limit` anunturi, dupa prioritatea ceruta."""
    scored = []
    for L in listings:
        if L.get("offer_type") != "RENT":
            continue  # utilizatorul vrea sa inchirieze
        if L.get("status") != "act":
            continue
        if not C.is_rich_enough(L):
            continue
        cat, kw = C.classify(L)
        scored.append((C.quality_score(L, cat, kw), cat, kw, L))

    scored.sort(key=lambda t: -t[0])

    chosen, n_wohnen, n_altele = [], 0, 0
    for score, cat, kw, L in scored:
        if len(chosen) >= limit:
            break
        if cat == C.CAT_WOHNEN:
            if n_wohnen >= max_wohnen:
                continue
            n_wohnen += 1
        if cat == C.CAT_ALTELE:
            if n_altele >= max_altele:
                continue
            n_altele += 1
        chosen.append((score, cat, kw, L))
    return chosen, scored


def save_listing(score, cat, kw, L, outdir, max_images, want_html):
    """Scrie un anunt pe disc: JSON brut, Markdown, imagini, snapshot HTML."""
    bern_city = C.is_bern_city(L)
    regiune = "Berna (oraș)" if bern_city else ("Cantonul Berna" if C.is_bern(L) else "Elveția — altă regiune")

    slug = render.slugify("%s-%s" % (L.get("city") or "", L.get("short_title") or L.get("object_type") or ""))
    folder = os.path.join(outdir, cat, "%06d-%s" % (L["pk"], slug))
    imgdir = os.path.join(folder, "images")
    os.makedirs(imgdir, exist_ok=True)

    # --- imagini ---
    saved_imgs = []
    for idx, (url, caption, w, h) in enumerate(flatfox.image_urls(L, max_images), start=1):
        ext = os.path.splitext(url.split("?")[0])[1] or ".jpg"
        fname = "%02d%s" % (idx, ext)
        try:
            blob = flatfox.fetch_image(url)
        except RuntimeError:
            continue
        with open(os.path.join(imgdir, fname), "wb") as fh:
            fh.write(blob)
        saved_imgs.append((fname, caption, w, h))

    # --- snapshot al paginii publice; redirectul ne da si URL-ul german canonic ---
    url = flatfox.listing_url(L)
    if want_html:
        html, url = flatfox.fetch_page_html(L)
        if html:
            with open(os.path.join(folder, "pagina.html"), "wb") as fh:
                fh.write(html)

    meta = {
        "categorie": cat,
        "categorie_label": C.CATEGORY_LABEL[cat],
        "scor": round(score, 1),
        "regiune": regiune,
        "in_bern": C.is_bern(L),
        "sursa": "flatfox.ch",
        "url": url,
        "descarcat": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "cuvinte_cheie": kw,
        "nr_imagini": len(saved_imgs),
    }

    with open(os.path.join(folder, "anunt.md"), "w", encoding="utf-8") as fh:
        fh.write(render.to_markdown(L, meta, saved_imgs))

    with open(os.path.join(folder, "anunt.json"), "w", encoding="utf-8") as fh:
        json.dump({"meta": meta, "raw": L}, fh, ensure_ascii=False, indent=2)

    return folder, meta, saved_imgs


def write_index(rows, outdir):
    path = os.path.join(outdir, "index.csv")
    cols = ["categorie", "categorie_label", "praxis_relevant", "scor", "regiune",
            "npa", "oras", "adresa", "titlu", "tip_obiect", "chirie_neta",
            "nebenkosten", "suprafata_utila", "nr_imagini", "lungime_descriere",
            "url", "folder"]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in cols})
    return path


def write_corpus(rows, outdir):
    """Un singur fisier cu toate textele germane — pentru studiul limbajului."""
    path = os.path.join(outdir, "CORPUS-TEXTE.md")
    by_cat = {}
    for r in rows:
        by_cat.setdefault(r["categorie"], []).append(r)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("# Corpus de texte — toate anunțurile într-un singur fișier\n\n")
        fh.write("Generat: %s\n\n" % dt.datetime.now().strftime("%Y-%m-%d %H:%M"))
        for cat in C.CATEGORY_ORDER:
            items = by_cat.get(cat)
            if not items:
                continue
            fh.write("\n---\n\n# %s — %s (%d anunțuri)\n\n" % (cat, C.CATEGORY_LABEL[cat], len(items)))
            for r in items:
                fh.write("## %s\n\n" % (r["titlu"] or "(fără titlu)"))
                fh.write("*%s · %s · %s*\n\n" % (r["adresa"] or "-", r["tip_obiect"] or "-", r["url"]))
                if r.get("pitch"):
                    fh.write("**Pitch:** %s\n\n" % r["pitch"])
                if r.get("descriere_titlu"):
                    fh.write("**%s**\n\n" % r["descriere_titlu"])
                fh.write((r.get("descriere") or "").strip() + "\n\n")
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=100, help="cate anunturi sa descarce (implicit 100)")
    ap.add_argument("--wohnen", type=int, default=12, help="cate locuinte (secundare) sa includa")
    ap.add_argument("--max-images", type=int, default=12, help="poze maxim per anunt")
    ap.add_argument("--refresh", action="store_true", help="reia indexul de la server, ignora cache")
    ap.add_argument("--no-html", action="store_true", help="nu salva snapshot HTML al paginii")
    ap.add_argument("--out", default=OUTDIR, help="folderul de iesire")
    args = ap.parse_args()

    log("1/4  Index flatfox.ch ...")
    listings = flatfox.harvest_index(CACHE, refresh=args.refresh, progress=log)
    log("     %d anunturi in index" % len(listings))

    log("2/4  Clasificare si selectie ...")
    chosen, scored = select(listings, args.limit, args.wohnen)
    dist = {}
    for _, cat, _, _ in scored:
        dist[cat] = dist.get(cat, 0) + 1
    log("     disponibile pe categorii: %s" % dist)
    log("     selectate: %d" % len(chosen))

    log("3/4  Descarcare anunturi + imagini ...")
    os.makedirs(args.out, exist_ok=True)
    rows = []
    for i, (score, cat, kw, L) in enumerate(chosen, start=1):
        try:
            folder, meta, imgs = save_listing(score, cat, kw, L, args.out, args.max_images, not args.no_html)
        except Exception:
            log("     [!] esuat pk=%s" % L.get("pk"))
            traceback.print_exc()
            continue
        rows.append({
            "categorie": cat,
            "categorie_label": C.CATEGORY_LABEL[cat],
            "praxis_relevant": "da" if kw.get("praxis_relevant") else "nu",
            "scor": meta["scor"],
            "regiune": meta["regiune"],
            "npa": L.get("zipcode") or "",
            "oras": L.get("city") or "",
            "adresa": render.address_line(L),
            "titlu": L.get("public_title") or L.get("short_title") or "",
            "tip_obiect": L.get("object_type") or "",
            "chirie_neta": L.get("rent_net") or "",
            "nebenkosten": L.get("rent_charges") or "",
            "suprafata_utila": L.get("surface_usable") or "",
            "nr_imagini": len(imgs),
            "lungime_descriere": len(L.get("description") or ""),
            "url": meta["url"],
            "folder": os.path.relpath(folder, args.out),
            "pitch": L.get("pitch_title") or "",
            "descriere_titlu": L.get("description_title") or "",
            "descriere": L.get("description") or "",
        })
        if i % 10 == 0 or i == len(chosen):
            log("     %d / %d" % (i, len(chosen)))

    log("4/4  Index si corpus ...")
    idx = write_index(rows, args.out)
    cor = write_corpus(rows, args.out)

    final = {}
    for r in rows:
        final[r["categorie"]] = final.get(r["categorie"], 0) + 1
    log("\nGata. %d anunturi in %s" % (len(rows), args.out))
    for cat in C.CATEGORY_ORDER:
        if final.get(cat):
            log("  %-20s %3d   %s" % (cat, final[cat], C.CATEGORY_LABEL[cat]))
    n_bern = sum(1 for r in rows if "Bern" in r["regiune"])
    log("  din care regiunea Berna: %d" % n_bern)
    log("  index:  %s" % idx)
    log("  corpus: %s" % cor)


if __name__ == "__main__":
    main()
