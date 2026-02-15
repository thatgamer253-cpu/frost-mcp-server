/**
 * ══════════════════════════════════════════════════════════
 *  OVERLORD — Renderer Process
 *  Handles button clicks, UI state, and IPC messages.
 * ══════════════════════════════════════════════════════════
 */

const { ipcRenderer } = require('electron');
const fs = require('fs');
const path = require('path');

// ── DOM Elements ────────────────────────────────────────────
const $ = (id) => document.getElementById(id);

const projectName = $('projectName');
const mode        = $('mode');
const scale       = $('scale');
const platform    = $('platform');
const model       = $('model');
const budgetId    = $('budgetId');
const budgetVal   = $('budgetVal');
const optDocker   = $('optDocker');
const optReadme   = $('optReadme');
const optDebug    = $('optDebug');
const promptInput = $('promptInput');
const consoleEl   = $('console');
const synthesisEl = $('synthesis');
const btnBuild    = $('btnBuild');
const btnCancel   = $('btnCancel');
const fileTree    = $('fileTree');
const statFiles   = $('statFiles');

// HUD Stats
const liveCost    = $('liveCost');
const liveTime    = $('liveTime');
const statusText  = $('statusText');
const statusDot   = $('statusDot');
const statusBadge = $('statusBadge');
const feedDot     = $('feedDot');

// Missing configuration elements
const fixCycles     = $('fixCycles');
const sourcePath    = $('sourcePath');
const upgradeSection = $('upgradeSection');

const optSetup      = $('optSetup');
const optVoice      = $('optVoice');
const optNoBundle   = $('optNoBundle');
const optClean      = $('optClean');
const optDecompile  = $('optDecompile');

const archModel     = $('archModel');
const engModel      = $('engModel');
const reviewModel    = $('reviewModel');
const localModel    = $('localModel');
const phase         = $('phase');
const focus         = $('focus');

const advancedModels = $('advancedModels');
const advToggleIcon  = $('advToggleIcon');

// Tab Navigation
const tabs = document.querySelectorAll('.tab');
const views = document.querySelectorAll('.view-container');

// Dashboard elements
const dashTotalProjects = $('dashTotalProjects');
const dashTotalFiles    = $('dashTotalFiles');
const dashTotalCost     = $('dashTotalCost');
const dashSuccessRate   = $('dashSuccessRate');
const dashActivityLog   = $('dashActivityLog');
const libraryGrid       = $('libraryGrid');

// Preview Modal
const previewOverlay = $('previewOverlay');
const previewTitle   = $('previewTitle');
const previewContent = $('previewContent');
const closePreview   = $('closePreview');

let isBuilding = false;
let buildStartTime = 0;
let buildTimer = null;
let fileCount = 0;

window.toggleAdvanced = () => {
  const isHidden = advancedModels.style.display === 'none';
  advancedModels.style.display = isHidden ? 'block' : 'none';
  advToggleIcon.textContent = isHidden ? '⊖' : '⊕';
};

// ── API Status Check ────────────────────────────────────────
function checkAPIKeys() {
  ipcRenderer.invoke('check-api-keys').then(keys => {
    Object.keys(keys).forEach(key => {
      const el = $(`key-${key}`);
      if (el) {
        el.classList.remove('active', 'missing');
        el.classList.add(keys[key] ? 'active' : 'missing');
      }
    });
  });
}
checkAPIKeys();

// ── Tab Switching Logic ─────────────────────────────────────
tabs.forEach(tab => {
  tab.addEventListener('click', () => {
    const tabName = tab.getAttribute('data-tab'); // e.g. "build"
    const viewId = `view${tabName.charAt(0).toUpperCase() + tabName.slice(1)}`;
    
    // Update active tab
    tabs.forEach(t => t.classList.remove('active'));
    tab.classList.add('active');
    
    // Update active view
    views.forEach(v => {
      v.classList.remove('active');
      if (v.id === viewId) v.classList.add('active');
    });

    // Refresh data if switching to Library or Dashboard
    if (tabName === 'library') refreshLibrary();
    if (tabName === 'dashboard') refreshDashboard();
  });
});

