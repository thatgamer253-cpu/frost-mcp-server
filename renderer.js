/**
 * ══════════════════════════════════════════════════════════
 *  OVERLORD — Renderer Process
 *  Handles tabs, build pipeline, gallery, maintenance,
 *  settings, and all IPC communication.
 * ══════════════════════════════════════════════════════════
 */

const { ipcRenderer } = require('electron');
const os = require('os');
const path = require('path');
const fs = require('fs');

// ── DOM Helpers ──────────────────────────────────────────────
const $ = (id) => document.getElementById(id);

const projectName = $('projectName');
const outputDir   = $('outputDir');
const model       = $('model');
const apiKey      = $('apiKey');
const optDocker   = $('optDocker');
const optReadme   = $('optReadme');
const optDebug    = $('optDebug');
const optBundle   = $('optBundle');
const promptInput = $('promptInput');
const consoleEl   = $('console');
const btnBuild    = $('btnBuild');
const btnCancel   = $('btnCancel');
const statusDot   = $('statusDot');
const statusText  = $('statusText');
const fileTree    = $('fileTree');
const liveCost    = $('liveCost');
const liveTime    = $('liveTime');
const consensusLight = $('consensus-light');
const consensusText  = $('consensus-text');

let isBuilding = false;
let buildTimer = null;
let buildStartTime = null;

// ── Settings File ───────────────────────────────────────────
const SETTINGS_PATH = path.join(__dirname, 'settings.json');

function loadSettings() {
  try {
    if (fs.existsSync(SETTINGS_PATH)) {
      const data = JSON.parse(fs.readFileSync(SETTINGS_PATH, 'utf-8'));
      if (data.openaiKey)    $('setOpenaiKey').value  = data.openaiKey;
      if (data.groqKey)      $('setGroqKey').value    = data.groqKey;
      if (data.geminiKey)    $('setGeminiKey').value   = data.geminiKey;
      if (data.elevenKey)    $('setElevenKey').value   = data.elevenKey;
      if (data.anthropicKey) $('setAnthropicKey').value = data.anthropicKey;
      if (data.outputDir)    { $('setOutputDir').value = data.outputDir; outputDir.value = data.outputDir; }
      if (data.defaultModel) $('setDefaultModel').value = data.defaultModel;
      if (data.budget)       { $('setBudget').value = data.budget; $('budgetVal').textContent = `$${data.budget}.00`; }
      if (data.autoBundle !== undefined) $('setAutoBundle').checked = data.autoBundle;
      if (data.autoDocker !== undefined) $('setAutoDocker').checked = data.autoDocker;
      if (data.autoReadme !== undefined) $('setAutoReadme').checked = data.autoReadme;

      // Apply to sidebar
      if (data.openaiKey) apiKey.value = data.openaiKey;
      if (data.defaultModel) model.value = data.defaultModel;
      if (data.autoBundle !== undefined) optBundle.checked = data.autoBundle;
      if (data.autoDocker !== undefined) optDocker.checked = data.autoDocker;
      if (data.autoReadme !== undefined) optReadme.checked = data.autoReadme;
    }
  } catch (e) {
    console.log('No settings file found, using defaults.');
  }
}

window.saveSettings = function() {
  const data = {
    openaiKey:    $('setOpenaiKey').value,
    groqKey:      $('setGroqKey').value,
    geminiKey:    $('setGeminiKey').value,
    elevenKey:    $('setElevenKey').value,
    anthropicKey: $('setAnthropicKey').value,
    outputDir:    $('setOutputDir').value,
    defaultModel: $('setDefaultModel').value,
    budget:       parseInt($('setBudget').value),
    autoBundle:   $('setAutoBundle').checked,
    autoDocker:   $('setAutoDocker').checked,
    autoReadme:   $('setAutoReadme').checked,
  };
  try {
    fs.writeFileSync(SETTINGS_PATH, JSON.stringify(data, null, 2), 'utf-8');
    const msg = $('saveMsg');
    msg.classList.add('show');
    setTimeout(() => msg.classList.remove('show'), 2000);

    // Sync to sidebar
    outputDir.value = data.outputDir || './output';
    apiKey.value = data.openaiKey || '';
    model.value = data.defaultModel || model.value;
    optBundle.checked = data.autoBundle;
    optDocker.checked = data.autoDocker;
    optReadme.checked = data.autoReadme;
  } catch (e) {
    console.error('Failed to save settings:', e);
  }
};

