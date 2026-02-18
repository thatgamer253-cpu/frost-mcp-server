window.NexusOS_Apps.payout_app = {
    init: (winId) => {
        const win = document.getElementById(winId);
        const container = win.querySelector('.app-container');
        
        container.innerHTML = `
            <div style="padding: 20px; color: #E8E6F0; font-family: 'Consolas', monospace;">
                <h2 style="color: #00FF88; border-bottom: 2px solid #2A2D3A; padding-bottom: 10px;">💰 SOVEREIGN PAYOUT</h2>
                <div id="payout-status" style="margin: 20px 0; padding: 15px; background: #0D0D0D; border-radius: 8px; border: 1px solid #2A2D3A;">
                    <p style="color: #6B6F80;">TOTAL_COMMERCIAL_REVENUE:</p>
                    <p id="total-revenue" style="font-size: 24px; color: #00D4FF;">LOADING...</p>
                </div>
                
                <div style="margin-bottom: 20px;">
                    <label style="display: block; margin-bottom: 8px; color: #6B6F80;">STRIPE_DESTINATION:</label>
                    <input type="password" id="stripe-key-input" placeholder="sk_live_..." 
                        style="width: 100%; padding: 10px; background: #1C1F2B; border: 1px solid #2A2D3A; color: #E8E6F0; border-radius: 4px;">
                </div>

                <button id="cashout-btn" style="width: 100%; padding: 12px; background: #00FF88; color: #0D0D0D; border: none; border-radius: 6px; font-weight: bold; cursor: pointer; transition: 0.2s;">
                    INITIATE_CASHOUT
                </button>
                
                <div id="payout-log" style="margin-top: 20px; height: 100px; overflow-y: auto; background: #000; padding: 10px; font-size: 11px; color: #00FF00; border-radius: 4px;">
                    [INIT] Payout Gateway Ready.
                </div>
            </div>
        `;

        const log = (msg) => {
            const logEl = container.querySelector('#payout-log');
            logEl.innerHTML += `<div>[${new Date().toLocaleTimeString()}] ${msg}</div>`;
            logEl.scrollTop = logEl.scrollHeight;
        };

        const updateBalance = async () => {
             // In a real Nexus OS, we would fetch this from the backend
             // For now, we simulate the 'view' of the log
             container.querySelector('#total-revenue').innerText = "$769.62 (USD)";
        };

        updateBalance();

        container.querySelector('#cashout-btn').onclick = async () => {
            const key = container.querySelector('#stripe-key-input').value;
            if (!key) {
                log("ERROR: Stripe Key Required.");
                return;
            }

            log("COMMAND: INITIATE_CASHOUT");
            log("TARGET: SOVEREIGN_AMBASSADOR");
            
            // Send message to agent chat
            try {
                const response = await fetch('/api/agent/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ message: `cash out to stripe using key ${key}` })
                });
                log("UPLINK: SECURE_CHANNEL_READY");
                log("STATUS: PROCESSING_TRANSMUTATION...");
                alert("Payout sequence initiated. Monitor the Agent Hub for confirmation.");
            } catch (err) {
                log(`ERROR: Uplink failed - ${err.message}`);
            }
        };

        // Styling
        const btn = container.querySelector('#cashout-btn');
        btn.onmouseover = () => btn.style.background = "#00DD77";
        btn.onmouseout = () => btn.style.background = "#00FF88";
    }
};
