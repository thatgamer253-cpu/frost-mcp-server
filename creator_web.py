import sys
import os
import threading
import json
import webview

# Add current dir to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from creation_engine.llm_client import ask_llm_stream

# HTML Content with Embedded JS/CSS
HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Overlord V2</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        :root {
            --bg-app: #18181b;
            --bg-sidebar: #101012;
            --bg-pill: #27272a;
            --text-main: #f4f4f5;
            --text-dim: #a1a1aa;
            --accent: #e4e4e7;
            --user-bubble: #3f3f46;
            --border: #3f3f46;
        }
        body {
            margin: 0; padding: 0;
            background-color: var(--bg-app);
            color: var(--text-main);
            font-family: 'Segoe UI', system-ui, sans-serif;
            height: 100vh;
            display: flex;
            overflow: hidden;
        }
        
        /* Sidebar */
        .sidebar {
            width: 260px;
            background-color: var(--bg-sidebar);
            border-right: 1px solid var(--border);
            display: flex;
            flex-direction: column;
            padding: 20px;
            gap: 10px;
        }
        .btn-new {
            background: var(--bg-pill);
            color: var(--text-main);
            border: 1px solid var(--border);
            padding: 12px;
            border-radius: 8px;
            text-align: left;
            cursor: pointer;
            transition: 0.2s;
            font-weight: 500;
        }
        .btn-new:hover { background: #333; }
        
        .history-label {
            font-size: 12px;
            font-weight: 700;
            color: var(--text-dim);
            text-transform: uppercase;
            margin-top: 20px;
            margin-bottom: 10px;
        }
        .history-item {
            padding: 10px;
            border-radius: 6px;
            color: var(--text-dim);
            cursor: pointer;
            font-size: 14px;
        }
        .history-item:hover { background: #1f1f22; color: var(--text-main); }
        
        /* Main Chat Area */
        .main {
            flex: 1;
            display: flex;
            flex-direction: column;
            position: relative;
        }
        
        .chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 40px;
            display: flex;
            flex-direction: column;
            gap: 24px;
            max-width: 900px;
            margin: 0 auto;
            width: 100%;
            box-sizing: border-box;
        }
        
        .welcome {
            text-align: center;
            margin-top: 15vh;
            color: var(--text-dim);
        }
        .welcome h1 { font-size: 28px; color: var(--text-main); margin-bottom: 8px; }
        
        /* Bubbles */
        .msg-row { display: flex; width: 100%; }
        .msg-row.user { justify-content: flex-end; }
        
        .bubble {
            max-width: 80%;
            line-height: 1.6;
            font-size: 16px;
        }
        
        .bubble.user {
            background-color: var(--user-bubble);
            padding: 12px 20px;
            border-radius: 20px;
            color: var(--text-main);
        }
        
        .bubble.bot {
            color: var(--text-main);
            padding-right: 20px;
        }
        
        /* Code Blocks */
        pre { background: #121214; padding: 15px; border-radius: 8px; overflow-x: auto; border: 1px solid #333; }
        code { font-family: 'Consolas', monospace; background: #222; padding: 2px 4px; border-radius: 4px; }
        
        /* Input Area (Pill) */
        .input-wrapper {
            padding: 20px;
            display: flex;
            justify-content: center;
            background: linear-gradient(to top, var(--bg-app) 80%, transparent);
        }
        
        .pill {
            background: var(--bg-pill);
            border: 1px solid var(--border);
            border-radius: 32px;
            width: 100%;
            max-width: 760px;
            display: flex;
            align-items: center;
            padding: 8px 8px 8px 24px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.2);
            transition: 0.2s;
        }
        .pill:focus-within { border-color: #666; box-shadow: 0 6px 25px rgba(0,0,0,0.3); }
        
        textarea {
            flex: 1;
            background: transparent;
            border: none;
            color: var(--text-main);
            font-size: 16px;
            font-family: inherit;
            resize: none;
            outline: none;
            height: 24px;
            max-height: 200px;
            padding: 10px 0;
            line-height: 1.5;
        }
        
        .send-btn {
            width: 44px;
            height: 44px;
            background: var(--text-main);
            color: var(--bg-app);
            border-radius: 50%;
            border: none;
            cursor: pointer;
            font-size: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-left: 10px;
            transition: 0.2s;
        }
        .send-btn:hover { background: #fff; transform: scale(1.05); }
        .send-btn:disabled { background: #444; color: #888; cursor: default; transform: none; }
        
        .footer-text {
            text-align: center;
            font-size: 12px;
            color: #52525b;
            margin-top: 8px;
        }
        
        /* Scrollbar */
        ::-webkit-scrollbar { width: 8px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #333; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #444; }
    </style>
</head>
<body>

    <div class="sidebar">
        <div class="btn-new" onclick="resetChat()">+ New Chat</div>
        <div class="history-label">Recents</div>
        <div class="history-item">Project Alpha Setup</div>
        <div class="history-item">Python Script Gen</div>
    </div>

    <div class="main">
        <div class="chat-container" id="chat">
            <div class="welcome" id="welcome">
                <h1>⚛️ Overlord V2</h1>
                <p>Ready to create something amazing?</p>
            </div>
        </div>

        <div class="input-wrapper">
            <div style="width: 100%; max-width: 760px;">
                <div class="pill">
                    <textarea id="prompt" placeholder="Message Overlord..." rows="1" oninput="autoExpand(this)" onkeydown="checkEnter(event)"></textarea>
                    <button id="sendBtn" class="send-btn" onclick="sendMessage()">➤</button>
                </div>
                <div class="footer-text">Overlord can make mistakes. Verify critical code.</div>
            </div>
        </div>
    </div>

<script>
    const chat = document.getElementById('chat');
    const welcome = document.getElementById('welcome');
    const prompt = document.getElementById('prompt');
    const sendBtn = document.getElementById('sendBtn');
    
    let currentBotMsg = null;
    let md = window.marked ? window.marked : { parse: (t) => t.replace(/\\n/g, '<br>') }; // Fallback

    function autoExpand(field) {
        field.style.height = 'inherit';
        const computed = window.getComputedStyle(field);
        field.style.height = Math.min(field.scrollHeight, 200) + "px";
    }

    function checkEnter(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    }
    
    function resetChat() {
        chat.innerHTML = '';
        chat.appendChild(welcome);
        welcome.style.display = 'block';
    }

    function appendBubble(role, htmlContent) {
        if (welcome.style.display !== 'none') welcome.style.display = 'none';
        
        const row = document.createElement('div');
        row.className = `msg-row ${role}`;
        
        const bubble = document.createElement('div');
        bubble.className = `bubble ${role}`;
        bubble.innerHTML = htmlContent;
        
        row.appendChild(bubble);
        chat.appendChild(row);
        chat.scrollTop = chat.scrollHeight;
        return bubble;
    }

    async function sendMessage() {
        const text = prompt.value.trim();
        if (!text) return;
        
        prompt.value = '';
        autoExpand(prompt);
        sendBtn.disabled = true;
        
        appendBubble('user', md.parse(text));
        
        // Prepare bot bubble
        currentBotMsg = appendBubble('bot', '<span class="typing">Thinking...</span>');
        
        // Call Python
        await pywebview.api.send_msg(text);
    }

    // Exposed to Python
    window.startStream = function() {
        currentBotMsg.innerHTML = ''; // Clear "Thinking..."
        window.streamBuffer = '';
    };

    window.appendChunk = function(chunk) {
        if (!window.streamBuffer) window.streamBuffer = '';
        window.streamBuffer += chunk;
        if (currentBotMsg) {
            currentBotMsg.innerHTML = md.parse(window.streamBuffer);
            chat.scrollTop = chat.scrollHeight;
        }
    };

    window.finishStream = function() {
        sendBtn.disabled = false;
        prompt.focus();
    };
    
    window.showSearchStatus = function(msg) {
        if (currentBotMsg && currentBotMsg.innerHTML === '<span class="typing">Thinking...</span>') {
            currentBotMsg.innerHTML = `<span style="color:#888;">${msg}</span>`;
        }
    };

</script>
</body>
</html>
"""

class Api:
    def __init__(self):
        self.history = []

    def send_msg(self, text):
        threading.Thread(target=self.process, args=(text,)).start()

    def process(self, text):
        try:
            # 1. Start Stream UI
            webview.windows[0].evaluate_js("window.startStream()")
            
            # 2. Search Logic
            search_context = ""
            keywords = ["search", "google", "find", "news", "price", "weather", "who is", "what is", "current"]
            if any(k in text.lower() for k in keywords):
                webview.windows[0].evaluate_js(f"window.showSearchStatus('🔍 Searching web...')")
                try:
                    from creation_engine.web_search import search_web
                    results = search_web(text, max_results=3)
                    if results:
                        search_context = "**Web Search Results:**\\n"
                        for r in results:
                            # Simple formatting
                            title = r.get('title', 'Result').replace("'", "").replace('"', "")
                            body = r.get('body', '')[:200].replace("'", "").replace('"', "")
                            search_context += f"- [{title}]: {body}\\n"
                except Exception as e:
                    pass

            # 3. Prepare Prompt
            system = "You are Overlord. Be helpful, concise, and technical. Use Markdown."
            full_user = f"{search_context}\\nUSER: {text}"
            
            # 4. Stream
            stream = ask_llm_stream(client=None, model="gpt-4o-mini", system_role=system, user_content=full_user)
            
            for chunk in stream:
                # Escape for JS
                safe_chunk = chunk.replace("`", "\\`").replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "")
                webview.windows[0].evaluate_js(f"window.appendChunk(`{safe_chunk}`)")
                
        except Exception as e:
            webview.windows[0].evaluate_js(f"window.appendChunk(`[Error: {str(e)}]`)")
            
        finally:
            webview.windows[0].evaluate_js("window.finishStream()")

if __name__ == '__main__':
    api = Api()
    webview.create_window(
        'Overlord V2 (Web)', 
        html=HTML, 
        js_api=api, 
        width=1200, 
        height=800, 
        background_color='#18181b',
        resizable=True
    )
    webview.start(debug=True)
