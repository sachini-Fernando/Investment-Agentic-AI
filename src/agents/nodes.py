"""
Agent nodes for the Investment Agentic AI system.
Contains 4 agents:
1. Data Acquisition & IR Agent
2. Sentiment & NLP Analysis Agent
3. Financial Reasoning & LLM Agent
4. Risk Assessment & Validation Agent
"""

from typing import Dict, Any, Optional
from datetime import datetime
from loguru import logger
from .state import InvestmentState
from ..tools.data_tools import (
    fetch_stock_data,
    fetch_historical_prices,
    fetch_company_info,
    fetch_financial_statements,
    fetch_news_articles,
    perform_ir_search
)
from ..tools.sentiment_tools import analyze_all_sentiment
from ..tools.quant_tools import (
    calculate_technical_indicators,
    calculate_risk_metrics,
    forecast_price_lstm,
    forecast_price_arima,
    perform_fundamental_analysis,
    calculate_position_size
)
from ..tools.llm_tools import generate_investment_recommendation
from ..tools.portfolio_tools import build_portfolio_insights

# ============================================
# FIX: Import serialization helper
# ============================================
from ..utils.serialization import clean_state_for_serialization


# ============================================================================
# AGENT 1: DATA ACQUISITION & IR AGENT
# ============================================================================
def data_acquisition_agent(state: InvestmentState) -> InvestmentState:
    """
    Data Acquisition & IR Agent
    Fetches stock data, financial statements, news articles, and performs IR search.
    
    Responsibilities:
    - Fetch real-time and historical stock data
    - Retrieve company financial statements
    - Scrape news articles about the company
    - Perform Information Retrieval search for relevant data
    """
    logger.info(f"Data Acquisition Agent processing ticker: {state['ticker']}")
    
    try:
        # Initialize execution tracking
        if state['agent_execution_order'] is None:
            state['agent_execution_order'] = []
        if state['timestamps'] is None:
            state['timestamps'] = {}
        if state['errors'] is None:
            state['errors'] = []
        
        # Record execution
        state['agent_execution_order'].append('data_acquisition_agent')
        state['timestamps']['data_acquisition_agent'] = datetime.now().isoformat()
        
        # Fetch actual data using data_tools
        ticker = state['ticker']
        
        # Fetch stock data
        state['stock_data'] = fetch_stock_data(ticker)
        
        # Fetch historical prices
        state['historical_prices'] = fetch_historical_prices(ticker)
        
        # Fetch company info
        state['company_info'] = fetch_company_info(ticker)
        
        # Fetch financial statements
        state['financial_statements'] = fetch_financial_statements(ticker)
        
        # Fetch news articles
        state['news_articles'] = fetch_news_articles(ticker)
        
        # Perform IR search
        state['search_results'] = perform_ir_search(f"{ticker} financial analysis")
        
        logger.info(f"Data Acquisition Agent completed successfully for {ticker}")
        
    except Exception as e:
        logger.error(f"Data Acquisition Agent error: {str(e)}")
        state['errors'].append(f"data_acquisition_agent: {str(e)}")
    
    # ============================================
    # FIX: Clean state before returning
    # ============================================
    return clean_state_for_serialization(state)


# ============================================================================
# AGENT 2: SENTIMENT & NLP ANALYSIS AGENT
# ============================================================================
def sentiment_nlp_agent(state: InvestmentState) -> InvestmentState:
    """
    Sentiment & NLP Analysis Agent
    Analyzes sentiment from news articles and performs NLP processing.
    
    Responsibilities:
    - Calculate sentiment scores from news articles
    - Extract key events and entities
    - Perform topic analysis
    - Summarize news content
    """
    logger.info(f"Sentiment & NLP Agent processing ticker: {state['ticker']}")
    
    try:
        # Record execution
        state['agent_execution_order'].append('sentiment_nlp_agent')
        state['timestamps']['sentiment_nlp_agent'] = datetime.now().isoformat()
        
        # Perform actual sentiment analysis using sentiment_tools
        articles = state['news_articles'] or []
        ticker = state['ticker']
        
        sentiment_results = analyze_all_sentiment(articles, ticker)
        
        # Update state with sentiment results
        state['sentiment_score'] = sentiment_results.get('sentiment_score')
        state['sentiment_confidence'] = sentiment_results.get('sentiment_confidence')
        state['sentiment_breakdown'] = sentiment_results.get('sentiment_breakdown')
        state['news_summary'] = sentiment_results.get('news_summary')
        state['key_events'] = sentiment_results.get('key_events')
        state['entity_sentiments'] = sentiment_results.get('entity_sentiments')
        state['topic_analysis'] = sentiment_results.get('topic_analysis')
        
        logger.info(f"Sentiment & NLP Agent completed successfully for {state['ticker']}")
        
    except Exception as e:
        logger.error(f"Sentiment & NLP Agent error: {str(e)}")
        state['errors'].append(f"sentiment_nlp_agent: {str(e)}")
    
    # ============================================
    # FIX: Clean state before returning
    # ============================================
    return clean_state_for_serialization(state)


