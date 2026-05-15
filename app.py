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
    'BAD LIES':'inn','BADFIT':'inn','BARE BROWN':'inn','Bear House':'inn',
    'Bewakoof':'inn',
    'Bombay Troopers':'inn','Bummer':'inn',
    'CARRIALL':'inn','CHK':'inn','CLOUT JEANS':'inn','CULTURE':'inn',
    'Capsul':'inn','DEEBACO':'inn','DREAM ISLAND':'inn',
    'DaMENSCH':'inn','Daily Life Forever52':'inn','De Novoo':'inn',
    'Esthreall':'inn','Exhale Label':'inn','FLAWS':'inn',
    'Gully Labs':'inn','HEEL YOUR SOLE':'inn',
    'Hamptons':'inn','House Of Mae':'inn','Huemn':'inn',
    'Instinct First':'van','Instinct first':'van','JulietIsDead':'inn',
    'Kingdom of White':'inn','Label Ishnya':'inn','Life & Jam':'inn',
    'MAGRE':'inn','MANACA':'inn','Masha':'inn','Misnomer':'inn',
    'Mokobara':'inn','Nasher Miles':'inn','Nobero':'inn','Nona':'inn',
    'No Nazar':'inn',          # VAN has size embedded; INN has design+color
    'Nude Streetwear':'inn','OFFMINT':'inn','Outerworld':'inn',
    'PAZZION':'inn','PINQ POLKA':'inn','PawsnCollars':'inn','PrimalGray':'inn',
    'Qua':'inn','Qunic':'inn','RIPOFF':'inn','RWDY':'inn',
    'Rare Rabbit':'inn','Rareism':'inn','Rising Among':'inn','Roar For Good':'inn',
    'SIHANSH':'inn','STITCH STORIES':'inn','SUBTRACT':'inn','Stitchinc':'inn',
    'Style Island':'inn',      # VAN has size; INN correctly groups same design
    'Suta':'inn','Terminal Z':'inn','Terractive':'inn',
    'The Finicky Colorist':'inn','The Forbidden Fruit':'aid',  # → see AID below
    'The Mitesh':'inn','Tinkle':'inn','Urban Jungle':'inn','Urbano Fashion':'inn',
    'VINDOF':'inn','Virgio':'van',  # VAN is the product code (VWWTO...)
    'WAKE YOUR DREAM':'inn','WARPING THEORIES':'inn',
    'Western Era':'inn','WomanLikeU':'inn','Xaya':'inn','ZORI WORLD':'inn',
    'bare wear':'inn','hexafun':'inn','sorta':'inn',
    'ATBW':'inn','Aakar Taro':'inn','LVL99':'inn','Love Pangolin':'inn',
    # ── VAN: use vendor_article_name, strip trailing size ─────────────────────
    '63 East':'van',           # VAN=design name; INN has collection not design
    'ARISTOBRAT':'van','Aaina Sleepwear':'van',
    'Aldeno':'van',
    'Almost Gods':'aid',       # → see AID (VAN has size; AID is numeric per barcode)
    'Aer':'van',
    'Auburban':'van',          # VAN = NOIR WOOL VEST / NOIR LUREX VEST (distinct designs)
    'Around The City':'van','BAWSE':'van','BLCKORCHID':'van','BOOZY BUTTON':'van',
    'Bomaachi':'van','Broke Memers':'van','By The Bay':'van',
    'CAI':'van','Cava':'van','COMET':'van',
    'Crazy Mosquitoes':'van','DULAAR':'van','Dash and Dot':'van','DenZ':'van',
    'Dorabi':'van','EVERDION':'van',
    'Ewoke':'van','FLYAF':'van','FUR JADEN':'van','FYVA':'van',
    'Fearless Under Everything':'van','Femmella':'van',
    'GOTHIC TOONS':'van','Genes Lecoanet Hemant':'van',
    'House of Fett':'van','IWE STUDIOS':'van','Imperfecto':'van',
    'Invogue':'van','KIU':'van','Kairo':'van','Kickers':'van',
    'LALAFLOWER':'van','Lovicide':'van','Ludic':'van',
    'MODAU':'van','MOKY':'van','Modern Crew':'van','Nap Story':'van',
    'NautiNati':'van','Notch Above':'van','OZiva':'aid',  # → see AID
    'PAST MODERN':'van','PRDGY':'van','Poppi':'van','Private Lives':'van',
    'PurplFrog':'van','QB - QUINTESSENTIAL BASICS':'van',
    'RATAN JAIPUR':'van','REDONRAW':'van','Rarez':'van',
    'SKO':'van','SLEEPLOVE':'van','STRANGE':'van','Shop Mauve':'van',
    'Sullitt':'van','TENHEM':'van',
    'THE PONY & PEONY CO.':'van','TURMS':'van',
    'Tailor&Circus':'van','Tao Paris':'van','The Clothing Factory':'van',
    'The Khwaab':'van','The Label Life':'van','The Original Knit':'van',
    'The Pant Project':'van','The Souled Store':'van','Theater':'van',
    'Thr3letter':'van','Trendy Affair':'van','TrueBrowns':'van',
    'Tura Turi':'van','Twelve Thirty One':'van','Un Denim':'van',
    'WOOMN':'van','Younglings':'van','Zeesh':'van','Zumee':'van','teeside':'van',
    'Auburban':'van','Khushbu Rathod Label':'van','Natty Garb':'van',
    # ── AID: use vendor_article_id, strip trailing size ───────────────────────
    'A Toddler Thing':'aid','ARISTA VAULT':'aid','BILABA':'aid',
    'Almost Gods':'aid',       # AID is numeric (53364), same per design, VAN has size
    'Bird Eye':'aid','Blissclub':'aid','Bluer':'aid','Ceya':'aid','Chapter 2':'aid',
    'COLOR CAPITAL':'aid',
    'Contemponari':'aid',
    'Duchess Kumari':'aid','ECHO STUDIO':'aid','EUME':'aid','Echolope':'aid',
    'FEIER':'aid','Farda':'aid',
    'The Forbidden Fruit':'aid',  # AID: californiaXL→california, watermelonteeXL→watermelontee
    'Dhaaga':'aid',
    'Fitkin':'aid',
    'Freakins':'aid',
    'Freyja':'aid',
    'Fuaark':'aid',            # AID FBKCSTSHT10=Brisk, FLCRNTSHT10=Legacy
    'GINNA':'aid','House Of Kari':'aid','House of Koala':'aid','Hunnit':'aid',
    'KHAAKI':'aid','Lea Clothing':'aid','Lino Perros':'aid',
    'MAIN CHARACTER':'aid','Muvazo':'aid','NeceSera':'aid','Nishorama':'aid',
    'OZiva':'aid',             # AID SAGE0106=Amalia, SAGE0160=Emily — unique per design
    'Ombrello':'aid','Oroh':'aid','PastModern':'aid',
    'Rare Ones':'aid','SEEAASH':'aid','Saanjh by Lea':'aid',
    'Replyall':'aid',
    'Sew and You':'aid','Shibui':'aid','STUDIO MODA INDIA':'aid',
    'StyleAsh':'aid',
    'Sugga':'aid',
    'Suqah':'aid','TRUE WEST':'aid','The White Pole':'aid',
    'Torqadorn':'aid',
    'Uptownie':'aid',
    'TONI ROSSI':'aid',        # AID encodes design+color: 8596119056660_Black (strip _EU\d+)
    'DOG D ORIGINALS':'aid',   # AID already has color: aki-laptop-backpack_Bottle Green
    'Vellure':'aid','neopalms':'aid',
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
# PURE-PYTHON KEY LOGIC  (no DB, runs on every row)
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
        for sep in [' - ', '-', '_', ' ', '']:
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

