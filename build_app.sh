#!/bin/bash
# build_app.sh — builds CleanDaMacintosh.app  then calls build_dmg.sh
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
APP="CleanDaMacintosh"
BUNDLE="$DIR/$APP.app"

echo ""
echo "  ✦  Building $APP.app  (v2.0)"
echo "  ══════════════════════════════════════"

# 1. Bundle skeleton
rm -rf "$BUNDLE"
mkdir -p "$BUNDLE/Contents/MacOS"
mkdir -p "$BUNDLE/Contents/Resources"
echo "  [1/5] Bundle structure created"

# 2. Python script
cp "$DIR/$APP.py" "$BUNDLE/Contents/Resources/"
echo "  [2/5] Python source copied"

# 3. Launcher
cat > "$BUNDLE/Contents/MacOS/$APP" << 'LAUNCHER'
#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON=""
for candidate in \
    /opt/homebrew/bin/python3.14 \
    /opt/homebrew/bin/python3.13 \
    /opt/homebrew/bin/python3.12 \
    /opt/homebrew/bin/python3.11 \
    /opt/homebrew/bin/python3.10 \
    /opt/homebrew/bin/python3 \
    /usr/local/bin/python3.14 \
    /usr/local/bin/python3 \
    /usr/bin/python3; do
    if [ -x "$candidate" ] && "$candidate" -c "import tkinter" 2>/dev/null; then
        PYTHON="$candidate"
        break
    fi
done
if [ -z "$PYTHON" ]; then
    osascript -e 'display alert "CleanDaMacintosh — Python Required" message "Python 3 with tkinter is required.\n\nInstall via Homebrew:\n  brew install python-tk\n\nOr download Python from python.org" as critical'
    exit 1
fi
exec "$PYTHON" "$DIR/../Resources/CleanDaMacintosh.py" "$@"
LAUNCHER
chmod +x "$BUNDLE/Contents/MacOS/$APP"
echo "  [3/5] Launcher script created"

# 4. Icon
echo "  [4/5] Generating icon…"
python3 "$DIR/make_icon.py" "$BUNDLE" || echo "        (icon generation non-fatal)"

# 5. Info.plist
cat > "$BUNDLE/Contents/Info.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key><string>CleanDaMacintosh</string>
    <key>CFBundleDisplayName</key><string>CleanDaMacintosh</string>
    <key>CFBundleIdentifier</key><string>com.opensource.cleandamacintosh</string>
    <key>CFBundleVersion</key><string>2.0.0</string>
    <key>CFBundleShortVersionString</key><string>2.0.0</string>
    <key>CFBundleExecutable</key><string>CleanDaMacintosh</string>
    <key>CFBundleIconFile</key><string>AppIcon</string>
    <key>CFBundlePackageType</key><string>APPL</string>
    <key>LSMinimumSystemVersion</key><string>11.0</string>
    <key>NSHighResolutionCapable</key><true/>
    <key>NSRequiresAquaSystemAppearance</key><false/>
    <key>NSAppleScriptEnabled</key><true/>
    <key>LSApplicationCategoryType</key><string>public.app-category.utilities</string>
    <key>NSHumanReadableCopyright</key>
    <string>© 2026 CleanDaMacintosh. Free &amp; Open Source. MIT License.</string>
</dict>
</plist>
PLIST
echo "  [5/5] Info.plist written"

echo ""
echo "  ✅  CleanDaMacintosh.app is ready!"
echo "  ──────────────────────────────────────"
echo "  → $BUNDLE"
echo ""

# Also build DMG
if [ -f "$DIR/build_dmg.sh" ]; then
    bash "$DIR/build_dmg.sh"
fi
