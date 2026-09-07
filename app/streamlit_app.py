"""
Streamlit UI for the Investment Agentic AI system.
Provides an interactive dashboard for investment analysis.
"""

import sys
from pathlib import Path
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.agents.graph import run_investment_analysis, print_analysis_summary
from src.pipeline import MongoPipelineStore
from loguru import logger


# Page configuration
st.set_page_config(
    page_title="InvestSage - AI Investment Agent",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .recommendation-buy {
        background-color: #d4edda;
        color: #155724;
        padding: 1rem;
        border-radius: 0.5rem;
        font-weight: bold;
    }
    .recommendation-sell {
        background-color: #f8d7da;
        color: #721c24;
        padding: 1rem;
        border-radius: 0.5rem;
        font-weight: bold;
    }
    .recommendation-hold {
        background-color: #fff3cd;
        color: #856404;
        padding: 1rem;
        border-radius: 0.5rem;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)


def render_header():
    """Renders the application header."""
    st.markdown('<h1 class="main-header">🤖 InvestSage</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">AI-Powered Investment Decision Making</p>', unsafe_allow_html=True)
    st.markdown("---")


def render_sidebar():
    """Renders the sidebar with input controls."""
    st.sidebar.header("📊 Analysis Configuration")
    
    # Ticker input
    ticker = st.sidebar.text_input(
        "Stock Ticker",
        value="AAPL",
        help="Enter stock ticker symbol (e.g., AAPL, GOOGL, MSFT)"
    ).upper()
    
    # User query
    user_query = st.sidebar.text_area(
        "Your Question",
        placeholder="e.g., Should I buy this stock?",
        help="Ask a specific question about the stock"
    )
    
    # Advanced options
    with st.sidebar.expander("Advanced Options"):
        use_conditional = st.checkbox(
            "Use Conditional Routing",
            value=False,
            help="Enable dynamic agent routing"
        )
        use_mongodb = st.checkbox(
            "Use MongoDB Persistence",
            value=False,
            help="Enable state persistence with MongoDB"
        )
        thread_id = st.text_input(
            "Thread ID",
            value="",
            help="Required if MongoDB is enabled"
        )
    
    # Analyze button
    analyze_button = st.sidebar.button(
        "🔍 Analyze Stock",
        type="primary",
        use_container_width=True
    )
    
    return ticker, user_query, use_conditional, use_mongodb, thread_id, analyze_button


def render_stock_data(state):
    """Renders stock data section."""
    st.subheader("📈 Stock Data")
    
    if state.get('stock_data'):
        data = state['stock_data']
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Current Price",
                f"${data.get('current_price', 'N/A'):.2f}" if data.get('current_price') else "N/A",
                delta=f"{((data.get('current_price', 0) - data.get('previous_close', 0)) / data.get('previous_close', 1) * 100):.2f}%" if data.get('current_price') and data.get('previous_close') else None
            )
        
        with col2:
            st.metric(
                "Market Cap",
                f"${data.get('market_cap', 0) / 1e9:.1f}B" if data.get('market_cap') else "N/A"
            )
        
        with col3:
            st.metric(
                "52W High",
                f"${data.get('52_week_high', 'N/A'):.2f}" if data.get('52_week_high') else "N/A"
            )
        
        with col4:
            st.metric(
                "52W Low",
                f"${data.get('52_week_low', 'N/A'):.2f}" if data.get('52_week_low') else "N/A"
            )
        
        # Additional info
        with st.expander("Additional Stock Information"):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Open:** ${data.get('open', 'N/A')}")
                st.write(f"**High:** ${data.get('high', 'N/A')}")
                st.write(f"**Low:** ${data.get('low', 'N/A')}")
            with col2:
                st.write(f"**Volume:** {data.get('volume', 'N/A'):,}" if data.get('volume') else "N/A")
                st.write(f"**Avg Volume:** {data.get('avg_volume', 'N/A'):,}" if data.get('avg_volume') else "N/A")
    else:
        st.warning("No stock data available")


def render_company_info(state):
    """Renders company information section."""
    st.subheader("🏢 Company Information")
    
    if state.get('company_info'):
        info = state['company_info']
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Name:** {info.get('name', 'N/A')}")
            st.write(f"**Sector:** {info.get('sector', 'N/A')}")
            st.write(f"**Industry:** {info.get('industry', 'N/A')}")
            st.write(f"**Exchange:** {info.get('exchange', 'N/A')}")
        
        with col2:
            st.write(f"**P/E Ratio:** {info.get('pe_ratio', 'N/A'):.2f}" if info.get('pe_ratio') else "N/A")
            st.write(f"**Beta:** {info.get('beta', 'N/A'):.2f}" if info.get('beta') else "N/A")
            st.write(f"**EPS:** ${info.get('eps', 'N/A'):.2f}" if info.get('eps') else "N/A")
            st.write(f"**Dividend Yield:** {info.get('dividend_yield', 'N/A'):.2%}" if info.get('dividend_yield') else "N/A")
        
        if info.get('description'):
            with st.expander("Business Summary"):
                st.write(info.get('description'))
    else:
        st.warning("No company information available")


