import streamlit as st


def render_user_guide() -> None:
    st.header("User Guide")
    st.markdown(
        """
        ### Getting Started
        1. **Set a starting cash balance.** When you first open the app the dashboard
           will ask for an initial amount of cash to trade with.
        2. **Maintain a watchlist.** Use the sidebar lookup to search for tickers and
           add them to your personal watchlist.

        ### Buying Stocks
        1. Open the *Log a Buy* form.
        2. Enter the ticker symbol, number of shares, and the price you paid.
        3. Provide a **Stop Loss %**. For example, entering `10` will set a stop price
           10% below your purchase price. The app stores the calculated price for you.

        ### Selling Stocks
        - Once you hold a position it will appear in the *Current Portfolio* table.
          Use the *Log a Sell* form to close or trim a position.

        ### Current Portfolio Table
        - Shows each holding with buy price, current price, stop loss and
          unrealised profit or loss. Refresh prices manually or enable
          auto-refresh for updates every 30 minutes.

        ### Daily Summary
        - Use the *Generate Daily Summary* button to create a markdown snapshot of
          your portfolio and watchlist for easy sharing or journaling.

        ### Tips
        - Add extra funds at any time using the *Add Cash* button.
        - Stop losses are stored as dollar prices even though you input a
          percentage.
        - The app saves data to the local `data/` folder so you can pick up where
          you left off.
        """
    )
