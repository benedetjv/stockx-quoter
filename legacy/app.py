import streamlit as st
import os
import time
import pandas as pd
from quoter import StockXQuoter

# Page Config
st.set_page_config(
    page_title="StockX Auto Quoter",
    page_icon="👟",
    layout="wide"
)

# Initialize Session State for the Quoter Instance
if 'quoter' not in st.session_state:
    st.session_state.quoter = None

if 'browser_running' not in st.session_state:
    st.session_state.browser_running = False

# Sidebar - Browser Controls
st.sidebar.title("🎮 Control Panel")

st.sidebar.subheader("Browser Configuration")
headless_mode = st.sidebar.checkbox("Invisible Mode (Headless)", value=True, help="Run without opening a window.")
use_saved_session = st.sidebar.checkbox("Use Saved Session", value=True, help="Load 'session.json' to skip login.")

# Credentials (Optional Override)
with st.sidebar.expander("Credentials (Override)"):
    email = st.text_input("Email", value="jvkrtgc@gmail.com")
    password = st.text_input("Password", value="joaovb15A@", type="password")

# Start/Stop Buttons
col_ctrl1, col_ctrl2 = st.sidebar.columns(2)

def start_browser():
    try:
        if st.session_state.quoter is None:
            st.session_state.quoter = StockXQuoter(email, password)
        
        if not st.session_state.browser_running:
            with st.spinner("Starting Browser..."):
                st.session_state.quoter.start_browser(headless=headless_mode, use_saved_session=use_saved_session)
                
                # Check for cached token or login needs
                if not use_saved_session:
                    st.session_state.quoter.login()
                    st.session_state.quoter.save_session()
                else:
                    # Visit home to warm up
                    st.session_state.quoter.page.goto("https://stockx.com")
                
                st.session_state.browser_running = True
            st.sidebar.success("Browser Started!")
    except Exception as e:
        st.error(f"Failed to start: {e}")

def stop_browser():
    if st.session_state.quoter:
        st.session_state.quoter.close()
        st.session_state.browser_running = False
        st.session_state.quoter = None
        st.sidebar.warning("Browser Stopped.")

with col_ctrl1:
    if st.button("🚀 Start Browser"):
        start_browser()

with col_ctrl2:
    if st.button("🛑 Stop Browser"):
        stop_browser()

# Status Indicator
if st.session_state.browser_running:
    st.sidebar.success("✅ Browser Active")
else:
    st.sidebar.error("🔴 Browser Inactive")

# Main Interface
st.title("👟 StockX Personal Shopper")
st.markdown("Automated quoting tool for Sneakers, T-Shirts, Hoodies, and Jackets.")
st.markdown("---")

# Only show controls if browser is running
if st.session_state.browser_running:
    
    # 1. URL Input
    url = st.text_input("StockX Product URL", placeholder="https://stockx.com/...")
    
    col_scan, col_man = st.columns([1, 4])
    
    if col_scan.button("🔍 Scan Product"):
        if not url:
            st.warning("Please enter a URL first.")
        else:
            with st.spinner("Scanning sizes..."):
                try:
                    # Scan
                    options = st.session_state.quoter.scan_sizes(url)
                    category = st.session_state.quoter.detect_category()
                    
                    # Store results in state for persistence
                    st.session_state.current_options = options
                    st.session_state.current_category = category
                    st.session_state.scan_url = url
                    st.success(f"Scan Complete! Category: **{category}**")
                except Exception as e:
                    st.error(f"Error scanning: {e}")

    # Display Scan Results
    if 'current_options' in st.session_state and st.session_state.current_options:
        st.markdown(f"### Detected Category: {st.session_state.current_category}")
        
        # Override Category
        new_cat = st.selectbox("Incorrect Category? Override here:", ["Sneakers", "T-Shirt", "Hoodie", "Jacket"], index=["Sneakers", "T-Shirt", "Hoodie", "Jacket"].index(st.session_state.current_category))
        if new_cat != st.session_state.current_category:
            st.session_state.current_category = new_cat
            st.experimental_rerun()

        # Convert options to dataframe for display
        df = pd.DataFrame(st.session_state.current_options)
        if not df.empty:
            df['Display'] = df.apply(lambda x: f"ID: {x['index']} | {x['text']}", axis=1)
            
            # Selection Dropdown
            selected_option = st.selectbox("Select Size:", df['Display'].tolist())
            
            # Extract Index
            selected_idx = int(selected_option.split("|")[0].replace("ID:", "").strip())
            
            if st.button("💰 Get Final Quote"):
                with st.spinner("Clicking buttons... accessing Checkout..."):
                    try:
                        final_price = st.session_state.quoter.execute_quote(selected_idx)
                        
                        if final_price > 0:
                            service_price = st.session_state.quoter.calculate_service_price(final_price, st.session_state.current_category)
                            
                            st.markdown("---")
                            col_res1, col_res2 = st.columns(2)
                            with col_res1:
                                st.metric("StockX Checkut Total", f"${final_price:.2f}")
                            with col_res2:
                                st.metric("Final Service Quote", f"${service_price:.2f}", delta="Profit Included")
                            
                            st.balloons()
                        else:
                            st.error("Failed to extract price. Please try 'Manual Capture' mode or check the visible browser.")
                    except Exception as e:
                        st.error(f"Quote Error: {e}")
        else:
            st.warning("No sizes found. Try Manual Mode.")

else:
    st.info("👈 Please start the browser in the sidebar to begin.")
