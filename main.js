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
    stdio: 'inherit'
  }).unref();
  process.exit(0);
}

const { app, BrowserWindow, ipcMain, shell, dialog } = electronMod;

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
ipcMain.on('start-build', (event, { projectName, prompt, outputDir, model, engModel, reviewModel, apiKey, enableDocker, enableReadme, enableDebug, enableBundle, mode, sourcePath, phase, focus, decompileOnly, cleanOutput }) => {
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
      '--output', outputDir || './output',
      '--model', model
    ];
    if (engModel) {
      args.push('--arch-model', model);
      args.push('--eng-model', engModel);
    }
    // TODO: Add upgrade support to local_overlord if needed, for now only agent_brain
  } else {
    agentPath = path.join(__dirname, 'agent_brain.py');
    args = [
      agentPath,
      '--project', projectName,
      '--prompt', prompt,
      '--output', outputDir || './output',
      '--model', model || 'gpt-4o'
    ];
    if (engModel) {
      args.push('--arch-model', model || 'gpt-4o');
      args.push('--eng-model', engModel);
    }
    if (apiKey) args.push('--api-key', apiKey);
    if (reviewModel) args.push('--review-model', reviewModel);
    if (enableDocker) args.push('--docker');
    if (enableReadme) args.push('--readme');
    if (enableDebug) args.push('--debug');
    if (enableBundle === false) args.push('--no-bundle');
    
    // NEW: Upgrade / Reverse Flow
    if (mode === 'upgrade' || mode === 'reverse') {
        args.push('--mode', mode);
        if (sourcePath) {
            args.push('--source', sourcePath);
        }
    }

    // NEW: Advanced Controls
    if (decompileOnly) args.push('--decompile-only');
    if (phase && phase !== 'all') args.push('--phase', phase);
    if (focus) args.push('--focus', focus);
    if (cleanOutput) args.push('--clean');

    args.push('--dashboard');  // Always activate EventBus for Antigravity Dashboard
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
    env: { ...process.env, ...poolEnv, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' }
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

// ── IPC: Launch Antigravity Dashboard ───────────────────────
let dashboardProcess = null;

ipcMain.on('launch-dashboard', (event, { projectPath }) => {
  // Kill any existing dashboard
  if (dashboardProcess) {
    try { dashboardProcess.kill(); } catch {}
    dashboardProcess = null;
  }

  const dashboardScript = path.join(__dirname, 'antigravity_dashboard.py');
  if (!fs.existsSync(dashboardScript)) {
    event.reply('log-update', '[ERROR] antigravity_dashboard.py not found.');
    return;
  }

  event.reply('log-update', '[SYSTEM]  🚀 Launching Antigravity Dashboard...');

  dashboardProcess = spawn('streamlit', [
    'run', dashboardScript,
    '--', '--project', projectPath || './output'
  ], {
    cwd: __dirname,
    env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' },
  });

  dashboardProcess.stdout.on('data', (data) => {
    const text = data.toString();
    // Auto-open browser when Streamlit reports its URL
    if (text.includes('Local URL:') || text.includes('localhost:8501')) {
      const { shell: electronShell } = require('electron');
      electronShell.openExternal('http://localhost:8501');
    }
  });

  dashboardProcess.stderr.on('data', (data) => {
    const text = data.toString();
    if (text.includes('Local URL:') || text.includes('localhost:8501')) {
      const { shell: electronShell } = require('electron');
      electronShell.openExternal('http://localhost:8501');
    }
  });

  dashboardProcess.on('close', () => {
    dashboardProcess = null;
  });

  dashboardProcess.on('error', (err) => {
    event.reply('log-update', `[ERROR] Failed to launch dashboard: ${err.message}`);
    dashboardProcess = null;
  });
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
    env: { ...process.env, PYTHONIOENCODING: 'utf-8', PYTHONUTF8: '1' }
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

// ── IPC: Get Project Details ────────────────────────────────
ipcMain.handle('get-project-details', async (event, projectPath) => {
  try {
    const manifestPath = path.join(projectPath, 'package_manifest.json');
    const costPath = path.join(projectPath, 'cost_report.json');
    let name = path.basename(projectPath);
    let totalCost = '$0.00';
    let fileCount = 0;
    
    // Read manifest/cost if available
    try {
        const costData = JSON.parse(fs.readFileSync(costPath, 'utf-8'));
        if (costData.total_cost) totalCost = `$${costData.total_cost.toFixed(2)}`;
    } catch {}

    try {
        const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
        if (manifest.project) name = manifest.project;
        if (manifest.total_files) fileCount = manifest.total_files;
    } catch {}

    // Fallback: Recursively count files if manifest doesn't have it
    if (fileCount === 0) {
        let count = 0;
        function countFiles(dir) {
            try {
                const files = fs.readdirSync(dir, { withFileTypes: true });
                for (const file of files) {
                    if (file.isDirectory() && !file.name.startsWith('.') && file.name !== 'node_modules' && file.name !== 'venv' && file.name !== '__pycache__') {
                        countFiles(path.join(dir, file.name));
                    } else if (file.isFile()) {
                        count++;
                    }
                }
            } catch {}
        }
        countFiles(projectPath);
        fileCount = count;
    }

    const stats = fs.statSync(projectPath);
    const lastModified = stats.mtime.toLocaleString();

    return { name, totalCost, fileCount, lastModified };

  } catch (err) {
    return { name: 'Error', totalCost: '-', fileCount: '-', lastModified: '-' };
  }
});

// ── IPC: Select Directory ───────────────────────────────────
ipcMain.handle('select-directory', async (event) => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory']
  });
  if (!result.canceled && result.filePaths.length > 0) {
    return result.filePaths[0];
  }
  return null;
});

// ── IPC: Delete Project ─────────────────────────────────────
ipcMain.on('delete-project', (event, projectPath) => {
  try {
    if (fs.existsSync(projectPath)) {
      // Safety check: ensure we are deleting inside the output directory? 
      // For now, assuming UI passes valid paths.
      fs.rmSync(projectPath, { recursive: true, force: true });
      event.reply('delete-complete', { success: true });
    } else {
      event.reply('delete-complete', { success: false, error: 'Path does not exist' });
    }
  } catch (e) {
    event.reply('delete-complete', { success: false, error: e.message });
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
