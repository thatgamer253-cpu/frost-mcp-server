/**
 * Code Editor App for Nexus OS
 * Uses Monaco Editor via CDN
 */
const editorTemplate = `
<div class="editor-shell" style="display: flex; flex-direction: column; height: 100%; background: #1e1e1e;">
    <div class="editor-toolbar" style="padding: 10px; background: #252526; border-bottom: 1px solid #333; display: flex; gap: 10px; align-items: center;">
        <input id="editor-file-path" type="text" placeholder="project/file.py" style="flex: 1; background: #3c3c3c; border: 1px solid #555; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px;">
        <button id="editor-load" class="win-btn" style="width: auto; height: auto; padding: 4px 10px; border-radius: 4px; background: #0e639c; color: white; border: none; cursor: pointer; font-size: 11px;">Load</button>
        <button id="editor-save" class="win-btn" style="width: auto; height: auto; padding: 4px 10px; border-radius: 4px; background: #28a745; color: white; border: none; cursor: pointer; font-size: 11px;">Save</button>
        <span id="editor-status" style="font-size: 10px; color: #888;"></span>
    </div>
    <div id="editor-container" style="flex: 1; overflow: hidden;"></div>
</div>
`;

window.NexusOS_Apps = window.NexusOS_Apps || {};
window.NexusOS_Apps.editor = {
    editor: null,
    init: async (winId) => {
        const content = document.getElementById(`${winId}-content`);
        content.innerHTML = editorTemplate;
        content.style.padding = "0";

        const container = content.querySelector('#editor-container');
        const pathInput = content.querySelector('#editor-file-path');
        const loadBtn = content.querySelector('#editor-load');
        const saveBtn = content.querySelector('#editor-save');
        const status = content.querySelector('#editor-status');

        // Load Monaco if not present
        if (!window.monaco) {
            await new Promise(resolve => {
                const script = document.createElement('script');
                script.src = "https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs/loader.min.js";
                script.onload = () => {
                    require.config({ paths: { vs: 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs' } });
                    require(['vs/editor/editor.main'], () => resolve());
                };
                document.head.appendChild(script);
            });
        }

        this.editor = monaco.editor.create(container, {
            value: "# Select a file to edit\nprint('Nexus OS Editor')\n",
            language: 'python',
            theme: 'vs-dark',
            automaticLayout: true,
            fontSize: 12,
            minimap: { enabled: false }
        });

        loadBtn.onclick = async () => {
            const path = pathInput.value;
            if (!path) return;
            status.textContent = "Loading...";
            try {
                const res = await fetch(`http://${window.location.hostname}:8081/api/fs/file?path=${encodeURIComponent(path)}`);
                const data = await res.json();
                if (data.content) {
                    this.editor.setValue(data.content);
                    const ext = path.split('.').pop();
                    const langMap = { 'py': 'python', 'js': 'javascript', 'html': 'html', 'css': 'css', 'json': 'json' };
                    monaco.editor.setModelLanguage(this.editor.getModel(), langMap[ext] || 'plaintext');
                    status.textContent = "Loaded";
                } else {
                    status.textContent = "Error: " + (data.error || "Not found");
                }
            } catch (e) {
                status.textContent = "Failed to connect";
            }
        };

        saveBtn.onclick = async () => {
            const path = pathInput.value;
            if (!path) return;
            status.textContent = "Saving...";
            try {
                const res = await fetch(`http://${window.location.hostname}:8081/api/fs/file`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ path, content: this.editor.getValue() })
                });
                const data = await res.json();
                status.textContent = data.success ? "Saved" : "Save Error";
            } catch (e) {
                status.textContent = "Save Failed";
            }
        };
    }
};
