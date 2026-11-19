"""
build_rooyin_font.py - Generates 4bpp VWF Font 1 and Font 2 using Rooyin Pixel Font.
Full 8px height, 0x00 slant table (zero distortion), pixel-perfect Arabic rendering.
Flawless baseline connectivity, solid Alef corner & side-bearing padding,
flipped Arabic question mark (؟), and authentic Genesis Font 2 yellow palette (0x0C).
"""
import sys, os, json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

rom_path = os.environ.get("COMIX_ZONE_ROM", ROOT / "rom" / "Comix Zone (USA).md")
rom = open(rom_path, "rb").read() if os.path.exists(rom_path) else None

# 1. Parse Rooyin render data
render_path = os.environ.get("ROOYIN_RENDER", ROOT / "font" / "rooyin_render.txt")
with open(render_path, 'r', encoding='utf-8') as f:
    content = f.read()

entries = re.split(r'\n(?=cp )', content.strip())
raw_glyphs = {}
for e in entries:
    lines = e.strip().splitlines()
    header = lines[0].split()
    cp = header[1].lower()
    if len(header) >= 6:
        minx = int(header[2])
        miny = int(header[3])
        w = int(header[4])
        h = int(header[5])
        raw_glyphs[cp] = {'minx': minx, 'miny': miny, 'w': w, 'h': h, 'pattern': lines[1:1+h]}

