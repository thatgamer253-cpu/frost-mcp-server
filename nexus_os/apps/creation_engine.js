
/**
 * Creation Engine App for Nexus OS
 * Embeds the Streamlit Dashboard (localhost:8501)
 */
window.NexusOS_Apps = window.NexusOS_Apps || {};
window.NexusOS_Apps.creation_engine = {
    init: (winId) => {
        const content = document.getElementById(`${winId}-content`);
        // Remove padding to allow iframe to fill the window
        content.style.padding = "0";
        content.style.overflow = "hidden";
        
        content.innerHTML = `
            <div style="width: 100%; height: 100%; display: flex; flex-direction: column; background: #0e1117;">
                <div style="padding: 10px; background: #262730; color: #fff; font-family: 'JetBrains Mono'; font-size: 12px; border-bottom: 1px solid #444; display: flex; justify-content: space-between;">
                    <span>🔵 Connected: localhost:8501</span>
                    <span style="color: #0f0;">● Online</span>
                </div>
                <iframe src="http://localhost:8501/?embed=true" 
                        style="width: 100%; height: 100%; border: none;"
                        allow="clipboard-read; clipboard-write; microphone;">
                </iframe>
            </div>
        `;
    }
};
