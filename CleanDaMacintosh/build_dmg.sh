#!/bin/bash
# build_dmg.sh — creates a distributable CleanDaMacintosh.dmg with custom UI
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
APP="CleanDaMacintosh"
BUNDLE="$DIR/$APP.app"
DMG_NAME="$APP.dmg"
DMG_FINAL="$DIR/$DMG_NAME"
DMG_TMP="$DIR/${APP}_tmp.dmg"
STAGING="$DIR/.dmg_staging"
VOL_NAME="$APP"
BACKGROUND="$STAGING/.background/bg.png"

if [ ! -d "$BUNDLE" ]; then
    echo "  ✗  $BUNDLE not found — run build_app.sh first"
    exit 1
fi

echo ""
echo "  ✦  Building $DMG_NAME"
echo "  ══════════════════════════════════════"

# ── 1. Create staging area ─────────────────────────────────────────────────
rm -rf "$STAGING"
mkdir -p "$STAGING/.background"
echo "  [1/7] Staging area created"

# ── 2. Copy app ────────────────────────────────────────────────────────────
cp -R "$BUNDLE" "$STAGING/"
ln -sf /Applications "$STAGING/Applications"
echo "  [2/7] App and Applications symlink copied"

# ── 3. Generate custom DMG background ──────────────────────────────────────
python3 - "$BACKGROUND" << 'PYEOF'
import sys, struct, zlib, math

def lerp(a, b, t): return int(a + (b-a)*max(0,min(1,t)))
def hex2rgb(h): return int(h[1:3],16), int(h[3:5],16), int(h[5:7],16)

def make_dmg_bg(path, W=660, H=400):
    rows = []
    # Colors
    c1 = hex2rgb("#0e0825")  # top-left dark purple
    c2 = hex2rgb("#1a0f38")  # right mid
    c3 = hex2rgb("#2a1060")  # center glow
    c4 = hex2rgb("#0a0418")  # bottom

    for y in range(H):
        row = bytearray(b'\x00')  # filter byte
        for x in range(W):
            # Radial glow from center-left area
            cx, cy = W * 0.38, H * 0.5
            dist = math.sqrt((x-cx)**2 + (y-cy)**2)
            t_rad = min(1.0, dist / (W * 0.55))
            # Base gradient (left-right, top-bottom)
            t_lr = x / W
            t_tb = y / H

            r = lerp(lerp(c1[0],c2[0],t_lr), c4[0], t_tb*0.5)
            g = lerp(lerp(c1[1],c2[1],t_lr), c4[1], t_tb*0.5)
            b = lerp(lerp(c1[2],c2[2],t_lr), c4[2], t_tb*0.5)

            # Center glow overlay (purple-ish)
            glow = max(0.0, 1.0 - t_rad) ** 2.5 * 0.6
            r = lerp(r, c3[0], glow)
            g = lerp(g, c3[1], glow)
            b = lerp(b, c3[2], glow)

            row += bytes([min(255,r), min(255,g), min(255,b)])
        rows.append(bytes(row))

    # Encode as RGB PNG
    def chunk(tag, data):
        blk = tag + data
        return struct.pack('>I', len(data)) + blk + struct.pack('>I', zlib.crc32(blk)&0xffffffff)

    raw = zlib.compress(b''.join(rows), 9)
    png = (b'\x89PNG\r\n\x1a\n'
           + chunk(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', raw)
           + chunk(b'IEND', b''))

    with open(path, 'wb') as f:
        f.write(png)

make_dmg_bg(sys.argv[1])
PYEOF
echo "  [3/7] Background image generated"

# ── 4. Create writable DMG ─────────────────────────────────────────────────
rm -f "$DMG_TMP" "$DMG_FINAL"
hdiutil create \
    -volname "$VOL_NAME" \
    -srcfolder "$STAGING" \
    -ov \
    -format UDRW \
    -size 200m \
    "$DMG_TMP" > /dev/null
echo "  [4/7] Writable DMG created"

# ── 5. Mount and style the DMG window ──────────────────────────────────────
MOUNT_POINT="$(hdiutil attach "$DMG_TMP" -readwrite -noverify -noautoopen \
    | awk -F'\t' 'NF==3{print $NF}' | tail -1)"
echo "  [5/7] DMG mounted at $MOUNT_POINT"

# Copy background into mounted volume
mkdir -p "$MOUNT_POINT/.background"
cp "$BACKGROUND" "$MOUNT_POINT/.background/bg.png"

# Set Finder window appearance via AppleScript
osascript << APPLESCRIPT
tell application "Finder"
    tell disk "$VOL_NAME"
        open
        set current view of container window to icon view
        set toolbar visible of container window to false
        set statusbar visible of container window to false
        set the bounds of container window to {400, 100, 1060, 500}
        set viewOptions to the icon view options of container window
        set arrangement of viewOptions to not arranged
        set icon size of viewOptions to 100
        set background picture of viewOptions to file ".background:bg.png"
        set position of item "$APP.app"   of container window to {180, 185}
        set position of item "Applications" of container window to {480, 185}
        close
        open
        update without registering applications
        delay 2
        close
    end tell
end tell
APPLESCRIPT
echo "  [6/7] DMG window styled"

# ── 6. Detach and convert to compressed read-only DMG ─────────────────────
hdiutil detach "$MOUNT_POINT" -quiet
hdiutil convert "$DMG_TMP" \
    -format UDZO \
    -imagekey zlib-level=9 \
    -o "$DMG_FINAL" > /dev/null
rm -f "$DMG_TMP"
rm -rf "$STAGING"

SIZE=$(du -sh "$DMG_FINAL" | cut -f1)
echo "  [7/7] Compressed DMG created  ($SIZE)"

echo ""
echo "  ✅  $DMG_NAME is ready!"
echo "  ──────────────────────────────────────"
echo "  → $DMG_FINAL"
echo "  Size: $SIZE"
echo ""
echo "  Distribute this DMG — users double-click it,"
echo "  then drag CleanDaMacintosh → Applications."
echo ""
