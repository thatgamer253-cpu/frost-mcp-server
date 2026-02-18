/**
 * Nexus OS Core
 * Simple Window Manager & App Orchestrator
 */

class WindowManager {
    constructor() {
        this.container = document.getElementById('windowsContainer');
        this.windows = [];
        this.zIndexBase = 100;
        this.activeWindow = null;
        this.startMenuOpen = false;
        
        this.initEventListeners();
        this.updateClock();
        setInterval(() => this.updateClock(), 1000);
    }

    initEventListeners() {
        // Desktop Shortcuts
        document.querySelectorAll('.shortcut').forEach(el => {
            el.onclick = () => this.openApp(el.dataset.app);
        });

        // Start Menu Items
        document.querySelectorAll('.start-item').forEach(el => {
            el.onclick = () => {
                this.openApp(el.dataset.app);
                this.toggleStartMenu(false);
            };
        });

        // Start Button
        document.getElementById('startMenuBtn').onclick = (e) => {
            e.stopPropagation();
            this.toggleStartMenu();
        };

        // Global Clicks
        document.addEventListener('mousedown', (e) => {
            const winEl = e.target.closest('.window');
            if (winEl) {
                this.focusWindow(winEl.id);
            } else if (!e.target.closest('#startMenu')) {
                this.toggleStartMenu(false);
            }
            
            // Close Context Menu
            if (!e.target.closest('#contextMenu')) {
                const ctx = document.getElementById('contextMenu');
                if (ctx) ctx.style.display = 'none';
            }

            // Close Command Palette
            if (!e.target.closest('#command-palette')) {
                document.getElementById('command-palette').style.display = 'none';
            }
        });

        // Global Hotkeys
        document.addEventListener('keydown', (e) => {
            if (e.altKey && e.code === 'Space') {
                e.preventDefault();
                this.toggleCommandPalette();
            }
        });

        // Command Palette Input
        const cmdInput = document.getElementById('cmd-input');
        cmdInput.oninput = (e) => this.filterCommands(e.target.value);
        cmdInput.onkeydown = (e) => {
            if (e.key === 'Enter') {
                const results = document.getElementById('cmd-results');
                if (results.firstChild) results.firstChild.click();
            }
        };

        // Desktop Context Menu
        document.getElementById('desktop').oncontextmenu = (e) => {
            e.preventDefault();
            this.showContextMenu(e, [
                { label: '🚀 Launch Overlord', icon: '🚀', action: () => this.openApp('overlord') },
                { label: '🖥️ New Terminal', icon: '🖥️', action: () => this.openApp('terminal') },
                { label: '📂 Explorer', icon: '📂', action: () => this.openApp('explorer') },
                { type: 'sep' },
                { label: '🖼️ Change Wallpaper', icon: '🖼️', action: () => this.notify('Theme', 'System UI Customization pending...') },
                { label: '⚙️ Settings', icon: '⚙️', action: () => this.openApp('settings') }
            ]);
        };
    }

    toggleCommandPalette() {
        const pal = document.getElementById('command-palette');
        const visible = pal.style.display === 'block';
        pal.style.display = visible ? 'none' : 'block';
        if (!visible) {
            document.getElementById('cmd-input').value = '';
            document.getElementById('cmd-results').innerHTML = '';
            setTimeout(() => document.getElementById('cmd-input').focus(), 10);
        }
    }

