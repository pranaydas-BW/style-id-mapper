import streamlit as st
import pandas as pd
import psycopg2
import re
import unicodedata
import io
import os

st.set_page_config(page_title="Style ID Mapper", page_icon="🏷️", layout="wide")

# ─────────────────────────────────────────────────────────────────────────────
# STOP WORDS
# ─────────────────────────────────────────────────────────────────────────────
STOP_WORDS = {
    'shirt','tshirt','tee','top','dress','pants','pant','jeans','shorts','skirt',
    'jacket','hoodie','sweatshirt','kurta','set','trouser','trousers','joggers',
    'jogger','leggings','bra','polo','vest','tank','crop','blouse','tunic','suit',
    'maxi','midi','mini','cargo','bag','backpack','sneakers','heels','flats',
    'sandals','sandal','footwear','luggage','fit','slim','regular','relaxed',
    'relax','oversized','oversize','straight','loose','fitted','classic','casual',
    'formal','solid','printed','striped','checked','checkered','floral','graphic',
    'embroidered','embroidery','embellished','textured','woven','knit','lace',
    'satin','denim','linen','cotton','stretch','blend','pure','terry','french',
    'sleeve','sleeves','sleeveless','collar','neck','crew','shoulder','halter',
    'button','zip','zipper','strap','front','half','full','long','short','high',
    'mid','leg','waist','flare','box','summer','festive','party','occasion','wear',
    'collection','fashion','core','essential','luxe','ethnic','gymwear',
    'loungewear','nightwear','night','men','mens','women','womens','girls',
    'unisex','the','and','with','for','each',
}

# ─────────────────────────────────────────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────────────────────────────────────────

def get_db():
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        st.error("DATABASE_URL not set. Please check your Streamlit secrets.")
        st.stop()
    return psycopg2.connect(db_url)

# ─────────────────────────────────────────────────────────────────────────────
# SIZE HANDLING
# ─────────────────────────────────────────────────────────────────────────────

def normalize_size(size_val):
    if pd.isna(size_val):
        return ''
    s = str(size_val).strip()
    s = re.sub(r'^(?:UK|EU)\s*', '', s, flags=re.IGNORECASE).strip()
    return s

def strip_size_from_text(text, size_val):
    t = str(text).strip().rstrip('\n').replace('\\n', '').strip()
    size = normalize_size(size_val)
    if size:
        for sep in ['-', '_', ' ', '']:
            pattern = re.compile(re.escape(sep + size) + r'$', re.IGNORECASE)
            stripped = pattern.sub('', t)
            if stripped != t:
                return stripped.rstrip('-_ ').strip()
    size_pattern = re.compile(
        r'[-_\s](x{0,4}s|x{0,3}l|xxl|xl|2xl|3xl|4xl|5xl'
        r'|\d{2}x\d{2}|free\s*size?|one\s*size'
        r'|uk\s*\d+(?:\.\d+)?|eu\s*\d+(?:\.\d+)?'
        r'|(?:2[4-9]|[3-5]\d))$', re.IGNORECASE)
    return size_pattern.sub('', t).strip() or t

def remove_stop_words(text):
    tokens = re.split(r'[-_\s]+', str(text).lower())
    filtered = [t for t in tokens if t and t not in STOP_WORDS and len(t) > 1]
    return ' '.join(filtered)

# ─────────────────────────────────────────────────────────────────────────────
# COLOR EXTRACTION
# ─────────────────────────────────────────────────────────────────────────────

COLOR_MAP = {
    'off white':'OFFWHITE','off-white':'OFFWHITE','rose gold':'ROSEGOLD',
    'powder blue':'POWDERBLUE','sky blue':'SKYBLUE','navy blue':'NAVY',
    'forest green':'FORESTGREEN','hot pink':'HOTPINK','tie dye':'MULTI',
    'dusty pink':'DUSTYPINK','baby pink':'BABYPINK','baby blue':'BABYBLUE',
    'black':'BLACK','white':'WHITE','grey':'GREY','gray':'GREY','blue':'BLUE',
    'navy':'NAVY','teal':'TEAL','red':'RED','burgundy':'BURGUNDY','maroon':'MAROON',
    'pink':'PINK','green':'GREEN','olive':'OLIVE','khaki':'KHAKI','sage':'SAGE',
    'yellow':'YELLOW','mustard':'MUSTARD','gold':'GOLD','orange':'ORANGE',
    'brown':'BROWN','tan':'TAN','camel':'CAMEL','beige':'BEIGE','purple':'PURPLE',
    'lavender':'LAVENDER','lilac':'LILAC','multi':'MULTI','multicolor':'MULTI',
    'cream':'CREAM','ivory':'IVORY','nude':'NUDE','peach':'PEACH','coral':'CORAL',
    'silver':'SILVER','charcoal':'CHARCOAL','chambray':'CHAMBRAY','inferno':'RED',
    'ember':'RED','rust':'RUST','wine':'WINE','mint':'MINT','turquoise':'TURQUOISE',
    'indigo':'INDIGO','blush':'BLUSH','rose':'ROSE','mauve':'MAUVE','plum':'PLUM',
}
_COLOR_KEYS = sorted(COLOR_MAP.keys(), key=len, reverse=True)

def extract_color(text):
    if not text or pd.isna(text):
        return None
    t = str(text).lower().strip()
    for key in _COLOR_KEYS:
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
    if aid:
        c = extract_color(str(aid))
        if c:
            return c
    return 'UNKNOWN'

