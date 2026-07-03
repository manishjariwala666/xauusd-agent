import streamlit as st

def render_dashboard():
    # 1. Live Ticker Tape (CSS Based)
    ticker_data = "NIFTY: 24,100 | SENSEX: 79,200 | BTCUSD: 98,500 | XAUUSD: 4165.64 | SUI: 0.85 | ETH: 3,600"
    st.markdown(f"""
    <div style="background: #1a1a1a; padding: 10px; border-radius: 5px; border-left: 5px solid #00ff00;">
        <marquee behavior="scroll" direction="left" style="color: #00ff00; font-family: monospace; font-size: 18px;">
            {ticker_data}
        </marquee>
    </div>
    """, unsafe_allow_html=True)

    # 2. Market Summary Section
    st.subheader("Market Summary")
    col1, col2, col3 = st.columns(3)
    col1.metric("Market Sentiment", "Bullish", "+1.2%")
    col2.metric("XAU/USD Volatility", "High", "18.61")
    col3.metric("Liquidity Index", "94%", "-0.5%")

    # 3. Dynamic Tabs (Technical & Gainers/Losers)
    tab1, tab2 = st.tabs(["Technical Indicators", "Market Heatmap"])

    with tab1:
        st.write("### Real-Time Pivot Points")
        # Yahan aap apni Google Sheet ka data display kar sakte hain
        st.table(st.session_state.get('data', {})) 

    with tab2:
        st.write("### Top Gainers vs Losers")
        g_col, l_col = st.columns(2)
        g_col.write("**Top Gainers**") # Table Data
        l_col.write("**Top Losers**")  # Table Data

# Run the layout
render_dashboard()