// ── Pro Mode Toggle ──────────────────────────────────────────────
const proModeToggle = $('proModeToggle');
const proFeatures = $('proFeatures');

proModeToggle.addEventListener('change', () => {
  const isPro = proModeToggle.checked;
  proFeatures.style.display = isPro ? 'block' : 'none';
  // We no longer reset values here, allowing the user to "switch back and forth"
  // but the build logic below will enforce 'auto' if the toggle is off.
});

// ── Mode Toggle (Old) ──────────────────────────────────────────────
mode.addEventListener('change', () => {
  upgradeSection.style.display = mode.value === 'upgrade' ? 'block' : 'none';
});

// ── Log UI ──────────────────────────────────────────────────
const AGENT_PERSONAS = {
  ARCHITECT: { class: 'persona-architect', icon: '📐' },
  ENGINEER:  { class: 'persona-engineer',  icon: '🔧' },
  REVIEWER:  { class: 'persona-reviewer',  icon: '👁️' },
  DEBUGGER:  { class: 'persona-reviewer',  icon: '🧪' },
  DOCKER:    { class: 'persona-system',    icon: '🐳' },
  SUCCESS:   { class: 'persona-success',   icon: '✅' },
  ERROR:     { class: 'persona-error',     icon: '🚨' },
  SYSTEM:    { class: 'persona-system',    icon: '◈' },
  COMPLETE:  { class: 'persona-success',   icon: '🚀' },
  WISDOM:    { class: 'persona-architect', icon: '🧠' }
};

const PHASE_MAP = {
  'briefing':  ['INTERPRETING', 'BRIEFING', 'AUTONOMOUS'],
  'architect': ['ARCHITECT', 'BLUEPRINT', 'PLANNING'],
  'engineer':  ['ENGINEER', 'CODING', 'IMPLEMENTING', 'WRITING'],
  'reviewer':  ['REVIEWER', 'DIAGNOSTICS', 'WISDOM', 'QUALITY', 'AUDIT'],
  'complete':  ['COMPLETE', 'SUCCESS', 'FINISHED']
};

function updatePhaseStepper(phaseKey) {
  const steps = ['briefing', 'architect', 'engineer', 'reviewer', 'complete'];
  const currentIndex = steps.indexOf(phaseKey);
  
  steps.forEach((key, index) => {
    const el = $(`step-${key}`);
    if (!el) return;
    
    el.classList.remove('active', 'completed');
    if (index < currentIndex) {
      el.classList.add('completed');
    } else if (index === currentIndex) {
      el.classList.add('active');
    }
  });
}

function classifyLine(text) {
  const upper = text.toUpperCase();
  
  // Update phase stepper if keyword match found
  for (const [phaseKey, keywords] of Object.entries(PHASE_MAP)) {
    if (keywords.some(kw => upper.includes(kw))) {
      updatePhaseStepper(phaseKey);
      break;
    }
  }

  for (const [key, persona] of Object.entries(AGENT_PERSONAS)) {
    if (upper.includes(`[${key}]`)) return { ...persona, tag: key };
  }
  return { ...AGENT_PERSONAS.SYSTEM, tag: 'SYSTEM' };
}