def get_style_key(row):
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
            # AID "11 DBHP - Beige 3" → strip trailing space+digit = "11 DBHP - Beige"
            val = re.sub(r'\s+\d+$', '', nz(aid)).strip()
        elif brand == 'Sugga':
            # AID Blue_Shirt-L / Blue_shirt-M → strip_size handles it; case-normalise
            val = strip_size(aid, size).lower()
        elif brand in ('Dhaaga', 'Freakins', 'Fitkin', 'Freyja',
                       'Replyall', 'Uptownie', 'Contemponari'):
            # Standard strip — AID encodes design+color, size is the suffix
            val = strip_size(aid, size)
        elif brand == 'Fuaark':
            # AID FBKCSTSHT10-M → strip -size → FBKCSTSHT10 (unique per design)
            val = strip_size(aid, size)
        elif brand == 'Almost Gods':
            # AID is numeric (53364) — same per design; VAN has size embedded
            val = nz(aid).split()[0].strip()  # take just the number, strip any suffix
        elif brand == 'The Forbidden Fruit':
            # AID: californiaXL → strip size letters → california
            val = SIZE_PAT.sub('', nz(aid)).strip().rstrip('-_ ')
        elif brand == 'OZiva':
            # AID: SAGE0106-XS → SAGE0106 (unique per design)
            val = strip_size(aid, size)
        elif brand == 'Blissclub':
            # Numeric AID: 4391001001002 — first 10 digits = design(7) + color(3)
            # Text AID: AirMelt Crop tee_Arya Airmelt Fig_L — strip trailing _SIZE
            a = nz(aid)
            if a.replace(' ','').replace('-','').isdigit() or (len(a)>=10 and a[:7].isdigit()):
                val = a[:10]
            else:
                val = strip_size(a, size)
        elif brand == 'TONI ROSSI':
            # AID: 8596119056660_Black_EU44 → strip _EU\d+ → 8596119056660_Black
            val = re.sub(r'_EU\d+$', '', nz(aid), flags=re.IGNORECASE).strip()
            val = val if val != nz(aid) else strip_size(nz(aid), size)
        elif brand == 'DOG D ORIGINALS':
            # AID already encodes design+color: aki-laptop-backpack_Bottle Green (no size)
            val = nz(aid)
        else:
            val = strip_size(aid, size)
    elif kt == 'van':
        if brand == 'Theater':
            v = strip_size(van,size) if van else ''
            val = re.sub(r'\s+\d{1,2}$','',v).strip() if v else strip_size(aid,size)
        elif brand == 'Ludic':
            v = nz(van)
            val = re.sub(r'\s+(MEN\s+|WOMEN\s+)?\d{1,3}$','',v,flags=re.IGNORECASE).strip() or v
        elif brand == 'Virgio':
            # VAN is the actual product code (VWWTO242600670124); use as-is
            val = nz(van) if van else strip_size(aid, size)
        else:
            val = strip_size(van,size) if van else strip_size(aid,size)
    else:  # inn
        if brand == 'Instinct First' or brand == 'Instinct first':
            # VAN = "Oversized Tshirt - Black - L" → strip size → "Oversized Tshirt - Black"
            # This naturally encodes product type + color, regardless of VAN2 alternating
            val = strip_size(van, size) if van else inn_key(iname)
        else:
            val = inn_key(iname)

    # SOL锟斤拷ITE and VYAM锟斤拷S: AID is the reliable key regardless of FINAL_KEY encoding
    if 'SOL' in brand.upper() and 'ITE' in brand.upper():
        val = strip_size(aid, size)
    elif 'VYAM' in brand.upper():
        # AID: CD/WOM/DEN/BLU - s → strip trailing " - size"
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
# DATABASE  — single persistent connection, batched queries
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_resource
def get_db():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        st.error("DATABASE_URL not set.")
        st.stop()
    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    return conn