// ── Tab Navigation ──────────────────────────────────────────
document.querySelectorAll('.tab-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    btn.classList.add('active');
    $(`tab-${btn.dataset.tab}`).classList.add('active');

    // Auto-load gallery when switching to it
    if (btn.dataset.tab === 'gallery') loadGallery();
  });
});

// ── Log Tag Classification ──────────────────────────────────
function classifyLine(text) {
  const upper = text.toUpperCase();
  if (upper.includes('[ARCHITECT]')) return 'log-architect';
  if (upper.includes('[ENGINEER]'))  return 'log-engineer';
  if (upper.includes('[DEBUGGER]'))  return 'log-debugger';
  if (upper.includes('[AUDITOR]'))   return 'log-architect';
  if (upper.includes('[GATE]'))      return 'log-architect';
  if (upper.includes('[REVIEWER]'))  return 'log-success';
  if (upper.includes('[ASSEMBLER]')) return 'log-architect';
  if (upper.includes('[ENVIRON]'))   return 'log-engineer';
  if (upper.includes('[HANDOFF]'))   return 'log-success';
  if (upper.includes('[STATE]'))     return 'log-system';
  if (upper.includes('[VOICE]'))     return 'log-success';
  if (upper.includes('[HEALER]'))    return 'log-engineer';
  if (upper.includes('[DOCKER]'))    return 'log-docker';
  if (upper.includes('[BUNDLER]'))   return 'log-bundler';
  if (upper.includes('[SUCCESS]'))   return 'log-success';
  if (upper.includes('[ERROR]'))     return 'log-error';
  if (upper.includes('[WARN]'))      return 'log-error';
  if (upper.includes('[COMPLETE]'))  return 'log-success';
  if (upper.includes('[WISDOM]'))    return 'log-success';
  if (upper.includes('[MEDIA]'))     return 'log-engineer';
  if (upper.includes('[LOCAL]'))     return 'log-system';
  if (upper.includes('[LINT]'))      return 'log-engineer';
  if (upper.includes('[RESEARCH]'))  return 'log-architect';
  if (upper.includes('[KEYPOOL]'))   return 'log-system';
  if (upper.includes('[OUTPUT]'))    return 'log-success';
  if (upper.includes('[FORTRESS]'))  return 'log-architect';
  if (upper.includes('[SETUP]'))     return 'log-engineer';
  if (upper.includes('[GALLERY]'))   return 'log-success';
  if (upper.includes('---') || upper.includes('[SYSTEM]')) return 'log-system';
  return '';
}

// ── Append Log Line ─────────────────────────────────────────
function appendLog(text) {
  const line = document.createElement('div');
  line.className = `log-line ${classifyLine(text)}`;
  line.textContent = text;
  consoleEl.appendChild(line);
  consoleEl.scrollTop = consoleEl.scrollHeight;
}

// ── Status Updates ──────────────────────────────────────────
function setStatus(label, dotClass) {
  statusText.textContent = label;
  statusDot.className = `status-dot ${dotClass}`;
  
  // Toggle badge active state based on dot class
  const badge = $('statusBadge');
  if (badge) {
      if (dotClass === 'active' || dotClass === 'success' || dotClass === 'error') {
          badge.classList.add('active');
          // Optional: Add specific color classes if we want to differentiate
          badge.classList.toggle('success', dotClass === 'success');
          badge.classList.toggle('error', dotClass === 'error');
      } else {
          badge.classList.remove('active', 'success', 'error');
      }
  }
}

function setConsensus(state, label) {
    if (!consensusLight || !consensusText) return;
    
    consensusText.textContent = label;
    consensusLight.className = 'consensus-light'; // Reset
    
    if (state === 'reached') consensusLight.classList.add('pulse-green');
    else if (state === 'debating') consensusLight.classList.add('pulse-yellow');
    else if (state === 'conflict') consensusLight.classList.add('pulse-red');
}