def convert_to_8row(cp):
    if cp not in raw_glyphs:
        return None
    g = raw_glyphs[cp]
    w = g['w']
    miny = g['miny']
    pattern = g['pattern']
    grid = [['.' for _ in range(w)] for _ in range(25)]
    for r, line in enumerate(pattern):
        y = miny + r
        for c, ch in enumerate(line):
            grid[y][c] = ch
            
    target = [['.' for _ in range(w)] for _ in range(8)]
    
    # Hamza on top: fe83, fe84, fef7, fef8
    if cp in ['fe83', 'fe84', 'fef7', 'fef8']:
        for c in range(w):
            target[0][c] = grid[9][c]
            target[1][c] = grid[10][c]
        for r in range(2, 7):
            for c in range(w):
                target[r][c] = grid[14 + (r - 2)][c]
        
    # Hamza on bottom: fe87, fe88, fef9, fefa
    elif cp in ['fe87', 'fe88', 'fef9', 'fefa']:
        for r in range(6):
            y = 12 + r
            for c in range(w):
                target[r][c] = grid[y][c]
        # Baseline row 6
        for c in range(w):
            target[6][c] = grid[18][c]
        # Row 7 is hamza mark
        for c in range(w):
            for y in range(20, 24):
                if grid[y][c] == '#':
                    target[7][c] = '#'
                    break
        if cp in ['fe88', 'fefa']:
            target[6][w - 1] = '#'
            
    else:
        # Normal mapping: rows 12..18 -> 0..6 (row 6 is baseline row 18)
        for r in range(7):
            y = 12 + r
            for c in range(w):
                target[r][c] = grid[y][c]
                
        # Row 7: lower dots and descenders
        for c in range(w):
            for y in range(19, 25):
                if grid[y][c] == '#':
                    target[7][c] = '#'
                    break

    # --- GLYPH CONNECTIVITY FIXES ---
    # 1. Initial Yeh (U+FEF3)
    if cp == 'fef3':
        target[6][0] = '#'  # Connect to left edge
        target[7] = ['.', '#', '.', '#']  # Two crisp distinct dots

    # 2. Medial Yeh (U+FEF4)
    if cp == 'fef4':
        target[6][0] = '#'  # Connect to left edge
        target[7] = ['.', '#', '.', '#', '.']  # Two crisp distinct dots

    # 3. Final Lam-Alef with hamza below (U+FEFA)
    if cp == 'fefa':
        for c in range(w):
            target[6][c] = '#'
        target[7] = ['.', '#', '.', '.', '.']

    # --- PADDING / SIDE BEARING FOR NON-CONNECTING GLYPHS & ALEF FIXES ---
    
    # A. Isolated Alef variants: w = 3 (1px left and 1px right padding)
    if cp in ['fe8d', 'fe83', 'fe87', 'fe81']:
        new_target = []
        for r in range(8):
            new_target.append(['.', target[r][0], '.'])
        return 3, new_target

    # B. Final Alef variants: w = 3 (1px left padding and solid baseline corner)
    if cp in ['fe8e', 'fe84', 'fe88']:
        new_target = []
        for r in range(8):
            row = ['.', target[r][0], target[r][1]]
            new_target.append(row)
        new_target[6][1] = '#'  # Solid corner: vertical stem anchors to baseline!
        return 3, new_target

    # C. Initial Lam (U+FEDF): w = 3 (1px right padding so 'ال' doesn't touch)
    if cp == 'fedf':
        new_target = []
        for r in range(8):
            row = target[r] + ['.']
            new_target.append(row)
        return w + 1, new_target

    # D. Isolated Reh (U+FEAD) & Isolated Zain (U+FEAF): w = 4 (1px left and 1px right padding)
    if cp in ['fead', 'feaf']:
        new_target = []
        for r in range(8):
            new_target.append(['.', target[r][0], target[r][1], '.'])
        return 4, new_target

    # E. Final Reh (U+FEAE) & Final Zain (U+FEB0): w = 4 (1px left padding)
    if cp in ['feae', 'feb0']:
        new_target = []
        for r in range(8):
            row = ['.', target[r][0], target[r][1], target[r][2]]
            new_target.append(row)
        return 4, new_target

    # F. Isolated Waw (U+FEED) & Waw with Hamza (U+FE85): w = 6 (1px left and 1px right padding)
    if cp in ['feed', 'fe85']:
        new_target = []
        for r in range(8):
            row = ['.'] + target[r] + ['.']
            new_target.append(row)
        return w + 2, new_target

    # G. Final Waw (U+FEEE) & Final Waw with Hamza (U+FE86): w = 6 (1px left padding)
    if cp in ['feee', 'fe86']:
        new_target = []
        for r in range(8):
            row = ['.'] + target[r]
            new_target.append(row)
        return w + 1, new_target

    # H. Isolated Dal (U+FEA9) & Isolated Thal (U+FEAB): w = 6 (1px left and 1px right padding)
    if cp in ['fea9', 'feab']:
        new_target = []
        for r in range(8):
            row = ['.'] + target[r] + ['.']
            new_target.append(row)
        return w + 2, new_target

    # I. Final Dal (U+FEAA) & Final Thal (U+FEAC): w = 6 (1px left padding)
    if cp in ['feaa', 'feac']:
        new_target = []
        for r in range(8):
            row = ['.'] + target[r]
            new_target.append(row)
        return w + 1, new_target

    # J. Initial Kaf (U+FEDB): w = 6 (1px right padding so preceding letters have clean gap)
    if cp == 'fedb':
        new_target = []
        for r in range(8):
            row = target[r] + ['.']
            new_target.append(row)
        return w + 1, new_target

    return w, target

# Genuine Flipped Arabic Question Mark (؟)
custom_glyphs = {
    '00d7': (3, [
        ['.', '.', '.'], ['#', '.', '#'], ['.', '#', '.'], ['#', '.', '#'],
        ['.', '.', '.'], ['.', '.', '.'], ['.', '.', '.'], ['.', '.', '.']
    ]),
    '060c': (3, [
        ['.', '.', '.'], ['.', '.', '.'], ['.', '.', '.'], ['.', '.', '.'],
        ['.', '.', '.'], ['.', '#', '.'], ['#', '.', '.'], ['.', '.', '.']
    ]),
    '061f': (4, [
        ['.', '#', '#', '.'],
        ['#', '.', '.', '#'],
        ['#', '.', '.', '.'],
        ['.', '#', '.', '.'],
        ['.', '.', '#', '.'],
        ['.', '.', '.', '.'],
        ['.', '.', '#', '.'],
        ['.', '.', '.', '.']
    ]),
    '0640': (4, [
        ['.', '.', '.', '.'], ['.', '.', '.', '.'], ['.', '.', '.', '.'], ['.', '.', '.', '.'],
        ['.', '.', '.', '.'], ['.', '.', '.', '.'], ['#', '#', '#', '#'], ['.', '.', '.', '.']
    ]),
}

