#!/usr/bin/env python3
"""Generate the nice_view Snorlax art from the reference sprite.

Usage: python3 gen_snorlax.py [source.png]  (default: snorlax_sprite.png)

Traced from sprites/pokemon/143.png (PokeAPI), reduced to one bit per pixel:
the sprite's own black outline and blue body become ink, its cream belly and
foot pads become paper, so the belly, arms and claws survive the reduction
instead of being redrawn by hand.

The panel is mounted portrait and its canvas is rotated on the way to the
display, so the art is stored a quarter turn over to arrive upright. Which
way the panel turns isn't visible from the art this replaces, so both
rotations are emitted and CONFIG_NICE_VIEW_SNORLAX_ROTATE_CCW picks one.

Output matches the crystal geometry it replaces: 69x68 INDEXED_1BIT,
9 bytes per row, 620 bytes per frame including the palette header.
"""

import sys

import png

W, H = 69, 68
ART = 66  # the art's square footprint inside the 69x68 buffer
SPRITE = sys.argv[1] if len(sys.argv) > 1 else "snorlax_sprite.png"
INK_LUM = 140  # below this (and opaque) is ink


def trace():
    """Sprite -> 1-bit grid, cropped to its bounding box.

    The whole body stays solid ink; only the borders of the sprite's pale
    regions - belly, arm creases, foot pads - are cut back to paper. Filling
    the pale areas instead would leave a mostly-white shape, since a
    front-facing Snorlax is nearly all belly.
    """
    sw, sh, px, rgba = png.read(SPRITE)
    solid = [[0] * sw for _ in range(sh)]
    pale = [[0] * sw for _ in range(sh)]
    for y in range(sh):
        for x in range(sw):
            r, gg, b, a = rgba(px[y][x])
            if a < 128:
                continue
            solid[y][x] = 1
            if 0.299 * r + 0.587 * gg + 0.114 * b >= INK_LUM:
                pale[y][x] = 1

    # keep only substantial pale areas - the belly, the foot pads. The sprite
    # dithers its highlights, and tracing every stray pale pixel covers the
    # body in speckle.
    seen = [[0] * sw for _ in range(sh)]
    for y in range(sh):
        for x in range(sw):
            if not pale[y][x] or seen[y][x]:
                continue
            stack, blob = [(y, x)], []
            seen[y][x] = 1
            while stack:
                cy, cx = stack.pop()
                blob.append((cy, cx))
                for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < sh and 0 <= nx < sw and pale[ny][nx] and not seen[ny][nx]:
                        seen[ny][nx] = 1
                        stack.append((ny, nx))
            if len(blob) < 500:
                for by, bx in blob:
                    pale[by][bx] = 0

    xs = [x for y in range(sh) for x in range(sw) if solid[y][x]]
    ys = [y for y in range(sh) for x in range(sw) if solid[y][x]]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    crop = lambda m: [row[x0 : x1 + 1] for row in m[y0 : y1 + 1]]
    return crop(solid), crop(pale), x1 - x0 + 1, y1 - y0 + 1


def fit(g, gw, gh, size):
    """Area-majority downscale into a size x size box, aspect preserved."""
    scale = min(size / gw, size / gh)
    dw, dh = max(1, int(gw * scale)), max(1, int(gh * scale))
    out = [[0] * dw for _ in range(dh)]
    for dy in range(dh):
        for dx in range(dw):
            sx0, sx1 = int(dx / scale), max(int(dx / scale) + 1, int((dx + 1) / scale))
            sy0, sy1 = int(dy / scale), max(int(dy / scale) + 1, int((dy + 1) / scale))
            on = tot = 0
            for sy in range(sy0, min(sy1, gh)):
                for sx in range(sx0, min(sx1, gw)):
                    tot += 1
                    on += g[sy][sx]
            # bias toward keeping ink so the outline survives the reduction
            if tot and on * 2 >= tot:
                out[dy][dx] = 1
    return out, dw, dh


def despeckle(g, w, h, rounds=1):
    """Drop lone pixels and fill lone holes.

    The sprite dithers its shading, which survives the reduction as speckle
    and reads as dirt on a 1-bit panel.
    """
    for _ in range(rounds):
        out = [row[:] for row in g]
        for y in range(h):
            for x in range(w):
                n = 0
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        if dy == 0 and dx == 0:
                            continue
                        yy, xx = y + dy, x + dx
                        if 0 <= yy < h and 0 <= xx < w and g[yy][xx]:
                            n += 1
                if g[y][x] and n <= 2:
                    out[y][x] = 0
                elif not g[y][x] and n == 8:
                    out[y][x] = 1
        g = out
    return g


