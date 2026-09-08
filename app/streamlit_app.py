"""
Streamlit UI for the Investment Agentic AI system.
Provides an interactive dashboard for investment analysis.
"""

import sys
import base64
import os
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agents.graph import run_investment_analysis  # noqa: E402
from src.pipeline import MongoPipelineStore  # noqa: E402
from src.pipeline.local_history import load_local_history, save_analysis_summary  # noqa: E402

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


def render_header():
    """Renders the application header."""
    hero_candidates = ["market-hero.jpg", "market-hero.jpeg", "market-hero.png", "market-hero.svg"]
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
        ticker = st.sidebar.text_input(
            "Custom ticker symbol",
            placeholder="e.g., NFLX, BABA, CSE.N0000",
            help="Enter the exchange ticker used by Yahoo Finance.",
        ).upper().strip()
    else:
        ticker = ticker_options[selected_ticker]
        st.sidebar.caption(f"Selected: **{ticker}**")

    user_query = st.sidebar.text_area(
        "💬 Your Question",
        placeholder="e.g., Should I buy this stock?",
        help="Ask a specific question about the stock",
    )

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

    with st.sidebar.expander("⚙️ Advanced Options"):
        use_conditional = st.checkbox(
            "Use Conditional Routing",
            value=False,
            help="Enable dynamic agent routing",
        )
        use_mongodb = st.checkbox(
            "Save full workflow history to MongoDB",
            value=False,
            help="Optional. MongoDB requires a configured connection and a Thread ID for each saved workflow.",
        )
        thread_id = ""
        if use_mongodb:
            thread_id = st.text_input(
                "Thread ID",
                value="",
                help="Choose a unique label for this MongoDB workflow, for example: aapl-review-september.",
            )
            if not os.getenv("MONGODB_URI"):
                st.warning("MongoDB needs MONGODB_URI in your .env file. Local history still saves automatically without it.")

    analyze_button = st.sidebar.button(
        "🚀 Analyze Stock",
        type="primary",
        use_container_width=True,
    )

    return ticker, user_query, use_conditional, use_mongodb, thread_id, investor_profile, analyze_button


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
        marker={"colors": ["#40d1c8", "#7ca7ff", "#f5b84b"]}, textinfo="label+percent",
    )])
    chart.update_layout(height=300, margin=dict(l=15, r=15, t=15, b=15), paper_bgcolor="rgba(0,0,0,0)", font_color="#edf3fb")
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
                    "bar": {"color": "#40d1c8"},
                    "steps": [
                        {"range": [-1, -0.33], "color": "#ff7070"},
                        {"range": [-0.33, 0.33], "color": "#a7b8cf"},
                        {"range": [0.33, 1], "color": "#49d39c"},
                    ],
                    "threshold": {
                        "line": {"color": "#f5b84b", "width": 4},
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

        if state.get("news_summary"):
            st.write("**News Summary:**")
            st.write(state["news_summary"])

        if state.get("key_events"):
            st.write("**Key Events:**")
            for event in state["key_events"]:
                st.write(f"- {event}")
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


def load_analysis_history(ticker=None, limit=10):
    """Loads automatic on-device history; no database configuration required."""
    history = load_local_history()
    if ticker:
        history = [item for item in history if item.get("ticker") == ticker.upper()]
    return history[:limit]


def render_recent_analyses_summary(current_state=None):
    """Renders a compact summary card for recent analyses on the home view."""
    section_title("cpu", "Recent Analyses", "teal")

    try:
        recent = load_analysis_history(limit=3)
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
                "MongoDB is not connected, so saved analysis history is unavailable. "
                "Run an analysis and enable MongoDB persistence to build your history."
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
        history = load_analysis_history(history_ticker if history_ticker else None, history_limit)
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
    section_title("cpu", "Your Recent Analyses", "teal", "Saved automatically on this computer")
    recent = load_analysis_history(limit=3)
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
    """Provide a compact, no-database history view for new investors."""
    section_title("clock", "Your Past Analyses", "amber", "Compare your research without an account or database")
    all_history = load_analysis_history(limit=50)
    if not all_history:
        st.info("No saved analyses yet. Complete an analysis and it will appear here automatically.")
        return

    tickers = sorted({item.get("ticker") for item in all_history if item.get("ticker")})
    selection = st.selectbox("Show analyses for", ["All tickers"] + tickers, key="beginner_history_ticker")
    history = all_history if selection == "All tickers" else load_analysis_history(selection, 10)
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
            col3.write("**Stored on:** this computer")
            st.write("**What this means:**")
            st.write(item.get("summary", "No summary was available."))
            if item.get("risk_factors"):
                st.write("**Things to keep in mind:**")
                for factor in item["risk_factors"]:
                    st.warning(factor)


def main():
    """Main Streamlit application."""
    load_theme()
    render_header()

    ticker, user_query, use_conditional, use_mongodb, thread_id, investor_profile, analyze_button = render_sidebar()

    if "analysis_result" not in st.session_state:
        st.session_state.analysis_result = None
    if "last_ticker" not in st.session_state:
        st.session_state.last_ticker = None

    if analyze_button and ticker:
        with st.spinner(f"Analyzing {ticker}... This may take a moment."):
            try:
                if use_mongodb and not os.getenv("MONGODB_URI"):
                    st.warning("MongoDB is not configured, so this analysis will be saved only in automatic local history.")
                    use_mongodb = False
                if use_mongodb and not thread_id.strip():
                    st.warning("Enter a Thread ID to save this workflow to MongoDB. This analysis will still be saved in automatic local history.")
                    use_mongodb = False

                result = run_investment_analysis(
                    ticker=ticker,
                    user_query=user_query if user_query else None,
                    use_conditional=use_conditional,
                    use_mongodb=use_mongodb,
                    thread_id=thread_id.strip() if use_mongodb else None,
                    investor_profile=investor_profile,
                )

                st.session_state.analysis_result = result
                st.session_state.last_ticker = ticker
                try:
                    save_analysis_summary(result)
                    st.success(f"Analysis completed for {ticker} and saved to Your Past Analyses.")
                except OSError as history_error:
                    logger.error(f"Unable to save local history: {history_error}")
                    st.success(f"Analysis completed for {ticker}!")
                    st.warning("Your result could not be saved to local history on this computer.")

            except Exception as e:
                st.error(f"Analysis failed: {str(e)}")
                logger.error(f"Streamlit analysis error: {str(e)}")

    render_beginner_recent_analyses()

    if st.session_state.analysis_result:
        state = st.session_state.analysis_result

        section_title("search", f"Analysis for {state['ticker']}", "teal")

        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs(
            [
                "📊 Stock Data",
                "🏢 Company Info",
                "💬 Sentiment",
                "📈 Technical",
                "🎯 Recommendation",
                "🧩 Portfolio Fit",
                "🔮 Forecast",
                "🛡️ Risk",
                "🕓 History",
            ]
        )

        with tab1:
            render_stock_data(state)

        with tab2:
            render_company_info(state)

        with tab3:
            render_sentiment_analysis(state)

        with tab4:
            render_technical_indicators(state)

        with tab5:
            render_recommendation(state)

        with tab6:
            render_portfolio_fit(state)

        with tab7:
            render_price_forecast(state)

        with tab8:
            render_risk_metrics(state)

        with tab9:
            render_beginner_history()

        render_execution_info(state)
    else:
        st.info("Enter a stock ticker and click 'Analyze Stock' to begin")


if __name__ == "__main__":
    main()
