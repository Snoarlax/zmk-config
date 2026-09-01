#!/usr/bin/env python3
"""Minimal PNG reader - no third-party deps available in CI or on a fresh box.

read(path) -> (width, height, pixels, rgba)

pixels[y][x] is an (r, g, b, a) tuple and rgba() is the identity, so callers
can stay uniform across colour types. Handles the non-interlaced 8-bit forms
plus sub-byte palette and greyscale images, which covers what Piskel, GIMP
and the PokeAPI sprites emit.
"""

import struct
import sys
import zlib


def read(path):
    d = open(path, "rb").read()
    if d[:8] != b"\x89PNG\r\n\x1a\n":
        sys.exit(f"{path}: not a PNG")

    pos = 8
    plte = None
    trns = None
    idat = b""
    w = h = depth = ctype = interlace = None

    while pos + 8 <= len(d):
        (length,) = struct.unpack(">I", d[pos : pos + 4])
        tag = d[pos + 4 : pos + 8]
        data = d[pos + 8 : pos + 8 + length]
        pos += 12 + length
        if tag == b"IHDR":
            w, h, depth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", data[:13])
        elif tag == b"PLTE":
            plte = data
        elif tag == b"tRNS":
            trns = data
        elif tag == b"IDAT":
            idat += data
        elif tag == b"IEND":
            break

    if interlace:
        sys.exit(f"{path}: interlaced PNGs aren't supported - re-export without interlacing")
    if depth == 16:
        sys.exit(f"{path}: 16-bit PNGs aren't supported - re-export as 8-bit")

    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}
    if ctype not in channels:
        sys.exit(f"{path}: unsupported colour type {ctype}")
    spp = channels[ctype]

    bits_per_pixel = depth * spp
    stride = (w * bits_per_pixel + 7) // 8
    fbpp = max(1, bits_per_pixel // 8)

    raw = zlib.decompress(idat)
    lines = []
    prev = bytearray(stride)
    p = 0
    for _ in range(h):
        ft = raw[p]
        p += 1
        line = bytearray(raw[p : p + stride])
        p += stride
        if ft == 1:
            for i in range(fbpp, stride):
                line[i] = (line[i] + line[i - fbpp]) & 0xFF
        elif ft == 2:
            for i in range(stride):
                line[i] = (line[i] + prev[i]) & 0xFF
        elif ft == 3:
            for i in range(stride):
                left = line[i - fbpp] if i >= fbpp else 0
                line[i] = (line[i] + ((left + prev[i]) >> 1)) & 0xFF
        elif ft == 4:
            for i in range(stride):
                a = line[i - fbpp] if i >= fbpp else 0
                b = prev[i]
                c = prev[i - fbpp] if i >= fbpp else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[i] = (line[i] + pr) & 0xFF
        elif ft != 0:
            sys.exit(f"{path}: bad filter type {ft}")
        lines.append(bytes(line))
        prev = line

    def samples(line):
        """One scanline -> flat list of samples, expanding sub-byte depths."""
        if depth == 8:
            return list(line)
        per_byte = 8 // depth
        mask = (1 << depth) - 1
        out = []
        for i in range(w * spp):
            byte = line[i // per_byte]
            shift = 8 - depth * (i % per_byte + 1)
            out.append((byte >> shift) & mask)
        return out

    # sub-byte greyscale is stored scaled down; bring it back to 0-255
    grey_scale = 255 // ((1 << depth) - 1) if depth < 8 else 1

    pixels = []
    for line in lines:
        s = samples(line)
        row = []
        for x in range(w):
            if ctype == 3:
                idx = s[x]
                if plte is None:
                    sys.exit(f"{path}: palette image without a PLTE chunk")
                r, g, b = plte[idx * 3], plte[idx * 3 + 1], plte[idx * 3 + 2]
                a = trns[idx] if trns and idx < len(trns) else 255
            elif ctype == 0:
                v = s[x] * grey_scale
                r = g = b = v
                a = 255
            elif ctype == 4:
                v = s[x * 2] * grey_scale
                r = g = b = v
                a = s[x * 2 + 1] * grey_scale
            elif ctype == 2:
                r, g, b = s[x * 3], s[x * 3 + 1], s[x * 3 + 2]
                a = 255
            else:  # 6
                r, g, b, a = s[x * 4], s[x * 4 + 1], s[x * 4 + 2], s[x * 4 + 3]
            row.append((r, g, b, a))
        pixels.append(row)

    return w, h, pixels, lambda v: v