    filterCommands(query) {
        const results = document.getElementById('cmd-results');
        results.innerHTML = '';
        if (!query) return;

        const apps = [
            { id: 'overlord', name: 'Overlord Engine', icon: '🚀' },
            { id: 'terminal', name: 'Terminal', icon: '🖥️' },
            { id: 'explorer', name: 'Explorer', icon: '📂' },
            { id: 'pulse', name: 'Nexus Pulse', icon: '📶' },
            { id: 'sentinel', name: 'Nexus Sentinel', icon: '🛡️' },
            { id: 'nexus_agent', name: 'Nexus Agent', icon: '💎' },
            { id: 'settings', name: 'Settings', icon: '⚙️' }
        ];

        const matches = apps.filter(a => a.name.toLowerCase().includes(query.toLowerCase()));
        matches.forEach(m => {
            const el = document.createElement('div');
            el.className = 'menu-item';
            el.style.padding = '12px 24px';
            el.innerHTML = `<span>${m.icon}</span> ${m.name}`;
            el.onclick = () => {
                this.openApp(m.id);
                document.getElementById('command-palette').style.display = 'none';
            };
            results.appendChild(el);
        });
    }

    notify(title, message, type = 'info') {
        const stack = document.getElementById('notification-stack');
        if (!stack) {
            const el = document.createElement('div');
            el.id = 'notification-stack';
            document.body.appendChild(el);
        }
        
        const toast = document.createElement('div');
        toast.className = 'toast';
        toast.innerHTML = `
            <div class="toast-title">${title}</div>
            <div class="toast-body">${message}</div>
        `;
        
        document.getElementById('notification-stack').appendChild(toast);
        
        setTimeout(() => {
            toast.classList.add('fade-out');
            setTimeout(() => toast.remove(), 300);
        }, 5000);
    }

    showContextMenu(e, items) {
        let menu = document.getElementById('contextMenu');
        if (!menu) {
            menu = document.createElement('div');
            menu.id = 'contextMenu';
            document.body.appendChild(menu);
        }
        
        menu.innerHTML = '';
        items.forEach(item => {
            if (item.type === 'sep') {
                const sep = document.createElement('div');
                sep.className = 'menu-sep';
                menu.appendChild(sep);
            } else {
                const el = document.createElement('div');
                el.className = 'menu-item';
                el.innerHTML = `<span>${item.icon || ''}</span> ${item.label}`;
                el.onclick = () => {
                    item.action();
                    menu.style.display = 'none';
                };
                menu.appendChild(el);
            }
        });
        
        menu.style.left = `${e.clientX}px`;
        menu.style.top = `${e.clientY}px`;
        menu.style.display = 'block';
    }

    toggleStartMenu(force) {
        this.startMenuOpen = force !== undefined ? force : !this.startMenuOpen;
        const menu = document.getElementById('startMenu');
        if (this.startMenuOpen) {
            menu.classList.add('open');
        } else {
            menu.classList.remove('open');
        }
    }

    openApp(appName) {
        const id = `win-${appName}-${Date.now()}`;
        const title = appName.charAt(0).toUpperCase() + appName.slice(1);
        
        const winConfig = {
            id,
            title,
            appName,
            x: 100 + (this.windows.length * 20),
            y: 50 + (this.windows.length * 20)
        };

        this.createWindow(winConfig);
        this.initializeAppComponent(winConfig.id, appName);
        this.notify('System', `Launching ${title}...`);
    }

    async initializeAppComponent(winId, appName) {
        if (!window.NexusOS_Apps || !window.NexusOS_Apps[appName]) {
            const script = document.createElement('script');
            script.src = `apps/${appName}.js`;
            document.head.appendChild(script);
            script.onload = () => {
                if (window.NexusOS_Apps && window.NexusOS_Apps[appName]) {
                    window.NexusOS_Apps[appName].init(winId);
                }
            };
        } else {
            window.NexusOS_Apps[appName].init(winId);
        }
    }

