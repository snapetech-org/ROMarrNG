"""Synthetic distinct bytes with the same legacy CRC, for strong-hash tests."""
import zlib


def crc_collision(original):
    assert len(original) >= 5
    prefix = bytes([original[0] ^ 1]) + original[1:-4]
    baseline = zlib.crc32(prefix + bytes(4))
    basis = {}
    for bit in range(32):
        value = zlib.crc32(prefix + (1 << bit).to_bytes(4, "little")) ^ baseline
        mask = 1 << bit
        while value:
            pivot = value.bit_length() - 1
            if pivot not in basis:
                basis[pivot] = value, mask
                break
            v, m = basis[pivot]
            value ^= v
            mask ^= m
    value = zlib.crc32(original) ^ baseline
    mask = 0
    while value:
        v, m = basis[value.bit_length() - 1]
        value ^= v
        mask ^= m
    result = prefix + mask.to_bytes(4, "little")
    assert result != original and zlib.crc32(result) == zlib.crc32(original)
    return result
