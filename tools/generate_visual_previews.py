import sys, os, json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from build_rooyin_font import f1_bin, f2_bin, BYTE_TO_CHAR, CHAR_TO_BYTE

def parse_font(f_bin):
    pitch = int.from_bytes(f_bin[0:2], 'big')
    height = int.from_bytes(f_bin[2:4], 'big')
    off1 = int.from_bytes(f_bin[4:6], 'big')
    off2 = int.from_bytes(f_bin[6:8], 'big')
    off3 = int.from_bytes(f_bin[8:10], 'big')
    widths = list(f_bin[10:off2])
    bitmap = f_bin[off3 : off3 + pitch * height]
    return {'pitch': pitch, 'height': height, 'widths': widths, 'bitmap': bitmap}

f1_data = parse_font(f1_bin)
f2_data = parse_font(f2_bin)

pal_f1 = {
    0x0F: (255, 255, 255, 255), # White
    0x01: (0, 0, 0, 255),       # Black ink
}

pal_f2 = {
    0x0C: (234, 226, 0, 255),   # Genesis Authentic Yellow
    0x01: (0, 0, 0, 255),       # Black ink
}

def render_line(font_data, pal, default_bg, text):
    # Map chars to bytes
    bytes_list = []
    for c in text:
        if c in CHAR_TO_BYTE:
            bytes_list.append(CHAR_TO_BYTE[c])
        elif ord(c) < 128:
            bytes_list.append(ord(c))
        else:
            bytes_list.append(0x20)
            
    total_w = sum(font_data['widths'][b - 0x20] for b in bytes_list if 0 <= b - 0x20 < len(font_data['widths']))
    img = Image.new('RGBA', (max(total_w, 1), 8), default_bg)
    pixels = img.load()
    
    cur_x = 0
    pitch = font_data['pitch']
    bitmap = font_data['bitmap']
    widths = font_data['widths']
    
    for b in bytes_list:
        idx = b - 0x20
        if not (0 <= idx < len(widths)):
            continue
        w = widths[idx]
        char_start_x = sum(widths[:idx])
        
        for y in range(min(8, font_data['height'])):
            row_off = y * pitch
            for x in range(w):
                src_x = char_start_x + x
                byte_idx = src_x // 2
                nib_idx = src_x % 2
                if byte_idx < pitch:
                    val = bitmap[row_off + byte_idx]
                    nib = (val >> 4) if nib_idx == 0 else (val & 0x0F)
                    color = pal.get(nib, default_bg)
                    pixels[cur_x + x, y] = color
        cur_x += w
    return img

# 1. Preview Yellow Banner Box
tr_path = ROOT / "encoding" / "translations_final.json"
with open(tr_path, 'r', encoding='utf-8') as f:
    tr = json.load(f)

tr_map = {x['address']: x for x in tr}

l1_text = tr_map['0x1C87E4']['shaped']
l2_text = tr_map['0x1C87FA']['shaped']

img_l1 = render_line(f2_data, pal_f2, (234, 226, 0, 255), l1_text)
img_l2 = render_line(f2_data, pal_f2, (234, 226, 0, 255), l2_text)

box_w = max(img_l1.width, img_l2.width) + 16
box_h = 24
box = Image.new('RGB', (box_w, box_h), (234, 226, 0)) # Solid Yellow Box
box.paste(img_l1, (8, 3), img_l1)
box.paste(img_l2, (8, 13), img_l2)

# Save 1x and 4x
prev_dir = ROOT / "previews"
prev_dir.mkdir(parents=True, exist_ok=True)
box.save(prev_dir / 'preview_yellow_box_1x.png')
box.resize((box_w * 4, box_h * 4), Image.NEAREST).save(prev_dir / 'preview_yellow_box_4x.png')
print(f"Generated preview_yellow_box_4x.png ({box_w*4}x{box_h*4})")

# 2. Preview Dialogue Bubble (Room 2: "رودكيل، يا صاحبي!!!")
bubble_l1 = tr_map['0x1C89C8']['shaped'] # "،ﻞﻴﻛﺩﻭﺭ"
bubble_l2 = tr_map['0x1C89D2']['shaped'] # "!!!ﻲﺒﺣﺎﺻ ﺎﻳ"

b_img1 = render_line(f1_data, pal_f1, (255, 255, 255, 255), bubble_l1)
b_img2 = render_line(f1_data, pal_f1, (255, 255, 255, 255), bubble_l2)

bub_w = max(b_img1.width, b_img2.width) + 16
bub_h = 24
bubble = Image.new('RGB', (bub_w, bub_h), (255, 255, 255))
bubble.paste(b_img1, ((bub_w - b_img1.width) // 2, 3), b_img1)
bubble.paste(b_img2, ((bub_w - b_img2.width) // 2, 13), b_img2)

bubble.resize((bub_w * 4, bub_h * 4), Image.NEAREST).save(prev_dir / 'preview_bubble_4x.png')
print(f"Generated preview_bubble_4x.png ({bub_w*4}x{bub_h*4})")

# 3. Preview Cutscene (0x1C83CD: "مدينة نيويورك، الحاضر")
cut_text = tr_map['0x1C83CD']['shaped']
cut_img = render_line(f1_data, pal_f1, (0, 0, 0, 0), cut_text)
# On black background (like cutscene)
cut_bg = Image.new('RGB', (cut_img.width + 16, 16), (0, 0, 0))
# In cutscene text is white ink on black
# Invert pal1 for preview
cut_white = render_line(f1_data, {0x0F: (0, 0, 0, 0), 0x01: (255, 255, 255, 255)}, (0, 0, 0, 0), cut_text)
cut_bg.paste(cut_white, (8, 4), cut_white)
cut_bg.resize((cut_bg.width * 4, cut_bg.height * 4), Image.NEAREST).save(prev_dir / 'preview_cutscene_4x.png')
print(f"Generated preview_cutscene_4x.png ({cut_bg.width*4}x{cut_bg.height*4})")
