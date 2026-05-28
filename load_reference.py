"""
Run this ONCE to load your reference data into Supabase.
(Re-run anytime you have updated reference data - safe to rerun, no duplicates)

Usage:
    python load_reference.py reference.csv key_size.csv
"""

import pandas as pd
import psycopg2
import re
import unicodedata
import sys

DATABASE_URL = "postgresql://postgres.rcskopbekgfyqrgaiatv:Style_Broadway%402026@aws-1-ap-south-1.pooler.supabase.com:5432/postgres"

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
        r'|(?:2[4-9]|[3-5]\d))$',
        re.IGNORECASE
    )
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
# KEY BUILDING — triple key system
# ─────────────────────────────────────────────────────────────────────────────

def build_pk(brand, aid, size):
    """Primary: brand + stripped vendor_article_id"""
    stripped = strip_size_from_text(aid, size)
    return str(brand).strip().upper() + '||PK||' + stripped.upper()

def build_vk(brand, van, size):
    """Vendor key: brand + stripped + stop-word-cleaned vendor_article_name"""
    if not van or pd.isna(van):
        return None
    stripped = strip_size_from_text(van, size)
    cleaned  = remove_stop_words(stripped).upper()
    if not cleaned:
        return None
    return str(brand).strip().upper() + '||VK||' + cleaned

def build_sk(brand, iname):
    """Secondary: brand + item_name minus size + stop words removed"""
    if not iname or pd.isna(iname):
        return None
    parts = str(iname).split('-')
    if len(parts) >= 3:
        no_size = '-'.join(parts[:-1]).strip()
        cleaned = remove_stop_words(no_size).upper()
        if cleaned:
            return str(brand).strip().upper() + '||SK||' + cleaned
    return None

def sanitize_for_style_id(text, max_len=15):
    if not text:
        return 'UNK'
    text = unicodedata.normalize('NFKD', str(text))
    text = text.encode('ascii', 'ignore').decode('ascii')
    text = re.sub(r'[^A-Z0-9]', '', text.upper())
    return text[:max_len] or 'UNK'

# ─────────────────────────────────────────────────────────────────────────────
# MAIN LOADER
# ─────────────────────────────────────────────────────────────────────────────

def load_data(ref_csv, ks_csv):
    conn = psycopg2.connect(DATABASE_URL)
    cur  = conn.cursor()
    print("Connected to database.")

    # Key size
    print("Loading key size mapping...")
    ks = pd.read_csv(ks_csv)
    ks.columns = [c.strip() for c in ks.columns]
    ks = ks.rename(columns={'Key Size = 1': 'key_size'})
    ks['size_norm'] = ks['Size'].apply(normalize_size)

    ks_rows, seen_ks = [], set()
    for _, row in ks.iterrows():
        k = (str(row['Division']).strip(), str(row['Section']).strip(),
             str(row['Department']).strip(), str(row['Node']).strip(),
             str(row['size_norm']).strip())
        if k in seen_ks:
            continue
        seen_ks.add(k)
        ks_val = None if pd.isna(row['key_size']) else int(row['key_size'])
        ks_rows.append(k + (ks_val,))

    cur.executemany(
        """INSERT INTO key_size_map (division, section, department, node, size, key_size)
           VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING""", ks_rows)
    conn.commit()
    print(f"  Loaded {len(ks_rows)} key size rules")

    # Reference data
    print("Loading reference data (this may take a few minutes)...")
    df = pd.read_csv(ref_csv)
    df.columns = [c.strip() for c in df.columns]

    rows_to_insert = []
    seen_keys = set()
    pk_count = vk_count = sk_count = 0
    batch_size = 500

    for i, (_, row) in enumerate(df.iterrows()):
        brand = str(row['brand_name']).strip()
        aid   = str(row['vendor_article_id'])
        van   = row.get('vendor_article_name', '')
        iname = str(row['item_name'])
        size  = row.get('size', '')
        sid   = str(row['style_group_id']).strip()
        color = extract_color_from_row(aid, van, iname)

        pk = build_pk(brand, aid, size)
        if pk not in seen_keys:
            seen_keys.add(pk)
            rows_to_insert.append((pk, sid, brand, color, 'reference'))
            pk_count += 1

        vk = build_vk(brand, van, size)
        if vk and vk not in seen_keys:
            seen_keys.add(vk)
            rows_to_insert.append((vk, sid, brand, color, 'reference'))
            vk_count += 1

        sk = build_sk(brand, iname)
        if sk and sk not in seen_keys:
            seen_keys.add(sk)
            rows_to_insert.append((sk, sid, brand, color, 'reference'))
            sk_count += 1

        if len(rows_to_insert) >= batch_size:
            cur.executemany(
                """INSERT INTO style_map (style_key, style_group_id, brand_name, color, source)
                   VALUES (%s,%s,%s,%s,%s) ON CONFLICT (style_key) DO NOTHING""",
                rows_to_insert)
            conn.commit()
            rows_to_insert = []
            print(f"  Processed {i+1:,} rows...", end='\r')

    if rows_to_insert:
        cur.executemany(
            """INSERT INTO style_map (style_key, style_group_id, brand_name, color, source)
               VALUES (%s,%s,%s,%s,%s) ON CONFLICT (style_key) DO NOTHING""",
            rows_to_insert)
        conn.commit()

    print(f"\n  Inserted {pk_count} primary + {vk_count} vendor name + {sk_count} item name keys")
    cur.close()
    conn.close()
    print("Done! Your database is ready.")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("Usage: python load_reference.py reference.csv key_size.csv")
        sys.exit(1)
    load_data(sys.argv[1], sys.argv[2])
