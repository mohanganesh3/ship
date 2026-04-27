#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
ANDROID_DIR="$PROJECT_ROOT/android"
APK_PATH="$ANDROID_DIR/app/build/outputs/apk/debug/app-debug.apk"

export JAVA_HOME="${JAVA_HOME:-/Library/Java/JavaVirtualMachines/zulu-17.jdk/Contents/Home}"
if [[ -d "/Users/mohanganesh/Library/Android/sdk" ]]; then
    export ANDROID_HOME="/Users/mohanganesh/Library/Android/sdk"
elif [[ -d "/Users/mohanganesh/Library/Android/Sdk" ]]; then
    export ANDROID_HOME="/Users/mohanganesh/Library/Android/Sdk"
else
    echo "❌ Android SDK not found at expected paths. Set ANDROID_HOME and retry."
    exit 1
fi
export PATH="/opt/homebrew/bin:$JAVA_HOME/bin:$ANDROID_HOME/platform-tools:$PATH"

DEVICE_ID="${1:-}"
if [[ -z "$DEVICE_ID" ]]; then
    DEVICE_ID="$(adb devices | awk 'NR>1 && $2=="device" {print $1; exit}')"
fi

if [[ -z "$DEVICE_ID" ]]; then
    echo "❌ No connected Android device found. Connect device and enable USB debugging."
    exit 1
fi

echo "🚀 Building and deploying to device: $DEVICE_ID"

echo "📦 Bundling JS for Android..."
cd "$PROJECT_ROOT"
npx react-native bundle \
    --platform android \
    --dev false \
    --entry-file node_modules/expo-router/entry.js \
    --bundle-output android/app/src/main/assets/index.android.bundle \
    --assets-dest android/app/src/main/res

echo "🛠️ Building debug APK (no clean)..."
"$ANDROID_DIR/gradlew" -p "$ANDROID_DIR" assembleDebug --no-daemon

echo "📲 Installing APK..."
adb -s "$DEVICE_ID" install -r "$APK_PATH"

echo "✅ Installation complete."
