import streamlit as st
import pandas as pd
import psycopg2
import re
import unicodedata
import io
import os

st.set_page_config(page_title="Style ID Mapper", page_icon="🏷️", layout="wide")

# ─────────────────────────────────────────────────────────────────────────────
# BRAND → KEY FIELD MAPPING
# ─────────────────────────────────────────────────────────────────────────────

FINAL_KEY = {
    # ── INN: use item_name, strip last -size segment ──────────────────────────
    '7-10':'inn','AADVEKA':'inn','ACK':'inn','ANNY':'inn','ARKS':'inn',
    'Anaar':'inn','Aroop India':'inn','Averie':'inn',
    'BAD LIES':'inn','BADFIT':'inn',
    'Bewakoof':'inn','Bombay Troopers':'inn','Bummer':'inn',
    'CARRIALL':'inn','CLOUT JEANS':'inn','CULTURE':'inn',
    'Capsul':'inn','DEEBACO':'inn','DREAM ISLAND':'inn',
    'DaMENSCH':'inn','Daily Life Forever52':'inn','De Novoo':'inn',
    'Exhale Label':'inn','FLAWS':'inn',
    'Gully Labs':'inn','HEEL YOUR SOLE':'inn',
    'Hamptons':'van','House Of Mae':'inn',
    'Instinct First':'van','Instinct first':'van','JulietIsDead':'inn',
    'Label Ishnya':'inn','Life & Jam':'inn',
    'MAGRE':'inn','MANACA':'inn','Masha':'inn','Misnomer':'inn',
    'Mokobara':'inn','Nasher Miles':'inn','Nobero':'inn','Nona':'inn',
    'No Nazar':'inn','Nude Streetwear':'inn','OFFMINT':'inn',
    'PAZZION':'inn','PINQ POLKA':'inn','PawsnCollars':'inn','PrimalGray':'inn',
    'Qua':'inn','Qunic':'inn','RIPOFF':'inn',
    'Rareism':'inn','Rising Among':'inn','Roar For Good':'inn',
    'SIHANSH':'inn','SUBTRACT':'inn','Stitchinc':'inn',
    'Suta':'inn','Terminal Z':'inn','Terractive':'inn',
    'The Finicky Colorist':'inn','The Mitesh':'inn','Tinkle':'inn',
    'Urban Jungle':'inn','Urbano Fashion':'inn','VINDOF':'van','Virgio':'van',
    'WAKE YOUR DREAM':'inn','WARPING THEORIES':'inn',
    'Western Era':'inn','WomanLikeU':'inn','Xaya':'inn','ZORI WORLD':'inn',
    'bare wear':'inn','hexafun':'inn','sorta':'inn',
    'LVL99':'inn','Love Pangolin':'inn',
    # ── VAN: use vendor_article_name, strip trailing size ─────────────────────
    'ARISTOBRAT':'van','Aaina Sleepwear':'van','Aldeno':'van',
    'Auburban':'van','Around The City':'van','BAWSE':'van',
    'BLCKORCHID':'van','BOOZY BUTTON':'van','Bomaachi':'van','Broke Memers':'van',
    'By The Bay':'van','CAI':'van','Cava':'van','COMET':'van',
    'Crazy Mosquitoes':'van','Dash and Dot':'van','DenZ':'van','Dorabi':'van',
    'EVERDION':'van','Ewoke':'van','FLYAF':'van','FUR JADEN':'van','FYVA':'van',
    'Fearless Under Everything':'van','Femmella':'van','GOTHIC TOONS':'van',
    'House of Fett':'van','IWE STUDIOS':'van',
    'Imperfecto':'van','Invogue':'van','Kairo':'van','Kickers':'van',
    'LALAFLOWER':'van','Lovicide':'van','Ludic':'van','MODAU':'van','MOKY':'van',
    'Modern Crew':'van','Nap Story':'van','NautiNati':'van','Notch Above':'van',
    'PAST MODERN':'van','PRDGY':'van','Poppi':'van',
    'PurplFrog':'van','QB - QUINTESSENTIAL BASICS':'van',
    'RATAN JAIPUR':'van','REDONRAW':'van','Rarez':'van','SKO':'van',
    'SLEEPLOVE':'van','STRANGE':'van','Shop Mauve':'van','Sullitt':'van',
    'TENHEM':'van','THE PONY & PEONY CO.':'van','TURMS':'van',
    'Tailor&Circus':'van','Tao Paris':'van','The Clothing Factory':'van',
    'The Khwaab':'van','The Label Life':'van','The Original Knit':'van',
    'The Pant Project':'van','The Souled Store':'van','Theater':'van',
    'Thr3letter':'van','Trendy Affair':'van','TrueBrowns':'van',
    'Tura Turi':'van','Twelve Thirty One':'van','Un Denim':'van',
    'WOOMN':'van','Younglings':'van','teeside':'van',
    'Khushbu Rathod Label':'van',
    # ── Brands fixed from error analysis (May 2026) ───────────────────────────
    'ARUNI':'van',             # VAN has correct design+color; INN had wrong color
    'B5IVE':'van',             # VAN has correct design name; INN color=Blue for all
    'CHK':'van',               # VAN distinguishes STRIDE WHITE vs STRIDE WHITE/GREY
    'RWDY':'aid',              # VAN has copy-paste bug ("LIME YELLOW" for all colors); AID has correct color
    'Select Staples':'van',    # VAN has correct design name (Aisha/Darla/Shade)
    'Senses':'van',            # VAN has correct color; normalise unicode (Crème→Creme)
    'SilSIla':'van',           # VAN has correct design (Easy Days/Reset/Daylight)
    'Summer Away':'van',       # VAN has correct design; INN has \\n garbage
    'The Purple Sack':'van',   # VAN has unique product name (Shaamali/Shahiraa clutch)
    'Vahro':'van',             # VAN has full design name; INN node=Kingsley Stripes for all
    'World of Sisa':'van',     # VAN has unique design; INN color=White for all
    # ── Brands fixed from error analysis round 2 (June 2026) ─────────────────
    'FABLE STREET':'van',      # item_name brand prefix missing/color generic; VAN unique design
    'NANA-KI':'van',           # item_name color generic ("Red"); VAN unique design name
    'Pink Fort':'van',         # item_name color generic ("Green"); VAN unique design name
    # ── Brands fixed from error analysis round 3 (Aug 2026) ──────────────────
    'ATBW':'van',              # VAN has product names; item_name = MONOCHROME JUNGLE for all
    'Huemn':'van',             # item_name = description garbage; VAN has product name
    'Kingdom of White':'van',  # VAN has design names; item_name = white-Core for everything
    'Outerworld':'van',        # VAN has specific polo names; item_name = LUXE-Green for all
    'STITCH STORIES':'van',    # VAN has product names; item_name = SUMMER-Blue for all
    'Style Island':'van',      # VAN distinguishes Jane Denim vs Sussane Polka Dot (item_name doesn't)
    'B label':'van',           # VAN correctly identifies products; item_name = Multi/Season for all
    'Cotton Curio':'van',      # VAN has product names; AID has size embedded
    'House of Mohini':'van',   # VAN = AID without size; item_name generic
    'Manvi Daga':'van',        # VAN has design names; AID has color+size
    'Meiala':'van',            # VAN has design names; item_name = Multi for all
    'Odd Not Even':'van',      # VAN has product names; AID is raw barcode
    'Rustlines':'van',         # VAN has design+color; item_name = Core-Black/Brown/Blue
    'Weaving Cult':'van',      # VAN distinguishes genuinely different dress designs (RGDRS002/003)
    'glimmr':'van',            # VAN unique per letter (bag charms)
    'Özel':'van',              # VAN unique per bag
    # ── AID: use vendor_article_id, strip trailing size ───────────────────────
    'A Toddler Thing':'aid','ARISTA VAULT':'aid','BILABA':'aid','Almost Gods':'aid',
    'Bird Eye':'aid','Blissclub':'aid','Bluer':'aid','Ceya':'aid','Chapter 2':'aid',
    'COLOR CAPITAL':'aid','Contemponari':'aid','Duchess Kumari':'aid',
    'ECHO STUDIO':'aid','EUME':'aid','Echolope':'aid','FEIER':'aid','Farda':'aid',
    'The Forbidden Fruit':'aid','Dhaaga':'aid','Fitkin':'aid','Freakins':'aid',
    'Freyja':'aid','Fuaark':'aid','GINNA':'aid','House Of Kari':'aid',
    'House of Koala':'aid','Hunnit':'aid','KHAAKI':'aid','Lea Clothing':'aid',
    'Lino Perros':'aid','MAIN CHARACTER':'aid','Muvazo':'aid','NeceSera':'aid',
    'Nishorama':'aid','OZiva':'aid','Ombrello':'aid','Oroh':'aid','PastModern':'aid',
    'Rare Ones':'aid','SEEAASH':'aid','Saanjh by Lea':'aid','Replyall':'aid',
    'Sew and You':'aid','Shibui':'aid','STUDIO MODA INDIA':'aid','StyleAsh':'aid',
    'Sugga':'aid','Suqah':'aid','TRUE WEST':'aid','The White Pole':'aid',
    'Torqadorn':'aid','Uptownie':'aid','TONI ROSSI':'aid','DOG D ORIGINALS':'aid',
    'Vellure':'aid','neopalms':'aid',
    # ── Brands fixed from error analysis (May 2026) ───────────────────────────
    'Bear House':'aid',        # VAN=generic; AID=TBH-ASTRON-YL (design+color), strip size
    'Chapter 2 Jr':'aid',      # AID=C2JR26TS028, strip age-group suffix (-11-12Yrs)
    'DULAAR':'aid',            # AID=NW-01-LY-102, strip age-group suffix (-102,-203)
    'Esthreall':'aid',         # AID=LOTCL/LOTWM, strip size; different stems = different designs
    'Girls Dont Dress for Boys':'aid',  # AID=OPH-BLK-XL, strip last -segment
    'Natty Garb':'aid',        # AID=DLJN_TSRT_XXL, strip _size
    'Private Lives':'aid',     # AID=ROUND NECK-PL009-XXL, strip -size
    'Rare Rabbit':'aid',       # AID=RR257300_2XL, strip _size
    'The Missy Co':'aid',      # AID=T357/T346/P218 (unique per design), strip -size
    'Aer':'aid',               # AID=AERMRTGRNV018M (color+design code), VAN generic; strip size
    'BARE BROWN':'aid',        # AID=BRBATR0072-Brown-M-34, design code is first segment
    # ── Brands fixed from error analysis round 3 (Aug 2026), verified vs real data ──
    'Aakar Taro':'aid',        # AID=AT-S26-S-08_BLUE_XS; strip last 2 _segments (color+size)
    'Genes Lecoanet Hemant':'aid',  # AID=LHGW-323E02-Black-L; VAN="DRESS Black" merges distinct designs
    'KIU':'aid',               # AID=KLMBCCBEIGE (no separator); use as-is, more precise than item_name
    '63 East':'aid',           # AID=DT84B-Blue Stripe-FS; VAN="Blair Shirt" merges 3 colors
    'Zeesh':'aid',             # AID=ZS-MU-BGE-001-6; VAN="BELLAGIO" merges colors
    'Love,Viana':'aid',        # AID=BAMBOO_BROWN_S; VAN="BAMBOO TOP" etc merges color/size variants
    'KRAUS JEANS':'aid',       # AID=LFA2356_Beige_26; VAN="HIGH RISE STRAIGHT JEANS" wrongly
                               # merges up to 4 distinct design codes/washes under one style name
    'Zumee':'inn',             # VAN="Aurelia TOP" has no color; item_name does (Aurelia-Green vs
                               # Aurelia-Pink) — was merging 2 colors into 1 style, verified against real data
}