function setBuilding(active) {
  isBuilding = active;
  btnBuild.disabled = active;
  btnCancel.disabled = !active;

  if (active) {
    buildStartTime = Date.now();
    buildTimer = setInterval(updateTimer, 1000);
  } else {
    clearInterval(buildTimer);
    buildTimer = null;
  }
}

function updateTimer() {
  if (!buildStartTime) return;
  const elapsed = Math.floor((Date.now() - buildStartTime) / 1000);
  const mins = Math.floor(elapsed / 60);
  const secs = elapsed % 60;
  liveTime.textContent = `${mins}:${secs.toString().padStart(2, '0')}`;
}

// ── Pipeline Progress ───────────────────────────────────────
const PHASES = ['prompt', 'architect', 'engineer', 'reviewer', 'debugger', 'bundler', 'environ', 'handoff'];
let completedPhases = new Set();
let activePhase = '';

function setPipelinePhase(phase) {
  if (activePhase && activePhase !== phase) {
    completedPhases.add(activePhase);
    const prevDot = $(`pip-${activePhase}`);
    const prevLabel = prevDot?.parentElement?.querySelector('.pipeline-label');
    if (prevDot) { prevDot.classList.remove('active'); prevDot.classList.add('done'); }
    if (prevLabel) { prevLabel.classList.remove('active'); prevLabel.classList.add('done'); }
  }
  activePhase = phase;
  const dot = $(`pip-${phase}`);
  const label = dot?.parentElement?.querySelector('.pipeline-label');
  if (dot && !completedPhases.has(phase)) {
    dot.classList.add('active');
    dot.classList.remove('done');
  }
  if (label && !completedPhases.has(phase)) {
    label.classList.add('active');
    label.classList.remove('done');
  }
}

function resetPipeline() {
  completedPhases.clear();
  activePhase = '';
  PHASES.forEach(p => {
    const dot = $(`pip-${p}`);
    const label = dot?.parentElement?.querySelector('.pipeline-label');
    if (dot) { dot.classList.remove('active', 'done'); }
    if (label) { label.classList.remove('active', 'done'); }
  });
}

function finishPipeline() {
  PHASES.forEach(p => {
    const dot = $(`pip-${p}`);
    const label = dot?.parentElement?.querySelector('.pipeline-label');
    if (dot) { dot.classList.remove('active'); dot.classList.add('done'); }
    if (label) { label.classList.remove('active'); label.classList.add('done'); }
  });
}

// ── Live Cost Parsing ───────────────────────────────────────
function parseCost(text) {
  const match = text.match(/\$(\d+\.\d+)/);
  if (match && text.toUpperCase().includes('TOTAL')) {
    liveCost.textContent = `$${match[1]}`;
  }
}

// ── Build Button ────────────────────────────────────────────
const buildMode     = $('buildMode');
const sourcePathRow = $('sourcePathRow');
const sourcePath    = $('sourcePath');
const btnSelectSource = $('btnSelectSource');

// Toggle Source Path visibility
if (buildMode) {
  buildMode.addEventListener('change', () => {
    if (buildMode.value === 'upgrade' || buildMode.value === 'reverse') {
      sourcePathRow.style.display = 'block';
    } else {
      sourcePathRow.style.display = 'none';
    }
  });
}

// Handle Source Directory Selection
if (btnSelectSource) {
  btnSelectSource.addEventListener('click', async () => {
    const path = await ipcRenderer.invoke('select-directory');
    if (path) {
      sourcePath.value = path;
    }
  });
}

