/**
 * Nexus Agent - Conversational Interface for Nexus OS
 * Features a high-fidelity "Awareness Core" idle state and agentic talk functionality.
 */

const nexusAgentApp = `
<div class="agent-container" style="height: 100%; display: flex; flex-direction: column; background: #050508; color: #fff; overflow: hidden; position: relative;">
    <!-- Awareness Core Background -->
    <div class="core-stage" style="height: 200px; display: flex; align-items: center; justify-content: center; position: relative; background: radial-gradient(circle at 50% 50%, rgba(139, 92, 246, 0.1) 0%, transparent 70%);">
        <div id="awareness-orb" class="orb-idle"></div>
        <div class="orb-rings">
            <div class="ring r1"></div>
            <div class="ring r2"></div>
        </div>
        <div id="agent-status" style="position: absolute; bottom: 20px; font-family: 'JetBrains Mono'; font-size: 10px; color: var(--accent); letter-spacing: 2px; opacity: 0.8;">AWARENESS_SYNCED</div>
    </div>

    <!-- Chat Experience -->
    <div id="chat-log" style="flex: 1; overflow-y: auto; padding: 20px; display: flex; flex-direction: column; gap: 15px; font-family: 'Inter'; font-size: 14px; scroll-behavior: smooth;">
        <div class="chat-msg system">
            <div class="msg-content">Neural link established. Antigravity online.</div>
        </div>
    </div>

    <!-- Input Bar -->
    <div class="chat-input-area" style="padding: 20px; border-top: 1px solid rgba(255,255,255,0.05); background: rgba(0,0,0,0.4); backdrop-filter: blur(10px);">
        <div style="display: flex; gap: 10px; background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 5px 15px; align-items: center; transition: border-color 0.3s;" id="input-container">
            <input type="text" id="agent-input" placeholder="Communicate with Nexus..." style="flex: 1; background: transparent; border: none; padding: 12px 0; color: #fff; font-family: 'Inter'; outline: none; font-size: 14px;">
            <button id="send-btn" style="background: var(--accent); color: white; border: none; width: 32px; height: 32px; border-radius: 8px; cursor: pointer; display: flex; align-items: center; justify-content: center; transition: transform 0.2s;">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"></path></svg>
            </button>
        </div>
    </div>
</div>

<style>
:root {
    --accent: #8b5cf6;
    --accent-glow: rgba(139, 92, 246, 0.4);
}

.orb-idle {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    background: radial-gradient(circle at 30% 30%, #c4b5fd 0%, #8b5cf6 40%, #4c1d95 100%);
    box-shadow: 0 0 40px var(--accent-glow), inset 0 0 20px rgba(255,255,255,0.2);
    position: relative;
    z-index: 2;
    animation: breathe 4s ease-in-out infinite;
}

.orb-thinking {
    animation: thinking 1s linear infinite !important;
    background: radial-gradient(circle at 30% 30%, #fff 0%, #8b5cf6 50%, #1e1e2e 100%) !important;
    box-shadow: 0 0 60px var(--accent) !important;
}

.orb-rings .ring {
    position: absolute;
    top: 50%; left: 50%;
    transform: translate(-50%, -50%);
    border: 1px solid rgba(139, 92, 246, 0.2);
    border-radius: 50%;
}

.ring.r1 { width: 120px; height: 120px; animation: spin 10s linear infinite; border-style: dashed; }
.ring.r2 { width: 160px; height: 160px; animation: spin 15s linear reverse infinite; opacity: 0.5; }

@keyframes breathe {
    0%, 100% { transform: scale(1); opacity: 0.8; }
    50% { transform: scale(1.05); opacity: 1; }
}

@keyframes thinking {
    0% { transform: scale(1); filter: hue-rotate(0deg); }
    50% { transform: scale(1.1); filter: hue-rotate(90deg); }
    100% { transform: scale(1); filter: hue-rotate(0deg); }
}

@keyframes spin {
    from { transform: translate(-50%, -50%) rotate(0deg); }
    to { transform: translate(-50%, -50%) rotate(360deg); }
}

.chat-msg {
    max-width: 85%;
    padding: 12px 16px;
    border-radius: 12px;
    line-height: 1.5;
    animation: slideIn 0.3s ease-out;
}

.chat-msg.user {
    align-self: flex-end;
    background: var(--accent);
    color: white;
    border-bottom-right-radius: 2px;
}

.chat-msg.agent {
    align-self: flex-start;
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    color: #eee;
    border-bottom-left-radius: 2px;
}

.chat-msg.system {
    align-self: center;
    background: transparent;
    color: #555;
    font-size: 11px;
    font-family: 'JetBrains Mono';
    text-transform: uppercase;
    letter-spacing: 1px;
}

@keyframes slideIn {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}

#input-container.focused {
    border-color: var(--accent);
    box-shadow: 0 0 10px rgba(139, 92, 246, 0.2);
}
</style>
`;