SIZE_ALIASES = {'2XL':'XXL','XXL':'2XL','3XL':'XXXL','XXXL':'3XL'}
SIZE_PAT   = re.compile(r'\b(2XS|XS|S|M|L|XL|2XL|3XL|4XL|5XL|6XL|XXL|XXXL|2X|3X)\b', re.I)
PROD_PAT   = re.compile(r'\b(VALKYRE|JACKET|HOODIE|TEE|T[\-\s]?SHIRT|JEANS)\b', re.I)
COLOR_PAT  = re.compile(
    r'\b(BLACK|BLUE|WHITE|RED|GREEN|GREY|GRAY|BROWN|BEIGE|ICY\s*BLUE|COBALT|'
    r'NAVY|OLIVE|MAROON|PURPLE|PINK|YELLOW|ORANGE|CREAM|OFF\s*WHITE|CHARCOAL|'
    r'RUST|TEAL|CARAMEL|NUDE|SAGE|MINT|LAVENDER)\b', re.I)
SEASON_PAT = re.compile(r'\b(WINTER|SUMMER|NA|N/A|SPRING|AUTUMN|FALL|AW|SS|CORE|ARCHIVE)\b', re.I)

# ─────────────────────────────────────────────────────────────────────────────
# PURE-PYTHON KEY LOGIC
# ─────────────────────────────────────────────────────────────────────────────

