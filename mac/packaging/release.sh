#!/bin/bash
# Build, sign, notarize and staple Stick.app. Run from anywhere.
#
# Needs (never stored in the repo):
#   SIGN_IDENTITY   e.g. "Developer ID Application: Your Name (TEAMID)"
#   NOTARY_PROFILE  a keychain profile made once with:
#                   xcrun notarytool store-credentials NOTARY_PROFILE --apple-id ... --team-id ...
set -euo pipefail

: "${SIGN_IDENTITY:?Set SIGN_IDENTITY to your Developer ID Application certificate name}"
: "${NOTARY_PROFILE:?Set NOTARY_PROFILE to your notarytool keychain profile}"

HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
APP="dist/Stick.app"

rm -rf build dist
PYTHONPATH=.. ../.venv/bin/python setup.py py2app

# Sign inside-out: every nested binary first, then the bundle, with the hardened runtime.
find "$APP" \( -name '*.so' -o -name '*.dylib' \) -print0 |
  xargs -0 -n1 codesign --force --options runtime --timestamp --sign "$SIGN_IDENTITY"
codesign --force --deep --options runtime --timestamp \
  --entitlements entitlements.plist --sign "$SIGN_IDENTITY" "$APP"
codesign --verify --deep --strict --verbose=2 "$APP"

ditto -c -k --keepParent "$APP" dist/Stick.zip
xcrun notarytool submit dist/Stick.zip --keychain-profile "$NOTARY_PROFILE" --wait
xcrun stapler staple "$APP"
spctl --assess --type execute --verbose "$APP"
echo "Done: $HERE/$APP"
