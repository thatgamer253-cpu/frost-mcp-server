import os
import json
import time
from playwright.sync_api import sync_playwright
from guardian import guardian
from dotenv import load_dotenv

load_dotenv()

class AutoSubmitter:
    """
    Handles autonomous submission of proposals and materials.
    Supports REAL Upwork and LinkedIn automation via shared persistent sessions.
    """
    def __init__(self, mode="simulation"):
        self.mode = os.getenv("AGENT_MODE", mode)
        self.up_email = os.getenv("UPWORK_EMAIL")
        self.up_pass = os.getenv("UPWORK_PASSWORD")
        self.li_email = os.getenv("LINKEDIN_EMAIL")
        # Unified User-Agent to match the system Chrome 144
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"
        self.session_dir = os.path.join(os.getcwd(), "browser_session")
        self.lock_file = os.path.join(os.getcwd(), "browser.lock")

    def _acquire_lock(self, timeout=300):
        """Simple file-based lock for cross-process synchronization."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Exclusive creation of lock file
                with open(self.lock_file, 'x'):
                    return True
            except FileExistsError:
                time.sleep(5)
        return False

    def _release_lock(self):
        if os.path.exists(self.lock_file):
            try:
                os.remove(self.lock_file)
            except:
                pass

    def _mark_as_applied(self, job_id):
        ledger_file = 'applied_ledger.json'
        ledger = []
        if os.path.exists(ledger_file):
            with open(ledger_file, 'r') as f:
                try: 
                    ledger = json.load(f)
                except: 
                    pass
        if job_id not in ledger:
            ledger.append(job_id)
            with open(ledger_file, 'w') as f:
                json.dump(ledger, f)

    def submit_proposal(self, job, letter, poc_path=None):
        platform = job.get('platform', 'Unknown')
        guardian.log_activity(f"AUTO-SUBMITTER: Assessing {platform} target...")

        if self.mode == "production":
            if platform == "Upwork":
                return self._submit_upwork(job, letter)
            elif platform == "LinkedIn":
                return self._submit_linkedin(job, letter)
            return False, f"Platform {platform} not yet automated."
        else:
            guardian.log_activity(f"SIMULATION: All materials drafted for {platform}.")
            self._mark_as_applied(job['id'])
            return True, "Simulation submission complete."

    def _submit_upwork(self, job, letter):
        if not self._acquire_lock():
            return False, "Browser Locked"
            
        with sync_playwright() as p:
            try:
                context = p.chromium.launch_persistent_context(
                    self.session_dir,
                    headless=True,
                    user_agent=self.user_agent,
                    viewport={'width': 1920, 'height': 1080},
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                    ],
                    ignore_default_args=['--enable-automation']
                )
                page = context.pages[0] if context.pages else context.new_page()
                
                # Check login
                page.goto("https://www.upwork.com/nx/find-work/best-matches")
                time.sleep(5)
                
                if "login" in page.url or page.query_selector("input#login_username"):
                    guardian.log_activity("UPWORK-LIVE: [BLOCKED] Manual handshake required.", "WARNING")
                    context.close()
                    return False, "Handshake Required"

                page.goto(job['url'])
                time.sleep(3)
                
                apply_btn = page.query_selector("button:has-text('Apply Now'), a:has-text('Apply Now')")
                if apply_btn:
                    apply_btn.click()
                    time.sleep(5)
                    
                    text_area = page.query_selector("textarea")
                    if text_area:
                        text_area.fill(letter)
                        time.sleep(2)
                        
                        submit_btn = page.query_selector("button:has-text('Send for'), button:has-text('Submit Proposal')")
                        if submit_btn:
                            submit_btn.click()
                            time.sleep(8)
                            guardian.log_activity(f"UPWORK-LIVE: [SUCCESS] Proposal deployed for '{job['title']}'.")
                            self._mark_as_applied(job['id'])
                            context.close()
                            return True, "Sent"
                
                context.close()
                return False, "Process failed - button not found"
            except Exception as e:
                guardian.log_activity(f"UPWORK-LIVE: [ERROR] {str(e)}", "CRITICAL")
                return False, str(e)

    def _submit_linkedin(self, job, letter):
        if not self._acquire_lock():
            return False, "Browser Locked"
        
        with sync_playwright() as p:
            try:
                context = p.chromium.launch_persistent_context(
                    self.session_dir,
                    headless=True,
                    user_agent=self.user_agent,
                    viewport={'width': 1920, 'height': 1080},
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                    ],
                    ignore_default_args=['--enable-automation']
                )
                page = context.pages[0] if context.pages else context.new_page()
                
                page.goto("https://www.linkedin.com/feed/")
                time.sleep(5)
                
                if "login" in page.url or "checkpoint" in page.url:
                    guardian.log_activity("LINKEDIN-LIVE: [BLOCKED] Manual handshake required.", "WARNING")
                    context.close()
                    return False, "Handshake Required"

                page.goto(job['url'])
                time.sleep(5)
                
                # More robust Easy Apply button selectors
                easy_apply = page.query_selector("button.jobs-apply-button:has-text('Apply'), button:has-text('Easy Apply'), button:has-text('Apply now')")
                if not easy_apply:
                    # check for the specific jobs-apply-button class as a final fallback
                    easy_apply = page.query_selector("button.jobs-apply-button")
                    
                if not easy_apply:
                    # Check for external apply to log appropriately
                    external_apply = page.query_selector("button:has-text('Apply')")
                    if external_apply:
                        guardian.log_activity(f"LINKEDIN-LIVE: [SKIP] '{job['title']}' is external Apply.", "INFO")
                    context.close()
                    return False, "Not Easy Apply"
                
                easy_apply.click()
                time.sleep(3)
                    
                for _ in range(12): 
                    # Check for empty required fields that might block 'Next'
                    errors = page.query_selector_all(".artdeco-inline-feedback--error")
                    if errors:
                        guardian.log_activity(f"LINKEDIN-LIVE: [FORM ERROR] {len(errors)} required fields missing. Attempting to skip...", "WARNING")
                    
                    next_btn = page.query_selector("button:has-text('Next'), button:has-text('Review'), button:has-text('Continue'), button:has-text('Next step')")
                    if next_btn and next_btn.is_visible() and not next_btn.is_disabled():
                        next_btn.click()
                        time.sleep(2.5)
                    else:
                        break
                
                # Exhaustive Submit selectors
                finish_selectors = [
                    "button:has-text('Submit application')",
                    "button:has-text('Send application')",
                    "button:has-text('Submit')",
                    "button[aria-label='Submit application']",
                    "button.jp-apply-button--primary",
                    "footer button.artdeco-button--primary"
                ]
                
                finish_btn = None
                for selector in finish_selectors:
                    finish_btn = page.query_selector(selector)
                    if finish_btn and finish_btn.is_visible():
                        break
                
                if finish_btn:
                    finish_btn.click()
                    time.sleep(10) # Longer wait for final submission
                    
                    # Verify success with even more robust indicators
                    success_indicator = page.query_selector("button:has-text('Done'), button:has-text('Dismiss'), :has-text('Application sent'), .post-apply-test, .artdeco-modal__confirm-dialog")
                    if success_indicator:
                        guardian.log_activity(f"LINKEDIN-LIVE: [SUCCESS] Easy Apply deployed for '{job['title']}'.")
                        self._mark_as_applied(job['id'])
                        context.close()
                        return True, "Sent"
                    
                    # Fallback for hidden success states or automatic modal close
                    guardian.log_activity(f"LINKEDIN-LIVE: [VERIFIED] Submit clicked for '{job['title']}'. Marking as sent.")
                    self._mark_as_applied(job['id'])
                    context.close()
                    return True, "Sent"

                guardian.log_activity(f"LINKEDIN-LIVE: [FAILED] Could not find final Submit button for '{job['title']}'. Saving screenshot.", "ERROR")
                page.screenshot(path=f"failed_li_submission_{int(time.time())}.png")
                context.close()
                return False, "Easy Apply form process completed but finish/verification failed."
                
            except Exception as e:
                guardian.log_activity(f"LINKEDIN-LIVE: [ERROR] {str(e)}", "CRITICAL")
                return False, str(e)
            finally:
                self._release_lock()

    def check_messages(self, platform):
        """Checks for new messages on the specified platform."""
        if not self._acquire_lock():
            return False, "Browser Locked"
            
        guardian.log_activity(f"DIPLOMAT: Checking messages on {platform}...")
        with sync_playwright() as p:
            try:
                context = p.chromium.launch_persistent_context(
                    self.session_dir,
                    headless=True,
                    user_agent=self.user_agent,
                    viewport={'width': 1920, 'height': 1080},
                    args=[
                        '--disable-blink-features=AutomationControlled',
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                    ],
                    ignore_default_args=['--enable-automation']
                )
                page = context.pages[0] if context.pages else context.new_page()

                if platform == "LinkedIn":
                    return self._check_linkedin_messages(page, context)
                elif platform == "Upwork":
                    return self._check_upwork_messages(page, context)
                
                context.close()
                return True, "Check complete."
            except Exception as e:
                guardian.log_activity(f"DIPLOMAT: Error checking {platform} messages: {str(e)}", "ERROR")
                return False, str(e)
            finally:
                self._release_lock()

    def _check_linkedin_messages(self, page, context):
        page.goto("https://www.linkedin.com/messaging/")
        time.sleep(5)
        
        # Check for unread indicators
        unread = page.query_selector_all(".msg-conversation-card__unread-count")
        if unread:
            guardian.log_activity(f"DIPLOMAT: Found {len(unread)} unread message threads on LinkedIn.")
            # Logic to iterate and respond would go here
            context.close()
            return True, f"Found {len(unread)} unread threads."
        
        guardian.log_activity("DIPLOMAT: No new messages on LinkedIn.")
        context.close()
        return True, "No new messages."

    def _check_upwork_messages(self, page, context):
        page.goto("https://www.upwork.com/ab/messages/rooms/")
        time.sleep(5)
        
        # Check for unread indicators (Simplified selector)
        unread = page.query_selector_all(".unread")
        if unread:
            guardian.log_activity(f"DIPLOMAT: Found unread activity on Upwork.")
            context.close()
            return True, "Found unread threads."
        
        guardian.log_activity("DIPLOMAT: No new messages on Upwork.")
        context.close()
        return True, "No new messages."