def nz(s):
    return '' if pd.isna(s) else str(s).strip().rstrip('\n').replace('\\n', '')

def clean(t):
    t = unicodedata.normalize('NFKD', nz(t)).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'\s+', ' ', t).strip().lower()

def sanitize(t, n=15):
    t = unicodedata.normalize('NFKD', nz(t)).encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'[^A-Z0-9]', '', t.upper())[:n] or 'UNK'

def brand_prefix(b):
    return re.sub(r'[^a-zA-Z0-9]', '', nz(b))[:3].upper()

def strip_size(text, size):
    t  = nz(text)
    sz = re.sub(r'^(?:UK|EU)\s*', '', nz(size), flags=re.IGNORECASE).strip()
    if not sz:
        return t
    variants = {sz}
    su = sz.upper()
    if su in SIZE_ALIASES:
        variants.add(SIZE_ALIASES[su])
    if su == '2XL': variants |= {'XXL','2XL'}
    if su == 'XXL': variants |= {'2XL','XXL'}
    if su == '3XL': variants |= {'XXXL','3XL'}
    if sz.isdigit() and len(sz) == 1:
        variants.add('0' + sz)
    for s in variants:
        # For single-char sizes, require a non-empty separator to avoid substring match
        # e.g. "Althea Dress" size S should not strip the trailing 's'
        seps = [' - ', '-', '_', ' '] if len(s) == 1 else [' - ', '-', '_', ' ', '']
        for sep in seps:
            m = re.sub(re.escape(sep + s) + r'$', '', t, flags=re.IGNORECASE)
            if m != t:
                return m.rstrip('-_ ').strip()
    return t

def inn_key(iname):
    parts = str(iname).split('-')
    return '-'.join(parts[:-1]).strip() if len(parts) > 1 else iname

def valkyre_normalize_design(van):
    d = nz(van)
    for p in [SIZE_PAT, PROD_PAT, COLOR_PAT]:
        d = p.sub('', d)
    d = re.sub(r"['\u2019\u2018`]", '', d)
    d = re.sub(r'[^a-zA-Z0-9\s]', ' ', d)
    return re.sub(r'\s+', ' ', d).strip().lower()

def valkyre_color(aid, iname):
    aid = nz(aid); parts = nz(iname).split('-')
    if aid.startswith('VJAC-'):
        m = re.match(r'VJAC-[^-]+-([A-Z]+)_', aid)
        if m: return m.group(1).upper()
        c = parts[-2].strip() if len(parts) >= 3 else ''
        if c and not SEASON_PAT.match(c) and c.upper() not in ('NA','N/A',''):
            return re.sub(r'\s+','',c).upper()[:8]
        return 'BLK'
    if aid.startswith('VALK-'): return 'BLK'
    if len(parts) >= 4:
        c3 = parts[-3].strip()
        if c3 and not SEASON_PAT.match(c3) and c3.upper() not in ('NA','N/A',''):
            return re.sub(r'\s+','',c3).upper()[:10]
    c2 = parts[-2].strip() if len(parts) >= 3 else ''
    return re.sub(r'\s+','',c2).upper()[:8] if c2 and c2.upper() not in ('NA','N/A','') else 'NA'

def compute_nobero_overrides(df):
    """
    Nobero hybrid rule: default key = VAN (strip size). But if a VAN-based
    group exceeds 6 barcodes AND item_name actually splits that group into
    more than 1 distinct design (i.e. item_name is MORE specific than VAN
    for those rows), switch those rows to an item_name-based key instead.
    If item_name is equally/less specific (e.g. a generic placeholder like
    "Each"), VAN is kept — switching would only make things worse.
    Returns: dict {row_index: 'inn'} for rows that should override to item_name.
    """
    overrides = {}
    mask = df['brand_name'].astype(str).str.strip() == 'Nobero'
    if not mask.any():
        return overrides
    sub = df[mask]

    groups = {}  # (cat_key, van_val) -> list of row indices
    for idx, row in sub.iterrows():
        van  = nz(row.get('vendor_article_name',''))
        size = nz(row.get('size',''))
        cat_key = '|'.join([
            clean(nz(row.get('division',''))),
            clean(nz(row.get('section',''))),
            clean(nz(row.get('department',''))),
            clean(nz(row.get('node',''))),
        ])
        van_val = clean(strip_size(van, size)) if van else ''
        groups.setdefault((cat_key, van_val), []).append(idx)

    for (cat_key, van_val), idxs in groups.items():
        if len(idxs) > 6:
            inn_vals = {clean(inn_key(nz(df.loc[i, 'item_name']))) for i in idxs}
            if len(inn_vals) > 1:
                # item_name is more specific — use it for these rows
                for i in idxs:
                    overrides[i] = 'inn'
    return overrides

