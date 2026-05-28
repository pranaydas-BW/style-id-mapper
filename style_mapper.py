"""
Style ID Mapping System
=======================
Builds a SQLite DB from reference CSV, then maps new barcodes to
existing or new Style IDs and appends key_size.

Key strategy (in priority order):
  1. brand + stripped_vendor_article_id  (primary key - most specific)
  2. brand + item_name_minus_size        (secondary key - structured fallback)
  3. Generate new Style ID              (genuinely new style)
"""

import pandas as pd
import sqlite3
import re
import os
import unicodedata

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "style_db.sqlite")

# ─────────────────────────────────────────────────────────────────────────────
# SIZE HANDLING
# ─────────────────────────────────────────────────────────────────────────────

def normalize_size(size_val):
    """
    Normalize size: UK8 / UK 8 → 8, EU40 / EU 40 → 40, strip spaces.
    Leaves all other values unchanged.
    """
    if pd.isna(size_val):
        return ''
    s = str(size_val).strip()
    s = re.sub(r'^(?:UK|EU)\s*', '', s, flags=re.IGNORECASE).strip()
    return s


def strip_size_from_article_id(article_id, size_val):
    """
    Remove the size token from the end of an article_id.
    Tries the explicit size value first, then common size token patterns.
    """
    aid = str(article_id).strip()
    # Clean common dirty chars
    aid = aid.rstrip('\n').replace('\\n', '').strip()

    size = normalize_size(size_val)

    if size:
        # Try with common separators
        for sep in ['-', '_', ' ', '']:
            pattern = re.compile(
                re.escape(sep + size) + r'$', re.IGNORECASE
            )
            stripped = pattern.sub('', aid)
            if stripped != aid:
                return stripped.rstrip('-_ ').strip()

    # Fallback: regex-based size token stripping
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

