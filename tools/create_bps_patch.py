# Create BPS patch
import hashlib

def crc32(data):
    crc = 0xFFFFFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xEDB88320
            else:
                crc >>= 1
    return crc ^ 0xFFFFFFFF

def encode_varint(n):
    result = bytearray()
    while True:
        byte = n & 0x7F
        n >>= 7
        if n:
            result.append(byte | 0x80)
        else:
            result.append(byte)
            break
    return bytes(result)

def create_bps_patch(source_path, target_path, output_path):
    with open(source_path, 'rb') as f:
        source = f.read()
    with open(target_path, 'rb') as f:
        target = f.read()
    
    source_len = len(source)
    target_len = len(target)
    
    source_crc = crc32(source)
    target_crc = crc32(target)
    
    print(f'Source: {source_len} bytes, CRC32: {source_crc:08X}')
    print(f'Target: {target_len} bytes, CRC32: {target_crc:08X}')
    
    commands = bytearray()
    source_pos = 0
    target_pos = 0
    
    block_size = 16
    source_hashes = {}
    for i in range(0, len(source) - block_size + 1, block_size):
        block = source[i:i+block_size]
        h = hashlib.md5(block).digest()[:4]
        if h not in source_hashes:
            source_hashes[h] = []
        source_hashes[h].append(i)
    
    while target_pos < target_len:
        best_match_len = 0
        best_match_source = 0
        
        max_lookahead = min(65536, target_len - target_pos)
        if max_lookahead >= block_size:
            for lookahead in range(block_size, min(max_lookahead, 1024), block_size):
                block = target[target_pos:target_pos+lookahead]
                h = hashlib.md5(block).digest()[:4]
                if h in source_hashes:
                    for src_pos in source_hashes[h]:
                        match_len = 0
                        max_match = min(len(source) - src_pos, target_len - target_pos)
                        while match_len < max_match and source[src_pos + match_len] == target[target_pos + match_len]:
                            match_len += 1
                        if match_len > best_match_len:
                            best_match_len = match_len
                            best_match_source = src_pos
        
        if best_match_len >= 4:
            while best_match_len > 0:
                chunk = min(best_match_len, 64)
                cmd = 0xC0 + (chunk - 1)
                commands.append(cmd)
                rel_offset = best_match_source - source_pos
                commands.extend(encode_varint(rel_offset if rel_offset >= 0 else (rel_offset & 0xFFFFFFFFFFFFFFFF)))
                source_pos += chunk
                target_pos += chunk
                best_match_len -= chunk
        else:
            chunk = min(64, target_len - target_pos)
            cmd = 0x80 + (chunk - 1)
            commands.append(cmd)
            commands.extend(target[target_pos:target_pos+chunk])
            target_pos += chunk
    
    metadata = bytearray()
    meta_offset = 0
    while meta_offset < source_len:
        chunk_size = min(65536, source_len - meta_offset)
        chunk_crc = crc32(source[meta_offset:meta_offset+chunk_size])
        metadata.extend(encode_varint(chunk_size))
        metadata.extend(chunk_crc.to_bytes(4, 'big'))
        meta_offset += chunk_size
    
    meta_offset = 0
    while meta_offset < target_len:
        chunk_size = min(65536, target_len - meta_offset)
        chunk_crc = crc32(target[meta_offset:meta_offset+chunk_size])
        metadata.extend(encode_varint(chunk_size))
        metadata.extend(chunk_crc.to_bytes(4, 'big'))
        meta_offset += chunk_size
    
    with open(output_path, 'wb') as f:
        f.write(b'BPS1')
        f.write(encode_varint(source_len))
        f.write(encode_varint(target_len))
        f.write(commands)
        f.write(b'\x00')
        f.write(metadata)
    
    print(f'Created BPS patch: {output_path}')
    print(f'Commands: {len(commands)} bytes, Metadata: {len(metadata)} bytes')
    return output_path

def encode_varint(n):
    result = bytearray()
    while True:
        byte = n & 0x7F
        n >>= 7
        if n:
            result.append(byte | 0x80)
        else:
            result.append(byte)
            break
    return bytes(result)

# Create BPS patch
print('=== Creating BPS patch ===')
create_bps_patch('comix_zone_usa.md', 'comix_zone_final.md', 'comix_zone_arabic_easy_sram.bps')

# Quick verification
print('\n=== Verifying BPS patch header ===')
with open('comix_zone_arabic_easy_sram.bps', 'rb') as f:
    patch = f.read()
print(f'Magic: {patch[:4]}')
print(f'Size: {len(patch)} bytes')