window.NexusOS_Apps = window.NexusOS_Apps || {};
window.NexusOS_Apps.nexus_agent = {
  init: (winId) => {
    const container = document.getElementById(`${winId}-content`);
    container.style.padding = "0"; // Override default padding
    container.innerHTML = nexusAgentApp;

    const log = container.querySelector("#chat-log");
    const input = container.querySelector("#agent-input");
    const sendBtn = container.querySelector("#send-btn");
    const orb = container.querySelector("#awareness-orb");
    const status = container.querySelector("#agent-status");
    const inputCont = container.querySelector("#input-container");

    const addMessage = (text, side = "agent") => {
      const msg = document.createElement("div");
      msg.className = `chat-msg ${side}`;
      msg.innerHTML = `<div class="msg-content">${text}</div>`;
      log.appendChild(msg);
      log.scrollTop = log.scrollHeight;
      return msg; // Return the message element for later updates
    };

        const handleSend = async () => {
            const query = input.value.trim();
            if (!query) return;

            addMessage(query, 'user');
            input.value = '';
            
            orb.classList.add('orb-thinking');
            orb.classList.remove('orb-idle'); // Ensure idle state is removed
            status.innerText = 'PROCESSING_NEURAL_PATHWAY';
            status.style.color = "#fff"; // Set color for thinking state

            try {
                const response = await fetch(`http://${window.location.hostname}:8081/api/agent/chat`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: query })
                });

                if (!response.ok) throw new Error('Uplink failed');

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let agentMsg = addMessage('', 'agent');
                let fullText = '';

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    
                    const chunk = decoder.decode(value, { stream: true });
                    fullText += chunk;
                    agentMsg.querySelector('.msg-content').innerText = fullText;
                    log.scrollTop = log.scrollHeight;
                }

                // Check for code blocks to apply
                if (fullText.includes('window.NexusOS_Apps')) {
                    const applyBtn = document.createElement('button');
                    applyBtn.innerText = '✨ Install this App';
                    applyBtn.style.cssText = 'margin-top:10px; padding:5px 12px; background:var(--accent); border:none; border-radius:4px; color:#fff; cursor:pointer; font-size:11px;';
                    applyBtn.onclick = async () => {
                        const codeMatch = fullText.match(/```javascript\n([\s\S]*?)```/) || fullText.match(/```js\n([\s\S]*?)```/);
                        const code = codeMatch ? codeMatch[1] : fullText;
                        const appId = fullText.match(/NexusOS_Apps\.(\w+)/)?.[1] || 'custom_app';
                        
                        const res = await fetch(`http://${window.location.hostname}:8081/api/agent/apply`, {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ app_id: appId, code: code })
                        });
                        const data = await res.json();
                        if (data.success) {
                            alert(`App '${appId}' installed successfully! Refresh Nexus OS to see it.`);
                        } else {
                            alert(`Failed to install app '${appId}': ${data.error || 'Unknown error'}`);
                        }
                    };
                    agentMsg.appendChild(applyBtn);
                }

            } catch (err) {
                addMessage(`Uplink Error: ${err.message}`, 'system');
            } finally {
                orb.classList.remove('orb-thinking');
                orb.classList.add('orb-idle');
                status.innerText = 'AWARENESS_SYNCED';
                status.style.color = "var(--accent)"; // Reset color for idle state
            }
        };

            input.onfocus = () => inputCont.classList.add("focused");
            input.onblur = () => inputCont.classList.remove("focused");
            input.onkeydown = (e) => {
                if (e.key === "Enter") handleSend();
            };

            sendBtn.onclick = handleSend;
    }
};
