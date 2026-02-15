/**
 * ══════════════════════════════════════════════════════════
 *  OVERLORD — Electron Startup Script
 *  This script patches the module cache so that
 *  `require('electron')` returns the built-in Electron API
 *  instead of the npm stub that just exports the exe path.
 * ══════════════════════════════════════════════════════════
 */

// Step 1: Get the npm stub's resolved path so we can intercept it
const stubPath = require.resolve('electron');

// Step 2: Pre-load the stub so it enters the cache
require(stubPath);

// Step 3: Replace the cached export with the real Electron bindings.
// In the Electron main process, `process.type` is 'browser' and the
// internal Electron bindings are accessible. We build the module
// object by hand from `process._linkedBinding`.
if (process.versions && process.versions.electron) {
  // We are inside electron.exe — override the cache.
  // The electron internal module provides everything through
  // the native bindings. Unfortunately we can't access them
  // directly, so instead we use a trick: require the app from
  // the Electron internals via the compiled-in module path.
  
  // Access the internal electron module via the ASAR-packaged
  // path that Electron always provides:
  const electronInternalsPath = require('path').join(
    require('path').dirname(process.execPath),
    'resources', 'electron.asar', 'browser', 'api', 'exports', 'electron.js'
  );
  
  const fs = require('fs');
  if (fs.existsSync(electronInternalsPath)) {
    const realElectron = require(electronInternalsPath);
    require.cache[stubPath] = {
      id: stubPath,
      filename: stubPath,
      loaded: true,
      exports: realElectron
    };
  }
}

// Step 4: Now load the real main script
require('./main.js');