def batch_lookup_style_keys(style_keys, conn):
    """Single query: fetch all matching style_keys at once."""
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
    """
    size_tuples: list of (division, section, department, node, size_norm)
    Returns dict keyed by tuple → key_size value.
    """
    if not size_tuples:
        return {}
    unique = list(set(size_tuples))
    # Build VALUES for unnest
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
    """
    Given a set of base prefixes, fetch all style_group_ids that start with any of them.
    Returns dict: base → max_seq (int).
    """
    if not bases:
        return {}
    # Use LIKE ANY with array — one query
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
    """Insert all new (style_key, style_id, brand) rows in one executemany."""
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
# MAIN MAPPING  — all DB work in 3 round-trips regardless of file size
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

    # ── Step 1: compute all style keys (pure Python, no DB) ──────────────────
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
            'style_key': get_style_key(row),
            'base':      make_style_id_base(brand, aid, van, iname),
            'brand':     brand,
            'size_tuple': (div, sec, dept, node, size_norm),
        })

    if progress: progress.progress(0.25)

    # ── Step 2: batch fetch all existing style keys (1 query) ────────────────
    live_update(0.30, "Step 2/4 — looking up existing style IDs…", 0, 0)
    all_keys = list({m['style_key'] for m in rows_meta})
    key_to_sid = batch_lookup_style_keys(all_keys, conn)
    live_update(0.45, "Step 2/4 — done.", 0, 0)

    # ── Step 3: batch fetch key sizes (1 query) ───────────────────────────────
    live_update(0.50, "Step 3/4 — looking up key sizes…", 0, 0)
    all_size_tuples = list({m['size_tuple'] for m in rows_meta})
    size_map = batch_lookup_key_sizes(all_size_tuples, conn)
    live_update(0.60, "Step 3/4 — done.", 0, 0)

    # ── Step 4: resolve new style IDs (1 query for base sequences) ───────────
    live_update(0.62, "Step 4/4 — generating new style IDs…", 0, 0)
    new_keys  = {m['style_key'] for m in rows_meta if m['style_key'] not in key_to_sid}
    new_bases = {m['base'] for m in rows_meta if m['style_key'] in new_keys}
    base_max  = fetch_existing_bases(new_bases, conn) if new_bases else {}

    # Assign new style IDs in memory — tick the live counter as we go
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
        # Update live counter every 50 rows
        if i % 50 == 0 or i == len(rows_meta) - 1:
            pct = 0.62 + 0.28 * (i + 1) / len(rows_meta)
            live_update(pct, "Step 4/4 — assigning style IDs…", i + 1, new_so_far)

    # ── Step 5: batch insert all new rows (1 query) ───────────────────────────
    batch_insert_styles(new_inserts, conn)
    if progress: progress.progress(0.90)

    # ── Assemble output ───────────────────────────────────────────────────────
    style_ids = [key_to_sid[m['style_key']] for m in rows_meta]
    key_sizes = [size_map.get(m['size_tuple'], '') for m in rows_meta]

    df = df.copy()
    df['style_group_id'] = style_ids
    df['key_size']       = key_sizes

    new_keys_inserted = {r[0] for r in new_inserts}   # style_keys that are brand new
    generated = len(new_keys_inserted)                 # unique new style IDs created
    matched   = sum(1 for m in rows_meta
                    if m['style_key'] not in new_keys_inserted)  # rows resolved from DB

    if progress: progress.progress(1.0)
    return df, matched, generated

