import sys
import codecs
import os
import json
import time
from playwright.sync_api import sync_playwright

# Set encoding for Windows stdout
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())

def stealth_submit():
    url = "https://www.linkedin.com/jobs/view/4351324838"
    session_dir = os.path.join(os.getcwd(), "browser_session")
    
    with sync_playwright() as p:
        try:
            context = p.chromium.launch_persistent_context(
                session_dir,
                headless=True,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
                viewport={'width': 1920, 'height': 1080},
                args=['--disable-blink-features=AutomationControlled']
            )
            page = context.pages[0] if context.pages else context.new_page()
            
            # Stealth Inject
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            print(f"STEALTH-SUBMIT: Navigating to {url}")
            page.goto(url)
            time.sleep(10)
            
            # Find and Force Click Easy Apply
            btn = page.query_selector("button.jobs-apply-button")
            if not btn:
                 btn = page.query_selector("button:has-text('Easy Apply')")
            
            if btn:
                print(f"Button found. Visibility: {btn.is_visible()}. Forcing click...")
                btn.click(force=True)
                time.sleep(5)
                
                # Simple form filler (one step)
                print("Checking for form buttons...")
                next_btn = page.query_selector("button:has-text('Submit application'), button:has-text('Next')")
                if next_btn:
                    print(f"Form button found: {next_btn.inner_text()}. Clicking...")
                    next_btn.click(force=True)
                    time.sleep(10)
                    print("Submission attempted.")
                    page.screenshot(path="stealth_submit_result.png")
                    print("Result screenshot saved.")
                else:
                    print("Could not find next/submit button in form.")
            else:
                print("Could not find Easy Apply button even with stealth.")
                page.screenshot(path="stealth_submit_failed.png")
                
            context.close()
        except Exception as e:
            print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    stealth_submit()