def get_style_key(row, nobero_overrides=None):
    brand = nz(row.get('brand_name',''))
    aid   = nz(row.get('vendor_article_id',''))
    van   = nz(row.get('vendor_article_name',''))
    iname = nz(row.get('item_name',''))
    size  = nz(row.get('size',''))
    cat_key = '|'.join([
        clean(nz(row.get('division',''))),
        clean(nz(row.get('section',''))),
        clean(nz(row.get('department',''))),
        clean(nz(row.get('node',''))),
    ])

    if brand == 'VALKYRE':
        return clean(brand)+'||'+valkyre_normalize_design(van)+'||'+valkyre_color(aid,iname)+'||'+cat_key

    if brand == 'Nobero':
        # Hybrid rule: default to VAN; fall back to item_name only when
        # item_name is genuinely more specific for an over-sized VAN group.
        use_inn = nobero_overrides is not None and nobero_overrides.get(row.name) == 'inn'
        val = inn_key(iname) if use_inn else (strip_size(van, size) if van else inn_key(iname))
        return clean(brand)+'||'+clean(val)+'||'+cat_key

    kt = FINAL_KEY.get(brand, 'inn')
    if kt == 'aid':
        if brand == 'Hunnit':
            v2 = re.sub(r'_[^_]+$','',aid).strip(); val = v2 if v2!=aid else strip_size(aid,size)
        elif brand == 'NeceSera':
            v2 = re.sub(r'_[^_]+$','',aid).strip(); val = v2 if v2!=aid else strip_size(aid,size)
        elif brand == 'Farda':
            v2 = re.sub(r'[A-Z]$','',aid).strip(); val = v2 if v2!=aid else strip_size(aid,size)
        elif brand == 'Bird Eye':
            p = aid.split('-'); val = '-'.join(p[:2]).strip() if len(p)>=2 else strip_size(aid,size)
        elif brand == 'StyleAsh':
            val = re.sub(r'\s+\d+$', '', nz(aid)).strip()
        elif brand == 'Sugga':
            val = strip_size(aid, size).lower()
        elif brand == 'Chapter 2 Jr':
            # AID: C2JR26TS028-11-12Yrs → C2JR26TS028 (strip age-group suffix)
            val = re.sub(r'-\d+(?:-\d+)?[Yy]rs$', '', nz(aid)).strip()
        elif brand == 'DULAAR':
            # AID: NW-01-LY-102 (102=1-2Y) → NW-01-LY (strip 3-digit age-group code)
            val = re.sub(r'-\d{3}$', '', nz(aid)).strip()
        elif brand == 'Girls Dont Dress for Boys':
            # AID: OPH-BLK-XL → OPH-BLK (strip last -segment; size in AID ≠ actual size)
            val = re.sub(r'-[^-]+$', '', nz(aid)).strip()
        elif brand == 'The Missy Co':
            # AID: T357-XXL → T357, P218-S → P218 (unique per design, strip -size)
            val = strip_size(aid, size)
            # XS edge case: T353-XS not stripped by strip_size → strip last -segment
            if val == nz(aid):
                val = re.sub(r'[-_][^-_]+$', '', nz(aid)).strip()
        elif brand == 'Fuaark':
            val = strip_size(aid, size)
        elif brand == 'Almost Gods':
            parts_ag = nz(aid).split()
            val = parts_ag[0].strip() if parts_ag else strip_size(aid, size)
        elif brand == 'The Forbidden Fruit':
            val = SIZE_PAT.sub('', nz(aid)).strip().rstrip('-_ ')
        elif brand == 'OZiva':
            val = strip_size(aid, size)
        elif brand == 'Blissclub':
            a = nz(aid)
            if a.replace(' ','').replace('-','').isdigit() or (len(a)>=10 and a[:7].isdigit()):
                val = a[:10]
            else:
                val = strip_size(a, size)
        elif brand == 'TONI ROSSI':
            val = re.sub(r'_EU\d+$', '', nz(aid), flags=re.IGNORECASE).strip()
            val = val if val != nz(aid) else strip_size(nz(aid), size)
        elif brand == 'DOG D ORIGINALS':
            val = nz(aid)
        elif brand == 'Aer':
            # AID: AERMRTGRNV018M (size letters appended directly after digits, no separator)
            val = re.sub(r'(?<=\d)(XXXL|XXL|XL|XS|S|M|L)$', '', nz(aid), flags=re.IGNORECASE).strip()
        elif brand == 'BARE BROWN':
            # AID: BRBATR0072-Brown-M-34 — design code is the first segment before first hyphen
            val = nz(aid).split('-')[0].strip()
        elif brand == 'RWDY':
            # AID: "CHILL SERIES | NAVY BLUE_L" — strip trailing _size
            val = strip_size(aid, size)
        elif brand == 'Aakar Taro':
            # AID: AT-S26-S-08_BLUE_XS → AT-S26-S-08 (strip last 2 underscore segments: color+size)
            val = re.sub(r'(_[^_]+){2}$', '', nz(aid)).strip()
            if val == nz(aid):
                val = strip_size(aid, size)
        elif brand == 'Genes Lecoanet Hemant':
            # AID: LHGW-323E02-Black-L → LHGW-323E02-Black (strip last -segment generically;
            # a plain strip_size fails on the one row where size="L/2XL" but AID suffix is "L/XXL")
            val = re.sub(r'-[^-]+$', '', nz(aid)).strip()
        elif brand == 'KIU':
            # AID: KLMBCCBEIGE — no separators at all, color baked directly into the code.
            # Use as-is: item_name's color field is actually LESS precise (collapses
            # DenimBlue/MintBlue/LightBlue into one "Blue", Lilac/LightLilac into "Purple").
            val = nz(aid)
        elif brand == '63 East':
            # AID: DT84B-Blue Stripe-FS → DT84B-Blue Stripe (strip last -segment generically)
            val = re.sub(r'-[^-]+$', '', nz(aid)).strip()
        elif brand == 'Zeesh':
            # AID: ZS-MU-BGE-001-6 → ZS-MU-BGE-001 (strip last -segment generically)
            val = re.sub(r'-[^-]+$', '', nz(aid)).strip()
        elif brand == 'Love,Viana':
            # AID: BAMBOO_BROWN_S → BAMBOO_BROWN (standard strip_size), then normalise a
            # stray-space typo seen in source data (e.g. "IBIZA_TOP_ BLUE_M") so it doesn't
            # split off into its own group vs "IBIZA_TOP_BLUE_S"
            val = strip_size(aid, size)
            val = re.sub(r'_\s+', '_', val)
        elif brand == 'KRAUS JEANS':
            # AID: LFA2356_Beige_26 → LFA2356 (strip last 2 underscore segments: color+size).
            # VAN is a shared style name (e.g. "HIGH RISE STRAIGHT JEANS") reused across up to
            # 4 distinct design codes/washes — verified against real data, do not use VAN here.
            val = re.sub(r'(_[^_]+){2}$', '', nz(aid)).strip()
        else:
            val = strip_size(aid, size)
    elif kt == 'van':
        if brand == 'Theater':
            v = strip_size(van,size) if van else ''
            val = re.sub(r'\s+\d{1,2}$','',v).strip() if v else strip_size(aid,size)
        elif brand == 'Ludic':
            v = nz(van)
            val = re.sub(r'\s+(MEN\s+|WOMEN\s+)?\d{1,3}$','',v,flags=re.IGNORECASE).strip() or v
        elif brand == 'Senses':
            # Normalise unicode in VAN (Crème → Creme) before using as key
            val = unicodedata.normalize('NFKD', nz(van)).encode('ascii','ignore').decode('ascii').strip()
            val = strip_size(val, size) if val else strip_size(aid, size)
        elif brand == 'Virgio':
            val = nz(van) if van else strip_size(aid, size)
        else:
            val = strip_size(van,size) if van else strip_size(aid,size)
    else:  # inn
        if brand == 'Instinct First' or brand == 'Instinct first':
            val = strip_size(van, size) if van else inn_key(iname)
        else:
            val = inn_key(iname)

    if 'SOL' in brand.upper() and 'ITE' in brand.upper():
        val = strip_size(aid, size)
    elif 'VYAM' in brand.upper():
        val = re.sub(r'\s*-\s*\w+\s*$', '', nz(aid)).strip()

    return clean(brand)+'||'+clean(val)+'||'+cat_key

