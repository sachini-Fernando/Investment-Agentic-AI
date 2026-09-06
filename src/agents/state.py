from typing import TypedDict, Annotated, List, Dict, Optional, Any
from langgraph.graph.message import add_messages  # type: ignore

class InvestmentState(TypedDict):
    # === INPUT ===
    analysis_id: Optional[str]
    ticker: str
    user_query: Optional[str]
    
    # === COMMUNICATION CHANNEL ===
    messages: Annotated[List[Dict], add_messages]
    
    # === DATA ACQUISITION & IR AGENT OUTPUTS ===
    stock_data: Optional[Dict]          # price, volume, fundamentals
    historical_prices: Optional[List[Dict]]
    company_info: Optional[Dict]        # P/E, market cap, sector, etc.
    financial_statements: Optional[Dict]  # income statement, balance sheet, cash flow
    news_articles: Optional[List[Dict]]  # scraped news articles
    search_results: Optional[List[Dict]]  # IR search results
    
    # === SENTIMENT & NLP ANALYSIS AGENT OUTPUTS ===
    sentiment_score: Optional[float]      # -1.0 to +1.0 (overall sentiment)
    sentiment_confidence: Optional[float]  # 0.0 to 1.0
    sentiment_breakdown: Optional[Dict]    # sentiment by source/article
    news_summary: Optional[str]          # summarized news
    key_events: Optional[List[str]]      # extracted key events
    entity_sentiments: Optional[Dict]    # sentiment by entity (company, competitors)
    topic_analysis: Optional[Dict]        # topics/themes in news
    
    # === FINANCIAL REASONING & LLM AGENT OUTPUTS ===
    technical_indicators: Optional[Dict]  # RSI, MACD, SMA, Bollinger Bands
    price_forecast: Optional[Dict]        # LSTM/ARIMA predictions
    fundamental_analysis: Optional[Dict] # DCF, P/E analysis, etc.
    market_context: Optional[Dict]       # sector trends, market conditions
    reasoning_chain: Optional[List[str]]  # step-by-step reasoning
    preliminary_recommendation: Optional[str]  # BUY/SELL/HOLD
    confidence_score: Optional[float]     # 0.0 to 1.0
    llm_recommendation: Optional[str]     # Gemini BUY/SELL/HOLD
    llm_confidence: Optional[float]       # Gemini confidence score
    llm_reasoning: Optional[List[str]]    # Gemini rationale steps
    llm_decision_factors: Optional[List[Dict]]  # Structured decision factors
    llm_summary: Optional[str]            # Gemini summary
    llm_raw_response: Optional[str]       # Raw LLM response for traceability
    
    # === RISK ASSESSMENT & VALIDATION AGENT OUTPUTS ===
    risk_metrics: Optional[Dict]          # Sharpe, VaR, volatility, beta
    risk_factors: Optional[List[str]]    # identified risk factors
    validation_status: Optional[str]      # VALIDATED/NEEDS_REVIEW/REJECTED
    risk_adjusted_recommendation: Optional[str]  # final BUY/SELL/HOLD
    final_recommendation: Optional[str]   # alias for final BUY/SELL/HOLD
    risk_level: Optional[str]            # LOW/MEDIUM/HIGH
    position_sizing: Optional[Dict]      # recommended position size
    stop_loss: Optional[float]           # recommended stop loss
    take_profit: Optional[float]         # recommended take profit
    
    # === METADATA ===
    agent_execution_order: Optional[List[str]]  # order of agent execution
    timestamps: Optional[Dict[str, Any]]  # timestamps for each agent execution
    errors: Optional[List[str]]          # any errors encountered