def render_sentiment_analysis(state):
    """Renders sentiment analysis section."""
    st.subheader("💭 Sentiment Analysis")
    
    if state.get('sentiment_score') is not None:
        score = state['sentiment_score']
        confidence = state.get('sentiment_confidence', 0)
        
        # Sentiment gauge
        fig = go.Figure(go.Indicator(
            mode = "gauge+number",
            value = score,
            domain = {'x': [0, 1], 'y': [0, 1]},
            title = {'text': "Sentiment Score"},
            gauge = {
                'axis': {'range': [-1, 1]},
                'bar': {'color': "darkblue"},
                'steps': [
                    {'range': [-1, -0.33], 'color': "lightcoral"},
                    {'range': [-0.33, 0.33], 'color': "lightgray"},
                    {'range': [0.33, 1], 'color': "lightgreen"}
                ],
                'threshold': {
                    'line': {'color': "red", 'width': 4},
                    'thickness': 0.75,
                    'value': 0
                }
            }
        ))
        
        st.plotly_chart(fig, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Confidence", f"{confidence:.2%}")
        with col2:
            sentiment_label = "Positive" if score > 0.3 else "Negative" if score < -0.3 else "Neutral"
            st.metric("Sentiment", sentiment_label)
        
        if state.get('news_summary'):
            st.write("**News Summary:**")
            st.write(state['news_summary'])
        
        if state.get('key_events'):
            st.write("**Key Events:**")
            for event in state['key_events']:
                st.write(f"- {event}")
    else:
        st.warning("No sentiment analysis available")


def render_technical_indicators(state):
    """Renders technical indicators section."""
    st.subheader("📊 Technical Indicators")
    
    if state.get('technical_indicators'):
        indicators = state['technical_indicators']
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("RSI", f"{indicators.get('RSI', 'N/A'):.2f}" if indicators.get('RSI') else "N/A")
            st.metric("MACD", f"{indicators.get('MACD', 'N/A'):.2f}" if indicators.get('MACD') else "N/A")
        
        with col2:
            st.metric("SMA (20)", f"${indicators.get('SMA_20', 'N/A'):.2f}" if indicators.get('SMA_20') else "N/A")
            st.metric("SMA (50)", f"${indicators.get('SMA_50', 'N/A'):.2f}" if indicators.get('SMA_50') else "N/A")
        
        with col3:
            st.metric("EMA (12)", f"${indicators.get('EMA_12', 'N/A'):.2f}" if indicators.get('EMA_12') else "N/A")
            st.metric("EMA (26)", f"${indicators.get('EMA_26', 'N/A'):.2f}" if indicators.get('EMA_26') else "N/A")
    else:
        st.warning("No technical indicators available")


def render_recommendation(state):
    """Renders the investment recommendation section."""
    st.subheader("🎯 Investment Recommendation")
    
    final_recommendation = state.get('final_recommendation') or state.get('risk_adjusted_recommendation')
    llm_recommendation = state.get('llm_recommendation')
    llm_confidence = state.get('llm_confidence')

    if final_recommendation or llm_recommendation:
        if final_recommendation == 'BUY':
            st.markdown('<div class="recommendation-buy">BUY</div>', unsafe_allow_html=True)
        elif final_recommendation == 'SELL':
            st.markdown('<div class="recommendation-sell">SELL</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="recommendation-hold">HOLD</div>', unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Gemini Recommendation", llm_recommendation or "N/A")
            if llm_confidence is not None:
                st.metric("Gemini Confidence", f"{llm_confidence:.2%}")
            elif state.get('confidence_score') is not None:
                st.metric("Confidence", f"{state['confidence_score']:.2%}")

        with col2:
            st.metric("Final Recommendation", final_recommendation or "N/A")
            st.metric("Risk Level", state.get('risk_level', 'N/A'))

        with col3:
            st.metric("Validation", state.get('validation_status', 'N/A'))
            if state.get('stop_loss'):
                st.metric("Stop Loss", f"${state['stop_loss']:.2f}")

        details_col1, details_col2 = st.columns(2)

        with details_col1:
            if state.get('llm_summary'):
                st.write("**Gemini Summary:**")
                st.write(state['llm_summary'])

            if state.get('llm_reasoning'):
                st.write("**Gemini Reasoning:**")
                for reason in state['llm_reasoning']:
                    st.write(f"- {reason}")
            elif state.get('reasoning_chain'):
                st.write("**Reasoning:**")
                for reason in state['reasoning_chain']:
                    st.write(f"- {reason}")

        with details_col2:
            if state.get('llm_decision_factors'):
                st.write("**Decision Factors:**")
                for factor in state['llm_decision_factors']:
                    signal = factor.get('signal', 'signal')
                    impact = factor.get('impact', 'neutral')
                    evidence = factor.get('evidence', 'N/A')
                    action = factor.get('action', '')
                    st.info(f"{signal.title()} | {impact} | {evidence} {action}".strip())

            if state.get('risk_factors'):
                st.write("**Risk Factors:**")
                for factor in state['risk_factors']:
                    st.warning(factor)

        with st.expander("Recommendation Trace"):
            st.write("**LLM Source:**")
            st.write(state.get('llm_raw_response') or "No raw response stored.")
            if state.get('preliminary_recommendation'):
                st.write(f"**Preliminary Recommendation:** {state['preliminary_recommendation']}")
            if state.get('confidence_score') is not None:
                st.write(f"**Pipeline Confidence:** {state['confidence_score']:.2%}")
            if state.get('take_profit'):
                st.write(f"**Take Profit:** ${state['take_profit']:.2f}")
            if state.get('position_sizing'):
                allocation = state['position_sizing'].get('recommended_allocation', 0)
                st.write(f"**Allocation:** {allocation:.1%}")
    else:
        st.warning("No recommendation available")


def render_price_forecast(state):
    """Renders price forecast section."""
    st.subheader("🔮 Price Forecast")
    
    if state.get('price_forecast'):
        forecast = state['price_forecast']
        current_price = forecast.get('current_price')
        
        if current_price:
            forecast_7d = forecast.get('forecast_7d')
            forecast_30d = forecast.get('forecast_30d')
            
            col1, col2 = st.columns(2)
            
            with col1:
                if forecast_7d:
                    change_7d = ((forecast_7d - current_price) / current_price) * 100
                    st.metric(
                        "7-Day Forecast",
                        f"${forecast_7d:.2f}",
                        delta=f"{change_7d:.2f}%"
                    )
            
            with col2:
                if forecast_30d:
                    change_30d = ((forecast_30d - current_price) / current_price) * 100
                    st.metric(
                        "30-Day Forecast",
                        f"${forecast_30d:.2f}",
                        delta=f"{change_30d:.2f}%"
                    )
            
            if forecast.get('confidence'):
                st.write(f"**Forecast Confidence:** {forecast['confidence']:.2%}")
    else:
        st.warning("No price forecast available")


def render_risk_metrics(state):
    """Renders risk metrics section."""
    st.subheader("⚠️ Risk Metrics")
    
    if state.get('risk_metrics'):
        metrics = state['risk_metrics']
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if metrics.get('volatility'):
                st.metric("Volatility", f"{metrics['volatility']:.2%}")
            if metrics.get('Sharpe_ratio'):
                st.metric("Sharpe Ratio", f"{metrics['Sharpe_ratio']:.2f}")
        
        with col2:
            if metrics.get('max_drawdown'):
                st.metric("Max Drawdown", f"{metrics['max_drawdown']:.2%}")
            if metrics.get('VaR_95'):
                st.metric("VaR (95%)", f"{metrics['VaR_95']:.2%}")
        
        with col3:
            if metrics.get('beta'):
                st.metric("Beta", f"{metrics['beta']:.2f}")
            if metrics.get('Sortino_ratio'):
                st.metric("Sortino Ratio", f"{metrics['Sortino_ratio']:.2f}")
    else:
        st.warning("No risk metrics available")


def render_execution_info(state):
    """Renders execution information."""
    with st.expander("🔧 Execution Details"):
        if state.get('agent_execution_order'):
            st.write("**Agent Execution Order:**")
            for i, agent in enumerate(state['agent_execution_order'], 1):
                st.write(f"{i}. {agent}")
        
        if state.get('timestamps'):
            st.write("**Execution Timestamps:**")
            for agent, timestamp in state['timestamps'].items():
                st.write(f"- {agent}: {timestamp}")
        
        if state.get('errors'):
            st.write("**Errors:**")
            for error in state['errors']:
                st.error(error)


def load_analysis_history(ticker=None, limit=10):
    """Loads recent analysis runs from MongoDB."""
    store = MongoPipelineStore()
    database = store.db
    if not store.available or database is None:
        return []

    query = {}
    if ticker:
        query["ticker"] = ticker.upper()

    cursor = (
        database.analysis_runs
        .find(query)
        .sort("updated_at", -1)
        .limit(limit)
    )
    return list(cursor)


def render_recent_analyses_summary(current_state=None):
    """Renders a compact summary card for recent analyses on the home view."""
    st.subheader("🧾 Recent Analyses")

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
    latest_recommendation = latest.get("final_recommendation") or latest.get("risk_adjusted_recommendation") or "N/A"
    latest_confidence = latest.get("llm_confidence")

    buy_count = sum(1 for item in recent if (item.get("final_recommendation") or item.get("risk_adjusted_recommendation")) == "BUY")
    sell_count = sum(1 for item in recent if (item.get("final_recommendation") or item.get("risk_adjusted_recommendation")) == "SELL")
    hold_count = sum(1 for item in recent if (item.get("final_recommendation") or item.get("risk_adjusted_recommendation")) == "HOLD")

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
            st.metric("Latest Confidence", f"{latest_confidence:.2%}" if latest_confidence is not None else "N/A")

        st.caption(
            f"BUY: {buy_count} | SELL: {sell_count} | HOLD: {hold_count} | "
            f"Last saved: {latest.get('updated_at', 'N/A')}"
        )


def render_analysis_history(ticker):
    """Renders a history section for previous analyses."""
    st.subheader("🕘 Analysis History")

    history_limit = st.slider("History limit", min_value=5, max_value=50, value=10, step=5)
    history_ticker = st.text_input(
        "Filter by ticker",
        value=ticker or "",
        help="Leave blank to see all saved analyses"
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
                llm_conf = item.get('llm_confidence')
                st.write(f"**LLM Confidence:** {llm_conf:.2%}" if llm_conf is not None else "**LLM Confidence:** N/A")
                st.write(f"**Validation:** {item.get('validation_status', 'N/A')}")
            with col3:
                conf = item.get('confidence_score')
                st.write(f"**Pipeline Confidence:** {conf:.2%}" if conf is not None else "**Pipeline Confidence:** N/A")
                st.write(f"**Saved At:** {item.get('updated_at', 'N/A')}")
                st.write("**Saved Result:** available")

            if item.get('llm_summary'):
                st.write("**Summary:**")
                st.write(item.get('llm_summary'))

            if item.get('llm_reasoning'):
                st.write("**Reasoning:**")
                for reason in item.get('llm_reasoning', []):
                    st.write(f"- {reason}")

            if item.get('llm_decision_factors'):
                st.write("**Decision Factors:**")
                for factor in item.get('llm_decision_factors', []):
                    st.write(
                        f"- {factor.get('signal', 'signal')} | {factor.get('impact', 'neutral')} | "
                        f"{factor.get('evidence', 'N/A')}"
                    )

            if item.get('risk_factors'):
                st.write("**Risk Factors:**")
                for factor in item.get('risk_factors', []):
                    st.warning(factor)


def main():
    """Main Streamlit application."""
    render_header()
    
    # Render sidebar
    ticker, user_query, use_conditional, use_mongodb, thread_id, analyze_button = render_sidebar()
    
    # Initialize session state
    if 'analysis_result' not in st.session_state:
        st.session_state.analysis_result = None
    if 'last_ticker' not in st.session_state:
        st.session_state.last_ticker = None

    # Run analysis when button is clicked
    if analyze_button and ticker:
        with st.spinner(f"Analyzing {ticker}... This may take a moment."):
            try:
                # Validate MongoDB requirements
                if use_mongodb and not thread_id:
                    st.error("Thread ID is required when MongoDB is enabled")
                    st.stop()
                
                # Run analysis
                result = run_investment_analysis(
                    ticker=ticker,
                    user_query=user_query if user_query else None,
                    use_conditional=use_conditional,
                    use_mongodb=use_mongodb,
                    thread_id=thread_id if use_mongodb else None
                )
                
                st.session_state.analysis_result = result
                st.session_state.last_ticker = ticker
                
                st.success(f"Analysis completed for {ticker}!")
                
            except Exception as e:
                st.error(f"Analysis failed: {str(e)}")
                logger.error(f"Streamlit analysis error: {str(e)}")

    # Home view summary
    render_recent_analyses_summary(st.session_state.analysis_result)
    
    # Display results if available
    if st.session_state.analysis_result:
        state = st.session_state.analysis_result
        
        # Display ticker
        st.markdown(f"### Analysis for: {state['ticker']}")
        
        # Create tabs
        tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
            "📈 Stock Data", "🏢 Company Info", "💭 Sentiment", 
            "📊 Technical", "🎯 Recommendation", "🔮 Forecast", "⚠️ Risk", "🕘 History"
        ])
        
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
            render_price_forecast(state)
        
        with tab7:
            render_risk_metrics(state)

        with tab8:
            render_analysis_history(state.get('ticker'))
        
        # Execution info at bottom
        render_execution_info(state)
    
    else:
        st.info("👈 Enter a stock ticker and click 'Analyze Stock' to begin")


if __name__ == "__main__":
    main()