    createWindow(config) {
        const win = document.createElement('div');
        win.id = config.id;
        win.className = 'window';
        win.style.left = `${config.x}px`;
        win.style.top = `${config.y}px`;
        win.style.zIndex = this.zIndexBase + this.windows.length;

        win.innerHTML = `
            <div class="window-header">
                <div class="window-title">${config.title}</div>
                <div class="window-controls">
                    <div class="win-btn win-min"></div>
                    <div class="win-btn win-max"></div>
                    <div class="win-btn win-close"></div>
                </div>
            </div>
            <div class="window-content" id="${config.id}-content">
                <div style="padding: 20px; color: var(--text-dim); font-family: 'JetBrains Mono'">
                    Initializing ${config.appName.toUpperCase()} Matrix...
                </div>
            </div>
        `;

        this.container.appendChild(win);
        this.windows.push({ id: config.id, element: win, minimized: false });
        this.focusWindow(config.id);
        this.makeDraggable(win);
        this.addTaskbarItem(config);

        // Control buttons
        win.querySelector('.win-close').onclick = (e) => {
            e.stopPropagation();
            this.closeWindow(config.id);
        };
        win.querySelector('.win-min').onclick = (e) => {
            e.stopPropagation();
            this.minimizeWindow(config.id, true); // Fixed: minimizeWindow now takes force
        };
    }

    makeDraggable(el) {
        const header = el.querySelector('.window-header');
        let pos1 = 0, pos2 = 0, pos3 = 0, pos4 = 0;
        header.onmousedown = (e) => {
            e.preventDefault();
            this.focusWindow(el.id);
            pos3 = e.clientX;
            pos4 = e.clientY;
            document.onmouseup = () => {
                document.onmouseup = null;
                document.onmousemove = null;
            };
            document.onmousemove = (e) => {
                e.preventDefault();
                pos1 = pos3 - e.clientX;
                pos2 = pos4 - e.clientY;
                pos3 = e.clientX;
                pos4 = e.clientY;
                el.style.top = (el.offsetTop - pos2) + "px";
                el.style.left = (el.offsetLeft - pos1) + "px";
            };
        };
    }

    focusWindow(id) {
        const winObj = this.windows.find(w => w.id === id);
        if (winObj && winObj.minimized) {
            this.minimizeWindow(id, false);
        }

        this.windows.forEach(w => {
            w.element.classList.remove('active');
            if (w.id === id) {
                this.zIndexBase++;
                w.element.style.zIndex = this.zIndexBase;
                w.element.classList.add('active');
                this.activeWindow = id;
            }
        });
        
        document.querySelectorAll('.taskbar-item').forEach(item => {
            item.classList.remove('active');
            if (item.dataset.winId === id) item.classList.add('active');
        });
    }

    minimizeWindow(id, forceMin) {
        const winObj = this.windows.find(w => w.id === id);
        if (!winObj) return;

        winObj.minimized = forceMin !== undefined ? forceMin : !winObj.minimized;
        if (winObj.minimized) {
            winObj.element.classList.add('minimized');
            this.activeWindow = null;
        } else {
            winObj.element.classList.remove('minimized');
            this.focusWindow(id);
        }
    }

    closeWindow(id) {
        const winObj = this.windows.find(w => w.id === id);
        if (winObj) {
            winObj.element.remove();
            this.windows = this.windows.filter(w => w.id !== id);
            const taskItem = document.querySelector(`.taskbar-item[data-win-id="${id}"]`);
            if (taskItem) taskItem.remove();
        }
    }

    addTaskbarItem(config) {
        const tray = document.getElementById('runningApps');
        const item = document.createElement('div');
        item.className = 'taskbar-item running';
        item.dataset.winId = config.id;
        item.textContent = config.title;
        item.onclick = () => {
            const winObj = this.windows.find(w => w.id === config.id);
            if (this.activeWindow === config.id && !winObj.minimized) {
                this.minimizeWindow(config.id, true);
            } else {
                this.focusWindow(config.id);
            }
        };
        tray.appendChild(item);
    }

    updateClock() {
        const now = new Date();
        const dateStr = now.toLocaleDateString([], { month: 'short', day: 'numeric' });
        const timeStr = now.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit' });
        document.getElementById('clock').innerHTML = `<div style="text-align: right">${timeStr}<br><span style="font-size: 10px">${dateStr}</span></div>`;
    }
}

window.NexusOS = new WindowManager();

// Global OS Instance
window.NexusOS = new WindowManager();
