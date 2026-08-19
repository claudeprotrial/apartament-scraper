#!/usr/bin/env python3
"""Genereaza `anunturi/dashboard.html` — un dashboard autonom peste anunturile
deja descarcate, pentru rasfoire, cautare si prezentare.

Fisierul rezultat se deschide cu dublu-click; nu are nevoie de server si nici
de internet. Datele si textele germane sunt incorporate in pagina, iar pozele
sunt referite relativ, de pe disc.

Utilizare:
    python3 dashboard.py
    python3 dashboard.py --out anunturi/dashboard.html
"""

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from scraper import classify as C

ANUNTURI = os.path.join(HERE, "anunturi")

# Slug-urile de dotari vin in engleza din API; le aratam in germana, asa cum
# apar pe portaluri — e chiar vocabularul care ne intereseaza.
DOTARI_DE = {
    "lift": "Lift",
    "parkingspace": "Parkplatz",
    "accessiblewithwheelchair": "Rollstuhlgängig",
    "garage": "Garage / Einstellhalle",
    "balconygarden": "Balkon / Garten",
    "view": "Aussicht",
    "cable": "Kabelanschluss",
    "minergie": "Minergie",
    "broadbandinternet": "Breitband-Internet",
    "petsallowed": "Haustiere erlaubt",
    "ramp": "Rampe",
    "dishwasher": "Geschirrspüler",
    "parquetflooring": "Parkettboden",
    "tumbler": "Tumbler",
    "washingmachine": "Waschmaschine",
}

TIP_DE = {
    "OFFICE": "Büro",
    "COMMERCIAL": "Gewerbe",
    "SHOP": "Ladenfläche",
    "PRACTICE": "Praxis",
    "ATELIER": "Atelier",
    "WORKSHOP": "Werkstatt",
    "INDUSTRIAL_OBJECT": "Industrieobjekt",
    "LIVING_COMMERCIAL_BUILDING": "Wohn-/Geschäftshaus",
    "RESTAURANT": "Restaurant",
    "ARCADE": "Ladenlokal",
    "STORAGE_ROOM": "Lagerraum",
}


def pret_text(raw):
    """Eticheta de pret, in formatul german al portalului.

    `public_title` contine deja pretul formatat corect ("CHF 293 inkl. NK pro
    m² / Jahr"), inclusiv distinctia pe m²/an vs. pe luna — il refolosim.
    """
    titlu = raw.get("public_title") or ""
    if " - CHF" in titlu:
        return titlu.split(" - ", 1)[1]
    # ~16% din anunturi nu au pret public; portalul scrie "auf Anfrage".
    # E o formulare utila in sine, deci o aratam in loc de camp gol.
    coada = titlu.rsplit(" - ", 1)[-1] if " - " in titlu else ""
    if "anfrage" in coada.lower() or "demande" in coada.lower():
        return coada
    for key, sufix in (("rent_gross", "brutto"), ("rent_net", "netto")):
        if raw.get(key):
            return "CHF %s %s" % (format(int(raw[key]), ",d").replace(",", "'"), sufix)
    return ""