# Multi-word entries must come before single-word base colors
COLOR_MAP = {
    # Multi-word / compound (checked first due to sort-by-length)
    'off white': 'OFFWHITE', 'off-white': 'OFFWHITE',
    'optical white': 'WHITE',
    'rose gold': 'ROSEGOLD',
    'powder blue': 'POWDERBLUE',
    'sky blue': 'SKYBLUE',
    'baby blue': 'BABYBLUE',
    'royal blue': 'ROYALBLUE',
    'steel blue': 'STEELBLUE',
    'midnight blue': 'NAVY',
    'navy blue': 'NAVY',
    'denim blue': 'DENIMBLUE',
    'hot pink': 'HOTPINK',
    'dusty pink': 'DUSTYPINK',
    'baby pink': 'BABYPINK',
    'forest green': 'FORESTGREEN',
    'bottle green': 'BOTTLEGREEN',
    'olive green': 'OLIVE',
    'hunter green': 'GREEN',
    'army green': 'OLIVE',
    'military green': 'OLIVE',
    'moss green': 'OLIVE',
    'sage green': 'SAGE',
    'mint green': 'MINT',
    'lime green': 'LIME',
    'light blue': 'SKYBLUE',
    'light pink': 'BABYPINK',
    'light grey': 'LIGHTGREY',
    'light gray': 'LIGHTGREY',
    'dark grey': 'DARKGREY',
    'dark gray': 'DARKGREY',
    'barkha brown': 'BROWN',
    'bliss black': 'BLACK',
    'gowri grey': 'GREY',
    'naina navy': 'NAVY',
    'tie dye': 'MULTI',
    'tie-dye': 'MULTI',
    # Single words
    'black': 'BLACK', 'noir': 'BLACK', 'ebony': 'BLACK',
    'onyx': 'BLACK', 'jet': 'BLACK',
    'charcoal': 'CHARCOAL', 'graphite': 'CHARCOAL',
    'white': 'WHITE', 'ivory': 'IVORY',
    'cream': 'CREAM', 'ecru': 'CREAM',
    'offwhite': 'OFFWHITE',
    'grey': 'GREY', 'gray': 'GREY',
    'silver': 'SILVER', 'slate': 'SLATE',
    'ash': 'GREY', 'smoke': 'GREY',
    'stone': 'STONE', 'pebble': 'STONE',
    'blue': 'BLUE', 'navy': 'NAVY',
    'cobalt': 'COBALT', 'teal': 'TEAL',
    'turquoise': 'TURQUOISE', 'aqua': 'AQUA',
    'cyan': 'CYAN', 'denim': 'BLUE',
    'indigo': 'INDIGO', 'ocean': 'BLUE',
    'midnight': 'NAVY',
    'red': 'RED', 'crimson': 'RED', 'scarlet': 'RED',
    'burgundy': 'BURGUNDY', 'maroon': 'MAROON',
    'wine': 'WINE', 'rust': 'RUST', 'brick': 'BRICK',
    'cherry': 'CHERRY', 'rose': 'ROSE', 'blush': 'BLUSH',
    'pink': 'PINK', 'fuchsia': 'FUCHSIA',
    'magenta': 'MAGENTA', 'coral': 'CORAL', 'salmon': 'SALMON',
    'nude': 'NUDE', 'peach': 'PEACH', 'apricot': 'PEACH',
    'green': 'GREEN', 'olive': 'OLIVE', 'khaki': 'KHAKI',
    'sage': 'SAGE', 'mint': 'MINT', 'forest': 'FORESTGREEN',
    'lime': 'LIME', 'emerald': 'EMERALD',
    'yellow': 'YELLOW', 'mustard': 'MUSTARD',
    'golden': 'GOLD', 'gold': 'GOLD', 'lemon': 'YELLOW',
    'amber': 'AMBER', 'orange': 'ORANGE', 'tangerine': 'ORANGE',
    'brown': 'BROWN', 'tan': 'TAN', 'camel': 'CAMEL',
    'beige': 'BEIGE', 'sand': 'SAND', 'taupe': 'TAUPE',
    'coffee': 'BROWN', 'chocolate': 'BROWN', 'mocha': 'BROWN',
    'caramel': 'CARAMEL', 'cognac': 'COGNAC',
    'purple': 'PURPLE', 'violet': 'VIOLET',
    'lavender': 'LAVENDER', 'lilac': 'LILAC',
    'plum': 'PLUM', 'mauve': 'MAUVE',
    'multi': 'MULTI', 'multicolor': 'MULTI', 'multicolour': 'MULTI',
    'printed': 'MULTI', 'chambray': 'CHAMBRAY',
    'inferno': 'RED', 'ember': 'RED',
    'na': 'NA',
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


def extract_color_from_row(vendor_article_id, vendor_article_name, item_name):
    """
    Extract color from available fields.
    item_name structure: Brand-Sec-Dept-Node-Design-Color-Collection-Size
    Color is typically at position [-3] (3rd from end, before collection and size).
    """
    # Try item_name color segment first (most structured)
    if item_name and not pd.isna(item_name):
        parts = [p.strip() for p in str(item_name).split('-')]
        # Try positions -3, -2 (color can shift due to hyphens in names)
        for idx in [-3, -2, -4]:
            if abs(idx) <= len(parts):
                c = extract_color(parts[idx])
                if c and c != 'NA':
                    return c

    # Try vendor_article_name
    if vendor_article_name and not pd.isna(vendor_article_name):
        c = extract_color(str(vendor_article_name))
        if c:
            return c

    # Try vendor_article_id
    if vendor_article_id and not pd.isna(vendor_article_id):
        c = extract_color(str(vendor_article_id))
        if c:
            return c

    return 'UNKNOWN'


# ─────────────────────────────────────────────────────────────────────────────
# STYLE KEY BUILDING
# ─────────────────────────────────────────────────────────────────────────────

def build_primary_key(brand_name, vendor_article_id, size):
    """brand + stripped article_id — most specific key."""
    stripped = strip_size_from_article_id(vendor_article_id, size)
    return (
        str(brand_name).strip().upper() + '||PK||' + stripped.upper()
    )


def build_secondary_key(brand_name, item_name):
    """brand + item_name minus last segment (size) — structured fallback."""
    if item_name and not pd.isna(item_name):
        parts = str(item_name).split('-')
        if len(parts) >= 3:
            no_size = '-'.join(parts[:-1]).strip()
            return str(brand_name).strip().upper() + '||SK||' + no_size.upper()
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
# DATABASE
# ─────────────────────────────────────────────────────────────────────────────

def get_db():
    return sqlite3.connect(DB_PATH)


def init_db():
    con = get_db()
    con.executescript("""
        CREATE TABLE IF NOT EXISTS style_map (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            style_key       TEXT    NOT NULL,
            style_group_id  TEXT    NOT NULL,
            brand_name      TEXT,
            color           TEXT,
            source          TEXT    DEFAULT 'reference'
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_style_key
            ON style_map(style_key);
        CREATE INDEX IF NOT EXISTS idx_style_group
            ON style_map(style_group_id);
        CREATE INDEX IF NOT EXISTS idx_brand
            ON style_map(brand_name);

        CREATE TABLE IF NOT EXISTS key_size_map (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            division    TEXT,
            section     TEXT,
            department  TEXT,
            node        TEXT,
            size        TEXT,
            key_size    INTEGER
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_ks
            ON key_size_map(division, section, department, node, size);
    """)
    con.commit()
    con.close()


def build_db_from_reference(ref_csv_path, key_size_csv_path):
    """
    Load reference CSV and key size CSV into SQLite DB.
    Stores both primary (article_id-based) and secondary (item_name-based) keys.
    """
    print("Initialising database...")
    init_db()
    con = get_db()

    # ── Key size table ────────────────────────────────────────────────────────
    print("Loading key size mapping...")
    ks = pd.read_csv(key_size_csv_path)
    ks.columns = [c.strip() for c in ks.columns]
    ks = ks.rename(columns={'Key Size = 1': 'key_size'})
    ks['size_norm'] = ks['Size'].apply(normalize_size)

    ks_rows, seen_ks = [], set()
    for _, row in ks.iterrows():
        k = (
            str(row['Division']).strip(),
            str(row['Section']).strip(),
            str(row['Department']).strip(),
            str(row['Node']).strip(),
            str(row['size_norm']).strip(),
        )
        if k in seen_ks:
            continue
        seen_ks.add(k)
        ks_val = None if pd.isna(row['key_size']) else int(row['key_size'])
        ks_rows.append(k + (ks_val,))

    con.executemany(
        """INSERT OR IGNORE INTO key_size_map
           (division, section, department, node, size, key_size)
           VALUES (?,?,?,?,?,?)""",
        ks_rows
    )
    con.commit()
    print(f"  Loaded {len(ks_rows)} key size rules")

    # ── Style map table ───────────────────────────────────────────────────────
    print("Loading reference style data...")
    df = pd.read_csv(ref_csv_path)
    df.columns = [c.strip() for c in df.columns]

    rows_to_insert = []
    seen_keys = set()
    pk_count = sk_count = 0

    for _, row in df.iterrows():
        brand = str(row['brand_name']).strip()
        aid   = str(row['vendor_article_id'])
        van   = row.get('vendor_article_name', '')
        iname = str(row['item_name'])
        size  = row.get('size', '')
        sid   = str(row['style_group_id']).strip()

        color = extract_color_from_row(aid, van, iname)

        # Primary key
        pk = build_primary_key(brand, aid, size)
        if pk not in seen_keys:
            seen_keys.add(pk)
            rows_to_insert.append((pk, sid, brand, color, 'reference'))
            pk_count += 1

        # Secondary key
        sk = build_secondary_key(brand, iname)
        if sk and sk not in seen_keys:
            seen_keys.add(sk)
            rows_to_insert.append((sk, sid, brand, color, 'reference'))
            sk_count += 1

    con.executemany(
        """INSERT OR IGNORE INTO style_map
           (style_key, style_group_id, brand_name, color, source)
           VALUES (?,?,?,?,?)""",
        rows_to_insert
    )
    con.commit()
    con.close()

    print(f"  Inserted {pk_count} primary keys + {sk_count} secondary keys")
    print(f"  DB saved to: {DB_PATH}")


# ─────────────────────────────────────────────────────────────────────────────
# STYLE ID GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def generate_new_style_id(brand_name, vendor_article_id, vendor_article_name,
                          item_name, size, con):
    """Generate BW_XXX_DESIGN_COLOR_NN for a genuinely new style."""
    prefix = brand_prefix(brand_name)

    # Design identifier: vendor_article_name → item_name design segment → stripped article_id
    design_raw = ''
    if vendor_article_name and not pd.isna(vendor_article_name):
        design_raw = str(vendor_article_name).strip()
    elif item_name and not pd.isna(item_name):
        parts = str(item_name).split('-')
        design_raw = parts[4].strip() if len(parts) >= 5 else parts[-2].strip()
    if not design_raw:
        design_raw = strip_size_from_article_id(vendor_article_id, size)

    design_code = sanitize_for_style_id(design_raw, max_len=15)
    color_raw = extract_color_from_row(vendor_article_id, vendor_article_name, item_name)
    color_code = sanitize_for_style_id(color_raw or 'UNKNOWN', max_len=15)

    base = f"BW_{prefix}_{design_code}_{color_code}_"
    cur = con.cursor()
    cur.execute(
        "SELECT style_group_id FROM style_map WHERE style_group_id LIKE ?",
        (base + '%',)
    )
    existing = [r[0] for r in cur.fetchall()]

    if not existing:
        seq = '01'
    else:
        nums = [int(m.group(1)) for sid in existing
                for m in [re.search(r'_(\d+)$', sid)] if m]
        seq = str(max(nums) + 1).zfill(2) if nums else '01'

    return base + seq


