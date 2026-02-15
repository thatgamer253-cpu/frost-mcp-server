import sys
import codecs
import os
import json
import time
from playwright.sync_api import sync_playwright
from guardian import guardian

# Set encoding for Windows stdout
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())

def debug_li():
    url = "https://www.linkedin.com/jobs/view/4351324838"
    session_dir = os.path.join(os.getcwd(), "browser_session")
    
    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            session_dir,
            headless=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.pages[0] if context.pages else context.new_page()
        
        print(f"DEBUG: Navigating to {url}")
        page.goto(url)
        time.sleep(5)
        
        # Take screenshot
        page.screenshot(path="debug_li_job.png")
        print("Screenshot saved to debug_li_job.png")
        
        # Dump buttons
        buttons = page.query_selector_all("button")
        print(f"Found {len(buttons)} buttons:")
        for i, btn in enumerate(buttons):
            text = btn.inner_text().strip()
            if text:
                print(f"  [{i}] '{text}'")
        
        # Search specifically for Apply
        apply_elements = page.query_selector_all(":has-text('Apply')")
        print(f"Found {len(apply_elements)} elements with 'Apply' text.")
        
        context.close()

if __name__ == "__main__":
    debug_li()