btnBuild.addEventListener('click', () => {
  if (isBuilding) return;

  consoleEl.innerHTML = '';
  fileTree.textContent = 'Building...';
  liveCost.textContent = '$0.00';
  liveTime.textContent = '0:00';
  setConsensus('debating', 'Negotiating Path');
  resetPipeline();

  setBuilding(true);
  setStatus('BUILDING', 'active');

  // NEW: Capture Mode and Source Path
  const modeVal = buildMode ? buildMode.value : 'new';
  const sourcePathVal = sourcePath ? sourcePath.value.trim() : '';

  // NEW: Advanced Controls
  const phaseVal = $('limitPhase') ? $('limitPhase').value : 'all';
  const focusVal = $('focusPattern') ? $('focusPattern').value.trim() : '';
  const decompileOnlyVal = $('optDecompileOnly') ? $('optDecompileOnly').checked : false;
  const cleanOutputVal = $('optCleanOutput') ? $('optCleanOutput').checked : false;

  ipcRenderer.send('start-build', {
    projectName: projectName.value.trim() || 'GeneratedApp',
    prompt: promptInput.value.trim(),
    outputDir: outputDir.value.trim() || './output',
    model: model.value,
    engModel: ($('engModel') || {}).value || '',
    reviewModel: ($('reviewModel') || {}).value || '',
    apiKey: apiKey.value.trim(),
    enableDocker: optDocker.checked,
    enableReadme: optReadme.checked,
    enableDebug: optDebug.checked,
    enableBundle: optBundle.checked,
    mode: modeVal,
    sourcePath: sourcePathVal,
    phase: phaseVal,
    focus: focusVal,
    decompileOnly: decompileOnlyVal,
    cleanOutput: cleanOutputVal
  });
});

// ── Cancel Button ───────────────────────────────────────────
btnCancel.addEventListener('click', () => {
  if (!isBuilding) return;
  ipcRenderer.send('cancel-build');
});

// ── Launch Dashboard Button ─────────────────────────────────
const btnDashboard = $('btnDashboard');
if (btnDashboard) {
  btnDashboard.addEventListener('click', () => {
    const outDir = path.resolve(outputDir.value.trim() || './output');
    // Find the most recent project folder
    try {
      const entries = fs.readdirSync(outDir, { withFileTypes: true })
        .filter(e => e.isDirectory() && !e.name.startsWith('.'))
        .map(e => ({ name: e.name, mtime: fs.statSync(path.join(outDir, e.name)).mtime }))
        .sort((a, b) => b.mtime - a.mtime);
      const projectPath = entries.length > 0
        ? path.join(outDir, entries[0].name)
        : outDir;
      ipcRenderer.send('launch-dashboard', { projectPath });
    } catch {
      ipcRenderer.send('launch-dashboard', { projectPath: outDir });
    }
  });
}

// ── IPC: Log Updates ────────────────────────────────────────
ipcRenderer.on('log-update', (event, text) => {
  appendLog(text);
  parseCost(text);

  // Update pipeline phase
  const upper = text.toUpperCase();
  if (upper.includes('[PROMPT]') && upper.includes('ENHANC'))       setPipelinePhase('prompt');
  else if (upper.includes('[ARCHITECT]') && upper.includes('ENGAG')) setPipelinePhase('architect');
  else if (upper.includes('[ASSEMBLER]'))                            setPipelinePhase('architect');
  else if (upper.includes('[ENGINEER]') && upper.includes('ENGAG'))  setPipelinePhase('engineer');
  else if ((upper.includes('[AUDITOR]') || upper.includes('[REVIEWER]')) && upper.includes('ENGAG'))
                                                                     setPipelinePhase('reviewer');
  else if (upper.includes('[DEBUGGER]') && upper.includes('ENGAG'))  setPipelinePhase('debugger');
  else if (upper.includes('[BUNDLER]') && upper.includes('ENGAG'))   setPipelinePhase('bundler');
  else if (upper.includes('[ENVIRON]') && upper.includes('ENGAG'))   setPipelinePhase('environ');
  else if (upper.includes('[HANDOFF]'))                              setPipelinePhase('handoff');
  else if (upper.includes('[DOCKER]') && upper.includes('GENERAT'))  setPipelinePhase('environ');
  else if (upper.includes('[SETUP]') && upper.includes('ENGAG'))     setPipelinePhase('environ');

  // Consensus logic
  if (upper.includes('CONSENSUS REACHED')) {
      setConsensus('reached', 'Consensus Reached');
  } else if (upper.includes('CONFLICT DETECTED')) {
      setConsensus('conflict', 'Conflict! Recalculating...');
  }

  // Update status text
  if (upper.includes('[ARCHITECT]') && upper.includes('ENGAG'))      setStatus('ARCHITECT', 'active');
  else if (upper.includes('[ASSEMBLER]'))                            setStatus('ASSEMBLER', 'active');
  else if (upper.includes('[ENGINEER]') && upper.includes('ENGAG'))  setStatus('ENGINEER', 'active');
  else if (upper.includes('[REVIEWER]') && upper.includes('ENGAG'))  setStatus('REVIEWER', 'active');
  else if (upper.includes('[DEBUGGER]') && upper.includes('ENGAG'))  setStatus('DEBUGGER', 'active');
  else if (upper.includes('[BUNDLER]') && upper.includes('ENGAG'))   setStatus('BUNDLER', 'active');
  else if (upper.includes('[ENVIRON]') && upper.includes('ENGAG'))   setStatus('ENVIRONMENT', 'active');
  else if (upper.includes('[HANDOFF]'))                              setStatus('HANDOFF', 'active');
  else if (upper.includes('[DOCKER]') && upper.includes('PACKAGING'))setStatus('PACKAGING', 'active');
});

