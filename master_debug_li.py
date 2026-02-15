import os
import time
from playwright.sync_api import sync_playwright

def master_debug():
    # Use the currentJobId format which is often more stable for automated views
    url = "https://www.linkedin.com/jobs/collections/recommended/?currentJobId=4373229356"
    session_dir = os.path.join(os.getcwd(), "browser_session")
    
    with sync_playwright() as p:
        try:
            context = p.chromium.launch_persistent_context(
                session_dir,
                headless=True,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080}
            )
            page = context.pages[0] if context.pages else context.new_page()
            
            print(f"MASTER-DEBUG: Navigating to {url}")
            page.goto(url)
            time.sleep(10) # Heavy wait for JS
            
            # Screenshot
            page.screenshot(path="master_debug_li.png")
            print("Screenshot saved.")
            
            # HTML Dump
            with open("master_debug_content.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            print("HTML Dump saved.")
            
            # Button Text Search
            buttons = page.query_selector_all("button")
            print(f"Found {len(buttons)} buttons.")
            for btn in buttons:
                txt = btn.inner_text().strip()
                if "Apply" in txt:
                    print(f"  MATCH: '{txt}' | Visible: {btn.is_visible()}")
            
            context.close()
        except Exception as e:
            print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    master_debug()
