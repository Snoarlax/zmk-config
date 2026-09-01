#!/usr/bin/env python3
"""Rasterise a sleeping Snorlax for the nice_view peripheral screen.

Hand-authored at 34x34 as horizontal ink runs, then scaled 2x to 68x68 and
padded to the 69x68 the nice_view_gem art uses. Scaling gives the 2px stroke
weight the crystal frames it replaces are drawn with.

Output per frame: 69x68 INDEXED_1BIT, 9 bytes/row, 620 bytes with palette.
"""

W, H = 69, 68
SW, SH = 34, 34  # source grid

# Ink runs per source row: list of inclusive (x0, x1) spans.
BODY = {
    1: [(9, 10), (23, 24)],
    2: [(8, 11), (22, 25)],
    3: [(8, 12), (21, 25)],
    4: [(8, 25)],
    5: [(8, 25)],
    6: [(8, 25)],
    7: [(8, 25)],
    8: [(8, 25)],
    9: [(8, 25)],
    10: [(8, 25)],
    11: [(8, 25)],
    12: [(8, 25)],
    13: [(7, 26)],
    14: [(6, 27)],
    15: [(5, 28)],
    16: [(4, 29)],
    17: [(3, 30)],
    18: [(2, 31)],
    19: [(2, 31)],
    20: [(1, 32)],
    21: [(1, 32)],
    22: [(1, 32)],
    23: [(1, 32)],
    24: [(1, 32)],
    25: [(1, 32)],
    26: [(1, 32)],
    27: [(1, 32)],
    28: [(2, 31)],
    29: [(2, 31)],
    30: [(3, 30)],
    31: [(4, 29)],
    32: [(6, 27)],
}


def build(phase=0):
    """phase 0..3 shifts the belly line, giving a slow breathing cycle."""
    g = [[0] * SW for _ in range(SH)]
    for y, runs in BODY.items():
        for x0, x1 in runs:
            for x in range(x0, x1 + 1):
                g[y][x] = 1

    def cut(y, x0, x1):
        for x in range(x0, x1 + 1):
            if 0 <= y < SH and 0 <= x < SW:
                g[y][x] = 0

    # closed, contented eyes
    cut(8, 12, 13)
    cut(8, 20, 21)
    cut(9, 11, 14)
    cut(9, 19, 22)

    # mouth
    cut(12, 15, 18)
    cut(11, 15, 15)
    cut(11, 18, 18)

    # belly: shallow dome, drifting down a pixel as it "breathes"
    d = (0, 0, 1, 1)[phase]
    cut(20 + d, 11, 22)
    cut(21 + d, 8, 10)
    cut(21 + d, 23, 25)
    cut(22 + d, 6, 7)
    cut(22 + d, 26, 27)

    # line where the feet meet the body, plus the notch between them
    cut(27, 3, 30)
    for y in range(28, 33):
        cut(y, 16, 17)

    # two claws per foot
    for y in (30, 31):
        for cx in (6, 10, 23, 27):
            cut(y, cx, cx)

    return g


def scale(g):
    m = [[0] * W for _ in range(H)]
    for y in range(SH):
        for x in range(SW):
            if g[y][x]:
                for dy in range(2):
                    for dx in range(2):
                        Y, X = y * 2 + dy, x * 2 + dx
                        if Y < H and X < W:
                            m[Y][X] = 1
    return m


def to_bytes(m):
    rb = (W + 7) // 8
    out = []
    for y in range(H):
        for k in range(rb):
            byte = 0
            for bit in range(8):
                x = k * 8 + bit
                if x < W and m[y][x]:
                    byte |= 0x80 >> bit
            out.append(byte)
    return out, rb


def c_array(out):
    return "\n".join(
        "        " + " ".join(f"0x{v:02x}," for v in out[i : i + 15])
        for i in range(0, len(out), 15)
    )


phases = [0, 0, 0, 0, 1, 1, 2, 2, 2, 2, 3, 3, 2, 2, 1, 1]
frames = [scale(build(p)) for p in phases]

with open("snorlax_preview.txt", "w") as f:
    for y in range(H):
        f.write("".join("#" if frames[0][y][x] else "." for x in range(W)) + "\n")

parts = []
for i, fr in enumerate(frames, start=1):
    out, rb = to_bytes(fr)
    parts.append(
        f"""const LV_ATTRIBUTE_MEM_ALIGN LV_ATTRIBUTE_LARGE_CONST LV_ATTRIBUTE_IMG_SNORLAX uint8_t
    snorlax_{i:02d}_map[] = {{
#if CONFIG_NICE_VIEW_WIDGET_INVERTED
        0x00, 0x00, 0x00, 0xff, /*Color of index 0*/
        0xff, 0xff, 0xff, 0xff, /*Color of index 1*/
#else
        0xff, 0xff, 0xff, 0xff, /*Color of index 0*/
        0x00, 0x00, 0x00, 0xff, /*Color of index 1*/
#endif

{c_array(out)}
}};

const lv_img_dsc_t snorlax_{i:02d} = {{
    .header.cf = LV_IMG_CF_INDEXED_1BIT,
    .header.always_zero = 0,
    .header.reserved = 0,
    .header.w = {W},
    .header.h = {H},
    .data_size = {8 + rb * H},
    .data = snorlax_{i:02d}_map,
}};
"""
    )

with open("snorlax.c", "w") as f:
    f.write(
        """#include <lvgl.h>

#ifndef LV_ATTRIBUTE_MEM_ALIGN
#define LV_ATTRIBUTE_MEM_ALIGN
#endif

#ifndef LV_ATTRIBUTE_IMG_SNORLAX
#define LV_ATTRIBUTE_IMG_SNORLAX
#endif

"""
        + "\n".join(parts)
    )

print(f"snorlax.c: {len(frames)} frames, {W}x{H}, {8 + ((W + 7) // 8) * H} bytes each")