def aduna(root):
    """Citeste toate anunturile salvate si le pregateste pentru pagina."""
    items = []
    for cat in sorted(os.listdir(root)):
        catdir = os.path.join(root, cat)
        if not os.path.isdir(catdir):
            continue
        for name in sorted(os.listdir(catdir)):
            folder = os.path.join(catdir, name)
            jp = os.path.join(folder, "anunt.json")
            if not os.path.exists(jp):
                continue
            with open(jp, encoding="utf-8") as fh:
                d = json.load(fh)
            raw, meta = d["raw"], d["meta"]
            kw = meta.get("cuvinte_cheie") or {}

            imgdir = os.path.join(folder, "images")
            fisiere = sorted(os.listdir(imgdir)) if os.path.isdir(imgdir) else []
            # captions/dimensiuni, in aceeasi ordine ca fisierele de pe disc
            din_api = sorted(raw.get("images") or [], key=lambda i: i.get("ordering") or 0)
            imagini = []
            for idx, fn in enumerate(fisiere):
                info = din_api[idx] if idx < len(din_api) else {}
                imagini.append({
                    "f": fn,
                    "cap": info.get("caption") or "",
                    "w": info.get("width"),
                    "h": info.get("height"),
                })

            rel = os.path.relpath(folder, root)
            ag = raw.get("agency") or {}
            items.append({
                "pk": raw.get("pk"),
                "cat": meta["categorie"],
                "catLabel": meta["categorie_label"],
                "praxis": bool(kw.get("praxis_relevant")),
                "kwPraxis": kw.get("kw_praxis") or [],
                "scor": meta.get("scor"),
                "regiune": meta.get("regiune", ""),
                "titlu": raw.get("public_title") or raw.get("short_title") or "",
                "scurt": raw.get("short_title") or "",
                "pitch": raw.get("pitch_title") or "",
                "descTitlu": raw.get("description_title") or "",
                "desc": raw.get("description") or "",
                "oras": raw.get("city") or "",
                "npa": raw.get("zipcode"),
                "strada": raw.get("street") or "",
                "tip": raw.get("tip") or raw.get("object_type") or "",
                "tipDe": TIP_DE.get(raw.get("object_type") or "", raw.get("object_type") or ""),
                "catObj": raw.get("object_category") or "",
                "pret": pret_text(raw),
                "rentNet": raw.get("rent_net"),
                "rentNK": raw.get("rent_charges"),
                "rentBrut": raw.get("rent_gross"),
                "supr": raw.get("surface_usable") or raw.get("surface_living"),
                "camere": raw.get("number_of_rooms"),
                "etaj": raw.get("floor"),
                "anCons": raw.get("year_built"),
                "anRenov": raw.get("year_renovated"),
                "disponibil": raw.get("moving_date") or raw.get("moving_date_type") or "",
                "referinta": raw.get("reference") or "",
                "agentie": " ".join(x for x in (ag.get("name"), ag.get("name_2")) if x),
                "agentieLoc": " ".join(str(x) for x in (ag.get("zipcode"), ag.get("city")) if x),
                "dotari": [DOTARI_DE.get(a.get("name"), a.get("name"))
                           for a in (raw.get("attributes") or []) if a.get("name")],
                "url": meta.get("url", ""),
                "folder": rel.replace(os.sep, "/"),
                "imagini": imagini,
            })

    ordine = {c: i for i, c in enumerate(C.CATEGORY_ORDER)}
    items.sort(key=lambda x: (ordine.get(x["cat"], 9), -(x["scor"] or 0)))
    return items


