/**
 * Settings App for Nexus OS
 */
const settingsTemplate = `
<div class="settings-container" style="padding: 20px; font-family: 'Inter', sans-serif;">
    <h2 style="margin-bottom: 20px; font-size: 18px; color: var(--accent);">System Settings</h2>
    
    <div class="setting-group" style="margin-bottom: 20px;">
        <label style="display: block; font-size: 12px; color: var(--text-dim); margin-bottom: 8px;">System Performance</label>
        <div id="sys-stats" style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 8px;">
            <div style="margin-bottom: 10px;">CPU Usage: <span id="cpu-val">--%</span></div>
            <div style="margin-bottom: 10px;">Memory: <span id="mem-val">--%</span></div>
            <div>Disk Space: <span id="disk-val">--%</span></div>
        </div>
    </div>

    <div class="setting-group" style="margin-bottom: 20px;">
        <label style="display: block; font-size: 12px; color: var(--text-dim); margin-bottom: 8px;">Theme Accent Color</label>
        <input type="color" id="accent-picker" value="#8b5cf6" style="width: 100%; height: 40px; border: none; border-radius: 4px; background: transparent; cursor: pointer;">
    </div>

    <button id="settings-save" class="win-btn" style="width: 100%; height: 40px; border-radius: 8px; background: var(--accent); color: white; border: none; cursor: pointer; font-weight: 600;">Save Preferences</button>
</div>
`;

window.NexusOS_Apps = window.NexusOS_Apps || {};
window.NexusOS_Apps.settings = {
    init: (winId) => {
        const content = document.getElementById(`${winId}-content`);
        content.innerHTML = settingsTemplate;

        const picker = content.querySelector('#accent-picker');
        const saveBtn = content.querySelector('#settings-save');
        
        const updateStats = async () => {
            try {
                const res = await fetch(`http://${window.location.hostname}:8081/api/sys/stats`);
                const data = await res.json();
                content.querySelector('#cpu-val').textContent = data.cpu + '%';
                content.querySelector('#mem-val').textContent = data.memory + '%';
                content.querySelector('#disk-val').textContent = data.disk + '%';
            } catch (e) {}
        };

        updateStats();
        const interval = setInterval(updateStats, 3000);

        saveBtn.onclick = () => {
            document.documentElement.style.setProperty('--accent', picker.value);
            document.documentElement.style.setProperty('--accent-glow', picker.value + '66');
            alert("Settings Updated (Session only)");
        };

        // Cleanup interval on close (requires WindowManager to call a cleanup method)
        // For now, simplicity rules.
    }
};
