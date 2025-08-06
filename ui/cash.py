import streamlit as st

from data.portfolio import save_portfolio_snapshot


def show_cash_section() -> None:
    """Display cash balance and provide a toggleable form to add funds."""

    def submit_cash() -> None:
        amount = st.session_state.ac_amount
        if amount <= 0:
            st.session_state.feedback = (
                "error",
                "Amount must be greater than zero.",
            )
            return

        st.session_state.cash += amount
        save_portfolio_snapshot(st.session_state.portfolio, st.session_state.cash)
        st.session_state.feedback = (
            "success",
            f"Added ${amount:.2f} to cash balance.",
        )
        st.session_state.show_cash_form = False
        st.session_state.ac_amount = 0.0

    def cancel_cash() -> None:
        st.session_state.show_cash_form = False
        st.session_state.ac_amount = 0.0

    st.subheader("Cash Balance")
    st.markdown(f"<h3>${st.session_state.cash:.2f}</h3>", unsafe_allow_html=True)

    if st.session_state.show_cash_form:
        with st.form("add_cash_form", clear_on_submit=True):
            st.number_input(
                "Amount",
                min_value=0.0,
                format="%.2f",
                key="ac_amount",
            )
            col_add, col_cancel = st.columns(2)
            col_add.form_submit_button("Add", on_click=submit_cash)
            col_cancel.form_submit_button("Cancel", on_click=cancel_cash)
    else:
        st.button(
            "Add Cash",
            on_click=lambda: st.session_state.update(show_cash_form=True),
        )