// ── IPC: Build Complete ─────────────────────────────────────
ipcRenderer.on('build-complete', (event, result) => {
  setBuilding(false);

  if (result.aborted) {
    setStatus('ABORTED', 'error');
  } else if (result.success) {
    setStatus('COMPLETE', 'success');
    finishPipeline();
    updateFileTree();
  } else {
    setStatus('FAILED', 'error');
  }
});

// ── File Tree ───────────────────────────────────────────────
function updateFileTree() {
  const dir = path.resolve(outputDir.value.trim() || './output');

  if (!fs.existsSync(dir)) {
    fileTree.textContent = 'No output directory found.';
    return;
  }

  // Find the most recently modified subfolder
  try {
    const entries = fs.readdirSync(dir, { withFileTypes: true })
      .filter(e => e.isDirectory() && !e.name.startsWith('.'))
      .map(e => ({ name: e.name, mtime: fs.statSync(path.join(dir, e.name)).mtime }))
      .sort((a, b) => b.mtime - a.mtime);

    if (entries.length === 0) {
      fileTree.textContent = 'Empty output directory.';
      return;
    }

    const latest = entries[0].name;
    const latestPath = path.join(dir, latest);
    const lines = [`${latest}/`];

    function walk(dirPath, indent) {
      const items = fs.readdirSync(dirPath, { withFileTypes: true })
        .filter(e => !e.name.startsWith('.') && e.name !== 'build_temp' && e.name !== '__pycache__')
        .sort((a, b) => a.name.localeCompare(b.name));
      items.forEach(entry => {
        const fullPath = path.join(dirPath, entry.name);
        if (entry.isDirectory()) {
          lines.push(`${indent}${entry.name}/`);
          walk(fullPath, indent + '  ');
        } else {
          const size = fs.statSync(fullPath).size;
          const kb = (size / 1024).toFixed(1);
          lines.push(`${indent}${entry.name}  (${kb}KB)`);
        }
      });
    }

    walk(latestPath, '  ');
    fileTree.textContent = lines.join('\n') || 'Empty.';
  } catch (e) {
    fileTree.textContent = 'Error reading output.';
  }
}

// ── Gallery ─────────────────────────────────────────────────
// ── Gallery ─────────────────────────────────────────────────
let galleryProjects = [];

