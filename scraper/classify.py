"""Clasificarea si scorarea anunturilor.

Prioritatea ceruta: anunturile despre inchiriere de spatii pentru PRAXIS si
BUSINESS/BIROU sunt cele mai valoroase; locuintele sunt secundare.
"""

import re

# --- Categorii, in ordinea prioritatii -------------------------------------

CAT_PRAXIS = "A_praxis_medical"
CAT_BUSINESS = "B_buero_gewerbe"
CAT_RETAIL_GASTRO = "C_laden_gastro"
CAT_WOHNEN = "D_wohnen"
CAT_ALTELE = "E_altele"

CATEGORY_ORDER = [CAT_PRAXIS, CAT_BUSINESS, CAT_RETAIL_GASTRO, CAT_WOHNEN, CAT_ALTELE]

CATEGORY_LABEL = {
    CAT_PRAXIS: "Praxis / cabinet medical / terapie",
    CAT_BUSINESS: "Birou / gewerbe / atelier / coworking",
    CAT_RETAIL_GASTRO: "Ladenlokal / retail / gastronomie",
    CAT_WOHNEN: "Locuinte (secundar)",
    CAT_ALTELE: "Parcare / depozit / altele",
}

# --- Dictionare de cuvinte-cheie (DE, cu variante CH) -----------------------

# Termeni fara echivoc: apar practic doar in anunturi de cabinet/praxis.
KW_PRAXIS_STRONG = [
    "praxis", "praxen", "praxisraum", "praxisräume", "praxisfläche",
    "praxisräumlichkeiten", "arztpraxis", "zahnarzt", "ärztezentrum",
    "gesundheitszentrum", "behandlungsraum", "behandlungsräume",
    "behandlungszimmer", "sprechzimmer", "physiotherapie", "psychotherapie",
    "osteopathie", "chiropraktik", "logopädie", "ergotherapie", "podologie",
    "heilpraktiker", "naturheilkunde", "apotheke", "therapeut", "medizinisch",
]

# Termeni ambigui: apar si in descrieri de apartamente ("Wellnessbereich",
# "Massagedusche"), deci singuri nu decid categoria.
KW_PRAXIS_WEAK = [
    "arzt", "ärzt", "medical", "therapie", "tcm", "massage", "kosmetik",
    "coiffeur", "wellness", "beauty", "studio für",
]

KW_PRAXIS = KW_PRAXIS_STRONG + KW_PRAXIS_WEAK

KW_BUSINESS = [
    "büro", "buero", "bürofläche", "büroräume", "büroraum", "office",
    "gewerbe", "gewerbefläche", "gewerberaum", "gewerberäume", "gewerbeobjekt",
    "atelier", "werkstatt", "coworking", "co-working", "arbeitsplatz",
    "arbeitsplätze", "geschäftsraum", "geschäftsräume", "geschäftsfläche",
    "büroetage", "dienstleistung", "kanzlei", "agentur", "showroom",
    "besprechungsraum", "sitzungszimmer", "empfang", "grossraumbüro",
    "einzelbüro", "loft", "gewerblich", "büro-", "praxisfläche",
]

KW_RETAIL_GASTRO = [
    "ladenlokal", "laden", "ladenfläche", "verkaufsfläche", "verkaufsraum",
    "boutique", "shop", "schaufenster", "restaurant", "gastro", "gastronomie",
    "café", "cafe", "bar", "take-away", "takeaway", "bäckerei", "kiosk",
    "gastwirtschaft", "hotel", "pub",
]

KW_WOHNEN = [
    "wohnung", "wohnungen", "zimmerwohnung", "wohnhaus", "einfamilienhaus",
    "reihenhaus", "attikawohnung", "dachwohnung", "maisonette", "studio",
    "wg-zimmer", "wohngemeinschaft", "loftwohnung", "mietwohnung",
]

KW_ALTELE = [
    "parkplatz", "einstellhalle", "garage", "autoabstellplatz", "tiefgarage",
    "lagerraum", "kellerabteil", "abstellplatz", "bastelraum",
]

