#!/usr/bin/env python3
"""Generate the nice_view Snorlax art from PNG artwork.

Usage:
  gen_snorlax.py                       # the bundled reference sprite
  gen_snorlax.py frame1.png frame2.png # one PNG per animation frame
  gen_snorlax.py sheet.png --frames 2  # a Piskel spritesheet, frames in a row

Draw upright and roughly square; the rotation for the panel is applied here.

Reduction to one bit: opaque pixels become ink, transparent becomes
background, and the border of any large pale region - a belly, say - is cut
back to paper, so it reads as an outline instead of a hole.

The nice_view is mounted portrait and the widget canvas is rotated on its way
to the panel, so art drawn upright is stored a quarter turn over. Which way
the panel turns isn't knowable from the art this replaces, so both rotations
are emitted and CONFIG_NICE_VIEW_SNORLAX_ROTATE_CCW picks one.

Output matches the crystal geometry it replaces: 69x68 INDEXED_1BIT,
9 bytes per row, 620 bytes per frame including the palette header.
"""

import sys

import png

W, H = 69, 68
ART = 66  # the art's square footprint inside the 69x68 buffer
INK_LUM = 140  # below this (and opaque) is ink
PALE_MIN = 500  # smallest pale region worth outlining, in source pixels


def masks(px, rgba, x0, x1, y0, y1):
    """Slice of a decoded image -> (solid, pale) masks."""
    w, h = x1 - x0, y1 - y0
    solid = [[0] * w for _ in range(h)]
    pale = [[0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            r, g, b, a = rgba(px[y0 + y][x0 + x])
            if a < 128:
                continue
            solid[y][x] = 1
            if 0.299 * r + 0.587 * g + 0.114 * b >= INK_LUM:
                pale[y][x] = 1

    # Keep only substantial pale areas. Sprites dither their highlights, and
    # outlining every stray pale pixel covers the body in speckle.
    seen = [[0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            if not pale[y][x] or seen[y][x]:
                continue
            stack, blob = [(y, x)], []
            seen[y][x] = 1
            while stack:
                cy, cx = stack.pop()
                blob.append((cy, cx))
                for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < h and 0 <= nx < w and pale[ny][nx] and not seen[ny][nx]:
                        seen[ny][nx] = 1
                        stack.append((ny, nx))
            if len(blob) < PALE_MIN:
                for by, bx in blob:
                    pale[by][bx] = 0

    return solid, pale, w, h


def load(paths, sheet_frames):
    """Read the artwork into a list of (solid, pale) masks, one per frame."""
    frames = []
    if sheet_frames:
        sw, sh, px, rgba = png.read(paths[0])
        step = sw // sheet_frames
        for i in range(sheet_frames):
            frames.append(masks(px, rgba, i * step, (i + 1) * step, 0, sh))
    else:
        for p in paths:
            sw, sh, px, rgba = png.read(p)
            frames.append(masks(px, rgba, 0, sw, 0, sh))

    sizes = {(f[2], f[3]) for f in frames}
    if len(sizes) != 1:
        sys.exit(f"frames differ in size: {sorted(sizes)}")
    return frames


def shared_box(frames):
    """One bounding box across every frame, so the animation doesn't jitter."""
    x0 = y0 = 10**9
    x1 = y1 = -1
    for solid, _, w, h in frames:
        for y in range(h):
            for x in range(w):
                if solid[y][x]:
                    x0, x1 = min(x0, x), max(x1, x)
                    y0, y1 = min(y0, y), max(y1, y)
    if x1 < 0:
        sys.exit("artwork is empty - every pixel is transparent")
    return x0, x1, y0, y1


def fit(g, gw, gh, dw, dh, scale):
    """Area-majority downscale onto a fixed destination size."""
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
            # bias toward keeping ink so outlines survive the reduction
            if tot and on * 2 >= tot:
                out[dy][dx] = 1
    return out


def outline_pale(body, pale, w, h):
    """Solid body, with the border of the pale region cut back to paper."""
    art = [row[:] for row in body]
    for y in range(h):
        for x in range(w):
            if not pale[y][x]:
                continue
            for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                yy, xx = y + dy, x + dx
                if 0 <= yy < h and 0 <= xx < w and body[yy][xx] and not pale[yy][xx]:
                    art[y][x] = 0
                    break
    return art


def fill_small_holes(g, w, h, limit=8):
    """Close interior white specks, keep the long boundary lines.

    8-connected on purpose: a diagonal line has no 4-connected neighbours, so
    4-connectivity would score a diagonal outline as loose specks and fill it.
    """
    seen = [[0] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            if g[y][x] or seen[y][x]:
                continue
            stack, blob, edge = [(y, x)], [], False
            seen[y][x] = 1
            while stack:
                cy, cx = stack.pop()
                blob.append((cy, cx))
                if cy in (0, h - 1) or cx in (0, w - 1):
                    edge = True
                for dy, dx in ((-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < h and 0 <= nx < w and not g[ny][nx] and not seen[ny][nx]:
                        seen[ny][nx] = 1
                        stack.append((ny, nx))
            if not edge and len(blob) < limit:
                for by, bx in blob:
                    g[by][bx] = 1
    return g


def place(art, aw, ah, bob=0):
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
    body = "\n".join(frame_src(i, *to_bytes(f)) for i, f in enumerate(frames, start=1))
    refs = ", ".join(f"&snorlax_{i:02d}" for i in range(1, len(frames) + 1))
    return body + f"""
const lv_img_dsc_t *snorlax_imgs[] = {{{refs}}};
const size_t snorlax_frame_count = {len(frames)};
"""


def main():
    args = [a for a in sys.argv[1:]]
    sheet_frames = 0
    if "--frames" in args:
        i = args.index("--frames")
        sheet_frames = int(args[i + 1])
        del args[i : i + 2]
    paths = args or ["snorlax_sprite.png"]

    src = load(paths, sheet_frames)
    x0, x1, y0, y1 = shared_box(src)
    bw, bh = x1 - x0 + 1, y1 - y0 + 1
    scale = min(ART / bw, ART / bh)
    dw, dh = max(1, int(bw * scale)), max(1, int(bh * scale))

    upright = []
    for solid, pale, w, h in src:
        crop = lambda m: [row[x0 : x1 + 1] for row in m[y0 : y1 + 1]]
        body = fit(crop(solid), bw, bh, dw, dh, scale)
        belly = fit(crop(pale), bw, bh, dw, dh, scale)
        art = fill_small_holes(outline_pale(body, belly, dw, dh), dw, dh)
        upright.append(place(art, dw, dh))

    # A single still gets a slow one-pixel rise and fall so it reads as
    # breathing. Supplied frames are the animation and are left alone.
    if len(upright) == 1:
        solid, pale, w, h = src[0]
        crop = lambda m: [row[x0 : x1 + 1] for row in m[y0 : y1 + 1]]
        body = fit(crop(solid), bw, bh, dw, dh, scale)
        belly = fit(crop(pale), bw, bh, dw, dh, scale)
        art = fill_small_holes(outline_pale(body, belly, dw, dh), dw, dh)
        bobs = [0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0]
        upright = [place(art, dw, dh, b) for b in bobs]

    with open("snorlax_upright.txt", "w") as f:
        for row in upright[0]:
            f.write("".join("#" if v else "." for v in row) + "\n")

    with open("snorlax.c", "w") as f:
        f.write(
            """#include <lvgl.h>
#include <stddef.h>

#ifndef LV_ATTRIBUTE_MEM_ALIGN
#define LV_ATTRIBUTE_MEM_ALIGN
#endif

#ifndef LV_ATTRIBUTE_IMG_SNORLAX
#define LV_ATTRIBUTE_IMG_SNORLAX
#endif

/* Generated by gen_snorlax.py - edit the artwork, not this file.
 *
 * The panel is mounted portrait and the widget canvas is rotated on its way
 * there, so the art is stored a quarter turn over to land upright. Which way
 * the panel turns isn't visible from the art it replaces, so both are here
 * and CONFIG_NICE_VIEW_SNORLAX_ROTATE_CCW picks. Only one is compiled. */

#ifdef CONFIG_NICE_VIEW_SNORLAX_ROTATE_CCW

"""
            + emit([rotate(u, False) for u in upright])
            + """
#else

"""
            + emit([rotate(u, True) for u in upright])
            + """
#endif
"""
        )

    print(f"{len(upright)} frame(s), art {dw}x{dh} in {ART}x{ART} -> snorlax.c")
    print("preview of frame 1 -> snorlax_upright.txt")


main()
