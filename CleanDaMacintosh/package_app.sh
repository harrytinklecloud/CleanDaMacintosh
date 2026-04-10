#!/bin/bash
# Packages CleanDaMacintosh into a standalone .app bundle using py2app (optional)
# For quick use, just run: python3 CleanDaMacintosh.py
echo "Building CleanDaMacintosh.app..."

# Check py2app
if ! python3 -c "import py2app" 2>/dev/null; then
    echo "Installing py2app..."
    pip3 install py2app
fi

# Create setup.py
cat > /tmp/cdm_setup.py <<'EOF'
from setuptools import setup

APP = ['CleanDaMacintosh.py']
OPTIONS = {
    'argv_emulation': False,
    'iconfile': None,
    'plist': {
        'CFBundleName': 'CleanDaMacintosh',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleIdentifier': 'com.opensource.cleandamacintosh',
        'NSHighResolutionCapable': True,
    },
}
setup(app=APP, options={'py2app': OPTIONS}, setup_requires=['py2app'])
EOF

cp /tmp/cdm_setup.py setup.py
python3 setup.py py2app
echo "Done! App is in ./dist/CleanDaMacintosh.app"
