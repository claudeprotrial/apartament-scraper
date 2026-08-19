# Scraper anunțuri imobiliare CH — corpus pentru anunț de închiriere în zona Berna

Colectează prezentări reale de spații de închiriat din Elveția, ca material de
studiu pentru limbaj, formulări, imagini și forme de prezentare — înainte de a
publica un anunț propriu pe un portal ca homegate.ch.

**Prioritatea de clasificare** (conform cerinței): spațiile pentru **praxis** și
**birou / gewerbe** sunt cele mai valoroase; locuințele sunt colectate secundar.

## Rulare

```bash
python3 scrape.py
```

Nu are nevoie de nicio dependință — doar biblioteca standard Python 3.

Prima rulare descarcă indexul complet (~35.500 anunțuri) și îl salvează în
`.cache/flatfox_raw.json` (221 MB). Rulările următoare pornesc din cache, deci
sunt instantanee până la faza de descărcare. Poți șterge `.cache/` oricând —
se reconstruiește singur, în ~7 minute.

Opțiuni:

```bash
python3 scrape.py --limit 200        # mai multe anunțuri
python3 scrape.py --max-images 20    # mai multe poze per anunț
python3 scrape.py --wohnen 0         # exclude complet locuințele
python3 scrape.py --refresh          # reîmprospătează indexul de la server
python3 scrape.py --no-html          # sare peste snapshot-ul HTML al paginii
```

## Dashboard pentru răsfoit și prezentat

```bash
python3 dashboard.py
```

Generează `anunturi/dashboard.html` — un fișier HTML autonom pe care îl deschizi
cu dublu-click. Fără server, fără internet: datele și textele germane sunt
încorporate în pagină, iar pozele sunt citite relativ, de pe disc.

- **Căutare instantanee** în titluri, descrieri, adrese, agenții și dotări.
  Umlaut-urile sunt normalizate — `büro`, `buero` și `buro` dau același
  rezultat. Mai multe cuvinte = filtru ȘI. Termenii găsiți sunt evidențiați.
- **Filtre** pe categorie, „relevant praxis", doar orașul Berna, tip de obiect
  (Büro, Gewerbe, Ladenfläche, Praxis…), plus sortare după relevanță,
  suprafață, lungimea descrierii sau oraș.
- **★ Selectate** — marchează câteva anunțuri și filtrează doar pe ele; util
  când vrei să arăți 3–4 exemple. Selecția se ține minte între sesiuni.
- **Detaliu** cu toate pozele și captions-urile lor germane („Eingangsbereich",
  „Küche und Aufenthalt"), textul integral, dotările și tabelul de date.
  <kbd>←</kbd> <kbd>→</kbd> trec prin anunțuri, <kbd>/</kbd> sare în căutare,
  <kbd>Esc</kbd> închide. Fiecare anunț are link către originalul de pe flatfox.

Rulează `dashboard.py` din nou după orice `scrape.py` — pagina e un instantaneu
al folderului, nu se actualizează singură.

## Ce se descarcă

Pentru numerele curente, vezi antetul din `dashboard.html` sau `index.csv` —
se schimbă la fiecare rulare. Profilul rămâne același: **numai spații
comerciale de închiriat, numai din cantonul Berna**, pentru că pool-ul de
`B_buero_gewerbe` din regiune (peste 7.000 de anunțuri eligibile) acoperă orice
limită rezonabilă înainte să se ajungă la locuințe.

Rularea de referință (100 de anunțuri, 952 imagini, 281 MB) a dat: 21 în
`A_praxis_medical`, 79 în `B_buero_gewerbe`, dintre care 78 marcate
„relevant pentru praxis"; 55 în orașul Berna, restul în canton (Wabern,
Gümligen, Studen, Biel/Bienne). Tipuri: `OFFICE`, `COMMERCIAL`, `SHOP`,
`PRACTICE`, atelier, workshop, industrial. Descrierile au între 432 și 5.485 de
caractere (mediană ~1.720) — prezentări reale, nu anunțuri seci.

Dacă vrei și locuințe pentru comparație, ridică limita: categoriile secundare
intră automat după epuizarea celor comerciale.

