const { spawn, exec } = require('child_process');
const path = require('path');
const fs = require('fs');

// ── Load .env file into process environment ─────────────────
const dotenvPath = path.join(__dirname, '.env');
try {
  if (fs.existsSync(dotenvPath)) {
    const envContent = fs.readFileSync(dotenvPath, 'utf-8');
    envContent.split('\n').forEach(line => {
      const trimmed = line.trim();
      if (trimmed && !trimmed.startsWith('#')) {
        const eqIdx = trimmed.indexOf('=');
        if (eqIdx > 0) {
          const key = trimmed.substring(0, eqIdx).trim();
          const val = trimmed.substring(eqIdx + 1).trim();
          if (!process.env[key]) {  // Don't overwrite existing env vars
            process.env[key] = val;
          }
        }
      }
    });
  }
} catch (e) { /* .env loading is best-effort */ }

/** ── SELF-HEALING BOOTSTRAP ─────────────────────────────────
 * On some Windows systems, ELECTRON_RUN_AS_NODE=1 is set globally,
 * which causes the Electron binary to act as Node and prevents
 * Electron APIs (app, BrowserWindow, ipcMain) from loading.
 * This block detects the conflict and restarts the app correctly.
 */
let electronMod;
try { electronMod = require('electron'); } catch (e) {}

if (typeof electronMod === 'string' || !electronMod || !electronMod.app) {
  const env = { ...process.env };
  delete env.ELECTRON_RUN_AS_NODE;
  const electronPath = (typeof electronMod === 'string') ? electronMod : process.execPath;
  
  spawn(electronPath, [process.argv[1], ...process.argv.slice(2)], {
    env,
    detached: true,
    stdio: 'inherit',
    windowsHide: true
  }).unref();
  process.exit(0);
}

const { app, BrowserWindow, ipcMain, shell, dialog } = electronMod;

// ── SINGLE INSTANCE LOCK ─────────────────────────────────────
const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', (event, commandLine, workingDirectory) => {
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });

  let mainWindow = null;
  let pythonProcess = null;
  let maintProcess = null;

  function createWindow() {
    mainWindow = new BrowserWindow({
      width: 1200,
      height: 800,
      minWidth: 900,
      minHeight: 600,
      backgroundColor: '#030712',
      webPreferences: {
        nodeIntegration: true,
        contextIsolation: false
      },
      frame: true,
    });

    mainWindow.loadFile('index.html');

    mainWindow.on('closed', () => {
      mainWindow = null;
      killPython();
      killMaint();
    });
  }

  function killPython() {
    if (pythonProcess) {
      pythonProcess.kill();
      pythonProcess = null;
    }
  }

  function killMaint() {
    if (maintProcess) {
      maintProcess.kill();
      maintProcess = null;
    }
  }

