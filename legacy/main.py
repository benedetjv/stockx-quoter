import os
import time
from quoter import StockXQuoter

# CREDENTIALS
EMAIL = "jvkrtgc@gmail.com"
PASSWORD = "joaovb15A@"

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header(title):
    clear_screen()
    print("="*50)
    print(f" {title}")
    print("="*50 + "\n")

def main():
    print_header("StockX Automatic Quoter - Initializing")
    
    # Mode Selection
    use_saved = False
    headless = False
    
    if os.path.exists("session.json"):
        mode = input("Saved session found. Run in INVISIBLE mode? (y/n): ").strip().lower()
        if mode == 'y':
            use_saved = True
            headless = True # Invisible
            print(">> Starting Invisible Mode (using saved session)...")
        else:
            print(">> Starting Visible Mode (Login might be required)...")
    else:
        print(">> First run: Starting Visible Mode to save Login session...")

    email = EMAIL
    password = PASSWORD
    
    quoter = StockXQuoter(email, password)
    
    try:
        if use_saved:
             quoter.start_browser(headless=True, use_saved_session=True)
             print("Skipping login screen (using cookies).")
             # Visit home to ensure session is alive/warm up
             try:
                 quoter.page.goto("https://stockx.com")
             except:
                 pass
        else:
             quoter.start_browser(headless=False, use_saved_session=False)
             quoter.login()
             quoter.save_session() 
        
        while True:
            # Step 1: Input
            print_header("Step 1: Product Selection")
            url = input("Enter StockX Product URL (or 'q' to quit, 'm' for manual mode): ").strip()
            if not url: continue
            
            if url.lower() == 'q':
                break
            
            if url.lower() == 'm':
                 # Manual Logic
                 print_header("Manual Mode")
                 print("Starting Manual Mode in Browser...")
                 if not quoter.browser: quoter.start_browser()
                 quoter.page.goto("https://stockx.com")
                 
                 final_stockx_price = quoter.capture_price_manual()
                 
                 cat_input = input("Enter Category (Sneakers/T-Shirt/Hoodie/Jacket) [Default: Sneakers]: ").strip()
                 category = "Sneakers"
                 if "shirt" in cat_input.lower(): category = "T-Shirt"
                 elif "hoodie" in cat_input.lower(): category = "Hoodie"
                 elif "jacket" in cat_input.lower(): category = "Jacket"
                 
                 if final_stockx_price > 0:
                        service_price = quoter.calculate_service_price(final_stockx_price, category)
                        print_header("Quote Result")
                        print(f"Category: {category}")
                        print(f"StockX Total: ${final_stockx_price:.2f}")
                        print(f"Service Quote: ${service_price:.2f}")
                        print("="*30 + "\n")
                 else:
                        print("Could not capture price in Manual Mode.")
                 
                 input("Press Enter to continue...")
                 continue

            # Step 2: Scan
            print_header("Step 2: Scanning Product...")
            print(f"URL: {url}")
            print("Analyzing page...")
            try:
                # 1. Detect Category & Sizes
                options = quoter.scan_sizes(url)
                category = quoter.detect_category()
                
                if not options:
                    print("No sizes found. Trying manual entry...")
                    input("Press Enter to verify manually or restart...")
                    continue
                
                # Step 3: Display & Select
                print_header(f"Step 3: Select Size | Category: {category}")
                print(f"{'ID':<5} | {'Size Info':<30}")
                print("-" * 40)
                for opt in options:
                    print(f"{opt['index']:<5} | {opt['text']}")
                print("-" * 40)
                
                selected_idx = -1
                
                while True:
                    print(f"\nCurrent Category: {category}")
                    choice = input("Enter ID to Quote (or 'cat' to change category, 'c' to cancel): ").strip()
                    
                    if choice.lower() == 'c':
                        selected_idx = -2 # Cancel flag
                        break
                    
                    if choice.lower() == 'cat':
                        print("\nSelect Category: 1. Sneakers, 2. T-Shirt, 3. Hoodie, 4. Jacket")
                        c_idx = input("Enter number: ")
                        if c_idx == '1': category = "Sneakers"
                        elif c_idx == '2': category = "T-Shirt"
                        elif c_idx == '3': category = "Hoodie"
                        elif c_idx == '4': category = "Jacket"
                        print(f"Category updated to: {category}")
                        continue
                        
                    if choice.isdigit():
                        idx = int(choice)
                        # Validate
                        if any(o['index'] == idx for o in options):
                            selected_idx = idx
                            break
                        else:
                            print("Invalid ID.")
                    else:
                        print("Invalid input.")
                
                if selected_idx == -2:
                    continue
                
                # Step 4: Execute
                print_header("Step 4: Processing Quote...")
                print(f"Selected ID: {selected_idx}")
                print("Clicking buttons and fetching price...")
                
                final_stockx_price = quoter.execute_quote(selected_idx)
                
                if final_stockx_price > 0:
                    service_price = quoter.calculate_service_price(final_stockx_price, category)
                    
                    print_header("Final Quote Result")
                    print(f"Category:      {category}")
                    print(f"StockX Total:  ${final_stockx_price:.2f}")
                    print("-" * 30)
                    print(f"FINAL QUOTE:   ${service_price:.2f}")
                    print("="*30 + "\n")
                else:
                    print("\nFailed to retrieve final price.")
                    
                input("\nPress Enter to start next quote...")
            
            except Exception as e:
                print(f"An error occurred: {e}")
                input("Press Enter to continue...")
            
            print("Resetting for next item...")
            # quoter.go_home() # Removing this to avoid triggering bot checks on Homepage loading
            
    except KeyboardInterrupt:
        print("\nExiting...")
    finally:
        quoter.close()

if __name__ == "__main__":
    main()