def make_style_id_base(brand, aid, van, iname):
    prefix = brand_prefix(brand)
    design_raw = nz(van) if van else ''
    if not design_raw:
        parts = nz(iname).split('-')
        design_raw = parts[4].strip() if len(parts)>=5 else nz(aid)
    parts = nz(iname).split('-')
    color_raw = parts[-2].strip() if len(parts)>=3 else (nz(van) or nz(aid))
    return f'BW_{prefix}_{sanitize(design_raw,15)}_{sanitize(color_raw,12)}_'

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_resource
def _get_db_url():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        st.error("DATABASE_URL not set.")
        st.stop()
    return db_url

def get_db():
    """
    Returns a live psycopg2 connection. Supabase's pooler can close idle
    connections server-side; st.cache_resource would otherwise keep handing
    out that dead connection forever ('connection already closed'). So we
    cache only the URL, keep the live connection in session_state, and
    ping it before every use — reconnecting transparently if needed.
    """
    db_url = _get_db_url()

    conn = st.session_state.get("_db_conn")
    if conn is not None:
        try:
            # Cheap liveness check
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            return conn
        except Exception:
            try:
                conn.close()
            except Exception:
                pass
            conn = None

    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    st.session_state["_db_conn"] = conn
    return conn

def batch_lookup_style_keys(style_keys, conn):
    if not style_keys:
        return {}
    cur = conn.cursor()
    cur.execute(
        "SELECT style_key, style_group_id FROM style_map WHERE style_key = ANY(%s)",
        (list(style_keys),))
    result = {r[0]: r[1] for r in cur.fetchall()}
    cur.close()
    return result

def batch_lookup_key_sizes(size_tuples, conn):
    if not size_tuples:
        return {}
    unique = list(set(size_tuples))
    cur = conn.cursor()
    cur.execute(
        """SELECT division, section, department, node, size, key_size
           FROM key_size_map
           WHERE (division, section, department, node, size) IN %s""",
        (tuple(unique),))
    result = {(r[0],r[1],r[2],r[3],r[4]): r[5] for r in cur.fetchall()}
    cur.close()
    return result