# ─────────────────────────────────────────────────────────────────────────────
# KEY SIZE LOOKUP
# ─────────────────────────────────────────────────────────────────────────────

def lookup_key_size(division, section, department, node, size, con):
    size_norm = normalize_size(size)
    cur = con.cursor()
    cur.execute(
        """SELECT key_size FROM key_size_map
           WHERE division=? AND section=? AND department=? AND node=? AND size=?""",
        (
            str(division).strip() if not pd.isna(division) else '',
            str(section).strip()  if not pd.isna(section)  else '',
            str(department).strip() if not pd.isna(department) else '',
            str(node).strip()     if not pd.isna(node)     else '',
            size_norm,
        )
    )
    result = cur.fetchone()
    if result is None:
        return ''
    val = result[0]
    return '' if val is None else int(val)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN MAPPING FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def map_barcodes(input_csv_path, output_csv_path=None):
    """
    Process new barcode CSV → return it with style_group_id and key_size appended.

    Parameters
    ----------
    input_csv_path  : str  Path to input CSV (same column format as reference).
    output_csv_path : str  Optional output path. Defaults to <input>_mapped.csv.

    Returns
    -------
    pd.DataFrame  Input data with 'style_group_id' and 'key_size' filled.
    """
    if not os.path.exists(DB_PATH):
        raise RuntimeError(
            f"Database not found at {DB_PATH}. "
            "Run build_db_from_reference() first."
        )

    df = pd.read_csv(input_csv_path)
    df.columns = [c.strip() for c in df.columns]

    con = get_db()
    cur = con.cursor()

    style_ids  = []
    key_sizes  = []
    new_cache  = {}   # style_key → new style_id (within this batch)
    matched    = 0
    generated  = 0

    for _, row in df.iterrows():
        brand  = str(row.get('brand_name', '')).strip()
        aid    = str(row.get('vendor_article_id', '')).strip()
        van    = row.get('vendor_article_name', '')
        iname  = str(row.get('item_name', '')).strip()
        size   = row.get('size', '')
        div    = row.get('division', '')
        sec    = row.get('section', '')
        dept   = row.get('department', '')
        node   = row.get('node', '')

        # ── 1. Try primary key (article_id-based) ──
        pk = build_primary_key(brand, aid, size)
        cur.execute(
            "SELECT style_group_id FROM style_map WHERE style_key=?", (pk,)
        )
        res = cur.fetchone()

        if res:
            sid = res[0]
            matched += 1
        else:
            # ── 2. Try secondary key (item_name-based) ──
            sk = build_secondary_key(brand, iname)
            sid = None
            if sk:
                cur.execute(
                    "SELECT style_group_id FROM style_map WHERE style_key=?", (sk,)
                )
                res2 = cur.fetchone()
                if res2:
                    sid = res2[0]
                    matched += 1

            if sid is None:
                # ── 3. Check batch cache ──
                cache_key = pk
                if cache_key in new_cache:
                    sid = new_cache[cache_key]
                else:
                    # ── 4. Generate new style ID ──
                    sid = generate_new_style_id(brand, aid, van, iname, size, con)
                    color = extract_color_from_row(aid, van, iname)
                    # Persist both keys for future lookups
                    for key_to_store in [pk] + ([sk] if sk else []):
                        con.execute(
                            """INSERT OR IGNORE INTO style_map
                               (style_key, style_group_id, brand_name, color, source)
                               VALUES (?,?,?,?,?)""",
                            (key_to_store, sid, brand, color, 'generated')
                        )
                    con.commit()
                    new_cache[cache_key] = sid
                    generated += 1

        style_ids.append(sid)

        # ── Key size ──
        key_sizes.append(
            lookup_key_size(div, sec, dept, node, size, con)
        )

    con.close()

    df['style_group_id'] = style_ids
    df['key_size']       = key_sizes

    if output_csv_path is None:
        base = os.path.splitext(input_csv_path)[0]
        output_csv_path = base + '_mapped.csv'

    df.to_csv(output_csv_path, index=False)
    print(f"Mapped {len(df)} rows → {output_csv_path}")
    print(f"  Matched existing : {matched}")
    print(f"  New IDs generated: {generated}")

    return df


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("""
Usage:
  python style_mapper.py build <reference_csv> <key_size_csv>
      Build/rebuild the database from reference data.

  python style_mapper.py map <input_csv> [output_csv]
      Map barcodes and write results to output_csv.
""")
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == 'build':
        build_db_from_reference(sys.argv[2], sys.argv[3])
        print("Done.")

    elif cmd == 'map':
        out = sys.argv[3] if len(sys.argv) > 3 else None
        result = map_barcodes(sys.argv[2], out)
        print(result[['bar_code', 'brand_name', 'style_group_id', 'key_size']].head(20).to_string())
