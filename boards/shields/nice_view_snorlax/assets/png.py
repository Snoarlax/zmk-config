#!/usr/bin/env python3
"""Minimal PNG reader for palette sprites - no third-party deps available."""

import struct
import zlib


def read(path):
    d = open(path, "rb").read()
    assert d[:8] == b"\x89PNG\r\n\x1a\n", "not a png"

    pos = 8
    plte = None
    trns = b""
    idat = b""
    w = h = depth = ctype = None

    while pos < len(d):
        (length,) = struct.unpack(">I", d[pos : pos + 4])
        ctag = d[pos + 4 : pos + 8]
        data = d[pos + 8 : pos + 8 + length]
        pos += 12 + length
        if ctag == b"IHDR":
            w, h, depth, ctype = struct.unpack(">IIBB", data[:10])
        elif ctag == b"PLTE":
            plte = data
        elif ctag == b"tRNS":
            trns = data
        elif ctag == b"IDAT":
            idat += data
        elif ctag == b"IEND":
            break

    raw = zlib.decompress(idat)

    # samples per pixel, and the filter's byte offset
    if ctype == 3:
        spp = 1
    elif ctype == 0:
        spp = 1
    elif ctype == 2:
        spp = 3
    elif ctype == 4:
        spp = 2
    else:
        spp = 4

    bits_per_pixel = depth * spp
    stride = (w * bits_per_pixel + 7) // 8
    fbpp = max(1, bits_per_pixel // 8)

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
        lines.append(bytes(line))
        prev = line

    # expand to per-pixel palette indices
    px = []
    for line in lines:
        row = []
        if depth == 8:
            row = list(line[:w])
        elif depth == 4:
            for i in range(w):
                byte = line[i >> 1]
                row.append((byte >> 4) if i % 2 == 0 else (byte & 0x0F))
        elif depth == 2:
            for i in range(w):
                byte = line[i >> 2]
                row.append((byte >> (6 - 2 * (i % 4))) & 0x03)
        elif depth == 1:
            for i in range(w):
                byte = line[i >> 3]
                row.append((byte >> (7 - (i % 8))) & 0x01)
        px.append(row)

    def rgba(idx):
        r = plte[idx * 3]
        g = plte[idx * 3 + 1]
        b = plte[idx * 3 + 2]
        a = trns[idx] if idx < len(trns) else 255
        return r, g, b, a

    return w, h, px, rgba