# 2. Build character mapping
tr_path = os.environ.get("TRANSLATIONS_JSON", ROOT / "encoding" / "translations_final.json")
with open(tr_path, 'r', encoding='utf-8') as f:
    tr = json.load(f)

used_arabic = set()
for item in tr:
    for c in item.get('shaped', ''):
        if ord(c) >= 128:
            used_arabic.add(c)

print(f"Total used Arabic characters in translations: {len(used_arabic)}")

CHAR_TO_BYTE = {}
BYTE_TO_CHAR = {}

# ASCII
for cp in range(0x20, 0x7F):
    CHAR_TO_BYTE[chr(cp)] = cp
    BYTE_TO_CHAR[cp] = chr(cp)

# Arabic
cur_b = 0x80
for uchar in sorted(used_arabic):
    CHAR_TO_BYTE[uchar] = cur_b
    BYTE_TO_CHAR[cur_b] = uchar
    cur_b += 1

MAX_BYTE = cur_b - 1
print(f"MAX_BYTE = 0x{MAX_BYTE:02X} ({MAX_BYTE})")

def build_rooyin_font(orig_font_addr, is_font2=False):
    if rom is None:
        prebuilt = ROOT / "font" / ("font2_expanded.bin" if is_font2 else "font1_expanded.bin")
        if prebuilt.exists():
            return prebuilt.read_bytes()
        raise FileNotFoundError(f"Original ROM not provided and prebuilt font {prebuilt} missing.")
    orig_pitch = int.from_bytes(rom[orig_font_addr:orig_font_addr+2], 'big')
    orig_height = int.from_bytes(rom[orig_font_addr+2:orig_font_addr+4], 'big')
    orig_off2 = int.from_bytes(rom[orig_font_addr+6:orig_font_addr+8], 'big')
    orig_off3 = int.from_bytes(rom[orig_font_addr+8:orig_font_addr+10], 'big')
    
    orig_num_chars = orig_off2 - 10
    orig_widths = list(rom[orig_font_addr+10 : orig_font_addr+orig_off2])
    orig_bitmap_offset = orig_font_addr + orig_off3
    
    # Font 1 background = 0x0F (white bubble), Font 2 background = 0x0C (yellow banner)!
    bg_nibble = 0x0F if not is_font2 else 0x0C
    ink_nibble = 0x01
    
    glyphs = {}
    
    # 1. Space
    space_w = orig_widths[0]
    glyphs[0x20] = (space_w, [[bg_nibble]*space_w for _ in range(8)])
    
    # 2. Original ASCII characters
    cur_x = orig_widths[0]
    for idx in range(1, orig_num_chars):
        byte_val = 0x20 + idx
        w = orig_widths[idx]
        grid = []
        for y in range(7):
            row = []
            for x in range(cur_x, cur_x + w):
                byte_idx = x // 2
                nib_idx = x % 2
                b = rom[orig_bitmap_offset + y * orig_pitch + byte_idx]
                nib = (b >> 4) if nib_idx == 0 else (b & 0x0F)
                row.append(nib)
            grid.append(row)
        # 8th row is background padding
        grid.append([bg_nibble] * w)
        glyphs[byte_val] = (w, grid)
        cur_x += w
        
    # OVERRIDE ASCII 0x3F ('?') with Arabic question mark (؟)
    qmark_w, qmark_grid = custom_glyphs['061f']
    grid_q = []
    for y in range(8):
        row = [(ink_nibble if qmark_grid[y][x] == '#' else bg_nibble) for x in range(qmark_w)]
        grid_q.append(row)
    glyphs[0x3F] = (qmark_w, grid_q)
    orig_widths[0x3F - 0x20] = qmark_w
        
    # 3. Unused bytes up to 0x80
    for b in range(0x20 + orig_num_chars, 0x80):
        if b not in glyphs:
            glyphs[b] = (0, [[] for _ in range(8)])
        
    # 4. Arabic characters
    for b in range(0x80, MAX_BYTE + 1):
        uchar = BYTE_TO_CHAR[b]
        hex_cp = f'{ord(uchar):04x}'.lower()
        res = convert_to_8row(hex_cp)
        if res is None and hex_cp in custom_glyphs:
            res = custom_glyphs[hex_cp]
            
        assert res is not None, f"Glyph U+{hex_cp} missing!"
        w, str_rows = res
        grid = []
        for y in range(8):
            row = [(ink_nibble if str_rows[y][x] == '#' else bg_nibble) for x in range(w)]
            grid.append(row)
        glyphs[b] = (w, grid)
        
    width_table = bytearray([glyphs[b][0] for b in range(0x20, MAX_BYTE + 1)])
    
    off1 = 0x003C
    off2 = 0x000A + len(width_table)
    
    # Zero slant table: 8 words of 00 00 = 16 bytes
    slant_table = b'\x00\x00' * 8
    off3 = off2 + len(slant_table)
    if off3 % 2 != 0:
        off3 += 1
        slant_table = slant_table + b'\x00'
        
    total_px = sum(width_table)
    pitch = (total_px + 1) // 2
    if pitch % 2 != 0:
        pitch += 1
        
    print(f"Font building ({'Font 2' if is_font2 else 'Font 1'}): bg=0x{bg_nibble:02X}, total_px={total_px}, pitch={pitch} bytes, off2=0x{off2:04X}, off3=0x{off3:04X}")
    
    # Bitmap lines
    fill_byte = (bg_nibble << 4) | bg_nibble
    bitmap_lines = [bytearray([fill_byte] * pitch) for _ in range(8)]
    cur_px = width_table[0]
    for b in range(0x21, MAX_BYTE + 1):
        w, grid = glyphs[b]
        if w > 0:
            for y in range(8):
                for x in range(w):
                    px = cur_px + x
                    nib = grid[y][x]
                    byte_idx = px // 2
                    nib_idx = px % 2
                    if byte_idx < pitch:
                        if nib_idx == 0:
                            bitmap_lines[y][byte_idx] = (bitmap_lines[y][byte_idx] & 0x0F) | (nib << 4)
                        else:
                            bitmap_lines[y][byte_idx] = (bitmap_lines[y][byte_idx] & 0xF0) | (nib & 0x0F)
            cur_px += w
            
    hdr = bytearray()
    hdr.extend(pitch.to_bytes(2, 'big'))
    hdr.extend((8).to_bytes(2, 'big')) # height = 8
    hdr.extend(off1.to_bytes(2, 'big'))
    hdr.extend(off2.to_bytes(2, 'big'))
    hdr.extend(off3.to_bytes(2, 'big'))
    hdr.extend(width_table)
    hdr.extend(slant_table)
    
    pad = off3 - len(hdr)
    if pad > 0:
        hdr.extend(b'\x00' * pad)
        
    f_bin = bytearray(hdr)
    for row in bitmap_lines:
        f_bin.extend(row)
        
    return f_bin

f1_bin = build_rooyin_font(0x06DFEA, is_font2=False)
f2_bin = build_rooyin_font(0x06E59A, is_font2=True)
print(f"Font 1 binary size: {len(f1_bin)} bytes")
print(f"Font 2 binary size: {len(f2_bin)} bytes")