function appendLog(text) {
  if (typeof text !== 'string') text = String(text);
  const upper = text.toUpperCase();
  const persona = classifyLine(text);
  let cleanMsg = text.replace(/\[.*?\]/g, '').trim();
  
  if (!cleanMsg) cleanMsg = text.replace(/\[.*?\]/g, '') || '...';
  
  const isSynthesis = upper.includes('WRITING') || upper.includes('UPDATED') || upper.includes('✓ WRITTEN') || upper.includes('PLANNING');
  
  // Clear Synthesis Pane if major event
  if (isSynthesis && synthesisEl && (upper.includes('✓') || upper.includes('STARTING') || synthesisEl.childNodes.length > 40)) {
     synthesisEl.innerHTML = ''; 
  }

  const targets = [];
  const createSubEntry = (target) => {
    if (!target) return null;
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    const tagSpan = document.createElement('span');
    tagSpan.className = `log-tag ${persona.class}`;
    tagSpan.innerHTML = `${persona.icon} ${persona.tag}`;
    const msgSpan = document.createElement('span');
    msgSpan.className = `log-msg ${persona.class}`;
    entry.appendChild(tagSpan);
    entry.appendChild(msgSpan);
    target.appendChild(entry);
    return { entry, msgSpan };
  };

  const mainLog = createSubEntry(consoleEl);
  if (mainLog) targets.push(mainLog.msgSpan);

  if (isSynthesis && synthesisEl) {
    const synthLog = createSubEntry(synthesisEl);
    if (synthLog) targets.push(synthLog.msgSpan);
  }

  // Typewriter effect
  let i = 0;
  const charsPerTick = 5; 
  function type() {
    if (i < cleanMsg.length) {
      const chunk = cleanMsg.slice(i, i + charsPerTick);
      targets.forEach(span => span.textContent += chunk);
      i += charsPerTick;
      requestAnimationFrame(type);
    } else {
      if (consoleEl) consoleEl.scrollTop = consoleEl.scrollHeight;
      if (synthesisEl) synthesisEl.scrollTop = synthesisEl.scrollHeight;
    }
  }
  type();

  // Also append to dashboard log (instant)
  if (dashActivityLog && mainLog) {
    const dashEntry = mainLog.entry.cloneNode(true);
    dashEntry.querySelector('.log-msg').textContent = cleanMsg;
    dashActivityLog.appendChild(dashEntry);
    dashActivityLog.scrollTop = dashActivityLog.scrollHeight;
  }
}

// ── Status & State ──────────────────────────────────────────
function setStatStatus(text, color) {
  statusText.textContent = text;
  statusText.style.color = color;
  statusDot.className = `status-dot ${text.toLowerCase()}`;
  statusBadge.style.boxShadow = `0 0 10px ${color} inset`;
}

function setBuilding(active) {
  isBuilding = active;
  btnBuild.disabled = active;
  btnCancel.disabled = !active;
  
  if (active) {
    buildStartTime = Date.now();
    liveTime.textContent = '0:00';
    liveCost.textContent = '$0.00';
    buildTimer = setInterval(() => {
      const totalSec = Math.floor((Date.now() - buildStartTime) / 1000);
      const m = Math.floor(totalSec / 60);
      const s = totalSec % 60;
      liveTime.textContent = `${m}:${s < 10 ? '0' : ''}${s}`;
    }, 1000);
    setStatStatus('RUNNING', 'var(--accent)');
    feedDot.style.background = 'var(--accent)';
    feedDot.style.boxShadow = '0 0 10px var(--accent)';
    fileCount = 0;
    if (statFiles) statFiles.textContent = '0';
    updatePhaseStepper('briefing');
  } else {
    clearInterval(buildTimer);
    feedDot.style.background = 'var(--text-dim)';
    feedDot.style.boxShadow = 'none';
  }
}

// ── Build Execution ─────────────────────────────────────────
btnBuild.addEventListener('click', () => {
  if (isBuilding) return;

  const prompt = promptInput.value.trim();
  if (!prompt) {
    alert('Please enter a project description.');
    return;
  }

  // Clear UI
  consoleEl.innerHTML = '';
  fileTree.textContent = 'Initializing build engine...';

  const isManual = proModeToggle.checked;
  setBuilding(true);

  ipcRenderer.send('start-build', {
    projectName: projectName.value.trim() || 'GeneratedApp',
    prompt: prompt,
    mode: mode.value,
    scale:    isManual ? scale.value    : 'auto',
    platform: isManual ? platform.value : 'auto',
    model:    isManual ? model.value    : 'auto',
    phase:    isManual ? phase.value    : 'auto',
    budget: budgetId.value,
    fixCycles: fixCycles.value,
    sourcePath: sourcePath.value.trim(),
    focus: focus.value.trim(),
    enableDocker: optDocker.checked,
    enableReadme: optReadme.checked,
    enableDebug: optDebug.checked,
    enableSetup: optSetup.checked,
    enableVoice: optVoice.checked,
    noBundle: optNoBundle.checked,
    enableClean: optClean.checked,
    enableDecompile: optDecompile.checked,
    archModel: isManual ? archModel.value : '',
    engModel:  isManual ? engModel.value  : '',
    reviewModel: isManual ? reviewModel.value : '',
    localModel:  isManual ? localModel.value  : ''
  });
});