# ─────────────────────────────────────────────────────────────────────────────
# FLAGGING
# ─────────────────────────────────────────────────────────────────────────────

VAN_IS_SIZE_BRANDS = {'Ludic'}
SOURCE_DATA_BRANDS = {'Averie'}
# Brands where VAN has unicode garbage variants of the same text — use AID count instead
AID_KEYED_BRANDS   = {'House Of Kari', 'House of Koala'}
# Brands where VAN alternates between design name and color word for same product
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

        # For AID-keyed brands, use stripped AID count instead of VAN
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

        # For dual-VAN brands, only flag if INN keys differ
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

        # Auto-detect headerless CSV
        EXPECTED_COLS_12 = ['item_code','vendor_article_id','vendor_article_name','vendor_article_name2',
                            'division','section','department','brand_name','node','item_name','size']
        EXPECTED_COLS_STD = ['item_code','bar_code','vendor_article_id','vendor_article_name',
                             'division','section','department','brand_name','node','item_name','size']
        if 'brand_name' not in df_raw.columns and len(df_raw.columns) >= 11:
            uploaded.seek(0)
            df_raw = pd.read_csv(uploaded, header=None)
            if len(df_raw.columns) == 11:
                # 11-col format: no bar_code, col[1]=AID, col[2]=VAN-description, col[3]=VAN
                df_raw.columns = EXPECTED_COLS_12
                # bar_code = item_code for these rows (no separate barcode column)
                df_raw['bar_code'] = df_raw['item_code']
            else:
                df_raw.columns = EXPECTED_COLS_STD[:len(df_raw.columns)]
            st.info("ℹ️ No header row detected — column names assigned automatically.")
        n_rows   = len(df_raw)
        n_brands = df_raw['brand_name'].nunique() if 'brand_name' in df_raw.columns else '?'
        st.write(f"**{n_rows:,} rows** · **{n_brands} brands** detected")

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