window.loadGallery = function() {
  const galleryGrid = $('galleryGrid');
  // Clear search on reload if desired, or keep it? Let's keep it if possible, but simplest is clear.
  // $('gallerySearch').value = ''; 
  const outDir = path.resolve(outputDir.value.trim() || './output');

  if (!fs.existsSync(outDir)) {
    galleryGrid.innerHTML = '<div class="gallery-empty"><div class="icon">&#9881;</div><p>No projects yet. Build something!</p></div>';
    return;
  }

  galleryProjects = [];
  try {
    const entries = fs.readdirSync(outDir, { withFileTypes: true })
      .filter(e => e.isDirectory() && !e.name.startsWith('.'));

    entries.forEach(e => {
      const projPath = path.join(outDir, e.name);
      const manifestPath = path.join(projPath, 'package_manifest.json');
      const costPath = path.join(projPath, 'cost_report.json');
      const hasExe = fs.existsSync(path.join(projPath, 'dist'));

      let manifest = null, cost = null;
      try { manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf-8')); } catch {}
      try { cost = JSON.parse(fs.readFileSync(costPath, 'utf-8')); } catch {}

      galleryProjects.push({
        name: e.name,
        path: projPath,
        manifest,
        cost,
        hasExe,
        mtime: fs.statSync(projPath).mtime,
      });
    });
  } catch (e) {
    galleryGrid.innerHTML = '<div class="gallery-empty"><p>Error reading output directory.</p></div>';
    return;
  }

  if (galleryProjects.length === 0) {
    galleryGrid.innerHTML = '<div class="gallery-empty"><div class="icon">&#9881;</div><p>No projects yet. Build something!</p></div>';
    return;
  }

  // Sort newest first
  galleryProjects.sort((a, b) => b.mtime - a.mtime);
  
  renderGallery(galleryProjects);
};

function renderGallery(projects) {
  const galleryGrid = $('galleryGrid');
  if (projects.length === 0) {
     galleryGrid.innerHTML = '<div class="gallery-empty"><p>No matching projects found.</p></div>';
     return;
  }
  
  galleryGrid.innerHTML = projects.map(p => {
    const projName = p.manifest?.project || p.name;
    const files = p.manifest?.total_files || '?';
    const stack = p.manifest?.stack;
    const stackStr = stack ? `${stack.backend || ''}${stack.database ? ' + ' + stack.database : ''}` : '';
    const totalCost = p.cost?.total_cost ? `$${p.cost.total_cost.toFixed(2)}` : '';
    const date = new Date(p.mtime).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });

    // Escaped path for onClick strings
    const safePath = p.path.replace(/\\/g, '\\\\');

    return `
      <div class="gallery-card">
        <div class="card-name" title="${projName}">${projName}</div>
        <div class="card-meta">
          ${stackStr ? `<span class="card-tag stack">${stackStr}</span>` : ''}
          <span class="card-tag files">${files} files</span>
          ${totalCost ? `<span class="card-tag cost">${totalCost}</span>` : ''}
        </div>
        <div class="card-date">
            <span>${date}</span>
            <span style="opacity:0.6; font-size:9px;">${p.name}</span>
        </div>
        <div class="card-actions">
          <button class="card-btn" onclick="openFolder('${safePath}')">Open</button>
          <button class="card-btn details" style="border-color:var(--cyan); color:var(--cyan);" onclick="showDetails('${safePath}')">Details</button>
          <button class="card-btn upgrade" onclick="prepUpgrade('${safePath}')">Upgrade</button>
          <button class="card-btn delete" onclick="deleteProject('${safePath}', '${p.name}')">Delete</button>
          ${p.hasExe ? `<button class="card-btn run" onclick="runExe('${safePath}')">Run .exe</button>` : ''}
        </div>
      </div>
    `;
  }).join('');
}

window.filterGallery = function() {
    const query = $('gallerySearch').value.toLowerCase();
    const filtered = galleryProjects.filter(p => {
        const n = (p.manifest?.project || p.name).toLowerCase();
        const s = JSON.stringify(p.manifest?.stack || {}).toLowerCase();
        return n.includes(query) || s.includes(query);
    });
    renderGallery(filtered);
};

window.openFolder = function(folderPath) {
  ipcRenderer.send('open-folder', folderPath);
};

window.runExe = function(projectPath) {
  ipcRenderer.send('run-exe', projectPath);
};

window.prepUpgrade = function(projectPath) {
    // Switch to Build tab
    document.querySelector('[data-tab="build"]').click();
    
    // Set Mode to Upgrade
    if (buildMode) {
        buildMode.value = 'upgrade';
        buildMode.dispatchEvent(new Event('change'));
    }
    
    // Set Source Path
    if (sourcePath) {
        sourcePath.value = projectPath;
    }
    
    // Optional: Pre-fill prompt
    promptInput.value = "Analyze this project and suggest improvements. Then...";
    promptInput.focus();
};

