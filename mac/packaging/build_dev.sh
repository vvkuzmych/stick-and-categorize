#!/bin/bash
# Build Stick.app for this Mac and sign it with a stable local certificate.
# An ad-hoc signature changes with every build, so macOS asks for the microphone again each time.
# A fixed certificate keeps the app's identity, so the permission survives rebuilds.
# It uses the system LibreSSL: the Homebrew OpenSSL writes PKCS12 files that macOS cannot import.
# The certificate is made once in your login keychain. It is only for this Mac (use release.sh to ship).
set -euo pipefail

IDENTITY="${DEV_SIGN_IDENTITY:-Stick Local Dev}"
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE"
APP="dist/Stick.app"

if ! security find-identity -p codesigning | grep -q "\"$IDENTITY\""; then
  echo "Creating the local signing certificate \"$IDENTITY\" in your login keychain..."
  TMP="$(mktemp -d)"
  trap 'rm -rf "$TMP"' EXIT
  PASS="$(uuidgen)"
  cat > "$TMP/openssl.cnf" <<CNF
[req]
distinguished_name = dn
x509_extensions = ext
prompt = no
[dn]
CN = $IDENTITY
[ext]
basicConstraints = critical,CA:false
keyUsage = critical,digitalSignature
extendedKeyUsage = critical,codeSigning
CNF
  /usr/bin/openssl req -x509 -newkey rsa:2048 -nodes -days 3650 -config "$TMP/openssl.cnf" \
    -keyout "$TMP/key.pem" -out "$TMP/cert.pem" 2>/dev/null
  /usr/bin/openssl pkcs12 -export -inkey "$TMP/key.pem" -in "$TMP/cert.pem" -out "$TMP/id.p12" \
    -passout "pass:$PASS" 2>/dev/null
  security import "$TMP/id.p12" -k "$HOME/Library/Keychains/login.keychain-db" -P "$PASS" \
    -T /usr/bin/codesign >/dev/null
fi

rm -rf dist
PYTHONPATH=.. ../.venv/bin/python setup.py py2app >/dev/null

# Inside-out: nested binaries first, then the bundle.
find "$APP" \( -name '*.so' -o -name '*.dylib' \) -print0 |
  xargs -0 -n1 codesign --force --sign "$IDENTITY"
codesign --force --deep --sign "$IDENTITY" "$APP"
codesign --verify --deep --strict "$APP"
codesign -d -r- "$APP" 2>&1 | grep designated
echo "Built and signed: $HERE/$APP"