# object_type / object_category din API-ul flatfox
TYPE_PRAXIS = {"MEDICAL_PRACTICE", "PRACTICE"}
TYPE_BUSINESS = {
    "OFFICE", "COMMERCIAL", "WORKSHOP", "ATELIER", "STUDIO_ROOM",
    "FACTORY", "INDUSTRIAL_OBJECT", "COWORKING", "BUSINESS",
}
TYPE_RETAIL_GASTRO = {"ARCADE", "SHOP", "RESTAURANT", "BAR", "HOTEL", "GASTRONOMY"}
TYPE_ALTELE = {
    "GARAGE_SLOT", "OPEN_SLOT", "COVERED_SLOT", "STORAGE_ROOM", "PARKING",
    "DOUBLE_GARAGE", "SINGLE_GARAGE", "BOAT_PLACE", "HOBBY_ROOM",
}
TYPE_WOHNEN = {
    "APARTMENT", "DUPLEX", "ATTIC_FLAT", "ROOF_FLAT", "SHARED_FLAT",
    "SINGLE_ROOM", "FURNISHED_FLAT", "HOUSE", "TERRACE_FLAT", "STUDIO",
    "LOFT_FLAT", "ROW_HOUSE", "VILLA", "CHALET", "FARM_HOUSE", "MAISONETTE",
    "BACHELOR_FLAT", "SINGLE_HOUSE", "MULTIPLE_DWELLING",
}
CATEGORY_BUSINESSY = {"INDUSTRY", "GASTRO", "COMMERCIAL", "OFFICE"}
CATEGORY_WOHNEN = {"APARTMENT", "HOUSE", "SHARED"}


def _title_of(listing):
    """Doar titlurile — flatfox le genereaza din tipul obiectului
    ("235m² Praxis" vs "235m² Büro"), deci sunt semnalul cel mai curat."""
    return " ".join([
        listing.get("short_title") or "",
        listing.get("pitch_title") or "",
        listing.get("description_title") or "",
    ]).lower()


def _text_of(listing):
    parts = [
        listing.get("public_title") or "",
        listing.get("short_title") or "",
        listing.get("pitch_title") or "",
        listing.get("description_title") or "",
        listing.get("description") or "",
        listing.get("rent_title") or "",
        listing.get("object_type") or "",
        listing.get("object_category") or "",
    ]
    return " ".join(parts).lower()


def _hits(text, keywords):
    """Cuvintele-cheie distincte gasite in text.

    Termenii care sunt subsiruri ale altui termen gasit sunt eliminati:
    "Arztpraxis" ar declansa altfel si "praxis", si "arztpraxis", parand
    doua semnale independente cand de fapt e o singura aparitie.
    """
    found = {kw for kw in keywords if kw in text}
    return {kw for kw in found if not any(kw != other and kw in other for other in found)}


def classify(listing):
    """Returneaza (categorie, scor, detalii) pentru un anunt."""
    text = _text_of(listing)
    otype = (listing.get("object_type") or "").upper()
    ocat = (listing.get("object_category") or "").upper()

    h_praxis = _hits(text, KW_PRAXIS)
    h_praxis_strong = _hits(text, KW_PRAXIS_STRONG)
    h_biz = _hits(text, KW_BUSINESS)
    h_retail = _hits(text, KW_RETAIL_GASTRO)
    h_wohnen = _hits(text, KW_WOHNEN)
    h_alte = _hits(text, KW_ALTELE)

    # Semnal puternic din tipul obiectului
    if otype in TYPE_PRAXIS:
        h_praxis.add("<type>")
    if otype in TYPE_BUSINESS:
        h_biz.add("<type>")
    if otype in TYPE_RETAIL_GASTRO:
        h_retail.add("<type>")
    if otype in TYPE_ALTELE:
        h_alte.add("<type>")

    # Semnalele din metadatele obiectului sunt mai de incredere decat textul:
    # o descriere de apartament poate mentiona "Büro" fara sa fie spatiu comercial.
    meta_praxis = otype in TYPE_PRAXIS
    meta_biz = otype in TYPE_BUSINESS or ocat in CATEGORY_BUSINESSY
    meta_retail = otype in TYPE_RETAIL_GASTRO or ocat == "GASTRO"
    meta_wohnen = otype in TYPE_WOHNEN or ocat in CATEGORY_WOHNEN
    meta_alte = otype in TYPE_ALTELE or ocat == "PARK"

    # Obiectul ESTE o praxis (nu doar "potrivit si ca praxis"): o spune tipul
    # obiectului sau titlul. Foarte multe anunturi de birou mentioneaza in
    # descriere "geeignet als Büro oder Praxis" — acelea raman birouri, dar
    # sunt marcate ca relevante pentru praxis (vezi `praxis_relevant`).
    title = _title_of(listing)
    praxis_clar = (
        meta_praxis
        or "praxis" in title
        or (len(h_praxis_strong) >= 2 and not meta_biz)
    )

    if meta_wohnen and not meta_biz and not meta_retail and not meta_praxis:
        # Obiect de locuit. Il mutam la praxis doar daca textul e categoric
        # (ex. apartament transformat in cabinet, listat gresit ca locuinta).
        cat = CAT_PRAXIS if ("praxis" in text and len(h_praxis_strong) >= 2) else CAT_WOHNEN
    elif praxis_clar:
        cat = CAT_PRAXIS
    elif meta_biz or (len(h_biz) >= 2 and not meta_alte):
        cat = CAT_RETAIL_GASTRO if (meta_retail and not h_biz) else CAT_BUSINESS
    elif meta_retail or len(h_retail) >= 2:
        cat = CAT_RETAIL_GASTRO
    elif meta_alte or h_alte:
        cat = CAT_ALTELE
    elif h_wohnen:
        cat = CAT_WOHNEN
    elif h_biz:
        cat = CAT_BUSINESS
    else:
        cat = CAT_ALTELE

    detalii = {
        # True si pentru birourile care se ofera explicit si ca spatiu de praxis
        "praxis_relevant": bool(h_praxis_strong) or cat == CAT_PRAXIS,
        "kw_praxis": sorted(h_praxis_strong),
        "kw_praxis_slabe": sorted(h_praxis - h_praxis_strong),
        "kw_business": sorted(h_biz),
        "kw_retail": sorted(h_retail),
        "kw_wohnen": sorted(h_wohnen),
    }
    return cat, detalii