def fetch_existing_bases(bases, conn):
    if not bases:
        return {}
    cur = conn.cursor()
    patterns = [b + '%' for b in bases]
    cur.execute(
        "SELECT style_group_id FROM style_map WHERE style_group_id LIKE ANY(%s)",
        (patterns,))
    rows = cur.fetchall()
    cur.close()
    base_max = {}
    for (sid,) in rows:
        m = re.match(r'^(BW_[A-Z0-9]+_[A-Z0-9]+_[A-Z0-9]+_)(\d+)$', sid)
        if m:
            base = m.group(1)
            seq  = int(m.group(2))
            base_max[base] = max(base_max.get(base, 0), seq)
    return base_max

def batch_insert_styles(new_rows, conn):
    if not new_rows:
        return
    cur = conn.cursor()
    cur.executemany(
        """INSERT INTO style_map (style_key, style_group_id, brand_name, source)
           VALUES (%s,%s,%s,'generated') ON CONFLICT (style_key) DO NOTHING""",
        new_rows)
    conn.commit()
    cur.close()

# ─────────────────────────────────────────────────────────────────────────────
# MAIN MAPPING
# ─────────────────────────────────────────────────────────────────────────────

def map_dataframe(df, conn, progress=None, status=None, live=None):
    total = len(df)

    def live_update(step_pct, msg, rows_done=None, new_so_far=None):
        if progress: progress.progress(step_pct)
        if status:   status.text(msg)
        if live and rows_done is not None:
            pct = int(rows_done / total * 100)
            live.markdown(
                f"⏳ **{rows_done:,} / {total:,} rows** processed &nbsp;·&nbsp; "
                f"🆕 **{new_so_far:,}** new style IDs generated so far &nbsp; `{pct}%`")

    live_update(0.05, "Step 1/4 — computing style keys…", 0, 0)

    nobero_overrides = compute_nobero_overrides(df)

    rows_meta = []
    for _, row in df.iterrows():
        brand = nz(row.get('brand_name',''))
        aid   = nz(row.get('vendor_article_id',''))
        van   = nz(row.get('vendor_article_name',''))
        iname = nz(row.get('item_name',''))
        size  = nz(row.get('size',''))
        div   = nz(row.get('division',''))
        sec   = nz(row.get('section',''))
        dept  = nz(row.get('department',''))
        node  = nz(row.get('node',''))
        size_norm = re.sub(r'^(?:UK|EU)\s*','', size, flags=re.IGNORECASE).strip()
        rows_meta.append({
            'style_key': get_style_key(row, nobero_overrides),
            'base':      make_style_id_base(brand, aid, van, iname),
            'brand':     brand,
            'size_tuple': (div, sec, dept, node, size_norm),
        })

    if progress: progress.progress(0.25)

    live_update(0.30, "Step 2/4 — looking up existing style IDs…", 0, 0)
    all_keys = list({m['style_key'] for m in rows_meta})
    key_to_sid = batch_lookup_style_keys(all_keys, conn)
    live_update(0.45, "Step 2/4 — done.", 0, 0)

    live_update(0.50, "Step 3/4 — looking up key sizes…", 0, 0)
    all_size_tuples = list({m['size_tuple'] for m in rows_meta})
    size_map = batch_lookup_key_sizes(all_size_tuples, conn)
    live_update(0.60, "Step 3/4 — done.", 0, 0)

    live_update(0.62, "Step 4/4 — generating new style IDs…", 0, 0)
    new_keys  = {m['style_key'] for m in rows_meta if m['style_key'] not in key_to_sid}
    new_bases = {m['base'] for m in rows_meta if m['style_key'] in new_keys}
    base_max  = fetch_existing_bases(new_bases, conn) if new_bases else {}

    base_next   = {b: base_max.get(b, 0) + 1 for b in new_bases}
    new_inserts = []
    new_so_far  = 0

    for i, m in enumerate(rows_meta):
        sk = m['style_key']
        if sk not in key_to_sid:
            base = m['base']
            seq  = base_next[base]
            base_next[base] += 1
            sid = base + str(seq).zfill(2)
            key_to_sid[sk] = sid
            new_inserts.append((sk, sid, m['brand']))
            new_so_far += 1
        if i % 50 == 0 or i == len(rows_meta) - 1:
            pct = 0.62 + 0.28 * (i + 1) / len(rows_meta)
            live_update(pct, "Step 4/4 — assigning style IDs…", i + 1, new_so_far)

    batch_insert_styles(new_inserts, conn)
    if progress: progress.progress(0.90)

    style_ids = [key_to_sid[m['style_key']] for m in rows_meta]
    key_sizes = [size_map.get(m['size_tuple'], '') for m in rows_meta]

    df = df.copy()
    df['style_group_id'] = style_ids
    df['key_size']       = key_sizes

    new_keys_inserted = {r[0] for r in new_inserts}
    generated = len(new_keys_inserted)
    matched   = sum(1 for m in rows_meta if m['style_key'] not in new_keys_inserted)

    if progress: progress.progress(1.0)
    return df, matched, generated

# ─────────────────────────────────────────────────────────────────────────────
# FLAGGING
# ─────────────────────────────────────────────────────────────────────────────

VAN_IS_SIZE_BRANDS = {'Ludic'}
SOURCE_DATA_BRANDS = {'Averie'}
AID_KEYED_BRANDS   = {'House Of Kari', 'House of Koala'}
DUAL_VAN_BRANDS    = {'Instinct First', 'Instinct first'}