# ============================================================================
# AGENT 3: FINANCIAL REASONING & LLM AGENT
# ============================================================================
def financial_reasoning_agent(state: InvestmentState) -> InvestmentState:
    """
    Financial Reasoning & LLM Agent
    Performs financial analysis using LLM reasoning and technical indicators.
    
    Responsibilities:
    - Calculate technical indicators (RSI, MACD, SMA, etc.)
    - Generate price forecasts using ML models
    - Perform fundamental analysis (DCF, P/E, etc.)
    - Provide reasoning chain for recommendations
    - Generate preliminary investment recommendation
    """
    logger.info(f"Financial Reasoning Agent processing ticker: {state['ticker']}")
    
    try:
        # Record execution
        state['agent_execution_order'].append('financial_reasoning_agent')
        state['timestamps']['financial_reasoning_agent'] = datetime.now().isoformat()
        
        # Perform actual financial analysis using quant_tools
        historical_prices = state['historical_prices'] or []
        company_info = state['company_info'] or {}
        financial_statements = state['financial_statements'] or {}
        
        # Calculate technical indicators
        state['technical_indicators'] = calculate_technical_indicators(historical_prices)
        
        # Price forecasting (try LSTM first, fallback to ARIMA)
        lstm_forecast = forecast_price_lstm(historical_prices, forecast_days=30)
        if lstm_forecast.get('confidence', 0) > 0.5:
            state['price_forecast'] = lstm_forecast
        else:
            state['price_forecast'] = forecast_price_arima(historical_prices, forecast_days=30)
        
        # Fundamental analysis
        state['fundamental_analysis'] = perform_fundamental_analysis(company_info, financial_statements)
        
        # Market context (placeholder - would need external data)
        state['market_context'] = {
            'sector_trend': 'NEUTRAL',
            'market_condition': 'NORMAL',
            'sector_performance': 'N/A',
            'market_performance': 'N/A'
        }
        
        # Generate reasoning chain based on analysis
        reasoning_chain = []
        
        # Technical analysis reasoning
        if state['technical_indicators']:
            rsi = state['technical_indicators'].get('RSI')
            if rsi:
                if rsi > 70:
                    reasoning_chain.append(f"RSI at {rsi:.1f} indicates overbought conditions")
                elif rsi < 30:
                    reasoning_chain.append(f"RSI at {rsi:.1f} indicates oversold conditions")
                else:
                    reasoning_chain.append(f"RSI at {rsi:.1f} in neutral zone")
        
        # Fundamental analysis reasoning
        if state['fundamental_analysis']:
            pe_analysis = state['fundamental_analysis'].get('pe_analysis', {})
            valuation = pe_analysis.get('valuation', 'N/A')
            reasoning_chain.append(f"P/E analysis suggests {valuation}")
            
            profitability = state['fundamental_analysis'].get('profitability', {})
            rating = profitability.get('rating', 'N/A')
            reasoning_chain.append(f"Profitability rating: {rating}")
        
        # Sentiment reasoning
        if state['sentiment_score'] is not None:
            if state['sentiment_score'] > 0.3:
                reasoning_chain.append(f"Positive market sentiment ({state['sentiment_score']:.2f})")
            elif state['sentiment_score'] < -0.3:
                reasoning_chain.append(f"Negative market sentiment ({state['sentiment_score']:.2f})")
            else:
                reasoning_chain.append(f"Neutral market sentiment ({state['sentiment_score']:.2f})")
        
        # Forecast reasoning
        if state['price_forecast']:
            forecast_7d = state['price_forecast'].get('forecast_7d')
            current_price = state['price_forecast'].get('current_price')
            if forecast_7d and current_price:
                change_pct = ((forecast_7d - current_price) / current_price) * 100
                if change_pct > 5:
                    reasoning_chain.append(f"Price forecast indicates {change_pct:.1f}% upside in 7 days")
                elif change_pct < -5:
                    reasoning_chain.append(f"Price forecast indicates {change_pct:.1f}% downside in 7 days")

        state['reasoning_chain'] = reasoning_chain if reasoning_chain else ["Insufficient data for detailed reasoning"]
        
        logger.info(f"Financial Reasoning Agent completed successfully for {state['ticker']}")
        
    except Exception as e:
        logger.error(f"Financial Reasoning Agent error: {str(e)}")
        state['errors'].append(f"financial_reasoning_agent: {str(e)}")
    
    # ============================================
    # FIX: Clean state before returning
    # ============================================
    return clean_state_for_serialization(state)


