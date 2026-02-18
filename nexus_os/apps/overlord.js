/**
 * Overlord Agent App for Nexus OS
 */
const overlordApp = `
<div class="overlord-container" style="padding: 20px; display: flex; flex-direction: column; gap: 20px; height: 100%;">
    <div class="overlord-header" style="display: flex; justify-content: space-between; align-items: flex-end;">
        <div>
            <h2 style="font-family: 'JetBrains Mono'; font-size: 24px; color: var(--accent);">OVERLORD BUILDER</h2>
            <p style="font-size: 12px; color: var(--text-dim);">Autonomous Synthesis Interface</p>
        </div>
        <div id="build-status" style="font-family: 'JetBrains Mono'; color: var(--text-dim); border: 1px solid var(--glass-border); padding: 4px 12px; border-radius: 4px;">
            STANDBY
        </div>
    </div>

    <div class="setup-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 15px;">
        <div>
            <label style="font-size: 11px; font-weight: 700; color: var(--accent);">PROJECT NAME</label>
            <input id="overlord-name" type="text" value="NexusProject_1" style="width: 100%; background: rgba(0,0,0,0.3); border: 1px solid var(--glass-border); color: white; padding: 8px; border-radius: 4px; font-family: 'JetBrains Mono'; font-size: 12px;">
        </div>
        <div>
            <label style="font-size: 11px; font-weight: 700; color: var(--accent);">MODEL</label>
            <select id="overlord-model" style="width: 100%; background: rgba(0,0,0,0.3); border: 1px solid var(--glass-border); color: white; padding: 8px; border-radius: 4px; font-family: 'JetBrains Mono'; font-size: 12px;">
                <option value="gpt-4o">gpt-4o</option>
                <option value="gemini-2.0-pro-exp-02-05">gemini-2.0-pro</option>
                <option value="claude-3-5-sonnet-20241022">claude-3-5-sonnet</option>
            </select>
        </div>
    </div>

    <div class="prompt-section">
        <label style="font-size: 11px; font-weight: 700; color: var(--accent);">MISSION PROMPT</label>
        <textarea id="overlord-prompt" placeholder="Define the software requirements..." style="width: 100%; height: 80px; background: rgba(0,0,0,0.3); border: 1px solid var(--glass-border); color: white; padding: 10px; border-radius: 4px; font-family: 'JetBrains Mono'; font-size: 13px; resize: none;"></textarea>
    </div>

    <div class="logs-container" style="flex: 1; min-height: 0; background: #000; border: 1px solid var(--glass-border); border-radius: 8px; padding: 10px; overflow-y: auto; font-family: 'JetBrains Mono'; font-size: 12px; line-height: 1.4;">
        <div id="overlord-logs" style="color: #0f0;">[SYSTEM] Ready for mission deployment.</div>
    </div>

    <button id="overlord-launch" style="background: var(--accent); border: none; color: white; padding: 12px; border-radius: 8px; font-weight: 700; cursor: pointer; font-family: 'JetBrains Mono'; transition: all 0.2s;">🚀 LAUNCH MISSION</button>
</div>
`;

window.NexusOS_Apps = window.NexusOS_Apps || {};
window.NexusOS_Apps.overlord = {
    init: (winId) => {
        const content = document.getElementById(`${winId}-content`);
        content.innerHTML = overlordApp;

        const btn = content.querySelector('#overlord-launch');
        const logger = content.querySelector('#overlord-logs');
        const status = content.querySelector('#build-status');

        btn.onclick = () => {
            const name = content.querySelector('#overlord-name').value;
            const prompt = content.querySelector('#overlord-prompt').value;
            
            if (!prompt) return alert("Mission prompt required.");

            btn.disabled = true;
            btn.style.opacity = 0.5;
            status.textContent = "BUILDING";
            status.style.color = "var(--accent)";

            const ws = new WebSocket(`ws://${window.location.hostname}:8081/ws/build`);
            
            ws.onopen = () => {
                ws.send(JSON.stringify({
                    projectName: name,
                    prompt: prompt
                }));
                logger.innerHTML += `<div style="color: var(--accent)">[SYSTEM] Uplink established. Starting build...</div>`;
                window.NexusOS.notify('Overlord', 'Mission deployment initiated.');
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                if (data.type === "log") {
                    const line = document.createElement('div');
                    line.textContent = `[${data.tag}] ${data.message}`;
                    if (data.tag === "STDERR") line.style.color = "#f55";
                    logger.appendChild(line);
                    logger.parentElement.scrollTop = logger.parentElement.scrollHeight;
                } else if (data.type === "complete") {
                    status.textContent = data.success ? "SUCCESS" : "FAILED";
                    status.style.color = data.success ? "#0f0" : "#f00";
                    btn.disabled = false;
                    btn.style.opacity = 1;
                    
                    const msg = data.success ? 'Project synthesized successfully.' : 'Project synthesis failed.';
                    window.NexusOS.notify('Overlord', msg, data.success ? 'success' : 'error');
                }
            };
        };
    }
};
