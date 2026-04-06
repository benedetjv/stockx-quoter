import re
import time
import random
from playwright.sync_api import sync_playwright

class StockXQuoter:
    def __init__(self, email, password):
        self.email = email
        self.password = password
        self.browser = None
        self.page = None
        self.playwright = None

    def start_browser(self, headless=False, use_saved_session=False):
        self.is_headless = headless # Track state
        self.playwright = sync_playwright().start()
        # Add arguments to make the browser look more real
        args = [
            '--disable-blink-features=AutomationControlled',
            '--window-size=1920,1080',
            '--start-maximized' 
        ]
        
        # Determine launch options
        launch_opts = {
            "headless": headless,
            "args": args
        }
        
        self.browser = self.playwright.chromium.launch(**launch_opts)
        
        context_opts = {
            "no_viewport": True,
            "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        # Load session if requested and exists
        if use_saved_session:
            try:
                print("Attempting to load saved session...")
                self.context = self.browser.new_context(storage_state="session.json", **context_opts)
                print("Session loaded successfully.")
            except Exception as e:
                print(f"Could not load session: {e}. Starting fresh.")
                self.context = self.browser.new_context(**context_opts)
        else:
             self.context = self.browser.new_context(**context_opts)
             
        self.page = self.context.new_page()
        
        try:
            from playwright_stealth import stealth_sync
            stealth_sync(self.page)
        except ImportError:
            pass

    def save_session(self):
        try:
             self.context.storage_state(path="session.json")
             print("Session saved to 'session.json'. Next run can be headless!")
        except Exception as e:
             print(f"Failed to save session: {e}")

    def close(self):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def handle_cookies(self):
        # Dismiss OneTrust or other cookie banners
        try:
            # Common OneTrust selectors
            if self.page.locator('#onetrust-accept-btn-handler').is_visible():
                print("Dismissing Cookie Banner (Accept)...")
                self.page.locator('#onetrust-accept-btn-handler').click()
                time.sleep(1)
            # Try generic "Accept All" text which matches the user screenshot
            elif self.page.get_by_text("Accept All").first.is_visible():
                 print("Dismissing Cookie Banner (Generic Text)...")
                 self.page.get_by_text("Accept All").first.click()
                 time.sleep(1)
            elif self.page.locator('.onetrust-close-btn-handler').is_visible():
                 self.page.locator('.onetrust-close-btn-handler').click()
                 time.sleep(1)
        except:
             pass

    def handle_captcha(self):

        # Check for common bot detection phrases
        self.handle_cookies()
        
        try:
            # Check for PerimeterX (px-captcha)
            px_visible = False
            if self.page.locator('#px-captcha-modal').count() > 0 and self.page.locator('#px-captcha-modal').is_visible():
                px_visible = True
            
            content = self.page.content().lower()
            captcha_text = "press & hold" in content or "verify you are human" in content or "challenge" in self.page.url
            
            if px_visible or captcha_text:
                print("!!!" * 10)
                print("CAPTCHA / BOT DETECTION DETECTED")
                
                was_headless = False
                resume_url = self.page.url
                
                # 1. Switch to VISIBLE if needed
                if hasattr(self, 'is_headless') and self.is_headless:
                    print(">> Invisible Mode detected. Switching to VISIBLE for manual solution...")
                    was_headless = True
                    self.close() # Close headless
                    
                    # Restart Visible
                    self.start_browser(headless=False, use_saved_session=True)
                    print(f"Restoring page: {resume_url}")
                    self.page.goto(resume_url)
                
                print("Please manually solve the 'Press & Hold' checks in the browser window.")
                print("The script will wait until you are redirected or the challenge disappears.")
                print("!!!" * 10)
                
                # 2. Wait for solution
                self.page.wait_for_function(
                    "() => !document.body.innerText.toLowerCase().includes('press & hold')",
                    timeout=0 # Wait indefinitely
                )
                print("Challenge appears to be cleared. Resuming...")
                time.sleep(2)
                
                # Save session to capture the "human" token
                self.save_session()
                
                # 3. STAY in VISIBLE Mode
                # Switching back to headless often triggers the bot detection again immediately.
                if was_headless:
                    print(">> Staying in VISIBLE Mode for this session to avoid re-triggering Captcha.")
                    self.is_headless = False
                    # No need to restart, we just continue with the current open browser.
                    
        except Exception as e:
            # Ignore timeouts or errors during switch
            # print(f"Error handling captcha: {e}")
            pass

    def login(self):
        print("Navigating to login page...")
        self.page.goto("https://stockx.com/login")
        self.handle_captcha()
        
        print("Checking login status...")
        
        # Try to find the specific ID selectors found in debugging
        try:
            # Wait for email input to be visible
            print("Waiting for login form...")
            self.page.wait_for_selector('#email-login', state='visible', timeout=10000)
            
            print("Login form detected. Filling credentials...")
            
            # Use press_sequentially to simulate human typing and trigger validation
            email_field = self.page.locator('#email-login')
            email_field.click()
            email_field.press_sequentially(self.email, delay=100)
            email_field.press("Tab") # Trigger blur/validation
            time.sleep(0.5)
            
            pass_field = self.page.locator('#password-login')
            pass_field.click()
            pass_field.press_sequentially(self.password, delay=100)
            time.sleep(0.5)
            
            # Click login
            print("Clicking Log In...")
            self.page.locator('#btn-login').click()
            
        except Exception as e:
            print(f"Login form auto-fill failed: {e}")
            print("Checking if already logged in...")
        
        self.handle_captcha()
        
        # Ultimate fallback
        print(">>> PLEASE ENSURE YOU ARE LOGGED IN <<<")
        print("If the fields were not filled, please do so manually now.")
        print("Waiting for redirection to Homepage...")
        
        try:
            self.page.wait_for_url("https://stockx.com/", timeout=60000)
            print("Login confirmed (on homepage).")
            # Save session immediately after successful login
            self.save_session()
        except:
            print("Timed out waiting for homepage. Assuming we can proceed or user is debugging.")

    def go_home(self):
        print("Returning to Homepage...")
        self.page.goto("https://stockx.com/")
        self.handle_captcha()

    def detect_category(self):
        self.handle_captcha()
        try:
            # Get text from Breadcrumbs and Title
            breadcrumbs = ""
            try:
                if self.page.locator('nav[aria-label="Breadcrumb"]').count() > 0:
                    breadcrumbs = self.page.locator('nav[aria-label="Breadcrumb"]').inner_text().lower()
                elif self.page.locator('nav[aria-label="breadcrumb"]').count() > 0:
                    breadcrumbs = self.page.locator('nav[aria-label="breadcrumb"]').inner_text().lower()
                # Also try generic class if aria fails
                elif self.page.locator('.chakra-breadcrumb').count() > 0:
                    breadcrumbs = self.page.locator('.chakra-breadcrumb').inner_text().lower()
            except:
                pass
            
            title = self.page.title().lower()
            product_title = ""
            try:
                # Try to get the H1 product title on the page too
                if self.page.locator('h1').count() > 0:
                    product_title = self.page.locator('h1').first.inner_text().lower()
            except:
                pass
                
            # print(f"DEBUG: Breadcrumbs: '{breadcrumbs}'")
            # print(f"DEBUG: Page Title: '{title}'")
            # print(f"DEBUG: Product H1: '{product_title}'")
            
            # Combined text to search
            search_text = f"{breadcrumbs} {title} {product_title}"
            
            # Logic - Specific to General
            if "jacket" in search_text or "coat" in search_text or "parka" in search_text:
                return "Jacket"
            elif "hoodie" in search_text or "hooded" in search_text or "sweatshirt" in search_text or "pullover" in search_text:
                return "Hoodie"
            elif "t-shirt" in search_text or "tee" in search_text or "shirt" in search_text or "top" in search_text:
                # Be careful not to match 'shirt' in 'sweatshirt' (handled by order? No, sweatshirt is hoodie)
                if "sweatshirt" not in search_text:
                     return "T-Shirt"
            
            return "Sneakers" # Default
            
        except Exception as e:
            print(f"Error detecting category: {e}")
            return "Sneakers"

    def scan_sizes(self, url):
        print(f"Navigating to {url}...")
        
        # Random sleep to mimic human hesitation
        time.sleep(random.uniform(1.0, 3.0))
        
        self.page.goto(url)
        self.handle_captcha()
        
        # Open dropdown
        try:
            print("Scanning available sizes...")
            size_dropdown = self.page.locator('button[id^="menu-button-pdp-size-selector"]')
            if not size_dropdown.is_visible():
                    size_dropdown = self.page.get_by_text("Size:", exact=False)
            
            if size_dropdown.count() > 0:
                size_dropdown.first.click(force=True)
                time.sleep(1)
            else:
                print("Size dropdown not found.")
                # It might be One Size or Out of Stock
                return []
            
            # Scrape items
            menu_items = self.page.locator('[role="menuitemradio"], [role="menuitem"]')
            count = menu_items.count()
            options = []
            
            for i in range(count):
                raw_text = menu_items.nth(i).inner_text().replace('\n', ' ').strip()
                # e.g., "US M 8.5 $1,328"
                options.append({
                    "index": i,
                    "text": raw_text
                })
            
            return options
        except Exception as e:
            print(f"Error scanning sizes: {e}")
            return []

    def execute_quote(self, size_selection_index):
        # Assumes we are already on the page
        self.handle_captcha()
        
        try:
            # Re-open dropdown if needed or just find the item
            size_dropdown = self.page.locator('button[id^="menu-button-pdp-size-selector"]')
            if not size_dropdown.is_visible():
                 size_dropdown = self.page.get_by_text("Size:", exact=False)
            
            if size_dropdown.count() > 0:
                # If valid, click it. If it's already open, clicking might close it?
                # Check existance of menu items
                if self.page.locator('[role="menuitemradio"]').count() == 0:
                    size_dropdown.first.click()
                    time.sleep(1)
            
            # Click the specific index
            menu_items = self.page.locator('[role="menuitemradio"], [role="menuitem"]')
            if size_selection_index < menu_items.count():
                text = menu_items.nth(size_selection_index).inner_text()
                print(f"Selecting: {text}")
                menu_items.nth(size_selection_index).click()
                time.sleep(2)
            else:
                print("Invalid size index selected.")
                return 0.0

            # 2. Click Buy Now
            print("Clicking 'Buy Now'...")
            # Attempt multiple selectors
            clicked_buy = False
            selectors = [
                'button:has-text("Buy Now")',
                'button:has-text("Buy for")',
                '[data-testid="product-buy-button"]',
                'a:has-text("Buy Now")'
            ]
            
            for sel in selectors:
                if self.page.locator(sel).count() > 0 and self.page.locator(sel).first.is_visible():
                    try:
                        self.page.locator(sel).first.click(timeout=3000)
                        clicked_buy = True
                        break
                    except:
                        continue
            
            if not clicked_buy:
                 print("Could not auto-click Buy. Please click it manually.")

            self.handle_captcha()
            
            # 3. Click Review Order (Intermediate Page)
            print("Waiting for 'Review Order' page...")
            time.sleep(2)
            
            try:
                for _ in range(5):
                    if self.page.get_by_role("button", name="Review Order").first.is_visible():
                        print("Clicking 'Review Order'...")
                        self.page.get_by_role("button", name="Review Order").first.click()
                        break
                    elif "checkout" in self.page.url:
                        print("Already at checkout.")
                        break
                    time.sleep(1)
            except:
                pass

            self.handle_captcha()

            # 4. Final Checkout - Get Total
            print("Waiting for pricing breakdown...")
            time.sleep(5) 
            
            total_label = self.page.get_by_text("Total (incl. tax)")
            if total_label.count() > 0:
                parent_text = total_label.first.locator("..").inner_text()
                print(f"Found checkout line: {parent_text.replace(chr(10), ' ')}")
                matches = re.findall(r'\$[\d,]+\.\d{2}', parent_text)
                if matches:
                    return self.parse_price(matches[-1])

            print("Could not find total price automatically.")
            return 0.0

        except Exception as e:
            print(f"Error during quoting flow: {e}")
            return 0.0

    def capture_price_manual(self):
        print("Manual Capture Mode engaged.")
        print("1. Please navigate manually to the FINAL Checkout/Review page.")
        print("2. Ensure the 'Total' price is visible on screen.")
        input("3. Press Enter here when ready to capture...")
        
        # Capture logic
        try:
            # Save page source for debugging
            with open("checkout_dump.html", "w", encoding="utf-8") as f:
                f.write(self.page.content())
            print("Page structure saved to 'checkout_dump.html'.")
            
            # Try to find price
            print("Scanning page for prices...")
            text = self.page.locator("body").inner_text()
            
            # Look for "Total" lines
            total_patterns = ["Total", "Order Total", "Total (incl. tax)", "Payment Amount"]
            
            for line in text.split('\n'):
                for pattern in total_patterns:
                    if pattern.lower() in line.lower() and "$" in line:
                        print(f"Possible match: {line}")
                        matches = re.findall(r'\$[\d,]+\.\d{2}', line)
                        if matches:
                            return self.parse_price(matches[-1])
            
            # Fallback regex scan of entire body
            print("Trying deep scan...")
            matches = re.findall(r'Total.*\$([\d,]+\.\d{2})', text, re.IGNORECASE | re.DOTALL)
            if matches:
                 return self.parse_price(matches[0])

            return 0.0
        except Exception as e:
            print(f"Error in manual capture: {e}")
            return 0.0

    def parse_price(self, price_str):
        # Remove '$', ',' and convert to float
        clean_price = price_str.replace('$', '').replace(',', '')
        return float(clean_price)

    def calculate_service_price(self, stockx_total, category):
        # Rules:
        # Sneakers: * 0.98 + 50
        # T-Shirt: * 0.98 + 20
        # Hoodie: * 0.98 + 30
        # Jacket: * 0.98 + 40
        
        base = stockx_total * 0.98
        fee = 0
        if category == "Sneakers":
            fee = 50
        elif category == "T-Shirt":
            fee = 20
        elif category == "Hoodie":
            fee = 30
        elif category == "Jacket":
            fee = 40
        else:
            fee = 50 # Default to sneakers if unknown
            
        return base + fee