btnCancel.addEventListener('click', () => {
  if (!isBuilding) return;
  ipcRenderer.send('cancel-build');
});

// ── IPC Logic ───────────────────────────────────────────────
ipcRenderer.on('log-update', (event, text) => {
  appendLog(text);

  const upper = text.toUpperCase();
  
  // Parse Cost
  if (upper.includes('COST:') || upper.includes('BUDGET:')) {
    const match = text.match(/\$[\d.]+/);
    if (match) liveCost.textContent = match[0];
  }

  if (upper.includes('✓') && upper.includes('WRITTEN')) {
    fileCount++;
    if (statFiles) statFiles.textContent = fileCount;
  }
  
  if (upper.includes('COMPLETE') || upper.includes('SUCCESS') || upper.includes('VERIFIED')) {
    setStatStatus('VERIFIED', 'var(--green)');
  } else if (upper.includes('[ERROR]') || upper.includes('[CRITICAL]') || upper.includes('[FATAL]')) {
    setStatStatus('ISSUE DETECTED', 'var(--red)');
  }
});

ipcRenderer.on('build-complete', (event, result) => {
  setBuilding(false);

  if (result.aborted) {
    setStatStatus('ABORTED', 'var(--red)');
  } else if (result.success) {
    setStatStatus('COMPLETE', 'var(--green)');
    updatePhaseStepper('complete');
    updateFileTree();
  } else {
    setStatStatus('FAILED', 'var(--red)');
  }
});

// ── Library & Dashboard Refresh ──────────────────────────────
function refreshLibrary() {
  const outputDir = path.resolve(__dirname, './output');
  if (!fs.existsSync(outputDir)) {
    libraryGrid.innerHTML = '<div class="header-sub">No projects found. Build something first!</div>';
    return;
  }

  libraryGrid.innerHTML = '';
  const projects = fs.readdirSync(outputDir, { withFileTypes: true })
    .filter(dirent => dirent.isDirectory())
    .map(dirent => dirent.name);

  if (projects.length === 0) {
    libraryGrid.innerHTML = '<div class="header-sub">No projects found.</div>';
    return;
  }

  projects.forEach(pName => {
    const pDirPath = path.join(outputDir, pName);
    const manifestPath = path.join(pDirPath, 'project_manifest.json');
    const costPath = path.join(pDirPath, 'cost_report.json');
    
    let metadata = { stack: 'Python', date: 'Unknown' };
    let cost = 0.00;

    if (fs.existsSync(manifestPath)) {
      try {
        const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
        metadata.stack = manifest.stack || metadata.stack;
        if (manifest.timestamp) metadata.date = new Date(manifest.timestamp * 1000).toLocaleDateString();
      } catch(e){}
    }
    
    if (fs.existsSync(costPath)) {
      try {
        const costReport = JSON.parse(fs.readFileSync(costPath, 'utf-8'));
        cost = costReport.total_cost || 0;
      } catch(e){}
    }

    const card = document.createElement('div');
    card.className = 'project-card';
    
    // Escape backslashes for Windows path safety in the onclick handler
    const escapedPath = pDirPath.replace(/\\/g, '\\\\');
    
    card.innerHTML = `
      <div class="project-title">${pName}</div>
      <div class="project-meta">
        <span><strong>Stack:</strong> ${metadata.stack}</span>
        <span><strong>Date:</strong> ${metadata.date}</span>
        <span><strong>Cost:</strong> $${cost.toFixed(4)}</span>
      </div>
      <div class="project-actions">
        <button class="btn btn-sm btn-primary" onclick="inspectProject('${pName}')">Inspect</button>
        <button class="btn btn-sm" onclick="openProjectFolder('${escapedPath}')">Folder</button>
      </div>
    `;
    libraryGrid.appendChild(card);
  });
}