def flag_over10(df):
    bc = df.groupby('style_group_id')['bar_code'].count()
    over10 = bc[bc > 10].sort_values(ascending=False)
    rows = []
    for sid, cnt in over10.items():
        grp   = df[df['style_group_id'] == sid]
        brand = grp['brand_name'].iloc[0]
        nodes = sorted(set(nz(n) for n in grp['node'].dropna().unique()))
        sizes = sorted(set(nz(s) for s in grp['size'].dropna().unique()))
        n_node = len(nodes)

        if brand in AID_KEYED_BRANDS:
            import unicodedata as _ud
            def _strip_aid(aid, size):
                t = str(aid).strip(); sz = str(size).strip()
                m = re.sub(re.escape('_'+sz)+r'$','',t,flags=re.IGNORECASE)
                return m.rstrip('_').strip() if m!=t else t
            aid_keys = set(_strip_aid(a,s) for a,s in zip(grp['vendor_article_id'], grp['size']))
            n_designs = len(aid_keys)
            flag = 'GENUINE' if n_designs==1 else 'WRONG'
            reason = (f'1 design (AID: {next(iter(aid_keys))}), {len(sizes)} sizes'
                      if n_designs==1 else f'{n_designs} distinct AIDs after strip')
            vans = sorted(set(clean(v) for v in grp['vendor_article_name'].dropna().unique()))
            rows.append({'style_group_id':sid,'brand':brand,'barcodes':cnt,
                         'unique_vans':len(vans),'flag':flag,'reason':reason,
                         'van_sample':' | '.join(v[:40] for v in vans[:3]),
                         'sizes':','.join(sizes[:12])})
            continue

        if brand in DUAL_VAN_BRANDS:
            inn_keys = set()
            for iname in grp['item_name'].dropna().unique():
                parts = str(iname).split('-')
                design = parts[4].strip() if len(parts)>=5 else ''
                color  = parts[5].strip() if len(parts)>=6 else ''
                inn_keys.add(f'{design}-{color}')
            flag = 'GENUINE' if len(inn_keys)==1 else 'WRONG'
            reason = (f'1 design+color key, {len(sizes)} sizes'
                      if len(inn_keys)==1 else f'{len(inn_keys)} distinct design-color keys')
            vans = sorted(set(clean(v) for v in grp['vendor_article_name'].dropna().unique()))
            rows.append({'style_group_id':sid,'brand':brand,'barcodes':cnt,
                         'unique_vans':len(vans),'flag':flag,'reason':reason,
                         'van_sample':' | '.join(v[:40] for v in vans[:3]),
                         'sizes':','.join(sizes[:12])})
            continue

        vans  = sorted(set(clean(v) for v in grp['vendor_article_name'].dropna().unique()))
        n_van = len(vans)

        if n_node > 1:
            flag='WRONG';   reason=f'Multiple nodes: {", ".join(nodes)}'
        elif brand in VAN_IS_SIZE_BRANDS:
            flag='GENUINE'; reason=f'VAN encodes shoe size — {n_van} sizes'
        elif brand in SOURCE_DATA_BRANDS:
            flag='DATA ISSUE'; reason='VAN encodes size/collection — source data problem'
        elif n_van == 1:
            flag = 'GENUINE' if cnt<=20 else 'DATA ISSUE'
            reason = f'1 VAN, {len(sizes)} sizes' if cnt<=20 else f'1 VAN, {cnt} barcodes — duplicates'
        else:
            def clearly_diff(vlist):
                cl = [re.sub(r'\b(size|xs|s\b|m\b|l\b|xl|2xl|3xl|each|box|packet|set)\b','',v,flags=re.I).strip() for v in vlist]
                for i in range(len(cl)):
                    for j in range(i+1,len(cl)):
                        a,b = cl[i],cl[j]
                        if a in b or b in a: return False
                        wa,wb = set(a.split()),set(b.split())
                        if wa and wb and len(wa&wb)/max(len(wa),len(wb))>0.6: return False
                return True
            if clearly_diff(vans[:4]):
                flag='WRONG';  reason=f'{n_van} distinct VANs'
            else:
                flag='MANUAL'; reason=f'{n_van} VANs — may be variants/typos'

        rows.append({'style_group_id':sid,'brand':brand,'barcodes':cnt,
                     'unique_vans':n_van,'flag':flag,'reason':reason,
                     'van_sample':' | '.join(v[:40] for v in vans[:4]),
                     'sizes':','.join(sizes[:12])})
    return pd.DataFrame(rows)

# ─────────────────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────────────────

st.title("🏷️ Style ID Mapper")
st.caption("Upload a barcode CSV → Style IDs and Key Sizes mapped in seconds.")

try:
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("SELECT COUNT(DISTINCT style_group_id) FROM style_map")
    ts = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT brand_name) FROM style_map")
    tb = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM key_size_map")
    tk = cur.fetchone()[0]
    cur.close()
    c1,c2,c3 = st.columns(3)
    c1.metric("Style IDs in DB", f"{ts:,}")
    c2.metric("Brands in DB",    f"{tb:,}")
    c3.metric("Key size rules",  f"{tk:,}")
except Exception as e:
    st.warning(f"DB connection issue: {e}")

st.divider()

uploaded = st.file_uploader("Drop your CSV here", type=["csv"])