# ─────────────────────────────────────────────────────────────────────────────
# KEY BUILDING
# ─────────────────────────────────────────────────────────────────────────────

def build_pk(brand, aid, size):
    stripped = strip_size_from_text(aid, size)
    return str(brand).strip().upper() + '||PK||' + stripped.upper()

def build_vk(brand, van, size):
    if not van or pd.isna(van):
        return None
    stripped = strip_size_from_text(van, size)
    cleaned  = remove_stop_words(stripped).upper()
    if not cleaned:
        return None
    return str(brand).strip().upper() + '||VK||' + cleaned

def build_sk(brand, iname):
    if not iname or pd.isna(iname):
        return None
    parts = str(iname).split('-')
    if len(parts) >= 3:
        no_size = '-'.join(parts[:-1]).strip()
        cleaned = remove_stop_words(no_size).upper()
        if cleaned:
            return str(brand).strip().upper() + '||SK||' + cleaned
    return None

def brand_prefix(brand_name):
    clean = re.sub(r'[^a-zA-Z0-9]', '', str(brand_name))
    return clean[:3].upper()

def sanitize_for_style_id(text, max_len=15):
    if not text:
        return 'UNK'
    text = unicodedata.normalize('NFKD', str(text))
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^A-Z0-9]', '', text.upper())
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
        (str(division).strip() if not pd.isna(division) else '',
         str(section).strip()  if not pd.isna(section)  else '',
         str(department).strip() if not pd.isna(department) else '',
         str(node).strip()     if not pd.isna(node)     else '',
         size_norm))
    result = cur.fetchone()
    cur.close()
    if result is None:
        return ''
    return '' if result[0] is None else int(result[0])

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
        design_raw = strip_size_from_text(aid, size)

    design_code = sanitize_for_style_id(design_raw, 15)
    color_code  = sanitize_for_style_id(extract_color_from_row(aid, van, iname) or 'UNKNOWN', 15)

    base = f"BW_{prefix}_{design_code}_{color_code}_"
    cur = conn.cursor()
    cur.execute("SELECT style_group_id FROM style_map WHERE style_group_id LIKE %s", (base + '%',))
    existing = [r[0] for r in cur.fetchall()]
    cur.close()

    if not existing:
        seq = '01'
    else:
        nums = [int(m.group(1)) for sid in existing for m in [re.search(r'_(\d+)$', sid)] if m]
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

        sid = None

        # Step 1 — primary key (vendor_article_id)
        pk = build_pk(brand, aid, size)
        cur.execute("SELECT style_group_id FROM style_map WHERE style_key=%s", (pk,))
        res = cur.fetchone()
        if res:
            sid = res[0]
            matched += 1

        # Step 2 — vendor key (vendor_article_name)
        if sid is None:
            vk = build_vk(brand, van, size)
            if vk:
                cur.execute("SELECT style_group_id FROM style_map WHERE style_key=%s", (vk,))
                res = cur.fetchone()
                if res:
                    sid = res[0]
                    matched += 1

        # Step 3 — secondary key (item_name)
        if sid is None:
            sk = build_sk(brand, iname)
            if sk:
                cur.execute("SELECT style_group_id FROM style_map WHERE style_key=%s", (sk,))
                res = cur.fetchone()
                if res:
                    sid = res[0]
                    matched += 1

        # Step 4 — generate new
        if sid is None:
            cache_key = pk
            if cache_key in new_cache:
                sid = new_cache[cache_key]
            else:
                sid = generate_new_style_id(brand, aid, van, iname, size, conn)
                color = extract_color_from_row(aid, van, iname)
                vk = build_vk(brand, van, size)
                sk = build_sk(brand, iname)
                for key_to_store in [pk] + ([vk] if vk else []) + ([sk] if sk else []):
                    cur.execute(
                        """INSERT INTO style_map (style_key, style_group_id, brand_name, color, source)
                           VALUES (%s,%s,%s,%s,'generated') ON CONFLICT (style_key) DO NOTHING""",
                        (key_to_store, sid, brand, color))
                conn.commit()
                new_cache[cache_key] = sid
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
except Exception as e:
    st.error(f"Could not connect to database: {e}")
    st.stop()

st.divider()

st.subheader("Upload barcode file")
st.caption("CSV must have the same columns as your reference file.")

uploaded = st.file_uploader("Drop your CSV here", type=["csv"])

if uploaded:
    try:
        df = pd.read_csv(uploaded)
        df.columns = [c.strip() for c in df.columns]
        brands = df['brand_name'].nunique() if 'brand_name' in df.columns else '?'
        st.write(f"**{len(df):,} rows** · **{brands} brands** detected")
        st.dataframe(df.head(5), use_container_width=True)

        if st.button("▶ Map Style IDs", type="primary"):
            with st.spinner("Mapping... this may take a moment for large files"):
                conn = get_db()
                result, matched, generated = map_dataframe(df, conn)
                conn.close()

            st.success(f"Done! **{matched:,}** matched · **{generated}** new Style IDs generated")

            display_cols = ['bar_code','brand_name','vendor_article_id','size','style_group_id','key_size']
            display_cols = [c for c in display_cols if c in result.columns]
            st.subheader("Result preview")
            st.dataframe(result[display_cols].head(50), use_container_width=True)

            csv_buffer = io.StringIO()
            result.to_csv(csv_buffer, index=False)
            st.download_button(
                label="⬇ Download full mapped CSV",
                data=csv_buffer.getvalue(),
                file_name="mapped_output.csv",
                mime="text/csv")

    except Exception as e:
        st.error(f"Something went wrong: {e}")
