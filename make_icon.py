#!/usr/bin/env python3
"""
Generate CleanDaMacintosh.icns — premium pink/purple sparkle icon.
Pure Python stdlib only — no pip installs required.
Usage: python3 make_icon.py <AppBundle.app>
"""
import struct, zlib, math, os, subprocess, sys, tempfile

def lerp(a, b, t):
    return a + (b - a) * max(0.0, min(1.0, t))

def make_png(size):
    cx = cy = size / 2.0
    R  = cx * 0.94
    fe = max(2.0, size * 0.012)

    rows = []
    for y in range(size):
        row = bytearray(b'\x00')
        for x in range(size):
            dx, dy = x - cx, y - cy
            dist   = math.sqrt(dx*dx + dy*dy)

            # Circle mask with AA
            mask = max(0.0, min(1.0, (R - dist + fe) / (fe*2)))
            if mask == 0:
                row += b'\x00\x00\x00\x00'
                continue

            # Radial dark-purple background gradient
            t  = dist / R
            br = int(lerp(0x28, 0x0a, t))
            bg = int(lerp(0x10, 0x03, t))
            bb = int(lerp(0x52, 0x14, t))

            nx, ny = dx / R, dy / R

            # 4-pointed star via superellipse (k < 1 makes points)
            k    = 0.40
            star = abs(nx)**k + abs(ny)**k
            sm   = max(0.0, min(1.0, (0.78 - star) / 0.20))

            # Pink (#e91e8c) → Purple (#7c3aed) star color
            t2  = min(1.0, star * 0.9)
            sr  = int(lerp(0xe9, 0x7c, t2))
            sg  = int(lerp(0x1e, 0x3a, t2))
            sb_ = int(lerp(0x8c, 0xed, t2))
            pr  = int(lerp(br, sr, sm**0.6))
            pg  = int(lerp(bg, sg, sm**0.6))
            pb  = int(lerp(bb, sb_, sm**0.6))

            # Diagonal secondary rays (45°, blue #38bdf8)
            nx2 = (dx + dy) / (R * math.sqrt(2))
            ny2 = (dy - dx) / (R * math.sqrt(2))
            s2  = abs(nx2)**k + abs(ny2)**k
            m2  = max(0.0, min(1.0, (0.55 - s2) / 0.18))
            pr  = int(lerp(pr, 0x38, m2*0.65))
            pg  = int(lerp(pg, 0xbd, m2*0.65))
            pb  = int(lerp(pb, 0xf8, m2*0.65))

            # White-hot center glow
            cfe   = R * 0.06
            cmask = max(0.0, min(1.0, (R*0.10 - dist + cfe) / (cfe*2)))
            pr = int(lerp(pr, 255, cmask**0.5 * 0.95))
            pg = int(lerp(pg, 255, cmask**0.5 * 0.95))
            pb = int(lerp(pb, 255, cmask**0.5 * 0.95))

            # Rim highlight (subtle pink on outer edge)
            rim = max(0.0, min(1.0, (dist - R*0.82) / (R*0.12)))
            pr  = int(lerp(pr, 0xe9, rim * 0.28))
            pg  = int(lerp(pg, 0x1e, rim * 0.08))
            pb  = int(lerp(pb, 0x8c, rim * 0.18))

            row += bytes([min(255,pr), min(255,pg), min(255,pb), int(mask*255)])
        rows.append(bytes(row))

    def chunk(tag, data):
        blk = tag + data
        return struct.pack('>I', len(data)) + blk + struct.pack('>I', zlib.crc32(blk)&0xffffffff)

    raw = zlib.compress(b''.join(rows), 9)
    return (b'\x89PNG\r\n\x1a\n'
            + chunk(b'IHDR', struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0))
            + chunk(b'IDAT', raw)
            + chunk(b'IEND', b''))


def build_icns(app_bundle):
    res = os.path.join(app_bundle, "Contents", "Resources")
    os.makedirs(res, exist_ok=True)
    icns_path = os.path.join(res, "AppIcon.icns")

    sizes = [16, 32, 64, 128, 256, 512, 1024]
    with tempfile.TemporaryDirectory() as tmp:
        iconset = os.path.join(tmp, "AppIcon.iconset")
        os.makedirs(iconset)
        for sz in sizes:
            data = make_png(sz)
            with open(os.path.join(iconset, f"icon_{sz}x{sz}.png"), "wb") as f:
                f.write(data)
            if sz <= 512:
                data2 = make_png(sz * 2)
                with open(os.path.join(iconset, f"icon_{sz}x{sz}@2x.png"), "wb") as f:
                    f.write(data2)

        r = subprocess.run(["iconutil","-c","icns",iconset,"-o",icns_path],
                           capture_output=True)
        if r.returncode == 0:
            print(f"  [icon] AppIcon.icns → {os.path.getsize(icns_path)//1024} KB")
            return True
        else:
            with open(os.path.join(res,"AppIcon.png"),"wb") as f:
                f.write(make_png(512))
            print("  [icon] PNG fallback written")
            return False


if __name__ == "__main__":
    bundle = sys.argv[1] if len(sys.argv) > 1 else "."
    build_icns(bundle)
