#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"
ANDROID_DIR="$PROJECT_ROOT/android"

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

echo "✅ APK ready at: $ANDROID_DIR/app/build/outputs/apk/debug/app-debug.apk"