# --- Regiunea Berna --------------------------------------------------------

def is_bern(listing):
    """True daca anuntul e in cantonul Berna (dupa NPA / oras)."""
    zip_ = listing.get("zipcode")
    try:
        z = int(zip_)
    except (TypeError, ValueError):
        z = None
    city = (listing.get("city") or "").lower()

    if z is not None:
        # Cantonul Berna: 3000-3899 (Berna, Emmental, Thun, Interlaken).
        # Atentie: 3900-3999 este Valais (Brig, Visp, Gampel, Zermatt).
        if 3000 <= z <= 3899:
            return True
        # Biel/Bienne si Seeland; Jura bernois; Oberaargau (Langenthal).
        if 2500 <= z <= 2564 or 2710 <= z <= 2765:
            return True
        if 4900 <= z <= 4955:
            return True
        return False
    return "bern" in city or "biel" in city or "thun" in city


def is_bern_city(listing):
    try:
        z = int(listing.get("zipcode"))
    except (TypeError, ValueError):
        return False
    return 3000 <= z <= 3030


# --- Scor de calitate pentru selectie --------------------------------------

def quality_score(listing, cat, detalii=None):
    """Scor: cat mai relevant si mai bogat ca prezentare, cu atat mai mare."""
    score = 0.0

    # 1. Categoria (cerinta principala a utilizatorului)
    score += {
        CAT_PRAXIS: 1000,
        CAT_BUSINESS: 900,
        CAT_RETAIL_GASTRO: 500,
        CAT_WOHNEN: 150,
        CAT_ALTELE: 0,
    }[cat]

    # Birou/gewerbe oferit explicit si ca spatiu de praxis — tot foarte relevant
    if detalii and detalii.get("praxis_relevant") and cat != CAT_PRAXIS:
        score += 120

    # 2. Regiunea Berna
    if is_bern_city(listing):
        score += 300
    elif is_bern(listing):
        score += 200

    # 3. Bogatia prezentarii — asta conteaza pentru studiul limbajului
    desc = listing.get("description") or ""
    n = len(desc)
    if n >= 2000:
        score += 220
    elif n >= 1200:
        score += 180
    elif n >= 600:
        score += 130
    elif n >= 300:
        score += 70
    elif n >= 120:
        score += 25

    imgs = listing.get("images") or []
    score += min(len(imgs), 12) * 12

    if listing.get("documents"):
        score += 40
    if listing.get("tour_url") or listing.get("video_url"):
        score += 30
    if listing.get("attributes"):
        score += min(len(listing["attributes"]), 15) * 4
    if listing.get("surface_usable") or listing.get("surface_living"):
        score += 25
    if (listing.get("agency") or {}).get("name"):
        score += 15

    # 4. Doar inchirieri (utilizatorul vrea sa inchirieze)
    if listing.get("offer_type") == "RENT":
        score += 120

    return score


def is_rich_enough(listing):
    """Filtru minim de calitate: trebuie sa fie o prezentare reala."""
    desc = listing.get("description") or ""
    return len(desc) >= 150 and len(listing.get("images") or []) >= 1