def fill_small_holes(g, w, h, limit=12):
    """Close interior white specks, keep the long boundary lines.

    What's left after the reduction is a mix of real edges - the belly line,
    the arm creases - and shading fragments. The real ones are long connected
    runs; the fragments are small blobs.
    """
    seen = [[0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            if g[y][x] or seen[y][x]:
                continue
            stack, blob, touches_edge = [(y, x)], [], False
            seen[y][x] = 1
            while stack:
                cy, cx = stack.pop()
                blob.append((cy, cx))
                if cy in (0, h - 1) or cx in (0, w - 1):
                    touches_edge = True
                # 8-connected: a diagonal line has no 4-connected neighbours,
                # so 4-connectivity would score the belly line as loose specks
                # and fill it back in.
                for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < h and 0 <= nx < w and not g[ny][nx] and not seen[ny][nx]:
                        seen[ny][nx] = 1
                        stack.append((ny, nx))
            if not touches_edge and len(blob) < limit:
                for by, bx in blob:
                    g[by][bx] = 1
    return g


def place(art, aw, ah, bob):
    """Centre the art in the square footprint, offset vertically by bob."""
    m = [[0] * ART for _ in range(ART)]
    ox = (ART - aw) // 2
    oy = (ART - ah) // 2 + bob
    for y in range(ah):
        for x in range(aw):
            Y, X = y + oy, x + ox
            if art[y][x] and 0 <= Y < ART and 0 <= X < ART:
                m[Y][X] = 1
    return m


def rotate(m, cw):
    """Quarter turn into the 69x68 buffer."""
    out = [[0] * W for _ in range(H)]
    for y in range(ART):
        for x in range(ART):
            src = m[ART - 1 - x][y] if cw else m[x][ART - 1 - y]
            if src and y < H and x < W:
                out[y][x] = 1
    return out


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


def frame_src(i, out, rb):
    return f"""const LV_ATTRIBUTE_MEM_ALIGN LV_ATTRIBUTE_LARGE_CONST LV_ATTRIBUTE_IMG_SNORLAX uint8_t
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


def emit(frames):
    return "\n".join(frame_src(i, *to_bytes(f)) for i, f in enumerate(frames, start=1))


solid, pale, tw, th = trace()

# Reduce the two masks separately, then derive the belly line at final scale.
# Deriving it first and reducing afterwards fragments a 1px curve into specks
# that no amount of cleanup can tell apart from the sprite's dithering.
body, aw, ah = fit(solid, tw, th, ART)
belly, _, _ = fit(pale, tw, th, ART)

art = [row[:] for row in body]
for y in range(ah):
    for x in range(aw):
        if not belly[y][x]:
            continue
        for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            yy, xx = y + dy, x + dx
            if 0 <= yy < ah and 0 <= xx < aw and body[yy][xx] and not belly[yy][xx]:
                art[y][x] = 0
                break

# the belly line survives as one long run; the head's dithered shading
# survives as specks, so clear anything too small to be an edge
art = fill_small_holes(art, aw, ah, limit=8)

# a slow one-pixel rise and fall: sleeping, not idle
bob = [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0]
upright = [place(art, aw, ah, b) for b in bob]
cw = [rotate(u, True) for u in upright]
ccw = [rotate(u, False) for u in upright]

with open("snorlax_upright.txt", "w") as f:
    for row in upright[0]:
        f.write("".join("#" if v else "." for v in row) + "\n")

with open("snorlax_preview.txt", "w") as f:
    for row in cw[0]:
        f.write("".join("#" if v else "." for v in row) + "\n")

with open("snorlax.c", "w") as f:
    f.write(
        """#include <lvgl.h>

#ifndef LV_ATTRIBUTE_MEM_ALIGN
#define LV_ATTRIBUTE_MEM_ALIGN
#endif

#ifndef LV_ATTRIBUTE_IMG_SNORLAX
#define LV_ATTRIBUTE_IMG_SNORLAX
#endif

/* The panel is mounted portrait and the widget canvas is rotated on its way
 * there, so the art is stored a quarter turn over to land upright. Which way
 * the panel turns isn't visible from the art it replaces, so both are here
 * and CONFIG_NICE_VIEW_SNORLAX_ROTATE_CCW picks. Only one is compiled. */

#ifdef CONFIG_NICE_VIEW_SNORLAX_ROTATE_CCW

"""
        + emit(ccw)
        + """
#else

"""
        + emit(cw)
        + """
#endif
"""
    )

print(f"traced {tw}x{th} -> art {aw}x{ah} in {ART}x{ART}, 16 frames each rotation")