window.deleteProject = function(projectPath, name) {
    if (confirm(`Are you sure you want to permanently delete "${name}"?\nThis cannot be undone.`)) {
        ipcRenderer.send('delete-project', projectPath);
    }
};

ipcRenderer.on('delete-complete', (event, { success, error }) => {
    if (success) {
        loadGallery(); // Reload
    } else {
        alert(`Failed to delete project: ${error}`);
    }
});

// ── Maintenance ─────────────────────────────────────────────
let isMaintaining = false;

window.runMaintenance = function() {
  if (isMaintaining) return;
  isMaintaining = true;
  $('btnScan').disabled = true;
  $('maintStatus').textContent = 'Scanning...';
  $('maintConsole').innerHTML = '';

  ipcRenderer.send('run-maintenance', {
    libraryPath: path.resolve(outputDir.value.trim() || './output'),
  });
};

ipcRenderer.on('maint-log', (event, text) => {
  const line = document.createElement('div');
  line.className = `log-line ${classifyLine(text)}`;
  line.textContent = text;
  $('maintConsole').appendChild(line);
  $('maintConsole').scrollTop = $('maintConsole').scrollHeight;
});

ipcRenderer.on('maint-complete', (event, result) => {
  isMaintaining = false;
  $('btnScan').disabled = false;
  $('maintStatus').textContent = result.success ? 'Scan complete' : 'Scan failed';
});

// ── Keyboard Shortcuts ──────────────────────────────────────
document.addEventListener('keydown', (e) => {
  if (e.ctrlKey && e.key === 'Enter' && !isBuilding) btnBuild.click();
  if (e.key === 'Escape' && isBuilding) btnCancel.click();
});

// ── Details Modal Logic ───────────────────────────────────
const detailsModal = $('detailsModal');
const closeModalBtn = $('closeModalBtn');
const modalOpenBtn = $('modalOpenBtn');
const modalUpgradeBtn = $('modalUpgradeBtn');
const modalDeleteBtn = $('modalDeleteBtn');

window.showDetails = async function(projectPath) {
  if (!detailsModal) return;
  
  // Reset
  $('modalTitle').textContent = 'Loading...';
  $('modalCost').textContent = '...';
  $('modalFiles').textContent = '...';
  $('modalDate').textContent = '...';
  $('modalPath').textContent = projectPath;

  detailsModal.classList.remove('hidden');
  // Small delay to allow display:flex to apply before opacity transition
  requestAnimationFrame(() => detailsModal.classList.add('visible'));

  // Fetch details
  try {
      const details = await ipcRenderer.invoke('get-project-details', projectPath);
      
      $('modalTitle').textContent = details.name;
      $('modalCost').textContent = details.totalCost || '$0.00';
      $('modalFiles').textContent = details.fileCount || '0';
      $('modalDate').textContent = details.lastModified || 'Unknown';
      
      // Setup Actions
      modalOpenBtn.onclick = () => window.openFolder(projectPath);
      modalUpgradeBtn.onclick = () => {
          closeDetailsModal();
          window.prepUpgrade(projectPath);
      };
      modalDeleteBtn.onclick = () => {
          closeDetailsModal();
          window.deleteProject(projectPath, details.name);
      };

  } catch (e) {
      $('modalTitle').textContent = 'Error';
      console.error(e);
  }
};

function closeDetailsModal() {
  if (!detailsModal) return;
  detailsModal.classList.remove('visible');
  setTimeout(() => {
    detailsModal.classList.add('hidden');
  }, 300);
}

if (closeModalBtn) {
  closeModalBtn.addEventListener('click', closeDetailsModal);
}
// Close on click outside
if (detailsModal) {
    detailsModal.addEventListener('click', (e) => {
        if (e.target === detailsModal) closeDetailsModal();
    });
}

// ── Init ────────────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', () => {
  loadSettings();
  // Set default output to Desktop if not configured
  if (!outputDir.value || outputDir.value === './output') {
    const desktopOutput = path.join(os.homedir(), 'Desktop', 'Creator', 'output');
    if (fs.existsSync(path.join(os.homedir(), 'Desktop', 'Creator'))) {
      outputDir.value = desktopOutput;
    }
  }
});
