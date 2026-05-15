import streamlit as st
import pandas as pd
import psycopg2
import re
import unicodedata
import io
import os

st.set_page_config(page_title="Style ID Mapper", page_icon="🏷️", layout="wide")

# ─────────────────────────────────────────────────────────────────────────────
# BRAND → KEY FIELD MAPPING  (data-driven from 1.3L reference)
# ─────────────────────────────────────────────────────────────────────────────

FINAL_KEY = {
    # INN  — use item_name, strip last -size segment
    '7-10':'inn','AADVEKA':'inn','ACK':'inn','ANNY':'inn','ARKS':'inn',
    'Almost Gods':'inn','Anaar':'inn','Aroop India':'inn','Averie':'inn',
    'BAD LIES':'inn','BADFIT':'inn','BARE BROWN':'inn','Bear House':'inn',
    'Bewakoof':'inn','Bombay Troopers':'inn','Bummer':'inn',
    'CARRIALL':'inn','CHK':'inn','CLOUT JEANS':'inn','CULTURE':'inn',
    'Capsul':'inn','DEEBACO':'inn','DREAM ISLAND':'inn',
    'DaMENSCH':'inn','Daily Life Forever52':'inn','De Novoo':'inn',
    'Esthreall':'inn','Exhale Label':'inn','FLAWS':'inn','Fitkin':'inn',
    'Freyja':'inn','Fuaark':'inn','Gully Labs':'inn','HEEL YOUR SOLE':'inn',
    'Hamptons':'inn','House Of Mae':'inn','Huemn':'inn',
    'Instinct First':'inn','Instinct first':'inn','JulietIsDead':'inn',
    'Kingdom of White':'inn','Label Ishnya':'inn','Life & Jam':'inn',
    'MAGRE':'inn','MANACA':'inn','Masha':'inn','Misnomer':'inn',
    'Mokobara':'inn','Nasher Miles':'inn','Nobero':'inn','Nona':'inn',
    'Nude Streetwear':'inn','OFFMINT':'inn','Outerworld':'inn',
    'PAZZION':'inn','PINQ POLKA':'inn','PawsnCollars':'inn','PrimalGray':'inn',
    'Qua':'inn','Qunic':'inn','RIPOFF':'inn','RWDY':'inn',
    'Rare Rabbit':'inn','Rareism':'inn','Rising Among':'inn','Roar For Good':'inn',
    'SIHANSH':'inn','STITCH STORIES':'inn','SUBTRACT':'inn','Stitchinc':'inn',
    'Style Island':'inn','Suta':'inn','Terminal Z':'inn','Terractive':'inn',
    'The Finicky Colorist':'inn','The Forbidden Fruit':'inn',
    'The Mitesh':'inn','Tinkle':'inn','Urban Jungle':'inn','Urbano Fashion':'inn',
    'VINDOF':'inn','Virgio':'inn','WAKE YOUR DREAM':'inn','WARPING THEORIES':'inn',
    'Western Era':'inn','WomanLikeU':'inn','Xaya':'inn','ZORI WORLD':'inn',
    'bare wear':'inn','hexafun':'inn','sorta':'inn',
    'ATBW':'inn','Aakar Taro':'inn','LVL99':'inn','Love Pangolin':'inn',
    # VAN  — use vendor_article_name, strip trailing size
    'ARISTOBRAT':'van','Aaina Sleepwear':'van','Aer':'van','Aldeno':'van',
    'Around The City':'van','BAWSE':'van','BLCKORCHID':'van','BOOZY BUTTON':'van',
    'Blissclub':'van','Bomaachi':'van','Broke Memers':'van','By The Bay':'van',
    'CAI':'van','Cava':'van','COMET':'van','Contemponari':'van',
    'Crazy Mosquitoes':'van','DULAAR':'van','Dash and Dot':'van','DenZ':'van',
    'Dhaaga':'van','DOG D ORIGINALS':'van','Dorabi':'van','EVERDION':'van',
    'Ewoke':'van','FLYAF':'van','FUR JADEN':'van','FYVA':'van',
    'Fearless Under Everything':'van','Femmella':'van',
    'Freakins':'van','GOTHIC TOONS':'van','Genes Lecoanet Hemant':'van',
    'House of Fett':'van','IWE STUDIOS':'van','Imperfecto':'van',
    'Invogue':'van','KIU':'van','Kairo':'van','Kickers':'van',
    'LALAFLOWER':'van','Lovicide':'van','Ludic':'van',
    'MODAU':'van','MOKY':'van','Modern Crew':'van','Nap Story':'van',
    'NautiNati':'van','No Nazar':'van','Notch Above':'van','OZiva':'van',
    'PAST MODERN':'van','PRDGY':'van','Poppi':'van','Private Lives':'van',
    'PurplFrog':'van','QB - QUINTESSENTIAL BASICS':'van',
    'RATAN JAIPUR':'van','REDONRAW':'van','Rarez':'van','Replyall':'van',
    'SKO':'van','SLEEPLOVE':'van','STRANGE':'van','Shop Mauve':'van',
    'StyleAsh':'van','Sugga':'van','Sullitt':'van','TENHEM':'van',
    'THE PONY & PEONY CO.':'van','TONI ROSSI':'van','TURMS':'van',
    'Tailor&Circus':'van','Tao Paris':'van','The Clothing Factory':'van',
    'The Khwaab':'van','The Label Life':'van','The Original Knit':'van',
    'The Pant Project':'van','The Souled Store':'van','Theater':'van',
    'Thr3letter':'van','Trendy Affair':'van','TrueBrowns':'van',
    'Tura Turi':'van','Twelve Thirty One':'van','Un Denim':'van',
    'Uptownie':'van','WOOMN':'van','Younglings':'van','Zeesh':'van',
    'Zumee':'van','teeside':'van',
    '63 East':'van','Auburban':'van','Khushbu Rathod Label':'van',
    'Natty Garb':'van',
    # AID  — use vendor_article_id, strip trailing size
    'A Toddler Thing':'aid','ARISTA VAULT':'aid','BILABA':'aid',
    'Bird Eye':'aid','Bluer':'aid','Ceya':'aid','Chapter 2':'aid',
    'COLOR CAPITAL':'aid','Duchess Kumari':'aid','ECHO STUDIO':'aid',
    'EUME':'aid','Echolope':'aid','FEIER':'aid','Farda':'aid',
    'GINNA':'aid','House Of Kari':'aid','House of Koala':'aid','Hunnit':'aid',
    'KHAAKI':'aid','Lea Clothing':'aid','Lino Perros':'aid',
    'MAIN CHARACTER':'aid','Muvazo':'aid','NeceSera':'aid','Nishorama':'aid',
    'Ombrello':'aid','Oroh':'aid','PastModern':'aid',
    'Rare Ones':'aid','SEEAASH':'aid','Saanjh by Lea':'aid',
    'Sew and You':'aid','Shibui':'aid','STUDIO MODA INDIA':'aid',
    'Suqah':'aid','TRUE WEST':'aid','The White Pole':'aid',
    'Torqadorn':'aid','Vellure':'aid','neopalms':'aid',
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
# HELPERS
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
    if su == '2XL':
        variants |= {'XXL', '2XL'}
    if su == 'XXL':
        variants |= {'2XL', 'XXL'}
    if su == '3XL':
        variants |= {'XXXL', '3XL'}
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
    aid   = nz(aid)
    iname = nz(iname)
    parts = iname.split('-')
    if aid.startswith('VJAC-'):
        m = re.match(r'VJAC-[^-]+-([A-Z]+)_', aid)
        if m:
            return m.group(1).upper()
        c = parts[-2].strip() if len(parts) >= 3 else ''
        if c and not SEASON_PAT.match(c.strip()) and c.upper() not in ('NA', 'N/A', ''):
            return re.sub(r'\s+', '', c).upper()[:8]
        return 'BLK'
    if aid.startswith('VALK-'):
        return 'BLK'
    if len(parts) >= 4:
        c3 = parts[-3].strip()
        if c3 and not SEASON_PAT.match(c3.strip()) and c3.upper() not in ('NA', 'N/A', ''):
            return re.sub(r'\s+', '', c3).upper()[:10]
    c2 = parts[-2].strip() if len(parts) >= 3 else ''
    return re.sub(r'\s+', '', c2).upper()[:8] if c2 and c2.upper() not in ('NA', 'N/A', '') else 'NA'

# ─────────────────────────────────────────────────────────────────────────────
# CORE KEY FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def get_style_key(row):
    brand    = nz(row.get('brand_name', ''))
    aid      = nz(row.get('vendor_article_id', ''))
    van      = nz(row.get('vendor_article_name', ''))
    iname    = nz(row.get('item_name', ''))
    size     = nz(row.get('size', ''))
    node     = clean(nz(row.get('node', '')))
    division = clean(nz(row.get('division', '')))
    section  = clean(nz(row.get('section', '')))
    dept     = clean(nz(row.get('department', '')))
    cat_key  = f'{division}|{section}|{dept}|{node}'

    # VALKYRE: special multi-format logic
    if brand == 'VALKYRE':
        design = valkyre_normalize_design(van)
        color  = valkyre_color(aid, iname)
        return clean(brand) + '||' + design + '||' + color + '||' + cat_key

    kt = FINAL_KEY.get(brand, 'inn')

    if kt == 'aid':
        if brand == 'Hunnit':
            v2 = re.sub(r'_[^_]+$', '', aid).strip()
            val = v2 if v2 != aid else strip_size(aid, size)
        elif brand == 'NeceSera':
            v2 = re.sub(r'_[^_]+$', '', aid).strip()
            val = v2 if v2 != aid else strip_size(aid, size)
        elif brand == 'Farda':
            v2 = re.sub(r'[A-Z]$', '', aid).strip()
            val = v2 if v2 != aid else strip_size(aid, size)
        elif brand == 'Bird Eye':
            p = aid.split('-')
            val = '-'.join(p[:2]).strip() if len(p) >= 2 else strip_size(aid, size)
        else:
            val = strip_size(aid, size)

    elif kt == 'van':
        if brand == 'Theater':
            v = strip_size(van, size) if van else ''
            val = re.sub(r'\s+\d{1,2}$', '', v).strip() if v else strip_size(aid, size)
        elif brand == 'Ludic':
            v = nz(van)
            val = re.sub(r'\s+(MEN\s+|WOMEN\s+)?\d{1,3}$', '', v, flags=re.IGNORECASE).strip()
            val = val if val else v
        else:
            val = strip_size(van, size) if van else strip_size(aid, size)
    else:  # inn
        val = inn_key(iname)

    return clean(brand) + '||' + clean(val) + '||' + cat_key

# ─────────────────────────────────────────────────────────────────────────────
# STYLE ID GENERATION (brand-aware label)
# ─────────────────────────────────────────────────────────────────────────────

def make_style_id_label(brand, aid, van, iname, size):
    prefix = brand_prefix(brand)
    # Design label
    if van and not pd.isna(van):
        design_raw = nz(van)
    else:
        parts = nz(iname).split('-')
        design_raw = parts[4].strip() if len(parts) >= 5 else nz(aid)
    # Color label
    parts = nz(iname).split('-')
    color_raw = parts[-2].strip() if len(parts) >= 3 else (nz(van) or nz(aid))
    dc = sanitize(design_raw, 15)
    cc = sanitize(color_raw, 12)
    return f'BW_{prefix}_{dc}_{cc}_'

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_resource
def get_db():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        st.error("DATABASE_URL not set.")
        st.stop()
    return psycopg2.connect(db_url)

def lookup_style(style_key, conn):
    cur = conn.cursor()
    cur.execute("SELECT style_group_id FROM style_map WHERE style_key=%s", (style_key,))
    r = cur.fetchone()
    cur.close()
    return r[0] if r else None

def lookup_key_size(division, section, department, node, size, conn):
    size_norm = re.sub(r'^(?:UK|EU)\s*', '', nz(size), flags=re.IGNORECASE).strip()
    cur = conn.cursor()
    cur.execute(
        """SELECT key_size FROM key_size_map
           WHERE division=%s AND section=%s AND department=%s AND node=%s AND size=%s""",
        (nz(division), nz(section), nz(department), nz(node), size_norm))
    r = cur.fetchone()
    cur.close()
    if r is None:
        return ''
    return '' if r[0] is None else int(r[0])

def insert_style(style_key, style_id, brand, conn):
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO style_map (style_key, style_group_id, brand_name, source)
           VALUES (%s,%s,%s,'generated') ON CONFLICT (style_key) DO NOTHING""",
        (style_key, style_id, brand))
    conn.commit()
    cur.close()

def get_existing_ids_for_base(base, conn):
    cur = conn.cursor()
    cur.execute("SELECT style_group_id FROM style_map WHERE style_group_id LIKE %s", (base + '%',))
    rows = cur.fetchall()
    cur.close()
    return [r[0] for r in rows]

# ─────────────────────────────────────────────────────────────────────────────
# MAIN MAPPING FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def map_dataframe(df, conn, progress_bar=None, status_text=None):
    style_ids  = []
    key_sizes  = []
    new_cache  = {}   # style_key → style_id (within this session)
    base_cache = {}   # base_label → next_seq (to avoid DB calls per row)
    matched = generated = 0
    total = len(df)

    for i, (_, row) in enumerate(df.iterrows()):
        if progress_bar is not None:
            progress_bar.progress((i + 1) / total)
        if status_text is not None and i % 100 == 0:
            status_text.text(f"Processing row {i+1:,} of {total:,}…")

        brand = nz(row.get('brand_name', ''))
        aid   = nz(row.get('vendor_article_id', ''))
        van   = nz(row.get('vendor_article_name', ''))
        iname = nz(row.get('item_name', ''))
        size  = nz(row.get('size', ''))
        div   = nz(row.get('division', ''))
        sec   = nz(row.get('section', ''))
        dept  = nz(row.get('department', ''))
        node  = nz(row.get('node', ''))

        style_key = get_style_key(row)

        # 1 — check session cache
        if style_key in new_cache:
            sid = new_cache[style_key]
            matched += 1
        else:
            # 2 — check DB
            sid = lookup_style(style_key, conn)
            if sid:
                matched += 1
                new_cache[style_key] = sid
            else:
                # 3 — generate new
                base = make_style_id_label(brand, aid, van, iname, size)
                if base not in base_cache:
                    existing = get_existing_ids_for_base(base, conn)
                    nums = [int(m.group(1)) for s in existing
                            for m in [re.search(r'_(\d+)$', s)] if m]
                    base_cache[base] = (max(nums) + 1) if nums else 1
                seq = base_cache[base]
                base_cache[base] += 1
                sid = base + str(seq).zfill(2)
                insert_style(style_key, sid, brand, conn)
                new_cache[style_key] = sid
                generated += 1

        style_ids.append(sid)
        key_sizes.append(lookup_key_size(div, sec, dept, node, size, conn))

    df = df.copy()
    df['style_group_id'] = style_ids
    df['key_size']       = key_sizes
    return df, matched, generated

# ─────────────────────────────────────────────────────────────────────────────
# FLAGGING (thumb rule: >10 barcodes)
# ─────────────────────────────────────────────────────────────────────────────

VAN_IS_SIZE_BRANDS = {'Ludic'}
SOURCE_DATA_BRANDS = {'Averie', 'Blissclub'}

def flag_over10(df):
    bc = df.groupby('style_group_id')['bar_code'].count()
    over10 = bc[bc > 10].sort_values(ascending=False)
    rows = []
    for sid, cnt in over10.items():
        grp   = df[df['style_group_id'] == sid]
        brand = grp['brand_name'].iloc[0]
        vans  = sorted(set(clean(v) for v in grp['vendor_article_name'].dropna().unique()))
        nodes = sorted(set(nz(n) for n in grp['node'].dropna().unique()))
        sizes = sorted(set(nz(s) for s in grp['size'].dropna().unique()))
        n_van = len(vans); n_node = len(nodes)
        van_sample = ' | '.join(v[:40] for v in vans[:4])

        if n_node > 1:
            flag = 'WRONG'; reason = f'Multiple nodes: {", ".join(nodes)}'
        elif brand in VAN_IS_SIZE_BRANDS:
            flag = 'GENUINE'; reason = f'VAN encodes shoe size — {n_van} sizes'
        elif brand in SOURCE_DATA_BRANDS:
            flag = 'DATA ISSUE'; reason = 'VAN encodes size/collection — source data problem'
        elif n_van == 1:
            if cnt <= 20:
                flag = 'GENUINE'; reason = f'1 VAN, {len(sizes)} sizes'
            else:
                flag = 'DATA ISSUE'; reason = f'1 VAN but {cnt} barcodes — duplicate data'
        else:
            def clearly_different(vlist):
                cleaned = []
                for v in vlist:
                    v2 = re.sub(r'\b(size|xs|s\b|m\b|l\b|xl|2xl|3xl|each|box|packet|set)\b', '', v, flags=re.I)
                    cleaned.append(re.sub(r'\s+', ' ', v2).strip())
                for i in range(len(cleaned)):
                    for j in range(i + 1, len(cleaned)):
                        a, b = cleaned[i], cleaned[j]
                        if a in b or b in a:
                            return False
                        wa = set(a.split()); wb = set(b.split())
                        if wa and wb and len(wa & wb) / max(len(wa), len(wb)) > 0.6:
                            return False
                return True

            if clearly_different(vans[:4]):
                flag = 'WRONG'; reason = f'{n_van} distinct VANs'
            else:
                flag = 'MANUAL'; reason = f'{n_van} VANs — may be variants/typos, needs human review'

        rows.append({
            'style_group_id': sid, 'brand': brand, 'barcodes': cnt,
            'unique_vans': n_van, 'flag': flag,
            'reason': reason, 'van_sample': van_sample,
            'sizes': ', '.join(sizes[:12]),
        })
    return pd.DataFrame(rows)

# ─────────────────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────────────────

st.title("🏷️ Style ID Mapper")
st.caption("Upload a barcode CSV → get Style IDs and Key Sizes mapped using brand-specific key logic.")

# DB stats
try:
    conn = get_db()
    cur  = conn.cursor()
    cur.execute("SELECT COUNT(DISTINCT style_group_id) FROM style_map")
    total_styles = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT brand_name) FROM style_map")
    total_brands = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM key_size_map")
    total_ks = cur.fetchone()[0]
    cur.close()
    c1, c2, c3 = st.columns(3)
    c1.metric("Style IDs in DB",   f"{total_styles:,}")
    c2.metric("Brands in DB",      f"{total_brands:,}")
    c3.metric("Key size rules",    f"{total_ks:,}")
except Exception as e:
    st.warning(f"DB connection issue: {e}")

st.divider()

# ── Upload ──
uploaded = st.file_uploader("Drop your CSV here", type=["csv"])

if uploaded:
    try:
        df_raw = pd.read_csv(uploaded)
        df_raw.columns = [c.strip() for c in df_raw.columns]
        n_rows   = len(df_raw)
        n_brands = df_raw['brand_name'].nunique() if 'brand_name' in df_raw.columns else '?'
        st.write(f"**{n_rows:,} rows** · **{n_brands} brands** detected")

        with st.expander("Preview (first 5 rows)"):
            st.dataframe(df_raw.head(5), use_container_width=True)

        if st.button("▶ Map Style IDs", type="primary"):
            progress_bar = st.progress(0)
            status_text  = st.empty()

            conn = get_db()
            result, matched, generated = map_dataframe(
                df_raw, conn, progress_bar, status_text)
            progress_bar.progress(1.0)
            status_text.empty()

            st.success(
                f"Done! **{matched:,}** matched from DB · "
                f"**{generated:,}** new Style IDs generated · "
                f"**{result['style_group_id'].nunique():,}** unique style IDs total")

            # ── Thumb-rule check ──
            bc = result.groupby('style_group_id')['bar_code'].count()
            st.divider()
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total style IDs",  result['style_group_id'].nunique())
            m2.metric("Median barcodes",  int(bc.median()))
            m3.metric("Styles >10 bc",    int((bc > 10).sum()))
            m4.metric("Styles >15 bc",    int((bc > 15).sum()))

            # ── Flag table ──
            flag_df = flag_over10(result)
            if len(flag_df):
                st.subheader(f"Styles with >10 barcodes — {len(flag_df)} flagged")
                FLAG_COLORS = {
                    'GENUINE':    '🟢',
                    'DATA ISSUE': '🟡',
                    'WRONG':      '🔴',
                    'MANUAL':     '🔵',
                }
                flag_df['icon'] = flag_df['flag'].map(FLAG_COLORS)
                counts = flag_df['flag'].value_counts()
                cc1, cc2, cc3, cc4 = st.columns(4)
                cc1.metric("🟢 Genuine",    counts.get('GENUINE', 0))
                cc2.metric("🟡 Data issue", counts.get('DATA ISSUE', 0))
                cc3.metric("🔴 Wrong",      counts.get('WRONG', 0))
                cc4.metric("🔵 Manual",     counts.get('MANUAL', 0))

                filter_col1, filter_col2 = st.columns([1, 3])
                flag_filter  = filter_col1.selectbox(
                    "Filter by flag", ['All'] + list(FLAG_COLORS.keys()))
                brand_filter = filter_col2.selectbox(
                    "Filter by brand", ['All'] + sorted(flag_df['brand'].unique().tolist()))

                view = flag_df.copy()
                if flag_filter != 'All':
                    view = view[view['flag'] == flag_filter]
                if brand_filter != 'All':
                    view = view[view['brand'] == brand_filter]

                st.dataframe(
                    view[['icon', 'brand', 'style_group_id', 'barcodes',
                           'unique_vans', 'reason', 'van_sample']].rename(
                        columns={'icon': '', 'brand': 'Brand',
                                 'style_group_id': 'Style ID', 'barcodes': 'BCs',
                                 'unique_vans': 'VANs', 'reason': 'Reason',
                                 'van_sample': 'VAN sample'}),
                    use_container_width=True, hide_index=True)

            # ── Full result preview ──
            st.divider()
            st.subheader("Result preview")
            display_cols = ['bar_code', 'brand_name', 'vendor_article_id',
                            'vendor_article_name', 'item_name', 'size',
                            'style_group_id', 'key_size']
            display_cols = [c for c in display_cols if c in result.columns]
            st.dataframe(result[display_cols].head(100), use_container_width=True)

            # ── Downloads ──
            dl1, dl2 = st.columns(2)
            buf = io.StringIO()
            result.to_csv(buf, index=False)
            dl1.download_button(
                "⬇ Download mapped CSV",
                data=buf.getvalue(),
                file_name="mapped_output.csv",
                mime="text/csv")

            if len(flag_df):
                buf2 = io.StringIO()
                flag_df.drop(columns=['icon'], errors='ignore').to_csv(buf2, index=False)
                dl2.download_button(
                    "⬇ Download flag report",
                    data=buf2.getvalue(),
                    file_name="flagged_over10.csv",
                    mime="text/csv")

    except Exception as e:
        st.error(f"Error: {e}")
        import traceback
        st.code(traceback.format_exc())

# ── Brand key reference ──
st.divider()
with st.expander("📋 Brand → Key field reference"):
    brand_ref = pd.DataFrame([
        {'Brand': b, 'Key field': k.upper(),
         'Logic': {'inn': 'item_name (strip last -size segment)',
                   'van': 'vendor_article_name (strip trailing size)',
                   'aid': 'vendor_article_id (strip trailing size)'}[k]}
        for b, k in sorted(FINAL_KEY.items())
    ] + [{'Brand': 'VALKYRE', 'Key field': 'VALKYRE',
          'Logic': 'Special: design from VAN + color from AID format'}])
    kt_filter = st.selectbox("Filter by key type", ['All', 'INN', 'VAN', 'AID', 'VALKYRE'])
    if kt_filter != 'All':
        brand_ref = brand_ref[brand_ref['Key field'] == kt_filter]
    st.dataframe(brand_ref, use_container_width=True, hide_index=True)
