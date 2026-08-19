"""Transforma un anunt brut intr-un fisier Markdown lizibil (text german intact)."""

import json
import re

CHF = "CHF"


def _fmt_money(v):
    if v in (None, "", 0):
        return None
    try:
        return "%s %s" % (CHF, format(int(round(float(v))), ",d").replace(",", "'"))
    except (TypeError, ValueError):
        return str(v)


def _fmt_area(v):
    if v in (None, ""):
        return None
    try:
        return "%g m²" % float(v)
    except (TypeError, ValueError):
        return str(v)


def slugify(text, maxlen=60):
    text = (text or "").lower()
    repl = {"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss", "é": "e", "è": "e", "à": "a", "ç": "c"}
    for k, v in repl.items():
        text = text.replace(k, v)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text[:maxlen].strip("-") or "anunt"


def address_line(listing):
    parts = []
    if listing.get("street"):
        parts.append(listing["street"])
    loc = " ".join(str(x) for x in (listing.get("zipcode"), listing.get("city")) if x)
    if loc:
        parts.append(loc)
    return ", ".join(parts)


def to_markdown(listing, meta, image_files):
    """meta: dict cu categorie, scor, sursa, url etc."""
    L = listing
    out = []
    title = L.get("public_title") or L.get("short_title") or "Anunt"
    out.append("# %s\n" % title)

    # --- Bloc de metadate pentru baza de date ---
    out.append("> **Categorie:** `%s`  " % meta["categorie"])
    out.append("> **Regiune:** %s  " % meta["regiune"])
    out.append("> **Tip ofertă:** %s / %s  " % (L.get("offer_type") or "-", L.get("object_type") or "-"))
    kw = meta.get("cuvinte_cheie") or {}
    if kw.get("praxis_relevant"):
        termeni = ", ".join(kw.get("kw_praxis") or []) or "—"
        out.append("> **Relevant pentru praxis:** da (%s)  " % termeni)
    out.append("> **Sursă:** [%s](%s)  " % (meta["sursa"], meta["url"]))
    out.append("> **Descărcat:** %s\n" % meta["descarcat"])

    out.append("## Date obiect\n")
    rows = [
        ("Adresă", address_line(L)),
        ("Categorie obiect", L.get("object_category")),
        ("Tip obiect", L.get("object_type")),
        ("Chirie netă", _fmt_money(L.get("rent_net"))),
        ("Nebenkosten", _fmt_money(L.get("rent_charges"))),
        ("Chirie brută", _fmt_money(L.get("rent_gross"))),
        ("Preț afișat", _fmt_money(L.get("price_display"))),
        ("Suprafață utilă", _fmt_area(L.get("surface_usable"))),
        ("Suprafață locuibilă", _fmt_area(L.get("surface_living"))),
        ("Suprafață teren", _fmt_area(L.get("surface_property"))),
        ("Camere", L.get("number_of_rooms")),
        ("Etaj", L.get("floor")),
        ("An construcție", L.get("year_built")),
        ("An renovare", L.get("year_renovated")),
        ("Disponibil de la", L.get("moving_date") or L.get("moving_date_type")),
        ("Referință", L.get("reference")),
    ]
    out.append("| Câmp | Valoare |")
    out.append("|---|---|")
    for k, v in rows:
        if v not in (None, "", []):
            out.append("| %s | %s |" % (k, v))
    out.append("")

    # --- Textele germane: partea cea mai importanta pentru studiu ---
    out.append("## Texte originale (germană)\n")
    for label, key in (
        ("Titlu public", "public_title"),
        ("Titlu scurt", "short_title"),
        ("Pitch", "pitch_title"),
        ("Titlu descriere", "description_title"),
        ("Titlu chirie", "rent_title"),
        ("Spațiu afișat", "space_display"),
    ):
        val = L.get(key)
        if val:
            out.append("**%s:** %s\n" % (label, val))

    desc = L.get("description")
    if desc:
        out.append("### Descriere completă\n")
        out.append(desc.strip() + "\n")

    # --- Atribute / dotari ---
    attrs = L.get("attributes") or []
    if attrs:
        out.append("## Dotări (attributes)\n")
        for a in attrs:
            if isinstance(a, dict):
                out.append("- %s" % (a.get("name") or a.get("label") or json.dumps(a, ensure_ascii=False)))
            else:
                out.append("- %s" % a)
        out.append("")

    # --- Ofertant ---
    ag = L.get("agency") or {}
    if ag.get("name"):
        out.append("## Ofertant\n")
        for label, key in (("Nume", "name"), ("Nume 2", "name_2"), ("Stradă", "street"),
                           ("NPA", "zipcode"), ("Localitate", "city")):
            if ag.get(key):
                out.append("- **%s:** %s" % (label, ag[key]))
        out.append("")

    # --- Imagini ---
    if image_files:
        out.append("## Imagini (%d)\n" % len(image_files))
        for fname, caption, w, h in image_files:
            dim = " — %sx%s px" % (w, h) if w and h else ""
            cap = " — %s" % caption if caption else ""
            out.append("![%s](images/%s)" % (caption or fname, fname))
            out.append("*`%s`%s%s*\n" % (fname, dim, cap))

    extra = [(k, L.get(k)) for k in ("tour_url", "video_url", "website_url", "live_viewing_url") if L.get(k)]
    if extra:
        out.append("## Media suplimentară\n")
        for k, v in extra:
            out.append("- **%s:** %s" % (k, v))
        out.append("")

    return "\n".join(out)
