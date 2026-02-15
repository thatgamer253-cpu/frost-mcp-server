from playwright.sync_api import sync_playwright
import time
import random
import hashlib
import os

class JobScanner:
    """
    Handles scanning job boards using Playwright.
    """
    def __init__(self):
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36"
        self.session_dir = os.path.join(os.getcwd(), "browser_session")

    def _launch_browser(self, p):
        """Helper to launch browser with retry logic for locked sessions."""
        max_retries = 3
        temp_session = self.session_dir
        
        for i in range(max_retries):
            try:
                context = p.chromium.launch_persistent_context(
                    temp_session,
                    headless=True,
                    user_agent=self.user_agent
                )
                return context
            except Exception as e:
                if "locked" in str(e).lower() or "in use" in str(e).lower():
                    print(f"[Scanner] Session locked, retrying with unique path (Attempt {i+1}/{max_retries})...")
                    import time
                    temp_session = f"{self.session_dir}_{int(time.time())}_{i}"
                else:
                    raise e
        
        # Final fallback: use standard launch
        print("[Scanner] Persistent session failed, using ephemeral browser.")
        browser = p.chromium.launch(headless=True)
        return browser.new_context(user_agent=self.user_agent)

    def scan_upwork(self, keywords):
        jobs = []
        with sync_playwright() as p:
            context = self._launch_browser(p)
            page = context.pages[0] if hasattr(context, 'pages') and context.pages else context.new_page()
            
            for keyword in keywords:
                print(f"Searching Upwork for: {keyword}")
                search_url = f"https://www.upwork.com/nx/search/jobs/?q={keyword}&sort=recency"
                page.goto(search_url)
                time.sleep(random.uniform(3, 5)) # Respectful delay
                
                # Extract job cards (Simplified selector for demo)
                cards = page.query_selector_all("section.job-tile")
                for card in cards[:5]: # Take top 5 per keyword
                    try:
                        title_elem = card.query_selector("h3")
                        link_elem = card.query_selector("a")
                        desc_elem = card.query_selector(".job-description")
                        
                        if title_elem and link_elem:
                            url = "https://www.upwork.com" + link_elem.get_attribute("href")
                            job_id = hashlib.md5(url.encode()).hexdigest()[:12]
                            jobs.append({
                                "id": f"up-{job_id}",
                                "platform": "Upwork",
                                "title": title_elem.inner_text().strip(),
                                "company": "Upwork Client",
                                "description": desc_elem.inner_text().strip() if desc_elem else "No description",
                                "url": url
                            })
                    except Exception as e:
                        print(f"Error parsing card: {e}")
                        
            context.close()
        return jobs

    def scan_linkedin(self, keywords):
        """Scans LinkedIn Jobs (public search)."""
        jobs = []
        with sync_playwright() as p:
            context = self._launch_browser(p)
            page = context.pages[0] if hasattr(context, 'pages') and context.pages else context.new_page()
            
            for keyword in keywords:
                print(f"Searching LinkedIn for: {keyword}")
                # Public LinkedIn job search URL with Easy Apply (f_AL=true) and Remote filters
                search_url = f"https://www.linkedin.com/jobs/search/?keywords={keyword}&location=Remote&f_TPR=r86400&f_AL=true"
                page.goto(search_url)
                time.sleep(random.uniform(4, 6))
                
                # Extract job postings
                cards = page.query_selector_all(".jobs-search__results-list li")
                for card in cards[:5]:
                    try:
                        title_el = card.query_selector(".base-search-card__title")
                        link_el = card.query_selector("a.base-card__full-link")
                        company_el = card.query_selector(".base-search-card__subtitle")
                        
                        if title_el and link_el:
                            url = link_el.get_attribute("href").split('?')[0]
                            job_id = hashlib.md5(url.encode()).hexdigest()[:12]
                            jobs.append({
                                "id": f"li-{job_id}",
                                "platform": "LinkedIn",
                                "title": title_el.inner_text().strip(),
                                "company": company_el.inner_text().strip() if company_el else "Unknown Company",
                                "description": "LinkedIn Remote Opportunity",
                                "url": url
                            })
                    except:
                        pass
            context.close()
        return jobs

    def scan_craigslist(self, keywords):
        """Scans Craigslist for telecommuting gigs."""
        jobs = []
        # Craigslist locations to sweep (can be expanded)
        locations = ["sfbay", "austin", "newyork", "losangeles", "seattle"]
        
        with sync_playwright() as p:
            context = self._launch_browser(p)
            page = context.pages[0] if hasattr(context, 'pages') and context.pages else context.new_page()
            
            for loc in locations:
                for keyword in keywords:
                    print(f"Searching Craigslist ({loc}) for: {keyword}")
                    # Telecommuting filter is 'is_telecommuting=1'
                    search_url = f"https://{loc}.craigslist.org/search/jjj?query={keyword}&is_telecommuting=1"
                    try:
                        page.goto(search_url)
                        time.sleep(random.uniform(2, 4))
                        
                        posts = page.query_selector_all(".cl-static-search-result") # Static result cards
                        if not posts: posts = page.query_selector_all("li.result-row") # Fallback for different UI versions
                        
                        for post in posts[:5]:
                            title_el = post.query_selector("a .label, a")
                            link_el = post.query_selector("a")
                            
                            if title_el and link_el:
                                href = link_el.get_attribute("href")
                                if not href.startswith("http"):
                                    href = f"https://{loc}.craigslist.org" + href
                                
                                job_id = hashlib.md5(href.encode()).hexdigest()[:12]
                                jobs.append({
                                    "id": f"cl-{job_id}",
                                    "platform": "Craigslist",
                                    "title": title_el.inner_text().strip(),
                                    "company": f"Craigslist ({loc})",
                                    "description": f"Remote Gig found on Craigslist {loc}.",
                                    "url": href
                                })
                    except Exception as e:
                        print(f"Craigslist Error: {e}")
            context.close()
        return jobs

    def scan_all(self, profile):
        """Scans all enabled platforms."""
        all_jobs = []
        platforms = profile.get("platforms", {})
        
        # Upwork
        if platforms.get("upwork", {}).get("enabled"):
            keywords = platforms["upwork"].get("keywords", ["Python"])
            all_jobs.extend(self.scan_upwork(keywords))
        
        # LinkedIn
        if platforms.get("linkedin", {}).get("enabled", True):
            keywords = ["Python Automation", "AI Developer", "Content Creator"]
            all_jobs.extend(self.scan_linkedin(keywords))
            
        # Craigslist
        if platforms.get("craigslist", {}).get("enabled", True):
            keywords = platforms.get("craigslist", {}).get("keywords", ["Python", "Writing", "Content"])
            all_jobs.extend(self.scan_craigslist(keywords))
        
        # Fallback to mock if no real jobs found (for testing)
        if not all_jobs:
            all_jobs.append({
                "id": "mock-1",
                "platform": "Upwork",
                "title": "Default Python Dev",
                "company": "Mock Co",
                "description": "Simulation placeholder",
                "url": "https://example.com"
            })
            
        return all_jobs
