#!/bin/bash
set -e

cd "$(dirname "$0")"

echo "Building OZXAtlas..."

swiftc -parse-as-library \
  -target arm64-apple-macosx12.0 \
  -sdk $(xcrun --show-sdk-path) \
  -framework SwiftUI \
  -framework WebKit \
  -framework AppKit \
  -O \
  -o OZXAtlas_bin \
  OZXAtlas/OZXAtlasApp.swift \
  OZXAtlas/AppState.swift \
  OZXAtlas/ContentView.swift \
  OZXAtlas/AtlasWebView.swift \
  OZXAtlas/SettingsView.swift

# Create .app bundle
mkdir -p OZXAtlas.app/Contents/MacOS
mv OZXAtlas_bin OZXAtlas.app/Contents/MacOS/OZXAtlas
cp OZXAtlas/Info.plist OZXAtlas.app/Contents/Info.plist
echo "APPL????" > OZXAtlas.app/Contents/PkgInfo

echo "Done: OZXAtlas.app"