function refreshDashboard() {
  const outputDir = path.resolve(__dirname, './output');
  if (!fs.existsSync(outputDir)) return;

  const projects = fs.readdirSync(outputDir, { withFileTypes: true })
    .filter(dirent => dirent.isDirectory());

  let totalFiles = 0;
  let totalCost = 0;
  let successfulBuilds = 0;

  projects.forEach(proj => {
    const pPath = path.join(outputDir, proj.name);
    const costPath = path.join(pPath, 'cost_report.json');
    const manifestPath = path.join(pPath, 'project_manifest.json');

    if (fs.existsSync(costPath)) {
      try { totalCost += JSON.parse(fs.readFileSync(costPath, 'utf-8')).total_cost || 0; } catch(e){}
    }
    
    if (fs.existsSync(manifestPath)) {
      try {
        const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
        totalFiles += manifest.files_written || 0;
        if (manifest.status === 'COMPLETE' || manifest.success) successfulBuilds++;
      } catch(e){}
    }
  });

  dashTotalProjects.textContent = projects.length;
  dashTotalFiles.textContent = totalFiles;
  dashTotalCost.textContent = `$${totalCost.toFixed(2)}`;
  dashSuccessRate.textContent = projects.length > 0 ? `${Math.round((successfulBuilds / projects.length) * 100)}%` : '0%';
}

window.inspectProject = (pName) => {
  projectName.value = pName;
  updateFileTree();
  tabs[0].click(); // Switch to Builder
};

window.openProjectFolder = (pPath) => {
  ipcRenderer.send('open-folder', pPath);
};

// ── File Tree & Preview ─────────────────────────────────────
function updateFileTree() {
  const pName = projectName.value.trim() || 'GeneratedApp';
  const baseDir = path.resolve(__dirname, './output', pName);

  if (!fs.existsSync(baseDir)) {
    fileTree.textContent = 'Output directory not found.';
    return;
  }

  fileTree.innerHTML = ''; 

  function walk(dirPath, indent, depth = 0) {
    const entries = fs.readdirSync(dirPath, { withFileTypes: true });
    entries.sort((a, b) => a.name.localeCompare(b.name));

    entries.forEach(entry => {
      const fullPath = path.join(dirPath, entry.name);
      if (entry.isDirectory()) {
         if (entry.name === '__pycache__' || entry.name === 'node_modules' || entry.name === '.git') return;
         
         const div = document.createElement('div');
         div.style.paddingLeft = `${depth * 15}px`;
         div.textContent = `📂 ${entry.name}/`;
         fileTree.appendChild(div);
         walk(fullPath, indent + '  ', depth + 1);
      } else {
        const div = document.createElement('div');
        div.className = 'file-item';
        div.style.paddingLeft = `${depth * 15}px`;
        div.style.cursor = 'pointer';
        div.style.color = 'var(--text-dim)';
        div.textContent = `📄 ${entry.name}`;
        div.onmouseover = () => div.style.color = 'var(--accent)';
        div.onmouseout = () => div.style.color = 'var(--text-dim)';
        div.onclick = () => showPreview(fullPath, entry.name);
        fileTree.appendChild(div);
      }
    });
  }

  walk(baseDir, '', 0);
  statFiles.textContent = document.querySelectorAll('.file-tree .file-item').length;
}

function showPreview(filePath, fileName) {
  try {
    const content = fs.readFileSync(filePath, 'utf-8');
    previewTitle.textContent = fileName;
    previewContent.textContent = content;
    previewOverlay.style.display = 'flex';
  } catch (e) {
    console.error('Preview failed:', e);
  }
}

closePreview.onclick = () => previewOverlay.style.display = 'none';

// ── Keyboard Shortcuts ──────────────────────────────────────
document.addEventListener('keydown', (e) => {
  if (e.ctrlKey && e.key === 'Enter' && !isBuilding) btnBuild.click();
  if (e.key === 'Escape') {
    if (previewOverlay.style.display === 'flex') closePreview.onclick();
    else if (isBuilding) btnCancel.click();
  }
});
