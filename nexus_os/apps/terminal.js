/**
 * Terminal App for Nexus OS
 * Uses xterm.js via CDN + WebSocket bridge
 */
window.NexusOS_Apps = window.NexusOS_Apps || {};
window.NexusOS_Apps.terminal = {
    init: (winId) => {
        const content = document.getElementById(`${winId}-content`);
        content.style.background = "#000";
        content.style.padding = "0";
        content.innerHTML = `<div id="${winId}-xterm" style="height: 100%;"></div>`;
        
        const termContainer = document.getElementById(`${winId}-xterm`);
        
        // xterm.js is already linked in index.html
        const term = new Terminal({
            theme: {
                background: '#000',
                foreground: '#0f0',
                cursor: '#0f0'
            },
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: 12,
            convertEol: true
        });

        term.open(termContainer);
        term.writeln("Connecting to Nexus Shell...");

        const ws = new WebSocket(`ws://${window.location.hostname}:8081/ws/terminal`);
        
        ws.onopen = () => {
            term.writeln("Terminal Session Established.\r\n");
        };

        ws.onmessage = (event) => {
            term.write(event.data);
        };

        term.onData(data => {
            if (ws.readyState === WebSocket.OPEN) {
                ws.send(data);
            }
        });

        ws.onclose = () => {
            term.writeln("\r\nSession Closed.");
        };

        // Resize handling
        const resizeObserver = new ResizeObserver(() => {
            // In a real implementation we'd use use fitAddon
            // For now, xterm.js handles basic layout
        });
        resizeObserver.observe(termContainer);
    }
};
