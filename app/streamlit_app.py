
"""
Streamlit UI for the Investment Agentic AI system.
Provides an interactive dashboard for investment analysis.
"""

import sys
import base64
from pathlib import Path

# Make the repository root importable when Streamlit executes this file.
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

import plotly.graph_objects as go
import streamlit as st
from loguru import logger

from src.utils.security import (
    authenticate_user,
    check_rate_limit,
    ensure_default_user,
    get_secret,
    log_audit_event,
    validate_ticker_symbol,
)

from src.agents.graph import run_investment_analysis  # noqa: E402
from src.pipeline import MongoPipelineStore  # noqa: E402
from src.pipeline.local_history import load_persistent_history, save_analysis_summary  # noqa: E402
from src.tools.portfolio_tools import (  # noqa: E402
    calculate_portfolio_volatility,
    calculate_portfolio_summary,
    load_portfolio,
    save_portfolio,
    suggest_rebalancing,
)

assets_dir = Path(__file__).parent / "assets"


# Page configuration
st.set_page_config(
    page_title="InvestSage - AI Investment Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------------------------------------------------------------------------
# Icon system — small inline SVGs (stroke-based, currentColor) so the UI
# doesn't depend on any external icon font or CDN at render time.
# ---------------------------------------------------------------------------
_ICON_PATHS = {
    "sparkles": '<path d="M12 3v4M12 17v4M3 12h4M17 12h4M5.6 5.6l2.8 2.8M15.6 15.6l2.8 2.8M18.4 5.6l-2.8 2.8M8.4 15.6l-2.8 2.8"/>',
    "sliders": '<path d="M4 6h10M18 6h2M4 12h2M10 12h10M4 18h14M22 18h0"/><circle cx="16" cy="6" r="2"/><circle cx="7" cy="12" r="2"/><circle cx="18" cy="18" r="2"/>',
    "search": '<circle cx="11" cy="11" r="7"/><path d="M21 21l-4.3-4.3"/>',
    "message": '<path d="M21 15a2 2 0 0 1-2 2H8l-4 4V5a2 2 0 0 1 2-2h13a2 2 0 0 1 2 2z"/>',
    "bar-chart": '<path d="M3 3v18h18"/><rect x="7" y="12" width="3" height="6"/><rect x="12" y="8" width="3" height="10"/><rect x="17" y="5" width="3" height="13"/>',
    "building": '<rect x="4" y="3" width="16" height="18" rx="1"/><path d="M9 8h1M14 8h1M9 12h1M14 12h1M9 16h1M14 16h1"/>',
    "activity": '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
    "target": '<circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="5"/><circle cx="12" cy="12" r="1"/>',
    "crystal-ball": '<circle cx="12" cy="10" r="7"/><path d="M6 20h12M9 20l1-3M15 20l-1-3"/>',
    "shield": '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3.5 2"/>',
    "trending-up": '<path d="M3 17l6-6 4 4 8-8"/><path d="M15 7h6v6"/>',
    "trending-down": '<path d="M3 7l6 6 4-4 8 8"/><path d="M15 17h6v-6"/>',
    "minus-circle": '<circle cx="12" cy="12" r="9"/><path d="M8 12h8"/>',
    "cpu": '<rect x="7" y="7" width="10" height="10" rx="1"/><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 1v2M15 1v2M9 21v2M15 21v2M1 9h2M1 15h2M21 9h2M21 15h2"/>',
}


def icon_svg(name: str, size: str = "1em") -> str:
    """Returns an inline SVG icon as an HTML string, styled via currentColor."""
    path = _ICON_PATHS.get(name, "")
    return (
        f'<span class="icn" style="width:{size};height:{size};">'
        f'<svg viewBox="0 0 24 24">{path}</svg></span>'
    )


def icon_badge(name: str, tone: str = "teal", size: str = "1.15rem") -> str:
    """Returns an icon inside a soft rounded badge, for section headers."""
    path = _ICON_PATHS.get(name, "")
    return (
        f'<span class="icn-badge icn-badge--{tone}">'
        f'<svg viewBox="0 0 24 24" style="width:{size};height:{size};">{path}</svg></span>'
    )


def section_title(name: str, text: str, tone: str = "teal", sub: str = ""):
    """Renders a consistent icon + heading combo in place of st.subheader()."""
    sub_html = f'<div class="section-sub">{sub}</div>' if sub else ""
    st.markdown(
        f"""
        <div class="section-title">
            {icon_badge(name, tone)}
            <div><h3>{text}</h3>{sub_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def load_theme():
    """Loads the shared dashboard theme."""
    css_path = assets_dir / "style.css"
    if css_path.exists():
        st.markdown(
            f"<style>{css_path.read_text(encoding='utf-8')}</style>",
            unsafe_allow_html=True,
        )


def render_sign_in_dialog():
    """Open a modal sign-in form when the user wants to authenticate."""
    if st.session_state.get("authenticated"):
        return

    if st.sidebar.button("Sign in", key="open_signin_modal"):
        st.session_state.show_signin_modal = True

    if st.session_state.get("show_signin_modal"):
        @st.dialog("Sign in")
        def sign_in_modal():
            st.caption("Access your private analysis workspace")
            with st.form("sign_in_form"):
                username = st.text_input("Username", value="demo")
                password = st.text_input("Password", type="password", value="invest123")
                submitted = st.form_submit_button("Continue")

            if submitted:
                if not authenticate_user(username, password):
                    st.error("Invalid username or password.")
                    log_audit_event(username, "login", {"source": "streamlit"}, "failure")
                    return

                st.session_state.user_id = username
                st.session_state.authenticated = True
                st.session_state.show_signin_modal = False
                log_audit_event(username, "login", {"source": "streamlit"}, "success")
                st.rerun()

        sign_in_modal()

    st.sidebar.info("Sign in to unlock your private analyses and account-scoped history.")


def render_user_profile_panel():
    """Show the current account details and controls in the sidebar."""
    if not st.session_state.get("authenticated"):
        return

    user_id = st.session_state.get("user_id", "user")
    history_count = len(load_analysis_history(limit=50, user_id=user_id))

    st.sidebar.markdown(
        """
        <div style="
            background: linear-gradient(135deg, rgba(200,92,61,0.10), rgba(86,123,118,0.10));
            border: 1px solid rgba(38,37,32,0.10);
            border-radius: 18px;
            padding: 0.9rem 0.95rem 0.8rem;
            margin-bottom: 1rem;
            box-shadow: 0 10px 30px rgba(55,48,38,0.06);
        ">
            <div style="display:flex;align-items:center;gap:0.7rem;margin-bottom:0.65rem;">
                <div style="width:2.25rem;height:2.25rem;border-radius:50%;display:flex;align-items:center;justify-content:center;background:#fff;color:#252421;border:1px solid rgba(38,37,32,0.12);font-weight:700;">
                    {initial}
                </div>
                <div>
                    <div style="font-size:0.72rem;letter-spacing:0.08em;text-transform:uppercase;color:#6f6c64;">Investor profile</div>
                    <div style="font-size:1.1rem;font-weight:700;color:#252421;">{user_id}</div>
                </div>
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:0.55rem;margin-bottom:0.7rem;">
                <div style="background: rgba(255,255,255,0.60); border:1px solid rgba(38,37,32,0.08); border-radius: 12px; padding: 0.5rem 0.55rem;">
                    <div style="font-size:0.7rem; color:#6f6c64; text-transform:uppercase; letter-spacing:0.06em;">History</div>
                    <div style="font-size:1.05rem; font-weight:700; color:#252421;">{history_count}</div>
                </div>
                <div style="background: rgba(255,255,255,0.60); border:1px solid rgba(38,37,32,0.08); border-radius: 12px; padding: 0.5rem 0.55rem;">
                    <div style="font-size:0.7rem; color:#6f6c64; text-transform:uppercase; letter-spacing:0.06em;">Mode</div>
                    <div style="font-size:0.92rem; font-weight:700; color:#252421;">Private</div>
                </div>
            </div>
            <div style="padding:0.55rem 0.65rem;border-radius:12px;background:rgba(255,255,255,0.45);border:1px solid rgba(38,37,32,0.08);">
                <div style="font-size:0.7rem; color:#6f6c64; text-transform:uppercase; letter-spacing:0.06em; margin-bottom:0.2rem;">Trade acknowledgement</div>
                <div style="font-size:0.8rem; color:#252421; line-height:1.35;">
                    {confirmation_status}
                </div>
            </div>
        </div>
        """.format(
            initial=user_id[:1].upper(),
            user_id=user_id,
            history_count=history_count,
            confirmation_status="Confirmed" if st.session_state.get("trade_confirmed") else "Awaiting confirmation",
        ),
        unsafe_allow_html=True,
    )

    if st.sidebar.button("Review confirmation", use_container_width=True, type="secondary", key="profile_trade_review_button"):
        st.session_state.show_trade_modal = True

    if st.sidebar.button("Sign out", use_container_width=True, type="secondary"):
        st.session_state.pop("authenticated", None)
        st.session_state.pop("user_id", None)
        st.session_state.pop("trade_confirmed", None)
        st.rerun()


def render_trade_confirmation_dialog():
    """Render a modal confirmation box before the user can proceed with trade-related actions."""
    if st.session_state.get("trade_confirmed"):
        st.success("Trade confirmation acknowledged.")
        return

    trigger_key = "trade_confirm_button"
    if st.button("Review educational disclaimer", key=trigger_key):
        st.session_state.show_trade_modal = True

    if st.session_state.get("show_trade_modal"):
        @st.dialog("Educational Disclaimer & Trade Confirmation")
        def disclaimer_modal():
            st.warning(
                "This dashboard provides educational market research only. "
                "It does not execute trades, connect to a broker, or provide investment advice. "
                "Any real trade requires your explicit confirmation and a separate broker integration."
            )
            st.write("By continuing, you acknowledge that:")
            st.markdown(
                "- This tool is for research and learning only\n"
                "- No automated trade execution is enabled\n"
                "- You remain responsible for all investment decisions\n"
                "- A broker and your explicit authorization are required before any live trade"
            )
            confirmed = st.checkbox("I understand and confirm that no trade will be executed automatically.")
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Confirm", disabled=not confirmed, type="primary"):
                    st.session_state.trade_confirmed = True
                    st.session_state.show_trade_modal = False
                    st.rerun()
            with col2:
                if st.button("Cancel"):
                    st.session_state.show_trade_modal = False
                    st.rerun()

        disclaimer_modal()


def render_header():
    """Renders the application header."""
    hero_candidates = ["market-hero.gif", "market-hero.jpg", "market-hero.jpeg", "market-hero.png", "market-hero.svg"]
    hero_image_html = ""

    for filename in hero_candidates:
        hero_image = assets_dir / filename
        if hero_image.exists():
            mime = "image/svg+xml" if filename.endswith(".svg") else f"image/{hero_image.suffix.lstrip('.')}"
            hero_image_b64 = base64.b64encode(hero_image.read_bytes()).decode("utf-8")
            hero_image_html = (
                f'<div class="hero-art">'
                f'<div class="hero-live"><span class="dot"></span>Agent live</div>'
                f'<img src="data:{mime};base64,{hero_image_b64}" alt="Market momentum illustration" />'
                f'</div>'
            )
            break

    st.markdown(
        f"""
        <div class="hero-shell">
            <div class="hero-grid">
                <div class="hero-copy">
                    <div class="hero-kicker">{icon_svg('sparkles')} AI Investment Dashboard</div>
                    <h1 class="main-header">InvestSage</h1>
                    <p class="sub-header">A polished market cockpit for stock data, sentiment, technical indicators, and recommendation tracing.</p>
                    <span class="stat-chip stat-chip--accent"><span></span>Market intelligence</span>
                    <span class="stat-chip stat-chip--blue"><span></span>Risk-aware signals</span>
                    <span class="stat-chip stat-chip--amber"><span></span>Clean decision trail</span>
                </div>
                {hero_image_html}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar():
    """Renders the sidebar with input controls."""
    render_sign_in_dialog()

    if st.session_state.get("authenticated"):
        render_user_profile_panel()

    st.sidebar.markdown(
        f"""
        <div class="section-title">
            {icon_badge('sliders', 'blue', '1.05rem')}
            <div><h3 style="font-size:1.05rem;">Analysis Configuration</h3></div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    ticker_options = {
        "AAPL — Apple": "AAPL",
        "MSFT — Microsoft": "MSFT",
        "NVDA — NVIDIA": "NVDA",
        "GOOGL — Alphabet": "GOOGL",
        "AMZN — Amazon": "AMZN",
        "META — Meta Platforms": "META",
        "TSLA — Tesla": "TSLA",
        "JPM — JPMorgan Chase": "JPM",
        "V — Visa": "V",
        "JNJ — Johnson & Johnson": "JNJ",
        "SPY — S&P 500 ETF": "SPY",
        "Custom ticker…": "CUSTOM",
    }
    selected_ticker = st.sidebar.selectbox(
        "🔎 Select a ticker",
        options=list(ticker_options),
        help="Choose a common investment or select Custom ticker to enter another symbol.",
    )
    if ticker_options[selected_ticker] == "CUSTOM":
        try:
            ticker = validate_ticker_symbol(
                st.sidebar.text_input(
                    "Custom ticker symbol",
                    placeholder="e.g., NFLX, BABA, CSE.N0000",
                    help="Enter the exchange ticker used by Yahoo Finance.",
                )
            )
        except ValueError as exc:
            st.sidebar.error(str(exc))
            ticker = ""
    else:
        ticker = ticker_options[selected_ticker]
        st.sidebar.caption(f"Selected: **{ticker}**")

    if ticker:
        st.sidebar.caption(f"Selected: **{ticker}**")

    with st.sidebar.expander("🎯 Your portfolio plan", expanded=True):
        st.caption("A stock idea is more useful when it fits your goal, time horizon, and risk comfort.")
        goal = st.selectbox("Primary goal", ["Long-term growth", "Income", "Capital preservation", "Balanced growth and income"])
        risk_profile = st.select_slider("Risk comfort", options=["Conservative", "Balanced", "Growth", "Aggressive"], value="Balanced")
        horizon_years = st.slider("Investment horizon (years)", 1, 30, 10)
        portfolio_value = st.number_input("Portfolio value (USD)", min_value=0.0, value=100000.0, step=1000.0)
        existing_ticker_weight = st.slider("Current weight in this stock", 0, 100, 0) / 100
        proposed_weight = st.slider("Planned additional weight", 0, 30, 5) / 100
        liquidity_need = st.selectbox("Need this money soon?", ["Low", "Medium", "High"])

    investor_profile = {
        "goal": goal,
        "risk_profile": risk_profile,
        "horizon_years": horizon_years,
        "portfolio_value": portfolio_value,
        "existing_ticker_weight": existing_ticker_weight,
        "proposed_weight": proposed_weight,
        "liquidity_need": liquidity_need,
    }

    with st.sidebar.expander("🚨 Alerts", expanded=False):
        price_alert_enabled = st.checkbox("Price target", value=False)
        price_target = st.number_input("Target price", min_value=0.0, value=0.0, step=1.0, disabled=not price_alert_enabled)
        price_direction = st.selectbox("Trigger when price is", ["above", "below"], disabled=not price_alert_enabled)
        rsi_alert_enabled = st.checkbox("RSI threshold", value=True)
        rsi_overbought = st.number_input("Overbought RSI", min_value=50.0, max_value=100.0, value=70.0, step=1.0, disabled=not rsi_alert_enabled)
        rsi_oversold = st.number_input("Oversold RSI", min_value=0.0, max_value=50.0, value=30.0, step=1.0, disabled=not rsi_alert_enabled)
        large_move_enabled = st.checkbox("Large price movement", value=True)
        large_move_threshold = st.number_input("Movement threshold (%)", min_value=0.1, value=5.0, step=0.5, disabled=not large_move_enabled)
        negative_news_enabled = st.checkbox("Negative news", value=True)
        negative_news_threshold = st.number_input("Negative sentiment threshold", min_value=-1.0, max_value=0.0, value=-0.5, step=0.1, disabled=not negative_news_enabled)
        earnings_enabled = st.checkbox("Earnings announcement", value=True)
        earnings_lookahead = st.number_input("Earnings lookahead (days)", min_value=0, max_value=90, value=7, step=1, disabled=not earnings_enabled)
        allocation_enabled = st.checkbox("Portfolio allocation limit", value=True)
        allocation_limit = st.number_input("Maximum ticker allocation (%)", min_value=0.0, max_value=100.0, value=10.0, step=1.0, disabled=not allocation_enabled) / 100

    alert_rules = {
        "price_target": {"enabled": price_alert_enabled, "target": price_target, "direction": price_direction},
        "rsi": {"enabled": rsi_alert_enabled, "overbought": rsi_overbought, "oversold": rsi_oversold},
        "large_move": {"enabled": large_move_enabled, "threshold_percent": large_move_threshold},
        "negative_news": {"enabled": negative_news_enabled, "threshold": negative_news_threshold, "lookback_days": 3},
        "earnings": {"enabled": earnings_enabled, "lookahead_days": earnings_lookahead, "lookback_days": 3},
        "portfolio_allocation": {"enabled": allocation_enabled, "limit": allocation_limit},
    }

    with st.sidebar.expander("⚙️ Advanced Options"):
        use_conditional = st.checkbox(
            "Use Conditional Routing",
            value=False,
            help="Enable dynamic agent routing",
        )
    analyze_button = st.sidebar.button(
        "🚀 Analyze Stock",
        type="primary",
        use_container_width=True,
    )

    st.sidebar.markdown("---")
    st.sidebar.caption("API rate limit: 20 requests / 60s per user")
    if not check_rate_limit(st.session_state.get("user_id", "guest"), limit=20, window_seconds=60):
        st.sidebar.warning("Rate limit reached. Please wait before running another analysis.")
        analyze_button = False

    return ticker, use_conditional, investor_profile, alert_rules, analyze_button


def render_question_chat():
    """Render the chat composer and retain the latest submitted question."""
    submitted_question = st.chat_input(
        "Ask about this stock, its risks, or the outlook...",
        key="question_chat_input",
    )
    if submitted_question and submitted_question.strip():
        st.session_state.chat_question = submitted_question.strip()

    question = st.session_state.get("chat_question", "")
    if question:
        with st.chat_message("user"):
            st.write(question)
    return question, bool(submitted_question and submitted_question.strip())


def render_portfolio_fit(state):
    """Show how a single-stock view fits a diversified portfolio plan."""
    section_title("target", "Portfolio Fit & Rebalancing", "green", "Goal-based allocation, diversification, and concentration checks")
    insights = state.get("portfolio_insights")
    if not insights:
        st.info("Portfolio-fit guidance will appear after your analysis is complete.")
        return

    allocation = insights["target_allocation"]
    chart = go.Figure(data=[go.Pie(
        labels=list(allocation), values=list(allocation.values()), hole=0.58,
        marker={"colors": ["#c85c3d", "#567b76", "#b9823b"]}, textinfo="label+percent",
    )])
    chart.update_layout(height=300, margin=dict(l=15, r=15, t=15, b=15), paper_bgcolor="rgba(0,0,0,0)", font_color="#252421")
    left, right = st.columns(2)
    with left:
        st.plotly_chart(chart, use_container_width=True)
    with right:
        st.metric("Single-stock weight after this idea", f"{insights['resulting_ticker_weight']:.0%}")
        st.metric("Concentration check", insights["concentration_status"])
        st.write(f"**Goal:** {insights['goal']}  ")
        st.write(f"**Risk comfort:** {insights['risk_profile']}  ")
        st.write(f"**Horizon:** {insights['horizon_years']} years")
        st.info(f"**Rebalance cue:** {insights['rebalance_action']}")
    if insights["alerts"]:
        for alert in insights["alerts"]:
            st.warning(alert)
    else:
        st.success("This proposed weight is within the app's 10% single-company educational guardrail.")
    st.caption("Educational planning aid only. Consider your full finances, taxes, and professional advice before acting.")


def render_portfolio_manager(_state=None):
    """Render holdings, performance, allocation, dividend, and rebalance views."""
    user_id = st.session_state.get("user_id")
    if not user_id:
        return

    holdings = load_portfolio(user_id)
    with st.expander("💼 Portfolio Management", expanded=not holdings):
        section_title("target", "Portfolio Management", "green", "Track holdings, income, diversification, and educational rebalancing cues")
        with st.form("add_holding_form", clear_on_submit=True):
            st.markdown("**Add a holding**")
            input_col1, input_col2, input_col3 = st.columns(3)
            with input_col1:
                holding_ticker = st.text_input("Ticker", placeholder="AAPL").strip().upper()
                company = st.text_input("Company", placeholder="Apple Inc.")
                sector = st.text_input("Sector", value="Other")
            with input_col2:
                asset_type = st.selectbox("Asset type", ["Stocks", "Bonds", "Cash", "ETF", "Crypto", "Other"])
                shares = st.number_input("Shares", min_value=0.0, step=0.01, format="%.4f")
                purchase_price = st.number_input("Purchase price", min_value=0.0, step=0.01, format="%.2f")
            with input_col3:
                current_price = st.number_input("Current price", min_value=0.0, step=0.01, format="%.2f")
                dividend_per_share = st.number_input("Dividend per share", min_value=0.0, step=0.01, format="%.4f")
                total_dividends = st.number_input("Total dividends received", min_value=0.0, step=0.01, format="%.2f")
                annual_volatility = st.number_input("Annual volatility (%)", min_value=0.0, max_value=500.0, value=0.0, step=1.0, format="%.1f")
            submitted = st.form_submit_button("Add holding", type="primary", use_container_width=True)

        if submitted:
            if not holding_ticker or shares <= 0 or purchase_price <= 0 or current_price <= 0:
                st.error("Ticker, shares, purchase price, and current price are required.")
            elif any(item.get("ticker") == holding_ticker for item in holdings):
                st.error("That ticker is already in your portfolio. Update the existing holding or use a distinct ticker.")
            else:
                holdings.append({
                    "ticker": holding_ticker,
                    "company": company or holding_ticker,
                    "sector": sector or "Other",
                    "asset_type": asset_type,
                    "shares": shares,
                    "purchase_price": purchase_price,
                    "current_price": current_price,
                    "dividend_per_share": dividend_per_share,
                    "total_dividends": total_dividends or shares * dividend_per_share,
                    "annual_volatility": annual_volatility / 100,
                })
                save_portfolio(user_id, holdings)
                log_audit_event(user_id, "portfolio_holding_added", {"ticker": holding_ticker}, "success")
                st.success(f"Added {holding_ticker} to your portfolio.")
                st.rerun()

        if not holdings:
            st.info("Add your first holding to see performance, allocation, concentration, and dividend tracking.")
            return

        summary = calculate_portfolio_summary(holdings)
        metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
        metric_col1.metric("Current value", f"${summary['total_value']:,.2f}")
        metric_col2.metric("Cost basis", f"${summary['total_cost']:,.2f}")
        metric_col3.metric("Total return", f"${summary['total_return']:,.2f}", f"{summary['return_percent']:.1%}")
        metric_col4.metric("Dividends", f"${summary['total_dividends']:,.2f}")
        metric_col5.metric("Holdings", len(summary["holdings"]))

        portfolio_volatility = calculate_portfolio_volatility(summary["holdings"])
        if portfolio_volatility is None:
            st.info("Add annual volatility for each holding to calculate portfolio-level volatility.")
        else:
            st.metric("Portfolio volatility", f"{portfolio_volatility:.2%}")

        display_rows = [
            {
                "Ticker": item["ticker"],
                "Company": item["company"],
                "Shares": item["shares"],
                "Purchase": f"${item['purchase_price']:,.2f}",
                "Current": f"${item['current_price']:,.2f}",
                "Value": f"${item['current_value']:,.2f}",
                "Return": f"${item['total_return']:,.2f} ({item['return_percent']:.1%})",
                "Dividends": f"${item['total_dividends']:,.2f}",
                "Sector": item["sector"],
                "Asset type": item["asset_type"],
            }
            for item in summary["holdings"]
        ]
        st.dataframe(display_rows, use_container_width=True, hide_index=True)

        edit_ticker = st.selectbox("Holding to update", [item["ticker"] for item in summary["holdings"]], key="edit_portfolio_ticker")
        current_holding = next(item for item in summary["holdings"] if item["ticker"] == edit_ticker)
        with st.form("edit_holding_form"):
            st.markdown("**Update holding**")
            edit_col1, edit_col2, edit_col3 = st.columns(3)
            with edit_col1:
                edit_company = st.text_input("Company", value=current_holding["company"])
                edit_sector = st.text_input("Sector", value=current_holding["sector"])
            with edit_col2:
                edit_shares = st.number_input("Shares", min_value=0.0, value=current_holding["shares"], step=0.01, format="%.4f")
                edit_purchase_price = st.number_input("Purchase price", min_value=0.0, value=current_holding["purchase_price"], step=0.01, format="%.2f")
            with edit_col3:
                edit_current_price = st.number_input("Current price", min_value=0.0, value=current_holding["current_price"], step=0.01, format="%.2f")
                edit_dividends = st.number_input("Total dividends received", min_value=0.0, value=current_holding["total_dividends"], step=0.01, format="%.2f")
            update_submitted = st.form_submit_button("Update holding", use_container_width=True)

        if update_submitted:
            updated_holdings = []
            for item in holdings:
                if item.get("ticker") == edit_ticker:
                    updated_holdings.append({
                        **item,
                        "company": edit_company or edit_ticker,
                        "sector": edit_sector or "Other",
                        "shares": edit_shares,
                        "purchase_price": edit_purchase_price,
                        "current_price": edit_current_price,
                        "total_dividends": edit_dividends,
                    })
                else:
                    updated_holdings.append(item)
            save_portfolio(user_id, updated_holdings)
            log_audit_event(user_id, "portfolio_holding_updated", {"ticker": edit_ticker}, "success")
            st.success(f"Updated {edit_ticker}.")
            st.rerun()

        remove_col, risk_col = st.columns([1, 2])
        with remove_col:
            remove_ticker = st.selectbox("Remove holding", [item["ticker"] for item in summary["holdings"]], key="remove_portfolio_ticker")
            if st.button("Remove selected holding", key="remove_portfolio_holding"):
                save_portfolio(user_id, [item for item in holdings if item.get("ticker") != remove_ticker])
                log_audit_event(user_id, "portfolio_holding_removed", {"ticker": remove_ticker}, "success")
                st.rerun()
        with risk_col:
            risk_profile = st.selectbox("Rebalancing target", ["Conservative", "Balanced", "Growth", "Aggressive"], index=1, key="portfolio_risk_profile")

        chart_col1, chart_col2, chart_col3 = st.columns(3)
        for column, title, allocation, colors in [
            (chart_col1, "By company", summary["company_allocations"], ["#c85c3d", "#567b76", "#b9823b", "#6c6a63"]),
            (chart_col2, "By sector", summary["sector_allocations"], ["#567b76", "#c85c3d", "#b9823b", "#8f8b82"]),
            (chart_col3, "By asset type", summary["asset_type_allocations"], ["#b9823b", "#567b76", "#c85c3d", "#8f8b82"]),
        ]:
            with column:
                st.caption(title)
                chart = go.Figure(data=[go.Pie(labels=list(allocation), values=list(allocation.values()), hole=0.55, marker={"colors": colors})])
                chart.update_layout(height=250, margin=dict(l=5, r=5, t=5, b=5), showlegend=True, paper_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(chart, use_container_width=True, key=f"portfolio_{title.replace(' ', '_')}")

        if summary["concentration_alerts"]:
            for alert in summary["concentration_alerts"]:
                st.warning(alert)
        else:
            st.success("No company or sector concentration warning was triggered by the educational guardrails.")

        suggestions = suggest_rebalancing(summary, risk_profile)
        st.markdown("**Rebalancing suggestions**")
        if suggestions:
            for suggestion in suggestions:
                direction = "add exposure" if suggestion["action"] == "Increase" else "reduce exposure"
                st.info(
                    f"{suggestion['action']} {suggestion['asset_type']} exposure: "
                    f"{suggestion['current_weight']:.0%} currently vs {suggestion['target_weight']:.0%} target "
                    f"({direction} by about {abs(suggestion['difference']):.0%})."
                )
        else:
            st.success(f"Your asset-type mix is within 5 percentage points of the {risk_profile.lower()} educational target mix.")
        st.caption("Portfolio values and rebalancing cues are educational estimates. Verify prices, taxes, fees, and dividend records before acting.")


def render_alerts(state):
    """Render triggered market and portfolio alerts for the completed analysis."""
    section_title("shield", "Alerts", "red", "Signals triggered by the thresholds you selected")
    alerts = state.get("alerts") or []
    if not alerts:
        st.success("No configured alerts were triggered by the available data.")
        return

    st.warning(f"{len(alerts)} alert(s) triggered for {state.get('ticker', 'this ticker')}.")
    for alert in alerts:
        message = alert.get("message", "Alert triggered")
        if alert.get("severity") == "critical":
            st.error(message)
        else:
            st.warning(message)
        st.caption(
            f"Type: {alert.get('type', 'unknown')} | Source: {alert.get('source', 'unknown')} | "
            f"Triggered: {alert.get('triggered_at', 'N/A')}"
        )


def render_stock_data(state):
    """Renders stock data section."""
    section_title("bar-chart", "Stock Data", "teal")

    if state.get("stock_data"):
        data = state["stock_data"]

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Current Price",
                f"${data.get('current_price', 'N/A'):.2f}" if data.get("current_price") else "N/A",
                delta=(
                    f"{((data.get('current_price', 0) - data.get('previous_close', 0)) / data.get('previous_close', 1) * 100):.2f}%"
                    if data.get("current_price") and data.get("previous_close")
                    else None
                ),
            )

        with col2:
            st.metric(
                "Market Cap",
                f"${data.get('market_cap', 0) / 1e9:.1f}B" if data.get("market_cap") else "N/A",
            )

        with col3:
            st.metric(
                "52W High",
                f"${data.get('52_week_high', 'N/A'):.2f}" if data.get("52_week_high") else "N/A",
            )

        with col4:
            st.metric(
                "52W Low",
                f"${data.get('52_week_low', 'N/A'):.2f}" if data.get("52_week_low") else "N/A",
            )

        st.markdown("**Market data quality**")
        quality_col1, quality_col2, quality_col3, quality_col4 = st.columns(4)
        quality_col1.caption(f"Market: {data.get('market_status', 'Unknown')}")
        quality_col2.caption(f"Currency: {data.get('currency', 'N/A')}")
        quality_col3.caption(f"Exchange: {data.get('exchange', 'N/A')}")
        quality_col4.caption(f"Source: {data.get('source', 'N/A')}")
        st.caption(f"Quote timestamp: {data.get('data_timestamp') or data.get('as_of', 'N/A')}")

        history = state.get("historical_prices") or []
        if history:
            st.caption(
                f"Validated history: {len(history):,} records, "
                f"{history[0].get('date', 'N/A')[:10]} to {history[-1].get('date', 'N/A')[:10]} "
                "(missing and invalid rows removed)"
            )

        with st.expander("📋 Additional Stock Information"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Open:** ${data.get('open', 'N/A')}")
                st.write(f"**High:** ${data.get('high', 'N/A')}")
                st.write(f"**Low:** ${data.get('low', 'N/A')}")
            with col2:
                st.write(f"**Volume:** {data.get('volume', 'N/A'):,}" if data.get("volume") else "N/A")
                st.write(f"**Avg Volume:** {data.get('avg_volume', 'N/A'):,}" if data.get("avg_volume") else "N/A")
    else:
        st.warning("No stock data available")


def _format_percent(value):
    return f"{value:.1%}" if isinstance(value, (int, float)) else "N/A"


def _format_ratio(value):
    return f"{value:.2f}" if isinstance(value, (int, float)) else "N/A"


def _format_money(value, currency=None):
    if not isinstance(value, (int, float)):
        return "N/A"
    return f"{currency or '$'} {value:,.0f}"


def render_company_info(state):
    """Renders company information section."""
    section_title("building", "Company Information", "blue")

    if state.get("company_info"):
        info = state["company_info"]

        col1, col2 = st.columns(2)

        with col1:
            st.write(f"**Name:** {info.get('name', 'N/A')}")
            st.write(f"**Sector:** {info.get('sector', 'N/A')}")
            st.write(f"**Industry:** {info.get('industry', 'N/A')}")
            st.write(f"**Exchange:** {info.get('exchange', 'N/A')}")

        with col2:
            st.write(f"**P/E Ratio:** {info.get('pe_ratio', 'N/A'):.2f}" if info.get("pe_ratio") else "N/A")
            st.write(f"**Beta:** {info.get('beta', 'N/A'):.2f}" if info.get("beta") else "N/A")
            st.write(f"**EPS:** ${info.get('eps', 'N/A'):.2f}" if info.get("eps") else "N/A")
            st.write(f"**Dividend Yield:** {info.get('dividend_yield', 'N/A'):.2%}" if info.get("dividend_yield") else "N/A")

        if info.get("description"):
            with st.expander("📝 Business Summary"):
                st.write(info.get("description"))

        analysis = state.get("fundamental_analysis") or {}
        st.markdown("### Financial Overview")
        growth = analysis.get("growth_metrics") or {}
        cash_flow = analysis.get("cash_flow_metrics") or {}
        valuation = analysis.get("valuation_metrics") or {}
        balance_sheet = analysis.get("balance_sheet") or {}
        health = analysis.get("financial_health") or {}

        growth_col1, growth_col2, growth_col3, growth_col4 = st.columns(4)
        growth_col1.metric("Revenue Growth", _format_percent(growth.get("revenue_growth")))
        growth_col2.metric("Earnings Growth", _format_percent(growth.get("earnings_growth")))
        growth_col3.metric("Free Cash Flow", _format_money(cash_flow.get("free_cash_flow"), info.get("currency")))
        growth_col4.metric("Debt / Equity", _format_ratio(balance_sheet.get("debt_to_equity")))

        valuation_col1, valuation_col2, valuation_col3, valuation_col4 = st.columns(4)
        valuation_col1.metric("P/E", _format_ratio(valuation.get("pe_ratio")))
        valuation_col2.metric("PEG", _format_ratio(valuation.get("peg_ratio")))
        valuation_col3.metric("P/B", _format_ratio(valuation.get("price_to_book")))
        valuation_col4.metric("Dividend Yield", _format_percent(valuation.get("dividend_yield")))

        health_col1, health_col2 = st.columns([1, 2])
        with health_col1:
            score = health.get("score")
            st.metric("Financial Health", health.get("rating", "Unavailable"), f"{score:.0f}/100" if score is not None else None)
        with health_col2:
            st.caption(
                f"Health score: {health.get('metrics_scored', 0)} available signals. "
                "Growth, leverage, cash flow, and valuation are weighted equally."
            )

        peer_comparison = analysis.get("peer_comparison") or info.get("peer_comparison") or {}
        with st.expander("🏭 Industry & Competitor Comparison", expanded=True):
            peers = peer_comparison.get("peers") or []
            if peers:
                st.caption(f"Industry: {peer_comparison.get('industry') or 'Not available'}")
                peer_rows = [{
                    "Company": peer.get("name", peer.get("ticker")),
                    "Ticker": peer.get("ticker"),
                    "P/E": _format_ratio(peer.get("pe_ratio")),
                    "PEG": _format_ratio(peer.get("peg_ratio")),
                    "P/B": _format_ratio(peer.get("price_to_book")),
                    "Profit Margin": _format_percent(peer.get("profit_margin")),
                } for peer in peers]
                st.dataframe(peer_rows, use_container_width=True, hide_index=True)
                st.caption("Peer values are provider snapshots; compare companies with similar business models and accounting periods.")
            else:
                st.info("Peer comparison is unavailable for this ticker.")
    else:
        st.warning("No company information available")


def render_sentiment_analysis(state):
    """Renders sentiment analysis section."""
    section_title("message", "Sentiment Analysis", "amber")

    if state.get("sentiment_score") is not None:
        score = state["sentiment_score"]
        confidence = state.get("sentiment_confidence", 0)

        fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=score,
                domain={"x": [0, 1], "y": [0, 1]},
                title={"text": "Sentiment Score"},
                gauge={
                    "axis": {"range": [-1, 1]},
                    "bar": {"color": "#c85c3d"},
                    "steps": [
                        {"range": [-1, -0.33], "color": "#ff7070"},
                        {"range": [-0.33, 0.33], "color": "#a7b8cf"},
                        {"range": [0.33, 1], "color": "#49d39c"},
                    ],
                    "threshold": {
                        "line": {"color": "#b9823b", "width": 4},
                        "thickness": 0.75,
                        "value": 0,
                    },
                },
            )
        )

        st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Confidence", f"{confidence:.2%}")
        with col2:
            sentiment_label = "Positive" if score > 0.3 else "Negative" if score < -0.3 else "Neutral"
            st.metric("Sentiment", sentiment_label)

        with st.expander("📰 Full News Summary", expanded=True):
            st.write(state.get("news_summary") or "No news summary is available.")

        with st.expander("📌 Key Events", expanded=True):
            key_events = state.get("key_events") or []
            if key_events:
                for event in key_events:
                    st.markdown(f"- {event}")
            else:
                st.write("No key events were identified.")
    else:
        st.warning("No sentiment analysis available")


def render_technical_indicators(state):
    """Renders technical indicators section."""
    section_title("activity", "Technical Indicators", "teal")

    if state.get("technical_indicators"):
        indicators = state["technical_indicators"]

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("RSI", f"{indicators.get('RSI', 'N/A'):.2f}" if indicators.get("RSI") else "N/A")
            st.metric("MACD", f"{indicators.get('MACD', 'N/A'):.2f}" if indicators.get("MACD") else "N/A")

        with col2:
            st.metric("SMA (20)", f"${indicators.get('SMA_20', 'N/A'):.2f}" if indicators.get("SMA_20") else "N/A")
            st.metric("SMA (50)", f"${indicators.get('SMA_50', 'N/A'):.2f}" if indicators.get("SMA_50") else "N/A")

        with col3:
            st.metric("EMA (12)", f"${indicators.get('EMA_12', 'N/A'):.2f}" if indicators.get("EMA_12") else "N/A")
            st.metric("EMA (26)", f"${indicators.get('EMA_26', 'N/A'):.2f}" if indicators.get("EMA_26") else "N/A")
    else:
        st.warning("No technical indicators available")


def render_recommendation(state):
    """Renders the investment recommendation section."""
    section_title("target", "Investment Recommendation", "green")

    final_recommendation = state.get("final_recommendation") or state.get("risk_adjusted_recommendation")
    llm_recommendation = state.get("llm_recommendation")
    llm_confidence = state.get("llm_confidence")

    if final_recommendation or llm_recommendation:
        if state.get("user_query"):
            st.markdown("**Answer to your question**")
            st.info(state.get("direct_answer") or "The agent could not produce a direct answer from the available evidence.")

        if state.get("beginner_explanation"):
            st.markdown("**What this means**")
            st.write(state["beginner_explanation"])

        if final_recommendation == "BUY":
            st.markdown(
                f'<div class="recommendation-buy">{icon_svg("trending-up", "1.3rem")}BUY</div>',
                unsafe_allow_html=True,
            )
        elif final_recommendation == "SELL":
            st.markdown(
                f'<div class="recommendation-sell">{icon_svg("trending-down", "1.3rem")}SELL</div>',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="recommendation-hold">{icon_svg("minus-circle", "1.3rem")}HOLD</div>',
                unsafe_allow_html=True,
            )

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Gemini Recommendation", llm_recommendation or "N/A")
            if llm_confidence is not None:
                st.metric("Gemini Confidence", f"{llm_confidence:.2%}")
            elif state.get("confidence_score") is not None:
                st.metric("Confidence", f"{state['confidence_score']:.2%}")

        with col2:
            st.metric("Final Recommendation", final_recommendation or "N/A")
            st.metric("Risk Level", state.get("risk_level", "N/A"))

        with col3:
            st.metric("Validation", state.get("validation_status", "N/A"))
            if state.get("stop_loss"):
                st.metric("Stop Loss", f"${state['stop_loss']:.2f}")

        details_col1, details_col2 = st.columns(2)

        with details_col1:
            if state.get("llm_summary"):
                st.write("**Gemini Summary:**")
                st.write(state["llm_summary"])

            if state.get("llm_reasoning"):
                st.write("**Gemini Reasoning:**")
                for reason in state["llm_reasoning"]:
                    st.write(f"- {reason}")
            elif state.get("reasoning_chain"):
                st.write("**Reasoning:**")
                for reason in state["reasoning_chain"]:
                    st.write(f"- {reason}")

        with details_col2:
            if state.get("llm_decision_factors"):
                st.write("**Decision Factors:**")
                for factor in state["llm_decision_factors"]:
                    signal = factor.get("signal", "signal")
                    impact = factor.get("impact", "neutral")
                    evidence = factor.get("evidence", "N/A")
                    action = factor.get("action", "")
                    st.info(f"{signal.title()} | {impact} | {evidence} {action}".strip())

            if state.get("risk_factors"):
                st.write("**Risk Factors:**")
                for factor in state["risk_factors"]:
                    st.warning(factor)

        with st.expander("🧭 Recommendation Trace"):
            st.write("**LLM Source:**")
            st.write(state.get("llm_raw_response") or "No raw response stored.")
            if state.get("preliminary_recommendation"):
                st.write(f"**Preliminary Recommendation:** {state['preliminary_recommendation']}")
            if state.get("confidence_score") is not None:
                st.write(f"**Pipeline Confidence:** {state['confidence_score']:.2%}")
            if state.get("take_profit"):
                st.write(f"**Take Profit:** ${state['take_profit']:.2f}")
            if state.get("position_sizing"):
                allocation = state["position_sizing"].get("recommended_allocation", 0)
                st.write(f"**Allocation:** {allocation:.1%}")
    else:
        st.warning("No recommendation available")


def render_price_forecast(state):
    """Renders price forecast section."""
    section_title("crystal-ball", "Price Forecast", "blue")

    if state.get("price_forecast"):
        forecast = state["price_forecast"]
        current_price = forecast.get("current_price")

        if current_price:
            forecast_7d = forecast.get("forecast_7d")
            forecast_30d = forecast.get("forecast_30d")

            col1, col2 = st.columns(2)

            with col1:
                if forecast_7d:
                    change_7d = ((forecast_7d - current_price) / current_price) * 100
                    st.metric("7-Day Forecast", f"${forecast_7d:.2f}", delta=f"{change_7d:.2f}%")

            with col2:
                if forecast_30d:
                    change_30d = ((forecast_30d - current_price) / current_price) * 100
                    st.metric("30-Day Forecast", f"${forecast_30d:.2f}", delta=f"{change_30d:.2f}%")

            if forecast.get("confidence"):
                st.write(f"**Forecast Confidence:** {forecast['confidence']:.2%}")
    else:
        st.warning("No price forecast available")


def render_risk_metrics(state):
    """Renders risk metrics section."""
    section_title("shield", "Risk Metrics", "red")

    if state.get("risk_metrics"):
        metrics = state["risk_metrics"]

        col1, col2, col3 = st.columns(3)

        with col1:
            if metrics.get("volatility"):
                st.metric("Volatility", f"{metrics['volatility']:.2%}")
            if metrics.get("Sharpe_ratio"):
                st.metric("Sharpe Ratio", f"{metrics['Sharpe_ratio']:.2f}")

        with col2:
            if metrics.get("max_drawdown"):
                st.metric("Max Drawdown", f"{metrics['max_drawdown']:.2%}")
            if metrics.get("VaR_95"):
                st.metric("VaR (95%)", f"{metrics['VaR_95']:.2%}")

        with col3:
            if metrics.get("beta"):
                st.metric("Beta", f"{metrics['beta']:.2f}")
            if metrics.get("Sortino_ratio"):
                st.metric("Sortino Ratio", f"{metrics['Sortino_ratio']:.2f}")
    else:
        st.warning("No risk metrics available")


def render_execution_info(state):
    """Renders execution information."""
    with st.expander("🛠️ Execution Details"):
        if state.get("agent_execution_order"):
            st.write("**Agent Execution Order:**")
            for i, agent in enumerate(state["agent_execution_order"], 1):
                st.write(f"{i}. {agent}")

        if state.get("timestamps"):
            st.write("**Execution Timestamps:**")
            for agent, timestamp in state["timestamps"].items():
                st.write(f"- {agent}: {timestamp}")

        if state.get("errors"):
            st.write("**Errors:**")
            for error in state["errors"]:
                st.error(error)


def load_analysis_history(ticker=None, limit=10, user_id=None):
    """Load analysis history from MongoDB only, scoped to the logged-in user."""
    current_user = user_id or st.session_state.get("user_id")
    history = load_persistent_history(allow_local_fallback=False, user_id=current_user)
    if ticker:
        history = [item for item in history if item.get("ticker") == ticker.upper()]
    return history[:limit]


def render_recent_analyses_summary(current_state=None):
    """Renders a compact summary card for recent analyses on the home view."""
    section_title("cpu", "Recent Analyses", "teal")

    try:
        recent = load_analysis_history(limit=3, user_id=st.session_state.get("user_id"))
    except Exception as exc:
        st.error(f"Unable to load recent analyses: {exc}")
        return

    if current_state:
        recent = [
            {
                "ticker": current_state.get("ticker"),
                "final_recommendation": current_state.get("final_recommendation"),
                "risk_adjusted_recommendation": current_state.get("risk_adjusted_recommendation"),
                "llm_confidence": current_state.get("llm_confidence"),
                "updated_at": "Current session",
            }
        ] + recent
        recent = recent[:3]

    if not recent:
        store = MongoPipelineStore()
        if not store.available:
            st.info(
                "MongoDB is not connected, so saved analysis history is unavailable."
            )
        else:
            st.info("No saved analyses yet. Run an analysis to build your history.")
        return

    total_saved = len(recent)
    latest = recent[0]
    latest_ticker = latest.get("ticker", "N/A")
    latest_recommendation = (
        latest.get("final_recommendation")
        or latest.get("risk_adjusted_recommendation")
        or "N/A"
    )
    latest_confidence = latest.get("llm_confidence")

    buy_count = sum(
        1
        for item in recent
        if (item.get("final_recommendation") or item.get("risk_adjusted_recommendation")) == "BUY"
    )
    sell_count = sum(
        1
        for item in recent
        if (item.get("final_recommendation") or item.get("risk_adjusted_recommendation")) == "SELL"
    )
    hold_count = sum(
        1
        for item in recent
        if (item.get("final_recommendation") or item.get("risk_adjusted_recommendation")) == "HOLD"
    )

    card = st.container()
    with card:
        st.markdown("**Recent analyses overview**")
        metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)

        with metric_col1:
            st.metric("Recent Runs", total_saved)
        with metric_col2:
            st.metric("Latest Ticker", latest_ticker)
        with metric_col3:
            st.metric("Latest Decision", latest_recommendation)
        with metric_col4:
            st.metric(
                "Latest Confidence",
                f"{latest_confidence:.2%}" if latest_confidence is not None else "N/A",
            )

        st.caption(
            f"BUY: {buy_count} | SELL: {sell_count} | HOLD: {hold_count} | "
            f"Last saved: {latest.get('updated_at', 'N/A')}"
        )


def render_analysis_history(ticker):
    """Renders a history section for previous analyses."""
    section_title("clock", "Analysis History", "amber")

    history_limit = st.slider("History limit", min_value=5, max_value=50, value=10, step=5)
    history_ticker = st.text_input(
        "Filter by ticker",
        value=ticker or "",
        help="Leave blank to see all saved analyses",
    ).upper().strip()

    try:
        history = load_analysis_history(history_ticker if history_ticker else None, history_limit, user_id=st.session_state.get("user_id"))
    except Exception as exc:
        st.error(f"Unable to load history: {exc}")
        return

    if not history:
        st.info("No saved analyses found. Run an analysis first with MongoDB enabled.")
        return

    st.caption(f"Showing {len(history)} most recent saved analyses.")

    for item in history:
        with st.expander(
            f"{item.get('ticker', 'N/A')} | {item.get('risk_adjusted_recommendation', item.get('final_recommendation', 'N/A'))} | "
            f"{item.get('updated_at', 'N/A')}"
        ):
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**Ticker:** {item.get('ticker', 'N/A')}")
                st.write(f"**Final Recommendation:** {item.get('risk_adjusted_recommendation', item.get('final_recommendation', 'N/A'))}")
                st.write(f"**Risk Level:** {item.get('risk_level', 'N/A')}")
            with col2:
                st.write(f"**LLM Recommendation:** {item.get('llm_recommendation', 'N/A')}")
                llm_conf = item.get("llm_confidence")
                st.write(f"**LLM Confidence:** {llm_conf:.2%}" if llm_conf is not None else "**LLM Confidence:** N/A")
                st.write(f"**Validation:** {item.get('validation_status', 'N/A')}")
            with col3:
                conf = item.get("confidence_score")
                st.write(f"**Pipeline Confidence:** {conf:.2%}" if conf is not None else "**Pipeline Confidence:** N/A")
                st.write(f"**Saved At:** {item.get('updated_at', 'N/A')}")
                st.write("**Saved Result:** available")

            if item.get("llm_summary"):
                st.write("**Summary:**")
                st.write(item.get("llm_summary"))

            if item.get("llm_reasoning"):
                st.write("**Reasoning:**")
                for reason in item.get("llm_reasoning", []):
                    st.write(f"- {reason}")

            if item.get("llm_decision_factors"):
                st.write("**Decision Factors:**")
                for factor in item.get("llm_decision_factors", []):
                    st.write(
                        f"- {factor.get('signal', 'signal')} | {factor.get('impact', 'neutral')} | "
                        f"{factor.get('evidence', 'N/A')}"
                    )

            if item.get("risk_factors"):
                st.write("**Risk Factors:**")
                for factor in item.get("risk_factors", []):
                    st.warning(factor)


def render_beginner_recent_analyses():
    """Show automatic saved history with first-time-investor wording."""
    section_title("cpu", "Your Recent Analyses", "teal", "Saved automatically in MongoDB")
    recent = load_analysis_history(limit=3, user_id=st.session_state.get("user_id"))
    if not recent:
        st.info("Your first completed analysis will be saved here automatically. Choose a ticker and select Analyze Stock to begin.")
        return

    latest = recent[0]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Saved analyses", len(recent))
    col2.metric("Latest ticker", latest.get("ticker", "N/A"))
    col3.metric("Latest view", latest.get("recommendation", "N/A"))
    confidence = latest.get("confidence")
    col4.metric("Confidence", f"{confidence:.0%}" if confidence is not None else "Not available")
    st.caption("Saved records keep only your question, the latest view, confidence, summary, and up to three risk reminders. Signals are research, not trading instructions.")


def render_beginner_history():
    """Provide a compact MongoDB-backed history view for new investors."""
    section_title("clock", "Your Past Analyses", "amber", "Compare your research without an account or database")
    all_history = load_analysis_history(limit=50, user_id=st.session_state.get("user_id"))
    if not all_history:
        st.info("No saved analyses yet. Complete an analysis and it will appear here automatically.")
        return

    tickers = sorted({item.get("ticker") for item in all_history if item.get("ticker")})
    selection = st.selectbox("Show analyses for", ["All tickers"] + tickers, key="beginner_history_ticker")
    history = all_history if selection == "All tickers" else load_analysis_history(selection, 10, user_id=st.session_state.get("user_id"))
    st.caption("New analyses replace older entries for the same ticker, keeping this list clear and current.")
    for item in history:
        date = item.get("saved_at", "").replace("T", " ")[:16]
        with st.expander(f"{item.get('ticker', 'N/A')} | {item.get('recommendation', 'N/A')} | {date} UTC"):
            col1, col2, col3 = st.columns(3)
            col1.write(f"**Latest view:** {item.get('recommendation', 'N/A')}")
            col1.write(f"**Risk level:** {item.get('risk_level', 'N/A')}")
            confidence = item.get("confidence")
            col2.write(f"**Confidence:** {confidence:.0%}" if confidence is not None else "**Confidence:** Not available")
            col2.write(f"**Your question:** {item.get('question', 'General stock review')}")
            col3.write(f"**Saved:** {date} UTC")
            col3.write("**Stored in:** MongoDB")
            st.write("**What this means:**")
            st.write(item.get("summary", "No summary was available."))
            if item.get("direct_answer"):
                st.write("**Answer to your question:**")
                st.info(item["direct_answer"])
            if item.get("risk_factors"):
                st.write("**Things to keep in mind:**")
                for factor in item["risk_factors"]:
                    st.warning(factor)


def render_beginner_guide():
    """Explain the dashboard's measures in plain language for new investors."""
    with st.expander("📖 How to read this analysis", expanded=False):
        st.write(
            "This dashboard combines several clues. No single measure can predict the future, "
            "so read the recommendation together with the risk warnings and your own plan."
        )
        guide = {
            "Price and market data": "Current price is the latest available share price. Market cap is the total market value of the company. The 52-week high and low show the recent price range, not a target price.",
            "Sentiment": "News sentiment runs from -1 (mostly negative) to +1 (mostly positive). Sentiment confidence tells how strongly the language model detected that tone; it is not the probability that the share price will rise.",
            "RSI": "Relative Strength Index ranges from 0 to 100. Around 70 or above can mean recent buying was strong, while around 30 or below can mean recent selling was strong. It can stay high or low during a trend.",
            "MACD": "Moving Average Convergence Divergence compares short- and long-term price momentum. A positive value can signal stronger recent momentum; it is not a guarantee of profit.",
            "SMA and EMA": "Simple and exponential moving averages smooth prices. A price above an average can suggest an upward trend; EMA reacts faster to new prices than SMA.",
            "Forecast": "The 7-day and 30-day forecasts are model estimates based on historical patterns. Forecast confidence describes model certainty, not investment certainty.",
            "Volatility": "The typical size of price movements. Higher volatility means a bumpier ride and a greater chance of large gains or losses.",
            "Sharpe ratio": "Return compared with volatility. Higher is generally better, but it depends on the period and the benchmark used.",
            "Sortino ratio": "Like Sharpe, but focuses on harmful downside movements instead of all price movement. Higher is generally better.",
            "Maximum drawdown": "The largest historical fall from a previous peak to a later low. It helps answer: how painful could a past decline have been?",
            "Value at Risk (95%)": "An estimate of a bad one-day loss threshold based on history. A 95% VaR does not mean losses cannot be larger, and it is not a promise.",
            "Beta": "How strongly the stock has moved compared with the broad market. Around 1 means similar movement, above 1 usually means larger swings, and below 1 usually means smaller swings.",
            "Confidence and recommendation": "Confidence measures how consistently the available evidence supports the model's view. BUY, HOLD, and SELL are research signals for review, not instructions or guarantees.",
        }
        for measure, explanation in guide.items():
            st.markdown(f"**{measure}:** {explanation}")
        st.caption("Educational research only. Market data can be delayed or incomplete, and this tool does not replace professional financial advice.")


def render_analysis_page(state):
    """Render one analysis view selected from the sidebar navigation."""
    page_options = {
        "💼 Portfolio Management": render_portfolio_manager,
        "📊 Stock Data": render_stock_data,
        "🏢 Company Info": render_company_info,
        "💬 Sentiment": render_sentiment_analysis,
        "📈 Technical": render_technical_indicators,
        "🎯 Recommendation": render_recommendation,
        "🧩 Portfolio Fit": render_portfolio_fit,
        "🚨 Alerts": render_alerts,
        "🔮 Forecast": render_price_forecast,
        "🛡️ Risk": render_risk_metrics,
        "🕓 History": lambda current_state: render_beginner_history(),
    }
    selected_page = st.sidebar.radio(
        "Analysis pages",
        options=list(page_options),
        key="analysis_page",
        help="Choose which part of the completed analysis to view.",
    )
    page_options[selected_page](state)


def main():
    """Main Streamlit application."""
    load_theme()
    render_header()

    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = None
    if "last_ticker" not in st.session_state:
        st.session_state.last_ticker = None

    ticker, use_conditional, investor_profile, alert_rules, analyze_button = render_sidebar()
    user_query, chat_submitted = render_question_chat()
    analyze_button = analyze_button or chat_submitted

    if not st.session_state.get("authenticated"):
        st.info("Please sign in to continue using the dashboard.")
        st.stop()

    if analyze_button and ticker:
        if not st.session_state.get("trade_confirmed"):
            st.warning("Please confirm the educational-only trade disclaimer before running an analysis.")
            analyze_button = False

        if analyze_button and not check_rate_limit(st.session_state.get("user_id", "guest"), limit=20, window_seconds=60):
            st.warning("Rate limit reached. Please wait before another analysis run.")
            analyze_button = False

        if analyze_button:
            with st.spinner(f"Analyzing {ticker}... This may take a moment."):
                try:
                    result = run_investment_analysis(
                        ticker=ticker,
                        user_query=user_query if user_query else None,
                        use_conditional=use_conditional,
                        use_mongodb=True,
                        investor_profile=investor_profile,
                        alert_rules=alert_rules,
                        user_id=st.session_state.get("user_id"),
                    )

                    st.session_state.analysis_result = result
                    st.session_state.last_ticker = ticker
                    try:
                        save_analysis_summary(result, allow_local_fallback=False, user_id=st.session_state.get("user_id"))
                        log_audit_event(st.session_state.get("user_id"), "analysis_run", {"ticker": ticker, "user_query": user_query}, "success")
                        st.success(f"Analysis completed for {ticker} and saved to MongoDB.")
                    except OSError as history_error:
                        logger.error(f"Unable to save MongoDB history: {history_error}")
                        st.success(f"Analysis completed for {ticker}!")
                        st.error("The analysis could not be saved to MongoDB.")

                except Exception as e:
                    log_audit_event(st.session_state.get("user_id"), "analysis_run", {"ticker": ticker, "error": str(e)}, "failure")
                    st.error(f"Analysis failed: {str(e)}")
                    logger.error(f"Streamlit analysis error: {str(e)}")

    render_trade_confirmation_dialog()
    render_beginner_recent_analyses()
    render_beginner_guide()

    if st.session_state.analysis_result:
        state = st.session_state.analysis_result

        section_title("search", f"Analysis for {state['ticker']}", "teal")

        render_analysis_page(state)
    else:
        selected_page = st.sidebar.radio(
            "Dashboard pages",
            options=["💼 Portfolio Management"],
            key="dashboard_page",
        )
        if selected_page == "💼 Portfolio Management":
            render_portfolio_manager()


if __name__ == "__main__":
    main()