# ============================================================================
# AGENT 4: RISK ASSESSMENT & VALIDATION AGENT
# ============================================================================
def risk_assessment_agent(state: InvestmentState) -> InvestmentState:
    """
    Risk Assessment & Validation Agent
    Evaluates investment risks and validates recommendations.
    
    Responsibilities:
    - Calculate risk metrics (Sharpe, VaR, volatility, beta)
    - Identify risk factors
    - Validate preliminary recommendation
    - Provide risk-adjusted recommendation
    - Suggest position sizing, stop loss, and take profit levels
    """
    logger.info(f"Risk Assessment Agent processing ticker: {state['ticker']}")
    
    try:
        # Record execution
        state['agent_execution_order'].append('risk_assessment_agent')
        state['timestamps']['risk_assessment_agent'] = datetime.now().isoformat()
        
        # Perform actual risk assessment using quant_tools
        historical_prices = state['historical_prices'] or []
        stock_data = state['stock_data'] or {}
        preliminary_recommendation = state['preliminary_recommendation'] or state.get('llm_recommendation') or 'HOLD'
        
        # Calculate risk metrics
        state['risk_metrics'] = calculate_risk_metrics(historical_prices)
        
        # Identify risk factors based on analysis
        risk_factors = []
        
        # Volatility risk
        if state['risk_metrics']:
            volatility = state['risk_metrics'].get('volatility')
            if volatility and volatility > 0.4:
                risk_factors.append(f"High volatility ({volatility:.2%}) indicates elevated risk")
            elif volatility and volatility < 0.15:
                risk_factors.append(f"Low volatility ({volatility:.2%}) may indicate limited upside")
        
        # Drawdown risk
        if state['risk_metrics']:
            max_drawdown = state['risk_metrics'].get('max_drawdown')
            if max_drawdown and max_drawdown < -0.3:
                risk_factors.append(f"Significant historical drawdown ({max_drawdown:.2%})")
        
        # Sentiment risk
        if state['sentiment_score'] is not None and state['sentiment_score'] < -0.5:
            risk_factors.append("Strong negative sentiment presents downside risk")
        
        # Technical risk
        if state['technical_indicators']:
            rsi = state['technical_indicators'].get('RSI')
            if rsi and rsi > 75:
                risk_factors.append("Overbought conditions suggest potential pullback")
        
        # Fundamental risk
        if state['fundamental_analysis']:
            balance_sheet = state['fundamental_analysis'].get('balance_sheet', {})
            health = balance_sheet.get('health')
            if health == 'Weak':
                risk_factors.append("Weak balance sheet health increases financial risk")
        
        # Add general risk factors if none identified
        if not risk_factors:
            risk_factors.append("Market volatility and sector-specific risks")
        
        state['risk_factors'] = risk_factors
        state['portfolio_insights'] = build_portfolio_insights(
            state.get('investor_profile') or {}, state['ticker']
        )

        llm_payload = {
            "ticker": state["ticker"],
            "user_query": state.get("user_query"),
            "stock_data": stock_data,
            "company_info": state.get("company_info"),
            "financial_statements": state.get("financial_statements"),
            "technical_indicators": state.get("technical_indicators"),
            "price_forecast": state.get("price_forecast"),
            "fundamental_analysis": state.get("fundamental_analysis"),
            "sentiment_score": state.get("sentiment_score"),
            "sentiment_confidence": state.get("sentiment_confidence"),
            "news_summary": state.get("news_summary"),
            "key_events": state.get("key_events"),
            "entity_sentiments": state.get("entity_sentiments"),
            "topic_analysis": state.get("topic_analysis"),
            "risk_metrics": state.get("risk_metrics"),
            "risk_factors": state['risk_factors'],
            "market_context": state.get("market_context"),
            "investor_profile": state.get("investor_profile"),
            "portfolio_insights": state.get("portfolio_insights"),
        }

        llm_result = generate_investment_recommendation(llm_payload)
        state['llm_recommendation'] = llm_result.get('recommendation', 'HOLD')
        state['llm_confidence'] = llm_result.get('confidence', 0.5)
        state['llm_reasoning'] = llm_result.get('reasoning', [])
        state['llm_decision_factors'] = llm_result.get('decision_factors', [])
        state['llm_summary'] = llm_result.get('summary')
        state['direct_answer'] = llm_result.get('direct_answer')
        state['beginner_explanation'] = llm_result.get('beginner_explanation')
        state['llm_raw_response'] = llm_result.get('raw_response')
        state['preliminary_recommendation'] = state['llm_recommendation']
        state['confidence_score'] = state['llm_confidence']
        if state['llm_reasoning']:
            state['reasoning_chain'] = list(state['llm_reasoning']) + (state['reasoning_chain'] or [])
        
        # Validate preliminary recommendation based on risk
        validation_status = 'VALIDATED'
        risk_level = 'MEDIUM'
        
        # Adjust recommendation based on risk metrics
        if state['risk_metrics']:
            sharpe_ratio = state['risk_metrics'].get('Sharpe_ratio')
            volatility = state['risk_metrics'].get('volatility')
            
            if sharpe_ratio and sharpe_ratio < 0.5:
                validation_status = 'NEEDS_REVIEW'
                risk_level = 'HIGH'
            elif volatility and volatility > 0.5:
                validation_status = 'NEEDS_REVIEW'
                risk_level = 'HIGH'
            elif sharpe_ratio and sharpe_ratio > 1.5:
                risk_level = 'LOW'
        
        state['validation_status'] = validation_status
        state['risk_level'] = risk_level
        
        # Risk-adjusted recommendation
        if validation_status == 'VALIDATED':
            state['risk_adjusted_recommendation'] = preliminary_recommendation
        else:
            # Downgrade recommendation if high risk
            if preliminary_recommendation == 'BUY' and risk_level == 'HIGH':
                state['risk_adjusted_recommendation'] = 'HOLD'
            else:
                state['risk_adjusted_recommendation'] = preliminary_recommendation

        state['final_recommendation'] = state['risk_adjusted_recommendation']
        
        # Calculate position sizing based on risk
        current_price = stock_data.get('current_price') if stock_data else None
        if current_price:
            # Adjust risk per trade based on risk level
            risk_per_trade = 0.01 if risk_level == 'HIGH' else 0.02 if risk_level == 'MEDIUM' else 0.03
            stop_loss_pct = 0.08 if risk_level == 'HIGH' else 0.05 if risk_level == 'MEDIUM' else 0.03
            
            profile = state.get('investor_profile') or {}
            account_value = profile.get('portfolio_value', 100000)
            account_value = 100000 if account_value is None else float(account_value)
            position_sizing = calculate_position_size(
                current_price=current_price,
                account_value=account_value,
                risk_per_trade=risk_per_trade,
                stop_loss_pct=stop_loss_pct
            )
            
            state['position_sizing'] = {
                'recommended_allocation': position_sizing.get('position_percentage', 0.05),
                'max_position_size': position_sizing.get('position_percentage', 0.05) * 2,
                'shares': position_sizing.get('shares', 0),
                'reasoning': f"Based on {risk_level} risk level with {risk_per_trade:.1%} risk per trade"
            }
            if state['portfolio_insights']['resulting_ticker_weight'] > 0.10:
                state['position_sizing']['recommended_allocation'] = 0
                state['position_sizing']['reasoning'] = 'No additional allocation suggested until concentration is reviewed.'
            
            # Calculate stop loss and take profit
            state['stop_loss'] = position_sizing.get('stop_loss_price')
            state['take_profit'] = current_price * (1 + stop_loss_pct * 2)  # 2x risk-reward ratio
        else:
            state['position_sizing'] = {
                'recommended_allocation': 0.05,
                'max_position_size': 0.10,
                'reasoning': 'Default allocation - insufficient price data'
            }
            state['stop_loss'] = None
            state['take_profit'] = None
        
        logger.info(f"Risk Assessment Agent completed successfully for {state['ticker']}")
        
    except Exception as e:
        logger.error(f"Risk Assessment Agent error: {str(e)}")
        state['errors'].append(f"risk_assessment_agent: {str(e)}")
    
    # ============================================
    # FIX: Clean state before returning
    # ============================================
    return clean_state_for_serialization(state)


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================
def should_continue(state: InvestmentState) -> str:
    """
    Determines the next step in the agent workflow.
    Returns the name of the next agent to execute or 'END' to finish.
    """
    execution_order = state.get('agent_execution_order', [])
    
    # Define the workflow order
    workflow_order = [
        'data_acquisition_agent',
        'sentiment_nlp_agent',
        'financial_reasoning_agent',
        'risk_assessment_agent'
    ]
    
    # Find the last executed agent
    if not execution_order:
        return workflow_order[0]
    
    last_agent = execution_order[-1]
    
    # Find the next agent in the workflow
    try:
        current_index = workflow_order.index(last_agent)
        if current_index < len(workflow_order) - 1:
            return workflow_order[current_index + 1]
    except ValueError:
        pass
    
    return 'END'