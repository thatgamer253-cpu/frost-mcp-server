import os
import time
from playwright.sync_api import sync_playwright

def test_session():
    session_dir = os.path.join(os.getcwd(), "browser_session")
    with sync_playwright() as p:
        try:
            context = p.chromium.launch_persistent_context(
                session_dir,
                headless=True,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"
            )
            page = context.pages[0] if context.pages else context.new_page()
            
            print("Navigating to LinkedIn Homepage...")
            page.goto("https://www.linkedin.com/feed/")
            time.sleep(10)
            
            page.screenshot(path="session_check_li.png")
            print(f"URL: {page.url}")
            
            if "feed" in page.url:
                print("SUCCESS: Session is logged in and active.")
            elif "login" in page.url:
                print("FAILURE: Session is logged out.")
            else:
                print(f"UNKNOWN: Page state is {page.url}")
                
            context.close()
        except Exception as e:
            print(f"ERROR: {str(e)}")

if __name__ == "__main__":
    test_session()
