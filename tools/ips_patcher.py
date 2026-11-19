# Create a proper IPS patcher that handles ROM expansion
# Then create easy mode modifications

def create_ips_patch(original_rom, modified_rom, output_path):
    """Create IPS patch from original to modified ROM"""
    with open(original_rom, 'rb') as f:
        orig = f.read()
    with open(modified_rom, 'rb') as f:
        mod = f.read()
    
    patches = []
    i = 0
    while i < len(orig) and i < len(mod):
        if orig[i] != mod[i]:
            start = i
            # Find end of difference
            while i < len(orig) and i < len(mod) and orig[i] != mod[i]:
                i += 1
            end = i
            # Check if RLE (all same byte in modified)
            mod_slice = mod[start:end]
            if len(set(mod_slice)) == 1:
                # RLE patch
                patches.append(('RLE', start, mod_slice[0], len(mod_slice)))
            else:
                # Normal patch
                patches.append(('NORMAL', start, mod_slice))
        else:
            i += 1
    
    # Handle case where modified is longer
    if len(mod) > len(orig):
        start = len(orig)
        mod_slice = mod[start:]
        if len(set(mod_slice)) == 1:
            patches.append(('RLE', start, mod_slice[0], len(mod_slice)))
        else:
            patches.append(('NORMAL', start, mod_slice))
    
    # Write IPS
    with open(output_path, 'wb') as f:
        f.write(b'PATCH')
        for ptype, offset, *data in patches:
            f.write(offset.to_bytes(3, 'big'))
            if ptype == 'RLE':
                byte_val, size = data
                f.write((0).to_bytes(2, 'big'))  # RLE marker
                f.write(size.to_bytes(2, 'big'))
                f.write(bytes([byte_val]))
            else:
                mod_slice = data[0]
                size = len(mod_slice)
                f.write(size.to_bytes(2, 'big'))
                f.write(mod_slice)
        f.write(b'EOF')
    
    print(f'Created IPS patch with {len(patches)} hunks')
    return patches

def apply_ips_patch(original_rom, ips_path, output_rom):
    """Apply IPS patch to ROM, handling expansion"""
    with open(original_rom, 'rb') as f:
        rom = bytearray(f.read())
    with open(ips_path, 'rb') as f:
        ips = f.read()
    
    if ips[:5] != b'PATCH':
        raise ValueError('Not a valid IPS file')
    
    i = 5
    while i < len(ips):
        if i + 3 > len(ips):
            break
        offset = int.from_bytes(ips[i:i+3], 'big')
        i += 3
        
        if offset == 0x454F46:  # 'EOF'
            break
        
        if i + 2 > len(ips):
            break
        size = int.from_bytes(ips[i:i+2], 'big')
        i += 2
        
        # Ensure ROM is large enough
        if offset + size > len(rom):
            # Expand ROM with zeros
            rom.extend(b'\x00' * (offset + size - len(rom)))
        
        if size == 0:  # RLE
            if i + 2 > len(ips):
                break
            rle_size = int.from_bytes(ips[i:i+2], 'big')
            i += 2
            if i >= len(ips):
                break
            byte_val = ips[i]
            i += 1
            # Ensure ROM is large enough for RLE
            if offset + rle_size > len(rom):
                rom.extend(b'\x00' * (offset + rle_size - len(rom)))
            rom[offset:offset+rle_size] = bytes([byte_val]) * rle_size
        else:
            if i + size > len(ips):
                break
            # Ensure ROM is large enough
            if offset + size > len(rom):
                rom.extend(b'\x00' * (offset + size - len(rom)))
            rom[offset:offset+size] = ips[i:i+size]
            i += size
    
    with open(output_rom, 'wb') as f:
        f.write(rom)
    print(f'Applied IPS patch, output size: {len(rom)} bytes')
    return rom

# Test with SRAM patch
print('=== Testing IPS patcher with SRAM patch ===')
apply_ips_patch('comix_zone_usa.md', 'sram_patch_extracted/Comix Zone SRAM.ips', 'comix_zone_sram_test.md')

import hashlib
with open('comix_zone_sram_test.md', 'rb') as f:
    sha1 = hashlib.sha1(f.read()).hexdigest()
print(f'SRAM patched SHA1: {sha1.upper()}')
print(f'Size: {os.path.getsize("comix_zone_sram_test.md")} bytes')