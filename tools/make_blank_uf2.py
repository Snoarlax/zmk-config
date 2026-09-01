#!/usr/bin/env python3
"""Generate a UF2 that blanks the stale blelulu app region on a nice_nano_v2.

The blelulu board links its application at 0x1000; nice_nano_v2 links at
0x26000. Flashing blelulu firmware therefore left an application image in
0x1000-0x26000, a region no nice_nano UF2 ever rewrites. Writing 0xFF over
that range makes the bootloader's page-erase blank it.

Touches neither the MBR (0x0-0x1000) nor the bootloader (0xF4000+), so the
board can always re-enter bootloader mode.
"""

import struct

UF2_MAGIC_START0 = 0x0A324655  # "UF2\n"
UF2_MAGIC_START1 = 0x9E5D5157
UF2_MAGIC_END = 0x0AB16F30
UF2_FLAG_FAMILY_ID = 0x00002000
FAMILY_NRF52840 = 0xADA52840

START = 0x1000
END = 0x26000
PAYLOAD = 256

out = "blank_0x1000_0x26000.uf2"
addrs = list(range(START, END, PAYLOAD))
num_blocks = len(addrs)
blank = b"\xff" * PAYLOAD

with open(out, "wb") as f:
    for i, addr in enumerate(addrs):
        header = struct.pack(
            "<IIIIIIII",
            UF2_MAGIC_START0,
            UF2_MAGIC_START1,
            UF2_FLAG_FAMILY_ID,
            addr,
            PAYLOAD,
            i,
            num_blocks,
            FAMILY_NRF52840,
        )
        block = header + blank + b"\x00" * (476 - PAYLOAD) + struct.pack("<I", UF2_MAGIC_END)
        assert len(block) == 512, len(block)
        f.write(block)

print(f"{out}: {num_blocks} blocks, {num_blocks * 512} bytes")
print(f"covers 0x{START:05X}-0x{END:05X} ({END - START} bytes) with 0xFF")
