/**
 * Nexus Sentinel - System Monitoring & Agent Activity
 * Built for Nexus OS
 */

const sentinelApp = `
<div class="sentinel-container" style="height: 100%; padding: 20px; display: flex; flex-direction: column; gap: 20px; color: #fff; background: #08080c;">
    <div class="sentinel-header" style="display: flex; justify-content: space-between; align-items: center;">
        <h2 style="font-family: 'JetBrains Mono'; font-size: 20px; color: var(--accent);">NEXUS_SENTINEL v1.0</h2>
        <div id="sentinel-uptime" style="font-size: 11px; color: var(--text-dim);">UPTIME: 00:00:00</div>
    </div>

    <div class="stats-grid" style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px;">
        <div class="stat-card" style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; border: 1px solid var(--glass-border);">
            <div style="font-size: 10px; color: var(--accent); font-weight: 700;">CPU LOAD</div>
            <div id="cpu-val" style="font-size: 24px; font-weight: 700; margin-top: 5px;">0%</div>
            <div style="width: 100%; height: 4px; background: #222; margin-top: 10px; border-radius: 2px;">
                <div id="cpu-bar" style="width: 0%; height: 100%; background: var(--accent); transition: width 0.5s;"></div>
            </div>
        </div>
        <div class="stat-card" style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; border: 1px solid var(--glass-border);">
            <div style="font-size: 10px; color: var(--accent); font-weight: 700;">MEMORY</div>
            <div id="mem-val" style="font-size: 24px; font-weight: 700; margin-top: 5px;">0%</div>
            <div style="width: 100%; height: 4px; background: #222; margin-top: 10px; border-radius: 2px;">
                <div id="mem-bar" style="width: 0%; height: 100%; background: var(--accent); transition: width 0.5s;"></div>
            </div>
        </div>
        <div class="stat-card" style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; border: 1px solid var(--glass-border);">
            <div style="font-size: 10px; color: var(--accent); font-weight: 700;">DISK IO</div>
            <div id="disk-val" style="font-size: 24px; font-weight: 700; margin-top: 5px;">0%</div>
            <div style="width: 100%; height: 4px; background: #222; margin-top: 10px; border-radius: 2px;">
                <div id="disk-bar" style="width: 0%; height: 100%; background: var(--accent); transition: width 0.5s;"></div>
            </div>
        </div>
    </div>

    <div class="activity-log" style="flex: 1; background: #000; border: 1px solid var(--glass-border); border-radius: 8px; padding: 15px; overflow-y: auto; font-family: 'JetBrains Mono'; font-size: 12px;">
        <div style="color: var(--accent); margin-bottom: 10px; border-bottom: 1px solid #222; padding-bottom: 5px;">LIVE AGENT ACTIVITY</div>
        <div id="agent-activity-feed" style="display: flex; flex-direction: column; gap: 5px;">
            <div style="color: #444;">Initiating Agent Handshake...</div>
        </div>
    </div>
</div>
`;

window.NexusOS_Apps = window.NexusOS_Apps || {};
window.NexusOS_Apps.sentinel = {
    init: (winId) => {
        const container = document.getElementById(`${winId}-content`);
        container.innerHTML = sentinelApp;
        
        const cpuVal = container.querySelector('#cpu-val');
        const cpuBar = container.querySelector('#cpu-bar');
        const memVal = container.querySelector('#mem-val');
        const memBar = container.querySelector('#mem-bar');
        const diskVal = container.querySelector('#disk-val');
        const diskBar = container.querySelector('#disk-bar');
        const activityFeed = container.querySelector('#agent-activity-feed');

        const updateStats = async () => {
            try {
                const response = await fetch(`http://${window.location.hostname}:8081/api/sys/stats`);
                const stats = await response.json();
                
                cpuVal.innerText = `${Math.round(stats.cpu)}%`;
                cpuBar.style.width = `${stats.cpu}%`;
                memVal.innerText = `${Math.round(stats.memory)}%`;
                memBar.style.width = `${stats.memory}%`;
                diskVal.innerText = `${Math.round(stats.disk)}%`;
                diskBar.style.width = `${stats.disk}%`;

                // Heuristic coloring
                const color = stats.cpu > 80 ? '#f55' : (stats.cpu > 50 ? '#fb0' : 'var(--accent)');
                cpuBar.style.background = color;
            } catch (err) {
                console.error("Sentinel sync error", err);
            }
        };

        const updateActivity = async () => {
            try {
                const response = await fetch(`http://${window.location.hostname}:8081/api/pulse/feed`);
                const data = await response.json();
                
                if (data.feed && data.feed.length > 0) {
                    activityFeed.innerHTML = '';
                    data.feed.slice(0, 10).forEach(log => {
                        const line = document.createElement('div');
                        line.style.display = 'flex';
                        line.style.gap = '10px';
                        line.innerHTML = `
                            <span style="color: #666;">${log.timestamp.split('T')[1].split('.')[0]}</span>
                            <span style="color: var(--accent); font-weight: 700;">[${log.author.toUpperCase()}]</span>
                            <span style="color: #bbb;">${log.content.substring(0, 80)}${log.content.length > 80 ? '...' : ''}</span>
                        `;
                        activityFeed.appendChild(line);
                    });
                }
            } catch (err) {}
        };

        const interval = setInterval(() => {
            if (!document.getElementById(winId)) {
                clearInterval(interval);
                return;
            }
            updateStats();
            updateActivity();
        }, 2000);

        updateStats();
        updateActivity();
    }
};
