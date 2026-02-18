/**
 * Explorer App for Nexus OS
 */
const explorerApp = `
<div class="explorer-container" style="display: flex; flex-direction: column; height: 100%; font-family: 'Inter', sans-serif;">
    <div class="explorer-toolbar" style="padding: 10px; background: rgba(255,255,255,0.05); border-bottom: 1px solid var(--glass-border); display: flex; gap: 10px; align-items: center;">
        <button id="explorer-back" class="win-btn" style="width: auto; height: auto; padding: 4px 10px; border-radius: 4px; background: var(--glass-border); color: white; border: none; cursor: pointer; font-size: 11px;">⬅ Back</button>
        <button id="explorer-refresh" class="win-btn" style="width: auto; height: auto; padding: 4px 10px; border-radius: 4px; background: var(--glass-border); color: white; border: none; cursor: pointer; font-size: 11px;">🔄 Refresh</button>
        <div id="explorer-path" style="font-size: 11px; color: var(--text-dim); font-family: 'JetBrains Mono'; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">/output</div>
    </div>
    <div id="explorer-list" style="flex: 1; overflow-y: auto; padding: 10px; display: flex; flex-direction: column; gap: 2px;">
        <!-- Files will be injected here -->
    </div>
</div>
`;

window.NexusOS_Apps = window.NexusOS_Apps || {};
window.NexusOS_Apps.explorer = {
    currentPath: ".",
    init: (winId) => {
        const content = document.getElementById(`${winId}-content`);
        content.innerHTML = explorerApp;
        
        const list = content.querySelector('#explorer-list');
        const pathDisplay = content.querySelector('#explorer-path');
        const backBtn = content.querySelector('#explorer-back');
        const refreshBtn = content.querySelector('#explorer-refresh');

        const loadDir = async (path) => {
            this.currentPath = path;
            pathDisplay.textContent = `/output/${path === '.' ? '' : path}`;
            
            try {
                const res = await fetch(`http://${window.location.hostname}:8081/api/fs/ls?path=${encodeURIComponent(path)}`);
                const items = await res.json();
                
                list.innerHTML = '';
                if (items.error) {
                    list.innerHTML = `<div style="color: #f55; padding: 20px;">${items.error}</div>`;
                    return;
                }

                items.forEach(item => {
                    const row = document.createElement('div');
                    row.style.padding = '8px 12px';
                    row.style.display = 'flex';
                    row.style.alignItems = 'center';
                    row.style.gap = '10px';
                    row.style.cursor = 'pointer';
                    row.style.borderRadius = '6px';
                    row.onmouseover = () => row.style.background = 'rgba(255,255,255,0.05)';
                    row.onmouseout = () => row.style.background = 'transparent';
                    
                    row.innerHTML = `
                        <span style="font-size: 16px;">${item.isDir ? '📁' : '📄'}</span>
                        <span style="font-size: 12px; color: ${item.isDir ? 'var(--accent)' : 'var(--text)'};">${item.name}</span>
                        <span style="margin-left: auto; font-size: 10px; color: var(--text-dim);">${item.isDir ? '' : (item.size / 1024).toFixed(1) + ' KB'}</span>
                    `;

                    row.onclick = () => {
                        if (item.isDir) {
                            loadDir(path === '.' ? item.name : `${path}/${item.name}`);
                        }
                    };
                    list.appendChild(row);
                });
            } catch (e) {
                list.innerHTML = `<div style="color: #f55; padding: 20px;">Connection Failed</div>`;
            }
        };

        backBtn.onclick = () => {
            if (this.currentPath === ".") return;
            const parts = this.currentPath.split('/');
            parts.pop();
            loadDir(parts.join('/') || ".");
        };

        refreshBtn.onclick = () => loadDir(this.currentPath);

        loadDir(".");
    }
};
