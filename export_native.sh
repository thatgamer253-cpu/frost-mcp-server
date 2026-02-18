#!/bin/bash
# --- Creation Engine to Web OS Native Bundle Script ---

# 1. Define Paths
PROJECT_NAME=$1
SOURCE_DIR="./src/native_programs/$PROJECT_NAME"
EXPORT_DIR="./nexus-os-react/public/exports/$PROJECT_NAME"
ASSETS_DIR="$SOURCE_DIR/assets"

mkdir -p $EXPORT_DIR

echo "🚀 Compiling $PROJECT_NAME to Native WebAssembly..."

# 2. Run Emscripten Compiler
# -s WASM=1: Enables Wasm output
# -s USE_PTHREADS=1: Enables multi-threading for AI/3D tasks
# -s FULL_ES3=1: Provides WebGL 2.0 (OpenGL ES 3.0) support
# --preload-file: Bundles your 3D models/textures into a virtual file system
emcc $SOURCE_DIR/main.cpp \
    -o $EXPORT_DIR/binary.js \
    -O3 \
    -s WASM=1 \
    -s ALLOW_MEMORY_GROWTH=1 \
    -s USE_PTHREADS=1 \
    -s FULL_ES3=1 \
    -s USE_SDL=2 \
    --preload-file $ASSETS_DIR@/assets \
    -s EXPORTED_RUNTIME_METHODS='["ccall", "cwrap"]' \
    -s MODULARIZE=1 \
    -s 'EXPORT_NAME="NativeApp"'

# 3. Generate the OS Manifest (System Birth Certificate)
cat <<EOF > $EXPORT_DIR/app_manifest.json
{
  "app_id": "$PROJECT_NAME",
  "name": "${PROJECT_NAME^^}",
  "type": "native_engine_build",
  "entry_point": {
    "binary": "/exports/$PROJECT_NAME/binary.wasm",
    "glue_js": "/exports/$PROJECT_NAME/binary.js"
  },
  "resources": {
    "icon": "⚡",
    "min_memory": "1024MB"
  }
}
EOF

echo "✅ Done! Project is ready for the Overlord OS."
