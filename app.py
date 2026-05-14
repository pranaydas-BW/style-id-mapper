import streamlit as st
import pandas as pd
import psycopg2
import re
import unicodedata
import io
import os

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Style ID Mapper",
    page_icon="🏷️",
    layout="wide"
)

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE CONNECTION
# ─────────────────────────────────────────────────────────────────────────────

def get_db():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        st.error("DATABASE_URL not set. Please check your Streamlit secrets.")
        st.stop()
    conn = psycopg2.connect(db_url)
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS style_map (
            id              SERIAL PRIMARY KEY,
            style_key       TEXT    NOT NULL UNIQUE,
            style_group_id  TEXT    NOT NULL,
            brand_name      TEXT,
            color           TEXT,
            source          TEXT    DEFAULT 'reference'
        );
        CREATE INDEX IF NOT EXISTS idx_style_key   ON style_map(style_key);
        CREATE INDEX IF NOT EXISTS idx_style_group ON style_map(style_group_id);
        CREATE INDEX IF NOT EXISTS idx_brand       ON style_map(brand_name);
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS key_size_map (
            id          SERIAL PRIMARY KEY,
            division    TEXT,
            section     TEXT,
            department  TEXT,
            node        TEXT,
            size        TEXT,
            key_size    INTEGER,
            UNIQUE(division, section, department, node, size)
        );
    """)
    conn.commit()
    cur.close()
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# SIZE HANDLING
# ─────────────────────────────────────────────────────────────────────────────

def normalize_size(size_val):
    if pd.isna(size_val):
        return ''
    s = str(size_val).strip()
    s = re.sub(r'^(?:UK|EU)\s*', '', s, flags=re.IGNORECASE).strip()
    return s


def strip_size_from_article_id(article_id, size_val):
    aid = str(article_id).strip().rstrip('\n').replace('\\n', '').strip()
    size = normalize_size(size_val)
    if size:
        for sep in ['-', '_', ' ', '']:
            pattern = re.compile(re.escape(sep + size) + r'$', re.IGNORECASE)
            stripped = pattern.sub('', aid)
            if stripped != aid:
                return stripped.rstrip('-_ ').strip()
    size_pattern = re.compile(
        r'[-_\s]('
        r'x{0,4}s|x{0,3}l|xxl|xl|2xl|3xl|4xl|5xl|6xl|7xl|8xl'
        r'|\d{2}x\d{2}'
        r'|free\s*size?|one\s*size|onesize|freesize'
        r'|uk\s*\d+(?:\.\d+)?|eu\s*\d+(?:\.\d+)?'
        r'|(?:2[4-9]|[3-5]\d)'
        r')$',
        re.IGNORECASE
    )
    stripped = size_pattern.sub('', aid).strip()
    return stripped if stripped else aid


# ─────────────────────────────────────────────────────────────────────────────
# COLOR EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

COLOR_MAP = {
    'off white': 'OFFWHITE', 'off-white': 'OFFWHITE', 'optical white': 'WHITE',
    'rose gold': 'ROSEGOLD', 'powder blue': 'POWDERBLUE', 'sky blue': 'SKYBLUE',
    'baby blue': 'BABYBLUE', 'royal blue': 'ROYALBLUE', 'steel blue': 'STEELBLUE',
    'midnight blue': 'NAVY', 'navy blue': 'NAVY', 'denim blue': 'DENIMBLUE',
    'hot pink': 'HOTPINK', 'dusty pink': 'DUSTYPINK', 'baby pink': 'BABYPINK',
    'forest green': 'FORESTGREEN', 'bottle green': 'BOTTLEGREEN',
    'olive green': 'OLIVE', 'army green': 'OLIVE', 'military green': 'OLIVE',
    'sage green': 'SAGE', 'mint green': 'MINT', 'lime green': 'LIME',
    'light blue': 'SKYBLUE', 'light pink': 'BABYPINK',
    'light grey': 'LIGHTGREY', 'light gray': 'LIGHTGREY',
    'dark grey': 'DARKGREY', 'dark gray': 'DARKGREY',
    'tie dye': 'MULTI', 'tie-dye': 'MULTI',
    'black': 'BLACK', 'noir': 'BLACK', 'ebony': 'BLACK', 'onyx': 'BLACK',
    'charcoal': 'CHARCOAL', 'graphite': 'CHARCOAL',
    'white': 'WHITE', 'ivory': 'IVORY', 'cream': 'CREAM', 'ecru': 'CREAM',
    'offwhite': 'OFFWHITE',
    'grey': 'GREY', 'gray': 'GREY', 'silver': 'SILVER', 'slate': 'SLATE',
    'ash': 'GREY', 'smoke': 'GREY', 'stone': 'STONE',
    'blue': 'BLUE', 'navy': 'NAVY', 'cobalt': 'COBALT', 'teal': 'TEAL',
    'turquoise': 'TURQUOISE', 'aqua': 'AQUA', 'cyan': 'CYAN',
    'denim': 'BLUE', 'indigo': 'INDIGO', 'midnight': 'NAVY',
    'red': 'RED', 'crimson': 'RED', 'scarlet': 'RED',
    'burgundy': 'BURGUNDY', 'maroon': 'MAROON', 'wine': 'WINE',
    'rust': 'RUST', 'brick': 'BRICK', 'cherry': 'CHERRY',
    'rose': 'ROSE', 'blush': 'BLUSH',
    'pink': 'PINK', 'fuchsia': 'FUCHSIA', 'magenta': 'MAGENTA',
    'coral': 'CORAL', 'salmon': 'SALMON', 'nude': 'NUDE', 'peach': 'PEACH',
    'green': 'GREEN', 'olive': 'OLIVE', 'khaki': 'KHAKI', 'sage': 'SAGE',
    'mint': 'MINT', 'forest': 'FORESTGREEN', 'lime': 'LIME', 'emerald': 'EMERALD',
    'yellow': 'YELLOW', 'mustard': 'MUSTARD', 'gold': 'GOLD', 'golden': 'GOLD',
    'lemon': 'YELLOW', 'amber': 'AMBER', 'orange': 'ORANGE',
    'brown': 'BROWN', 'tan': 'TAN', 'camel': 'CAMEL', 'beige': 'BEIGE',
    'sand': 'SAND', 'taupe': 'TAUPE', 'coffee': 'BROWN', 'chocolate': 'BROWN',
    'caramel': 'CARAMEL', 'cognac': 'COGNAC',
    'purple': 'PURPLE', 'violet': 'VIOLET', 'lavender': 'LAVENDER',
    'lilac': 'LILAC', 'plum': 'PLUM', 'mauve': 'MAUVE',
    'multi': 'MULTI', 'multicolor': 'MULTI', 'multicolour': 'MULTI',
    'printed': 'MULTI', 'chambray': 'CHAMBRAY',
    'inferno': 'RED', 'ember': 'RED', 'na': 'NA',
}
_COLOR_KEYS_SORTED = sorted(COLOR_MAP.keys(), key=len, reverse=True)


def extract_color(text):
    if not text or pd.isna(text):
        return None
    t = str(text).lower().strip()
    for key in _COLOR_KEYS_SORTED:
        if key in t:
            return COLOR_MAP[key]
    return None


def extract_color_from_row(aid, van, iname):
    if iname and not pd.isna(iname):
        parts = [p.strip() for p in str(iname).split('-')]
        for idx in [-3, -2, -4]:
            if abs(idx) <= len(parts):
                c = extract_color(parts[idx])
                if c and c != 'NA':
                    return c
    if van and not pd.isna(van):
        c = extract_color(str(van))
        if c:
            return c
    if aid and not pd.isna(aid):
        c = extract_color(str(aid))
        if c:
            return c
    return 'UNKNOWN'


# ─────────────────────────────────────────────────────────────────────────────
# STYLE KEY BUILDING
# ─────────────────────────────────────────────────────────────────────────────

def build_primary_key(brand, aid, size):
    stripped = strip_size_from_article_id(aid, size)
    return str(brand).strip().upper() + '||PK||' + stripped.upper()


def build_secondary_key(brand, iname):
    if iname and not pd.isna(iname):
        parts = str(iname).split('-')
        if len(parts) >= 3:
            no_size = '-'.join(parts[:-1]).strip()
            return str(brand).strip().upper() + '||SK||' + no_size.upper()
    return None


def brand_prefix(brand_name):
    clean = re.sub(r'[^a-zA-Z0-9]', '', str(brand_name))
    return clean[:3].upper()


def sanitize_for_style_id(text, max_len=15):
    if not text:
        return 'UNK'
    text = unicodedata.normalize('NFKD', str(text))
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = text.upper()
    text = re.sub(r'[^A-Z0-9]', '', text)
    return text[:max_len] or 'UNK'


# ─────────────────────────────────────────────────────────────────────────────
# KEY SIZE LOOKUP
# ─────────────────────────────────────────────────────────────────────────────

def lookup_key_size(division, section, department, node, size, conn):
    size_norm = normalize_size(size)
    cur = conn.cursor()
    cur.execute(
        """SELECT key_size FROM key_size_map
           WHERE division=%s AND section=%s AND department=%s AND node=%s AND size=%s""",
        (
            str(division).strip() if not pd.isna(division) else '',
            str(section).strip()  if not pd.isna(section)  else '',
            str(department).strip() if not pd.isna(department) else '',
            str(node).strip()     if not pd.isna(node)     else '',
            size_norm,
        )
    )
    result = cur.fetchone()
    cur.close()
    if result is None:
        return ''
    val = result[0]
    return '' if val is None else int(val)


# ─────────────────────────────────────────────────────────────────────────────
# STYLE ID GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_new_style_id(brand, aid, van, iname, size, conn):
    prefix = brand_prefix(brand)
    design_raw = ''
    if van and not pd.isna(van):
        design_raw = str(van).strip()
    elif iname and not pd.isna(iname):
        parts = str(iname).split('-')
        design_raw = parts[4].strip() if len(parts) >= 5 else parts[-2].strip()
    if not design_raw:
        design_raw = strip_size_from_article_id(aid, size)

    design_code = sanitize_for_style_id(design_raw, 15)
    color_raw   = extract_color_from_row(aid, van, iname)
    color_code  = sanitize_for_style_id(color_raw or 'UNKNOWN', 15)

    base = f"BW_{prefix}_{design_code}_{color_code}_"
    cur = conn.cursor()
    cur.execute(
        "SELECT style_group_id FROM style_map WHERE style_group_id LIKE %s",
        (base + '%',)
    )
    existing = [r[0] for r in cur.fetchall()]
    cur.close()

    if not existing:
        seq = '01'
    else:
        nums = [int(m.group(1)) for sid in existing
                for m in [re.search(r'_(\d+)$', sid)] if m]
        seq = str(max(nums) + 1).zfill(2) if nums else '01'

    return base + seq


# ─────────────────────────────────────────────────────────────────────────────
# CORE MAPPING
# ─────────────────────────────────────────────────────────────────────────────

def map_dataframe(df, conn):
    style_ids = []
    key_sizes  = []
    new_cache  = {}
    matched = generated = 0

    cur = conn.cursor()

    for _, row in df.iterrows():
        brand = str(row.get('brand_name', '')).strip()
        aid   = str(row.get('vendor_article_id', '')).strip()
        van   = row.get('vendor_article_name', '')
        iname = str(row.get('item_name', '')).strip()
        size  = row.get('size', '')
        div   = row.get('division', '')
        sec   = row.get('section', '')
        dept  = row.get('department', '')
        node  = row.get('node', '')

        pk = build_primary_key(brand, aid, size)
        cur.execute("SELECT style_group_id FROM style_map WHERE style_key=%s", (pk,))
        res = cur.fetchone()

        if res:
            sid = res[0]
            matched += 1
        else:
            sk = build_secondary_key(brand, iname)
            sid = None
            if sk:
                cur.execute("SELECT style_group_id FROM style_map WHERE style_key=%s", (sk,))
                res2 = cur.fetchone()
                if res2:
                    sid = res2[0]
                    matched += 1

            if sid is None:
                if pk in new_cache:
                    sid = new_cache[pk]
                else:
                    sid = generate_new_style_id(brand, aid, van, iname, size, conn)
                    color = extract_color_from_row(aid, van, iname)
                    for key_to_store in [pk] + ([sk] if sk else []):
                        cur.execute(
                            """INSERT INTO style_map (style_key, style_group_id, brand_name, color, source)
                               VALUES (%s, %s, %s, %s, 'generated')
                               ON CONFLICT (style_key) DO NOTHING""",
                            (key_to_store, sid, brand, color)
                        )
                    conn.commit()
                    new_cache[pk] = sid
                    generated += 1

        style_ids.append(sid)
        key_sizes.append(lookup_key_size(div, sec, dept, node, size, conn))

    cur.close()
    df = df.copy()
    df['style_group_id'] = style_ids
    df['key_size']       = key_sizes
    return df, matched, generated


# ─────────────────────────────────────────────────────────────────────────────
# UI
# ─────────────────────────────────────────────────────────────────────────────

st.title("🏷️ Style ID Mapper")
st.caption("Upload a barcode CSV to get Style IDs and Key Sizes mapped automatically.")

# Init DB on first run
try:
    init_db()
except Exception as e:
    st.error(f"Could not connect to database: {e}")
    st.stop()

# ── Stats bar ────────────────────────────────────────────────────────────────
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
    conn.close()

    c1, c2, c3 = st.columns(3)
    c1.metric("Style IDs in database", f"{total_styles:,}")
    c2.metric("Brands", f"{total_brands:,}")
    c3.metric("Key size rules", f"{total_ks:,}")
except:
    pass

st.divider()

# ── Upload & Map ─────────────────────────────────────────────────────────────
st.subheader("Upload barcode file")
st.caption("CSV must have the same columns as your reference file.")

uploaded = st.file_uploader("Drop your CSV here", type=["csv"])

if uploaded:
    try:
        df = pd.read_csv(uploaded)
        df.columns = [c.strip() for c in df.columns]

        st.write(f"**{len(df):,} rows** · **{df['brand_name'].nunique() if 'brand_name' in df.columns else '?'} brands** detected")
        st.dataframe(df.head(5), use_container_width=True)

        if st.button("▶ Map Style IDs", type="primary"):
            with st.spinner("Mapping... this may take a moment for large files"):
                conn = get_db()
                result, matched, generated = map_dataframe(df, conn)
                conn.close()

            st.success(f"Done! **{matched:,}** matched · **{generated}** new Style IDs generated")

            # Preview
            st.subheader("Result preview")
            display_cols = ['bar_code', 'brand_name', 'vendor_article_id',
                            'size', 'style_group_id', 'key_size']
            display_cols = [c for c in display_cols if c in result.columns]
            st.dataframe(result[display_cols].head(50), use_container_width=True)

            # Download
            csv_buffer = io.StringIO()
            result.to_csv(csv_buffer, index=False)
            st.download_button(
                label="⬇ Download full mapped CSV",
                data=csv_buffer.getvalue(),
                file_name="mapped_output.csv",
                mime="text/csv"
            )

    except Exception as e:
        st.error(f"Something went wrong: {e}")