// ── IPC: Start Build ────────────────────────────────────────
ipcMain.on('start-build', (event, { 
  projectName, prompt, mode, scale, platform, model, budget, fixCycles, sourcePath, 
  enableDocker, enableReadme, enableDebug, enableSetup, enableVoice, enableNoBundle,
  enableClean, enableDecompile, phase, focus,
  archModel, engModel, reviewModel, localModel
}) => {
  killPython();

  // Detect if model is a local Ollama model
  const localModelPrefixes = ['deepseek', 'codellama', 'qwen', 'phi', 'starcoder', 'wizardcoder'];
  const cloudApiPrefixes = ['llama-', 'gemma', 'mixtral', 'gemini'];
  const isCloudApi = cloudApiPrefixes.some(prefix => model.toLowerCase().startsWith(prefix));
  const isLocalModel = !isCloudApi && localModelPrefixes.some(prefix => model.toLowerCase().startsWith(prefix));

  let agentPath, args;

  if (isLocalModel) {
    agentPath = path.join(__dirname, 'local_overlord.py');
    args = [
      agentPath,
      projectName,
      prompt,
      '--model', model
    ];
  } else {
    agentPath = path.join(__dirname, 'agent_brain.py');
    args = [
      agentPath,
      '--project', projectName,
      '--prompt', prompt,
      '--model', model || 'gpt-4o'
    ];
    
    if (budget) args.push('--budget', budget);
    if (scale) args.push('--scale', scale);
    if (platform) args.push('--platform', platform);
    if (mode) args.push('--mode', mode);
    if (fixCycles) args.push('--max-fix-cycles', fixCycles);
    if (sourcePath) args.push('--source', sourcePath);
    if (phase) args.push('--phase', phase);
    if (focus) args.push('--focus', focus);
    
    if (enableDocker) args.push('--docker');
    if (enableReadme) args.push('--readme');
    if (enableDebug)  args.push('--debug');
    if (enableSetup)  args.push('--setup');
    if (enableVoice)  args.push('--voice');
    if (enableNoBundle) args.push('--no-bundle');
    if (enableClean)    args.push('--clean');
    if (enableDecompile) args.push('--decompile');
    
    if (archModel)    args.push('--arch-model', archModel);
    if (engModel)     args.push('--eng-model', engModel);
    if (reviewModel)  args.push('--review-model', reviewModel);
    if (localModel)   args.push('--local-model', localModel);
  }

  // ── Build key pool env vars from settings ──
  const settingsPath = path.join(__dirname, 'settings.json');
  const poolEnv = {};
  try {
    if (fs.existsSync(settingsPath)) {
      const settings = JSON.parse(fs.readFileSync(settingsPath, 'utf-8'));
      const keyMap = {
        openaiKey:    { single: 'OPENAI_API_KEY',    pool: 'OPENAI_API_KEYS' },
        groqKey:      { single: 'GROQ_API_KEY',      pool: 'GROQ_API_KEYS' },
        geminiKey:    { single: 'GEMINI_API_KEY',     pool: 'GEMINI_API_KEYS' },
        anthropicKey: { single: 'ANTHROPIC_API_KEY',  pool: 'ANTHROPIC_API_KEYS' },
      };
      for (const [field, envNames] of Object.entries(keyMap)) {
        const raw = settings[field] || '';
        const keys = raw.split(/[\n,]/).map(k => k.trim()).filter(k => k.length > 0);
        if (keys.length > 0) {
          poolEnv[envNames.single] = keys[0]; // backward compat: first key
          if (keys.length > 1) {
            poolEnv[envNames.pool] = keys.join(','); // full pool
          }
        }
      }
    }
  } catch (e) { /* settings not required */ }

  pythonProcess = spawn('python', args, {
    cwd: __dirname,
    env: { ...process.env, ...poolEnv, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' },
    windowsHide: true
  });

  pythonProcess.stdout.on('data', (data) => {
    const lines = data.toString().split('\n').filter(l => l.trim());
    lines.forEach(line => {
      event.reply('log-update', line);
    });
  });

  pythonProcess.stderr.on('data', (data) => {
    const lines = data.toString().split('\n').filter(l => l.trim());
    lines.forEach(line => {
      event.reply('log-update', `[ERROR] ${line}`);
    });
  });

  pythonProcess.on('close', (code) => {
    if (code === 0) {
      event.reply('build-complete', { success: true });
    } else {
      event.reply('build-complete', { success: false, code });
    }
    pythonProcess = null;
  });

  pythonProcess.on('error', (err) => {
    event.reply('log-update', `[ERROR] Failed to start Python: ${err.message}`);
    event.reply('build-complete', { success: false });
    pythonProcess = null;
  });
});

// ── IPC: Cancel Build ───────────────────────────────────────
ipcMain.on('cancel-build', (event) => {
  if (pythonProcess) {
    killPython();
    event.reply('log-update', '[ERROR] Build aborted by operator.');
    event.reply('build-complete', { success: false, aborted: true });
  }
});

// ── IPC: Open Folder ────────────────────────────────────────
ipcMain.on('open-folder', (event, folderPath) => {
  shell.openPath(folderPath);
});

// ── IPC: Run .exe ───────────────────────────────────────────
ipcMain.on('run-exe', (event, projectPath) => {
  const distPath = path.join(projectPath, 'dist');
  if (!fs.existsSync(distPath)) {
    event.reply('log-update', '[ERROR] No dist/ folder found in project.');
    return;
  }

  try {
    const exeFiles = fs.readdirSync(distPath).filter(f => f.endsWith('.exe'));
    if (exeFiles.length > 0) {
      const exePath = path.join(distPath, exeFiles[0]);
      shell.openPath(exePath);
    } else {
      // Try LAUNCH.bat
      const launchBat = path.join(projectPath, 'LAUNCH.bat');
      if (fs.existsSync(launchBat)) {
        shell.openPath(launchBat);
      } else {
        event.reply('log-update', '[ERROR] No .exe or LAUNCH.bat found.');
      }
    }
  } catch (e) {
    event.reply('log-update', `[ERROR] Failed to run exe: ${e.message}`);
  }
});

// ── IPC: Run Maintenance ────────────────────────────────────
ipcMain.on('run-maintenance', (event, { libraryPath }) => {
  killMaint();

  const stewardPath = path.join(__dirname, 'maintenance_steward.py');
  if (!fs.existsSync(stewardPath)) {
    event.reply('maint-log', '[ERROR] maintenance_steward.py not found.');
    event.reply('maint-complete', { success: false });
    return;
  }

  maintProcess = spawn('python', [stewardPath, '--library', libraryPath], {
    cwd: __dirname,
    env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' },
    windowsHide: true
  });

  maintProcess.stdout.on('data', (data) => {
    const lines = data.toString().split('\n').filter(l => l.trim());
    lines.forEach(line => {
      event.reply('maint-log', line);
    });
  });

  maintProcess.stderr.on('data', (data) => {
    const lines = data.toString().split('\n').filter(l => l.trim());
    lines.forEach(line => {
      event.reply('maint-log', `[ERROR] ${line}`);
    });
  });

  maintProcess.on('close', (code) => {
    event.reply('maint-complete', { success: code === 0 });
    maintProcess = null;
  });

  maintProcess.on('error', (err) => {
    event.reply('maint-log', `[ERROR] Failed to start maintenance: ${err.message}`);
    event.reply('maint-complete', { success: false });
    maintProcess = null;
  });
});

// ── IPC: Open Folder ───────────────────────────────────────
ipcMain.on('open-folder', (event, pPath) => {
  shell.openPath(pPath);
});

// ── IPC: API Key Check ──────────────────────────────────────
ipcMain.handle('check-api-keys', async () => {
  const settingsPath = path.join(__dirname, 'settings.json');
  let settings = {};
  if (fs.existsSync(settingsPath)) {
    try {
      settings = JSON.parse(fs.readFileSync(settingsPath, 'utf-8'));
    } catch (e) {}
  }

  return {
    openai:    !!(process.env.OPENAI_API_KEY || settings.openaiKey),
    gemini:    !!(process.env.GEMINI_API_KEY || settings.geminiKey),
    anthropic: !!(process.env.ANTHROPIC_API_KEY || settings.anthropicKey),
    groq:      !!(process.env.GROQ_API_KEY || settings.groqKey)
  };
});

// ── IPC: Select Directory ───────────────────────────────────
ipcMain.on('select-directory', async (event) => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory']
  });
  if (!result.canceled && result.filePaths.length > 0) {
    event.reply('directory-selected', result.filePaths[0]);
  }
});

// ── App Lifecycle ───────────────────────────────────────────
app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  killPython();
  killMaint();
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});
}