```
anunturi/
├── dashboard.html            # interfața de răsfoit și căutat
├── index.csv                 # tabel cu toate anunțurile descărcate
├── CORPUS-TEXTE.md           # toate textele germane într-un singur fișier
├── A_praxis_medical/         # cabinete, praxis, terapie  ← cele mai relevante
├── B_buero_gewerbe/          # birouri, gewerbe, ateliere, coworking
├── C_laden_gastro/           # Ladenlokal, retail, gastronomie
├── D_wohnen/                 # locuințe (secundar)
└── E_altele/                 # parcări, depozite
```

Ultimele trei foldere apar doar dacă selecția ajunge până la ele.

Fiecare anunț are propriul folder cu:

| Fișier | Conținut |
|---|---|
| `anunt.md` | prezentarea completă, lizibilă — textele germane intacte |
| `anunt.json` | datele brute din API + metadatele de clasificare |
| `pagina.html` | snapshot al paginii publice (forma vizuală de prezentare) |
| `images/` | pozele anunțului, la rezoluție maximă |

`CORPUS-TEXTE.md` adună toate descrierile grupate pe categorii — util pentru a
citi zeci de formulări una după alta și a extrage tiparele de limbaj.

## Sursa datelor și de ce aceasta

Sursa este **flatfox.ch**, portal imobiliar elvețian care expune un API public
JSON (`/api/v1/public-listing/`) fără autentificare, acoperind toată Elveția,
inclusiv cantonul Berna, cu texte germane complete.

Portalurile verificate și respinse:

| Portal | Motiv |
|---|---|
| homegate.ch | protecție anti-bot DataDome — 403 + captcha |
| immoscout24.ch | protecție anti-bot — 403 |
| immobilienscout24.de | 401, protecție Akamai |
| immowelt.de | 403 / 410 |
| willhaben.at | robots.txt interzice explicit accesul automat |
| newhome.ch, urbanhome.ch | 403 / conținut randat prin JS |

API-ul flatfox ignoră parametrii de filtrare, deci scraperul descarcă indexul o
singură dată și filtrează/clasifică local. Cererile trimit
`Accept-Language: de-CH` — altfel titlurile generate vin în engleză.
Între cereri există o pauză de politețe.

## Cum se clasifică

`scraper/classify.py` decide categoria folosind în primul rând metadatele
obiectului (`object_category`, `object_type`) și abia apoi cuvintele-cheie din
text — o descriere de apartament care pomenește „Büro" nu devine spațiu comercial.

Un obiect intră în `A_praxis_medical` doar dacă **este** o praxis (tipul
obiectului sau titlul o spun). Foarte multe birouri se oferă în descriere și ca
spațiu de praxis („geeignet als Büro oder Praxis") — acelea rămân în
`B_buero_gewerbe`, dar primesc flag-ul **`praxis_relevant`** în `index.csv` și
în antetul din `anunt.md`. Deci pentru un cabinet, filtrează pe acel flag, nu
doar pe folder.

Scorul de selecție combină: categoria (praxis 1000 > birou 900 > retail 500 >
locuință 150, plus 120 pentru un birou relevant pentru praxis), regiunea
(orașul Berna +300, cantonul Berna +200), bogăția prezentării (lungimea
descrierii, numărul de poze, dotări, documente) și faptul că este închiriere.

Filtru minim: descriere de cel puțin 150 de caractere și cel puțin o poză.

Detecția regiunii Berna se face pe NPA: 3000–3899, plus Biel/Seeland
(2500–2564), Jura bernois (2710–2765) și Oberaargau (4900–4955). Atenție dacă
modifici: 3900–3999 **nu** este Berna, ci Valais (Brig, Visp, Gampel, Zermatt).

## Structura codului

```
scrape.py              CLI: selecție, descărcare, index, corpus
dashboard.py           generatorul de dashboard.html
scraper/flatfox.py     adaptorul sursei (API, imagini, pagini HTML)
scraper/classify.py    categorii, dicționare DE, detecția regiunii Berna, scor
scraper/render.py      randarea în Markdown a unui anunț
```

Pentru a adăuga o sursă nouă: un modul cu aceleași funcții ca `flatfox.py`
(`harvest_index`, `listing_url`, `image_urls`, `fetch_image`) și normalizarea
câmpurilor la aceleași chei.