if uploaded:
    try:
        df_raw = pd.read_csv(uploaded)
        df_raw.columns = [c.strip() for c in df_raw.columns]

        EXPECTED_COLS_12 = ['item_code','vendor_article_id','vendor_article_name','vendor_article_name2',
                            'division','section','department','brand_name','node','item_name','size']
        EXPECTED_COLS_STD = ['item_code','bar_code','vendor_article_id','vendor_article_name',
                             'division','section','department','brand_name','node','item_name','size']
        if 'brand_name' not in df_raw.columns and len(df_raw.columns) >= 11:
            uploaded.seek(0)
            df_raw = pd.read_csv(uploaded, header=None)
            if len(df_raw.columns) == 11:
                df_raw.columns = EXPECTED_COLS_12
                df_raw['bar_code'] = df_raw['item_code']
            else:
                df_raw.columns = EXPECTED_COLS_STD[:len(df_raw.columns)]
            st.info("ℹ️ No header row detected — column names assigned automatically.")
        n_rows   = len(df_raw)
        n_brands = df_raw['brand_name'].nunique() if 'brand_name' in df_raw.columns else '?'
        st.write(f"**{n_rows:,} rows** · **{n_brands} brands** detected")

        if 'brand_name' in df_raw.columns:
            def _looks_corrupted(b):
                # Heuristic: a brand name mixing CJK/Hangul/other unrelated-script
                # characters with ordinary Latin text is a strong signal of mojibake
                # (e.g. a UTF-8 "Ö" mis-decoded through the wrong codepage and
                # re-encoded, landing as an unrelated CJK ideograph). A brand that's
                # ALL CJK could be legitimate, so only flag mixed-script names.
                s = str(b)
                has_cjk = any('\u4e00' <= ch <= '\u9fff' or '\u3040' <= ch <= '\u30ff'
                              or '\uac00' <= ch <= '\ud7a3' for ch in s)
                has_latin = any(ch.isascii() and ch.isalpha() for ch in s)
                return has_cjk and has_latin
            suspicious = sorted(set(
                b for b in df_raw['brand_name'].dropna().unique() if _looks_corrupted(b)))
            if suspicious:
                st.warning(
                    "⚠️ Possible encoding corruption in brand_name — these values mix "
                    "CJK/other-script characters with Latin text, which usually means a "
                    "non-ASCII character (e.g. 'Ö', 'ï') got double-encoded/mis-decoded "
                    "somewhere in the export pipeline before reaching this app. Rows with "
                    "these brand names will silently fall back to the generic key logic "
                    "and likely produce WRONG groupings until the source encoding is fixed: "
                    + ', '.join(repr(b) for b in suspicious))

        with st.expander("Preview (first 5 rows)"):
            st.dataframe(df_raw.head(5), use_container_width=True)

        if st.button("▶ Map Style IDs", type="primary"):
            progress = st.progress(0.0)
            status   = st.empty()
            live     = st.empty()

            conn    = get_db()
            result, matched, generated = map_dataframe(df_raw, conn, progress, status, live)
            status.empty()
            live.empty()

            st.success("✅ Mapping complete!")

            bc = result.groupby('style_group_id')['bar_code'].count()
            m1,m2,m3,m4,m5,m6 = st.columns(6)
            m1.metric("Total rows",        f"{len(result):,}")
            m2.metric("Matched from DB",   f"{matched:,}")
            m3.metric("New IDs generated", f"{generated:,}")
            m4.metric("Unique style IDs",  f"{result['style_group_id'].nunique():,}")
            m5.metric("Styles >10 bc",     int((bc>10).sum()))
            m6.metric("Median barcodes",   int(bc.median()))

            flag_df = flag_over10(result)
            if len(flag_df):
                st.subheader(f"Styles with >10 barcodes — {len(flag_df)} flagged")
                ICONS = {'GENUINE':'🟢','DATA ISSUE':'🟡','WRONG':'🔴','MANUAL':'🔵'}
                counts = flag_df['flag'].value_counts()
                cc1,cc2,cc3,cc4 = st.columns(4)
                cc1.metric("🟢 Genuine",    counts.get('GENUINE',0))
                cc2.metric("🟡 Data issue", counts.get('DATA ISSUE',0))
                cc3.metric("🔴 Wrong",      counts.get('WRONG',0))
                cc4.metric("🔵 Manual",     counts.get('MANUAL',0))

                f1,f2 = st.columns([1,3])
                ff = f1.selectbox("Filter flag",  ['All']+list(ICONS.keys()))
                bf = f2.selectbox("Filter brand", ['All']+sorted(flag_df['brand'].unique().tolist()))
                view = flag_df.copy()
                if ff != 'All': view = view[view['flag']==ff]
                if bf != 'All': view = view[view['brand']==bf]
                view[''] = view['flag'].map(ICONS)
                st.dataframe(view[['','brand','style_group_id','barcodes',
                                   'unique_vans','reason','van_sample']].rename(
                    columns={'brand':'Brand','style_group_id':'Style ID',
                             'barcodes':'BCs','unique_vans':'VANs',
                             'reason':'Reason','van_sample':'VAN sample'}),
                    use_container_width=True, hide_index=True)

            st.divider()
            st.subheader("Result preview")
            disp = [c for c in ['bar_code','brand_name','vendor_article_id',
                                 'vendor_article_name','item_name','size',
                                 'style_group_id','key_size'] if c in result.columns]
            st.dataframe(result[disp].head(100), use_container_width=True)

            d1,d2 = st.columns(2)
            buf = io.StringIO(); result.to_csv(buf, index=False)
            d1.download_button("⬇ Download mapped CSV", buf.getvalue(),
                               "mapped_output.csv", "text/csv")
            if len(flag_df):
                buf2 = io.StringIO(); flag_df.to_csv(buf2, index=False)
                d2.download_button("⬇ Download flag report", buf2.getvalue(),
                                   "flagged_over10.csv", "text/csv")

    except Exception as e:
        st.error(f"Error: {e}")
        import traceback; st.code(traceback.format_exc())

st.divider()
with st.expander("📋 Brand → Key field reference"):
    brand_ref = pd.DataFrame(
        [{'Brand':b,'Key':k.upper(),
          'Logic':{'inn':'item_name (strip last -size)','van':'vendor_article_name (strip size)',
                   'aid':'vendor_article_id (strip size)'}[k]}
         for b,k in sorted(FINAL_KEY.items())]
        + [{'Brand':'VALKYRE','Key':'VALKYRE',
            'Logic':'design from VAN + color from AID format'}])
    kt = st.selectbox("Filter", ['All','INN','VAN','AID','VALKYRE'])
    if kt != 'All': brand_ref = brand_ref[brand_ref['Key']==kt]
    st.dataframe(brand_ref, use_container_width=True, hide_index=True)