TEMPLATE = r"""<!doctype html>
<html lang="ro">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Anunțuri Berna — spații comerciale de închiriat</title>
<style>
:root{
  --bg:#f6f7f9; --card:#fff; --ink:#16181d; --ink2:#5b626e; --ink3:#8a919e;
  --line:#e2e5ea; --accent:#1f6feb; --accent-ink:#fff;
  --a-cat:#7a3ea3; --a-cat-bg:#f3e9fa; --b-cat:#1d6f5c; --b-cat-bg:#e3f4ee;
  --praxis:#a8590a; --praxis-bg:#fdf0e0; --star:#e0a800;
  --shadow:0 1px 2px rgba(16,20,28,.06),0 4px 12px rgba(16,20,28,.05);
}
@media (prefers-color-scheme:dark){
  :root{
    --bg:#101216; --card:#181b21; --ink:#e8eaee; --ink2:#a3abb8; --ink3:#767e8b;
    --line:#272b33; --accent:#4c8dff; --accent-ink:#0b1220;
    --a-cat:#d2a8f0; --a-cat-bg:#2e2038; --b-cat:#7fd8bd; --b-cat-bg:#152e28;
    --praxis:#f0b878; --praxis-bg:#33240f; --star:#f0c443;
    --shadow:0 1px 2px rgba(0,0,0,.4),0 4px 14px rgba(0,0,0,.3);
  }
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
  -webkit-font-smoothing:antialiased}
a{color:var(--accent)}

/* ---- bara de sus ---- */
header{position:sticky;top:0;z-index:20;background:var(--bg);
  border-bottom:1px solid var(--line);padding:14px 20px 12px}
/* Pe ecrane inguste sau scunde controalele se aseaza pe multe randuri, iar un
   antet lipit ajunge mai inalt decat fereastra si acopera tot. Il lasam sa
   plece la derulare. */
@media (max-width:700px),(max-height:620px){header{position:static}}
.top{display:flex;align-items:baseline;gap:14px;flex-wrap:wrap;margin-bottom:11px}
h1{font-size:17px;margin:0;letter-spacing:-.01em}
.sub{color:var(--ink3);font-size:13px}
.controls{display:flex;gap:9px;flex-wrap:wrap;align-items:center}
#q{flex:1 1 300px;min-width:200px;padding:9px 12px;border:1px solid var(--line);
  border-radius:8px;background:var(--card);color:var(--ink);font-size:14px}
#q:focus{outline:2px solid var(--accent);outline-offset:-1px;border-color:transparent}
select{padding:9px 10px;border:1px solid var(--line);border-radius:8px;
  background:var(--card);color:var(--ink);font-size:13px}
.chip{padding:7px 12px;border:1px solid var(--line);border-radius:99px;background:var(--card);
  color:var(--ink2);font-size:13px;cursor:pointer;user-select:none;white-space:nowrap}
.chip:hover{border-color:var(--ink3)}
.chip.on{background:var(--accent);border-color:var(--accent);color:var(--accent-ink);font-weight:500}
.count{color:var(--ink3);font-size:13px;margin-left:auto;white-space:nowrap}

/* ---- grila ---- */
main{padding:18px 20px 60px}
.grid{display:grid;gap:16px;grid-template-columns:repeat(auto-fill,minmax(290px,1fr))}
.card{background:var(--card);border:1px solid var(--line);border-radius:11px;overflow:hidden;
  cursor:pointer;box-shadow:var(--shadow);display:flex;flex-direction:column;
  transition:transform .12s ease, box-shadow .12s ease}
.card:hover{transform:translateY(-2px);box-shadow:0 4px 10px rgba(16,20,28,.1),0 12px 28px rgba(16,20,28,.09)}
.thumb{aspect-ratio:4/3;background:var(--line);position:relative;overflow:hidden}
.thumb img{width:100%;height:100%;object-fit:cover;display:block}
.nimg{position:absolute;right:8px;bottom:8px;background:rgba(0,0,0,.62);color:#fff;
  font-size:11px;padding:2px 7px;border-radius:99px;backdrop-filter:blur(3px)}
.star{position:absolute;left:7px;top:7px;width:29px;height:29px;border:0;border-radius:50%;
  background:rgba(0,0,0,.45);color:#fff;font-size:15px;cursor:pointer;line-height:29px;
  padding:0;backdrop-filter:blur(3px)}
.star.on{color:var(--star)}
.body{padding:12px 13px 13px;display:flex;flex-direction:column;gap:7px;flex:1}
.badges{display:flex;gap:5px;flex-wrap:wrap}
.badge{font-size:11px;padding:2px 8px;border-radius:99px;font-weight:600;letter-spacing:.01em}
.badge.A{background:var(--a-cat-bg);color:var(--a-cat)}
.badge.B{background:var(--b-cat-bg);color:var(--b-cat)}
.badge.px{background:var(--praxis-bg);color:var(--praxis)}
.badge.tip{background:var(--line);color:var(--ink2)}
.ctitle{font-weight:600;font-size:14.5px;line-height:1.35;margin:0}
.cmeta{color:var(--ink2);font-size:12.5px}
.cprice{margin-top:auto;padding-top:6px;font-size:13px;color:var(--ink);font-weight:600}
.csnip{color:var(--ink3);font-size:12.5px;line-height:1.45;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
mark{background:#ffe9a8;color:#3a2c00;border-radius:2px;padding:0 1px}
@media (prefers-color-scheme:dark){mark{background:#5d4a12;color:#ffe9a8}}
.empty{text-align:center;color:var(--ink3);padding:70px 20px}

/* ---- detaliu ---- */
#ov{position:fixed;inset:0;z-index:50;background:rgba(10,12,16,.6);
  backdrop-filter:blur(3px);display:none;padding:26px}
#ov.open{display:block}
.panel{background:var(--bg);max-width:1180px;height:100%;margin:0 auto;border-radius:13px;
  overflow:hidden;display:flex;flex-direction:column;box-shadow:0 20px 60px rgba(0,0,0,.4)}
.phead{display:flex;align-items:center;gap:12px;padding:12px 16px;border-bottom:1px solid var(--line);
  background:var(--card)}
.phead h2{font-size:15px;margin:0;flex:1;font-weight:600;line-height:1.4}
.nav{display:flex;gap:6px}
.btn{border:1px solid var(--line);background:var(--card);color:var(--ink2);border-radius:7px;
  padding:6px 11px;cursor:pointer;font-size:13px}
.btn:hover{border-color:var(--ink3);color:var(--ink)}
.btn:disabled{opacity:.35;cursor:default}
.pbody{flex:1;overflow:auto;display:grid;grid-template-columns:minmax(0,1.15fr) minmax(0,1fr)}
@media (max-width:900px){.pbody{grid-template-columns:1fr}#ov{padding:0}.panel{border-radius:0}}
.gal{padding:16px;display:flex;flex-direction:column;gap:10px;min-width:0}
.gal figure{margin:0}
.gal img{width:100%;border-radius:9px;display:block;background:var(--line)}
.gal figcaption{color:var(--ink3);font-size:12px;margin-top:5px}
.txt{padding:16px 18px 40px;border-left:1px solid var(--line);min-width:0;background:var(--card)}
@media (max-width:900px){.txt{border-left:0;border-top:1px solid var(--line)}}
.txt h3{font-size:12px;text-transform:uppercase;letter-spacing:.06em;color:var(--ink3);
  margin:22px 0 9px;font-weight:600}
.txt h3:first-child{margin-top:0}
.desc{white-space:pre-wrap;font-size:14.5px;line-height:1.62}
.desc strong{font-weight:600}
table{border-collapse:collapse;width:100%;font-size:13px}
td{padding:5px 0;border-bottom:1px solid var(--line);vertical-align:top}
td:first-child{color:var(--ink3);width:44%;padding-right:10px}
.tags{display:flex;gap:6px;flex-wrap:wrap}
.tag{background:var(--line);color:var(--ink2);font-size:12px;padding:3px 9px;border-radius:99px}
kbd{background:var(--line);border-radius:4px;padding:1px 5px;font-size:11px;font-family:inherit}
.hint{color:var(--ink3);font-size:12px;padding:10px 20px 26px;text-align:center}
</style>
</head>
<body>
<header>
  <div class="top">
    <h1>Anunțuri Berna — spații comerciale de închiriat</h1>
    <span class="sub" id="stats"></span>
  </div>
  <div class="controls">
    <input id="q" type="search" placeholder="Caută în titluri, descrieri, adrese, agenții…  (apasă / )" autocomplete="off">
    <button class="chip" data-f="A">Praxis</button>
    <button class="chip" data-f="B">Birou / Gewerbe</button>
    <button class="chip" data-f="px">Relevant praxis</button>
    <button class="chip" data-f="city">Doar orașul Berna</button>
    <button class="chip" data-f="star">★ Selectate</button>
    <select id="tip"><option value="">Toate tipurile</option></select>
    <select id="sort">
      <option value="scor">Sortare: relevanță</option>
      <option value="supr">Suprafață (desc.)</option>
      <option value="desc">Lungime descriere</option>
      <option value="oras">Oraș (A–Z)</option>
    </select>
    <span class="count" id="count"></span>
  </div>
</header>

<main><div class="grid" id="grid"></div><div class="empty" id="empty" hidden>Niciun anunț nu corespunde filtrelor.</div></main>
<div class="hint"><kbd>/</kbd> caută · <kbd>←</kbd> <kbd>→</kbd> navighează · <kbd>Esc</kbd> închide · ★ marchează exemplele de prezentat</div>

<div id="ov"><div class="panel">
  <div class="phead">
    <button class="btn star-big" id="dstar" title="Marchează pentru prezentare">☆</button>
    <h2 id="dtitle"></h2>
    <div class="nav">
      <button class="btn" id="prev">←</button><button class="btn" id="next">→</button>
      <a class="btn" id="dlink" target="_blank" rel="noopener">Original ↗</a>
      <button class="btn" id="close">✕</button>
    </div>
  </div>
  <div class="pbody"><div class="gal" id="dgal"></div><div class="txt" id="dtxt"></div></div>
</div></div>

<script id="data" type="application/json">__DATE__</script>
<script>
const DATE = JSON.parse(document.getElementById('data').textContent);
const grid = document.getElementById('grid'), qEl = document.getElementById('q');
const ov = document.getElementById('ov');
let filtre = {A:false, B:false, px:false, city:false, star:false};
let vizibile = [], idxCurent = -1;

/* localStorage arunca SecurityError cand pagina e deschisa dintr-un context
   fara origine (file:// in unele browsere, data:). Stelele sunt un accesoriu —
   nu au voie sa opreasca restul paginii, deci cad elegant pe memorie. */
const depozit = {
  ia(){ try { return JSON.parse(localStorage.getItem('stele') || '[]'); }
        catch(e){ return []; } },
  pune(v){ try { localStorage.setItem('stele', JSON.stringify(v)); } catch(e){} }
};
let stele = new Set(depozit.ia());

/* Normalizare pentru cautare: fara diacritice, cu umlaut-urile germane
   scrise si "ae/oe/ue", ca sa gaseasca "buro", "buero" si "Büro" la fel. */
const norm = s => (s||'').toLowerCase()
  .replace(/ä/g,'ae').replace(/ö/g,'oe').replace(/ü/g,'ue').replace(/ß/g,'ss')
  .normalize('NFD').replace(/[\u0300-\u036f]/g,'');

DATE.forEach(d => {
  d._s = norm([d.titlu,d.scurt,d.pitch,d.descTitlu,d.desc,d.oras,d.strada,d.npa,
               d.agentie,d.tipDe,d.tip,d.dotari.join(' ')].join(' '));
});

/* tipurile disponibile, in dropdown */
const tipSel = document.getElementById('tip');
[...new Set(DATE.map(d=>d.tipDe).filter(Boolean))].sort().forEach(t=>{
  const o=document.createElement('option'); o.value=t; o.textContent=t; tipSel.appendChild(o);
});

const esc = s => (s||'').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));

/* evidentiaza termenii cautati, lucrand pe textul original */
function marcheaza(text, termeni){
  let out = esc(text);
  if(!termeni.length) return out;
  const re = new RegExp('(' + termeni.map(t=>t.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')).join('|') + ')','gi');
  return out.replace(re, '<mark>$1</mark>');
}

function termeniCautare(){
  return qEl.value.trim().split(/\s+/).filter(t=>t.length>1);
}

function potrivit(d, termeni){
  if(filtre.A && d.cat[0] !== 'A') return false;
  if(filtre.B && d.cat[0] !== 'B') return false;
  if(filtre.px && !d.praxis) return false;
  if(filtre.city && !d.regiune.startsWith('Berna')) return false;
  if(filtre.star && !stele.has(d.pk)) return false;
  if(tipSel.value && d.tipDe !== tipSel.value) return false;
  return termeni.every(t => d._s.includes(norm(t)));
}

function fragment(d, termeni){
  if(!termeni.length) return d.descTitlu || d.desc.slice(0,150);
  const n = norm(d.desc), poz = n.indexOf(norm(termeni[0]));
  if(poz < 0) return d.descTitlu || d.desc.slice(0,150);
  return (poz>60?'…':'') + d.desc.slice(Math.max(0,poz-60), poz+150);
}

function randeaza(){
  const termeni = termeniCautare();
  vizibile = DATE.filter(d => potrivit(d, termeni));
  const s = document.getElementById('sort').value;
  if(s==='supr') vizibile.sort((a,b)=>(b.supr||0)-(a.supr||0));
  else if(s==='desc') vizibile.sort((a,b)=>b.desc.length-a.desc.length);
  else if(s==='oras') vizibile.sort((a,b)=>a.oras.localeCompare(b.oras,'de'));

  document.getElementById('count').textContent =
    vizibile.length + ' din ' + DATE.length + ' anunțuri' +
    (stele.size ? '  ·  ★ ' + stele.size : '');
  document.getElementById('empty').hidden = vizibile.length > 0;

  grid.innerHTML = vizibile.map((d,i)=>{
    const img = d.imagini[0];
    return `<article class="card" data-i="${i}">
      <div class="thumb">
        ${img ? `<img loading="lazy" src="${esc(d.folder)}/images/${esc(img.f)}" alt="">` : ''}
        <button class="star ${stele.has(d.pk)?'on':''}" data-pk="${d.pk}" title="Marchează">${stele.has(d.pk)?'★':'☆'}</button>
        ${d.imagini.length>1?`<span class="nimg">${d.imagini.length} poze</span>`:''}
      </div>
      <div class="body">
        <div class="badges">
          <span class="badge ${d.cat[0]}">${d.cat[0]==='A'?'Praxis':'Birou / Gewerbe'}</span>
          ${d.praxis && d.cat[0]!=='A' ? '<span class="badge px">praxis-relevant</span>':''}
          ${d.tipDe?`<span class="badge tip">${esc(d.tipDe)}</span>`:''}
        </div>
        <p class="ctitle">${marcheaza(d.descTitlu || d.scurt || d.titlu, termeni)}</p>
        <div class="cmeta">${marcheaza((d.strada?d.strada+', ':'')+(d.npa||'')+' '+d.oras, termeni)}
          ${d.supr?' · '+d.supr+' m²':''}</div>
        <div class="csnip">${marcheaza(fragment(d,termeni), termeni)}</div>
        <div class="cprice">${esc(d.pret)}</div>
      </div></article>`;
  }).join('');
}

/* ---------- detaliu ---------- */
function rand(v,u){ return (v===null||v===undefined||v==='') ? '' : v+(u||''); }

function deschide(i){
  if(i<0 || i>=vizibile.length) return;
  idxCurent = i;
  const d = vizibile[i], termeni = termeniCautare();
  document.getElementById('dtitle').textContent = (d.descTitlu || d.scurt) + ' — ' + d.oras;
  document.getElementById('dlink').href = d.url;
  const st = document.getElementById('dstar');
  st.textContent = stele.has(d.pk) ? '★' : '☆';
  st.classList.toggle('on', stele.has(d.pk));
  st.onclick = () => { comuta(d.pk); deschide(i); };

  document.getElementById('dgal').innerHTML = d.imagini.map(im=>
    `<figure><img loading="lazy" src="${esc(d.folder)}/images/${esc(im.f)}" alt="">
     ${im.cap?`<figcaption>${esc(im.cap)}</figcaption>`:''}</figure>`).join('')
    || '<p style="color:var(--ink3)">Fără imagini.</p>';

  const randuri = [
    ['Adresă', (d.strada?d.strada+', ':'')+(d.npa||'')+' '+d.oras],
    ['Regiune', d.regiune], ['Tip obiect', d.tip + (d.tipDe?' ('+d.tipDe+')':'')],
    ['Categorie obiect', d.catObj], ['Preț', d.pret],
    ['Chirie netă', rand(d.rentNet,' CHF')], ['Nebenkosten', rand(d.rentNK,' CHF')],
    ['Chirie brută', rand(d.rentBrut,' CHF')], ['Suprafață', rand(d.supr,' m²')],
    ['Camere', rand(d.camere)], ['Etaj', rand(d.etaj)],
    ['An construcție', rand(d.anCons)], ['An renovare', rand(d.anRenov)],
    ['Disponibil', d.disponibil], ['Referință', d.referinta],
    ['Ofertant', d.agentie + (d.agentieLoc?', '+d.agentieLoc:'')],
  ].filter(r=>r[1]!=='' && r[1]!=null && String(r[1]).trim()!=='');

  document.getElementById('dtxt').innerHTML =
    (d.pitch?`<h3>Pitch generat de portal</h3><p>${marcheaza(d.pitch,termeni)}</p>`:'') +
    (d.titlu?`<h3>Titlu public</h3><p>${marcheaza(d.titlu,termeni)}</p>`:'') +
    `<h3>Descriere (germană)</h3>` +
    (d.descTitlu?`<p><strong>${marcheaza(d.descTitlu,termeni)}</strong></p>`:'') +
    `<div class="desc">${marcheaza(d.desc,termeni)}</div>` +
    (d.kwPraxis.length?`<h3>Termeni praxis găsiți</h3><div class="tags">${
       d.kwPraxis.map(k=>`<span class="tag">${esc(k)}</span>`).join('')}</div>`:'') +
    (d.dotari.length?`<h3>Dotări</h3><div class="tags">${
       d.dotari.map(k=>`<span class="tag">${esc(k)}</span>`).join('')}</div>`:'') +
    `<h3>Date obiect</h3><table>${randuri.map(r=>
       `<tr><td>${esc(r[0])}</td><td>${esc(String(r[1]))}</td></tr>`).join('')}</table>`;

  document.getElementById('prev').disabled = i===0;
  document.getElementById('next').disabled = i===vizibile.length-1;
  ov.classList.add('open');
  document.querySelector('.pbody').scrollTop = 0;
  try { location.hash = d.pk; } catch(e){}   // deep-link, nu functionalitate
}

function inchide(){ ov.classList.remove('open'); idxCurent=-1;
  try { history.replaceState(null,'',location.pathname); } catch(e){} }

function comuta(pk){
  stele.has(pk) ? stele.delete(pk) : stele.add(pk);
  depozit.pune([...stele]);
  randeaza();
}

/* ---------- evenimente ---------- */
grid.addEventListener('click', e=>{
  const s = e.target.closest('.star');
  if(s){ e.stopPropagation(); comuta(+s.dataset.pk); return; }
  const c = e.target.closest('.card');
  if(c) deschide(+c.dataset.i);
});
document.querySelectorAll('.chip').forEach(b=>b.addEventListener('click',()=>{
  const f=b.dataset.f;
  filtre[f]=!filtre[f];
  if(f==='A'&&filtre.A) {filtre.B=false;}
  if(f==='B'&&filtre.B) {filtre.A=false;}
  document.querySelectorAll('.chip').forEach(x=>x.classList.toggle('on',filtre[x.dataset.f]));
  randeaza();
}));
qEl.addEventListener('input', randeaza);
tipSel.addEventListener('change', randeaza);
document.getElementById('sort').addEventListener('change', randeaza);
document.getElementById('close').onclick = inchide;
document.getElementById('prev').onclick = ()=>deschide(idxCurent-1);
document.getElementById('next').onclick = ()=>deschide(idxCurent+1);
ov.addEventListener('click', e=>{ if(e.target===ov) inchide(); });
document.addEventListener('keydown', e=>{
  if(e.key==='/' && document.activeElement!==qEl){ e.preventDefault(); qEl.focus(); qEl.select(); }
  else if(e.key==='Escape'){ if(ov.classList.contains('open')) inchide(); else { qEl.value=''; randeaza(); } }
  else if(ov.classList.contains('open')){
    if(e.key==='ArrowRight') deschide(idxCurent+1);
    if(e.key==='ArrowLeft') deschide(idxCurent-1);
  }
});

/* ---------- pornire ---------- */
document.getElementById('stats').textContent =
  DATE.length + ' anunțuri · ' + DATE.reduce((s,d)=>s+d.imagini.length,0) + ' imagini · ' +
  DATE.filter(d=>d.cat[0]==='A').length + ' praxis · ' +
  DATE.filter(d=>d.praxis).length + ' praxis-relevante';
randeaza();
if(location.hash){
  const i = vizibile.findIndex(d=>String(d.pk)===location.hash.slice(1));
  if(i>=0) deschide(i);
}
</script>
</body>
</html>
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", default=ANUNTURI, help="folderul cu anunturi descarcate")
    ap.add_argument("--out", default=None, help="fisierul HTML de iesire")
    args = ap.parse_args()

    out = args.out or os.path.join(args.src, "dashboard.html")
    items = aduna(args.src)
    if not items:
        sys.exit("Niciun anunt in %s — ruleaza intai scrape.py" % args.src)

    date = json.dumps(items, ensure_ascii=False, separators=(",", ":"))
    date = date.replace("</", "<\\/")  # nu inchide blocul <script>
    html = TEMPLATE.replace("__DATE__", date)

    with open(out, "w", encoding="utf-8") as fh:
        fh.write(html)

    poze = sum(len(i["imagini"]) for i in items)
    print("Scris %s" % out)
    print("  %d anunturi, %d imagini, %.1f MB pagina" % (len(items), poze, os.path.getsize(out) / 1e6))


if __name__ == "__main__":
    main()
