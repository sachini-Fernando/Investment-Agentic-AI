#############################################
# Imports + MongoDB support
###########################################
"""
LangGraph workflow for the Investment Agentic AI system.
Defines the graph structure connecting the 4 agents:
1. Data Acquisition & IR Agent
2. Sentiment & NLP Analysis Agent
3. Financial Reasoning & LLM Agent
4. Risk Assessment & Validation Agent
"""

from typing import TypedDict, Annotated, Literal, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from loguru import logger
from .state import InvestmentState
from .nodes import (
    data_acquisition_agent,
    sentiment_nlp_agent,
    financial_reasoning_agent,
    risk_assessment_agent,
    should_continue,
)

# Optional MongoDB checkpoint support
try:
    from .checkpoint import (
        create_mongodb_checkpointer_with_env,
        test_mongodb_connection,
    )

    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False
    logger.warning(
        "MongoDB checkpoint support not available. Install langgraph-checkpoint-mongodb for MongoDB persistence."
    )


##################################
# Basic Investment Graph
##################################
def create_investment_graph(checkpointer=None):
    """
        Creates the LangGraph workflow for investment analysis.

        Args:
            checkpointer: Optional checkpointer for state persistence (e.g.,
    MongoDB)

        Returns:
            Compiled LangGraph workflow
    """
    logger.info("Creating Investment Agentic AI workflow graph")

    # Create the state graph
    workflow = StateGraph(InvestmentState)

    # Add all agent nodes to the graph
    workflow.add_node("data_acquisition_agent", data_acquisition_agent)
    workflow.add_node("sentiment_nlp_agent", sentiment_nlp_agent)
    workflow.add_node("financial_reasoning_agent", financial_reasoning_agent)
    workflow.add_node("risk_assessment_agent", risk_assessment_agent)

    # Define the workflow edges (sequential execution)
    # Start with Data Acquisition Agent
    workflow.set_entry_point("data_acquisition_agent")

    # Data Acquisition -> Sentiment & NLP
    workflow.add_edge("data_acquisition_agent", "sentiment_nlp_agent")

    # Sentiment & NLP -> Financial Reasoning
    workflow.add_edge("sentiment_nlp_agent", "financial_reasoning_agent")

    # Financial Reasoning -> Risk Assessment
    workflow.add_edge("financial_reasoning_agent", "risk_assessment_agent")

    # Risk Assessment -> END
    workflow.add_edge("risk_assessment_agent", END)

    # Compile the graph with optional checkpointer
    if checkpointer:
        app = workflow.compile(checkpointer=checkpointer)
        logger.info("Graph compiled with checkpointer")
    else:
        app = workflow.compile()
        logger.info("Graph compiled without checkpointer")

    return app


###################################
# Conditional Investment Graph
####################################
def create_conditional_investment_graph(checkpointer=None):
    """
        Creates a conditional LangGraph workflow with dynamic routing.
        This version uses conditional edges for more flexible agent execution.

        Args:
            checkpointer: Optional checkpointer for state persistence (e.g.,
    MongoDB)

        Returns:
            Compiled LangGraph workflow with conditional routing
    """
    logger.info("Creating conditional Investment Agentic AI workflow graph")

    # Create the state graph
    workflow = StateGraph(InvestmentState)

    # Add all agent nodes to the graph
    workflow.add_node("data_acquisition_agent", data_acquisition_agent)
    workflow.add_node("sentiment_nlp_agent", sentiment_nlp_agent)
    workflow.add_node("financial_reasoning_agent", financial_reasoning_agent)
    workflow.add_node("risk_assessment_agent", risk_assessment_agent)

    # Set entry point
    workflow.set_entry_point("data_acquisition_agent")

    # Add conditional edges for dynamic routing
    workflow.add_conditional_edges(
        "data_acquisition_agent",
        should_continue,
        {
            "sentiment_nlp_agent": "sentiment_nlp_agent",
            "financial_reasoning_agent": "financial_reasoning_agent",
            "risk_assessment_agent": "risk_assessment_agent",
            "END": END,
        },
    )

    workflow.add_conditional_edges(
        "sentiment_nlp_agent",
        should_continue,
        {
            "financial_reasoning_agent": "financial_reasoning_agent",
            "risk_assessment_agent": "risk_assessment_agent",
            "END": END,
        },
    )

    workflow.add_conditional_edges(
        "financial_reasoning_agent",
        should_continue,
        {"risk_assessment_agent": "risk_assessment_agent", "END": END},
    )

    workflow.add_conditional_edges(
        "risk_assessment_agent", should_continue, {"END": END}
    )

    # Compile the graph with optional checkpointer
    if checkpointer:
        app = workflow.compile(checkpointer=checkpointer)
        logger.info("Conditional graph compiled with checkpointer")
    else:
        app = workflow.compile()
        logger.info("Conditional graph compiled without checkpointer")

    return app


#################################
# MongoDB Graph Support
#################################
def create_investment_graph_with_mongodb():
    """
    Creates the LangGraph workflow with MongoDB checkpointing.

    Returns:
        Compiled LangGraph workflow with MongoDB checkpointer

    Raises:
        Exception: If MongoDB is not available or connection fails
    """
    if not MONGODB_AVAILABLE:
        raise Exception(
            "MongoDB checkpoint support is not available. "
            "Please install langgraph-checkpoint-mongodb: pip install langgraph-checkpoint-mongodb"
        )

    logger.info(
        "Creating Investment Agentic AI workflow graph with MongoDB checkpointing"
    )

    # Test MongoDB connection first
    if not test_mongodb_connection():
        raise Exception(
            "MongoDB connection test failed. Cannot create graph with MongoDB checkpointing."
        )

    # Create MongoDB checkpointer
    checkpointer = create_mongodb_checkpointer_with_env()

    # Create graph with checkpointer
    return create_investment_graph(checkpointer=checkpointer)


##############################################
# Investment Analysis Runner
##############################################
def run_investment_analysis(
    ticker: str,
    user_query: str = None,
    use_conditional: bool = False,
    use_mongodb: bool = False,
    thread_id: Optional[str] = None,
):
    """
        Runs the investment analysis workflow for a given ticker.

        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL', 'GOOGL')
            user_query: Optional user query for the analysis
            use_conditional: Whether to use conditional routing
            use_mongodb: Whether to use MongoDB for state persistence
            thread_id: Optional thread ID for MongoDB checkpointing (required if
    use_mongodb=True)

        Returns:
            Final state with all agent outputs
    """
    logger.info(f"Starting investment analysis for ticker: {ticker}")

    # Initialize the state
    initial_state: InvestmentState = {
        "ticker": ticker,
        "user_query": user_query,
        "messages": [],
        # Data Acquisition outputs
        "stock_data": None,
        "historical_prices": None,
        "company_info": None,
        "financial_statements": None,
        "news_articles": None,
        "search_results": None,
        # Sentiment & NLP outputs
        "sentiment_score": None,
        "sentiment_confidence": None,
        "sentiment_breakdown": None,
        "news_summary": None,
        "key_events": None,
        "entity_sentiments": None,
        "topic_analysis": None,
        # Financial Reasoning outputs
        "technical_indicators": None,
        "price_forecast": None,
        "fundamental_analysis": None,
        "market_context": None,
        "reasoning_chain": None,
        "preliminary_recommendation": None,
        "confidence_score": None,
        "llm_recommendation": None,
        "llm_confidence": None,
        "llm_reasoning": None,
        "llm_decision_factors": None,
        "llm_summary": None,
        "llm_raw_response": None,
        # Risk Assessment outputs
        "risk_metrics": None,
        "risk_factors": None,
        "validation_status": None,
        "risk_adjusted_recommendation": None,
        "final_recommendation": None,
        "risk_level": None,
        "position_sizing": None,
        "stop_loss": None,
        "take_profit": None,
        # Metadata
        "agent_execution_order": None,
        "timestamps": None,
        "errors": None,
    }

    # Create and run the graph
    if use_mongodb:
        if not MONGODB_AVAILABLE:
            raise Exception(
                "MongoDB checkpoint support is not available. "
                "Please install langgraph-checkpoint-mongodb: py -m pip install langgraph-checkpoint-mongodb"
            )
        if not thread_id:
            raise ValueError("thread_id is required when use_mongodb=True")

        if use_conditional:
            checkpointer = create_mongodb_checkpointer_with_env()
            app = create_conditional_investment_graph(checkpointer=checkpointer)
        else:
            checkpointer = create_mongodb_checkpointer_with_env()
            app = create_investment_graph(checkpointer=checkpointer)

        # Run with thread_id for MongoDB checkpointing
        config = {"configurable": {"thread_id": thread_id}}
        result = app.invoke(initial_state, config=config)

    else:
        if use_conditional:
            app = create_conditional_investment_graph()
        else:
            app = create_investment_graph()

        # Run the workflow
        result = app.invoke(initial_state)

    logger.info(f"Investment analysis completed for {ticker}")

    return result


#############################################
#Analysis Summary + Testing
#############################################
def print_analysis_summary(state: InvestmentState): 
    """ 
    Prints a summary of the investment analysis results. 
     
    Args: 
        state: The final state from the investment analysis 
    """ 
    print("\n" + "="*80) 
    print("INVESTMENT ANALYSIS SUMMARY") 
    print("="*80) 
    print(f"Ticker: {state['ticker']}") 
    print(f"User Query: {state['user_query'] or 'None'}") 
    print("\n" + "-"*80) 
     
    # Data Acquisition Summary 
    print("\n[DATA ACQUISITION & IR AGENT]") 
    if state['stock_data']: 
        print(f"Current Price: ${state['stock_data'].get('current_price', 'N/A')}") 
        print(f"Market Cap: ${state['stock_data'].get('market_cap', 'N/A'):,}") 
    if state['company_info']: 
        print(f"Sector: {state['company_info'].get('sector', 'N/A')}") 
        print(f"P/E Ratio: {state['company_info'].get('pe_ratio', 'N/A')}") 
    print(f"News Articles Found: {len(state['news_articles']) if state['news_articles'] else 0}") 
     
    # Sentiment Analysis Summary 
    print("\n[SENTIMENT & NLP ANALYSIS AGENT]") 
    if state['sentiment_score'] is not None: 
        print(f"Overall Sentiment: {state['sentiment_score']:.2f}") 
        print(f"Sentiment Confidence: {state['sentiment_confidence']:.2f}") 
    if state['news_summary']: 
        print(f"News Summary: {state['news_summary']}") 
     
    # Financial Reasoning Summary 
    print("\n[FINANCIAL REASONING & LLM AGENT]") 
    if state.get('llm_recommendation'): 
        print(f"Gemini Recommendation: {state['llm_recommendation']}") 
        print(f"Gemini Confidence: {state.get('llm_confidence', 0.0):.2f}") 
    if state['preliminary_recommendation']: 
        print(f"Preliminary Recommendation: {state['preliminary_recommendation']}") 
        print(f"Confidence Score: {state['confidence_score']:.2f}") 
    if state.get('llm_summary'): 
        print(f"LLM Summary: {state['llm_summary']}") 
    if state['price_forecast']: 
        print(f"7-Day Forecast: ${state['price_forecast'].get('forecast_7d', 'N/A')}") 
        print(f"30-Day Forecast: ${state['price_forecast'].get('forecast_30d', 'N/A')}") 
     
    # Risk Assessment Summary 
    print("\n[RISK ASSESSMENT & VALIDATION AGENT]") 
    if state['risk_adjusted_recommendation']: 
        print(f"Final Recommendation: {state['risk_adjusted_recommendation']}") 
        print(f"Risk Level: {state['risk_level']}") 
        print(f"Validation Status: {state['validation_status']}") 
    if state.get('final_recommendation'): 
        print(f"Final Recommendation Alias: {state['final_recommendation']}") 
    if state['position_sizing']: 
        print(f"Recommended Allocation: {state['position_sizing'].get('recommended_allocation', 'N/A')*100:.1f}%") 
    if state['stop_loss']: 
        print(f"Stop Loss: ${state['stop_loss']}") 
    if state['take_profit']: 
        print(f"Take Profit: ${state['take_profit']}") 
     
    # Metadata 
    print("\n[METADATA]") 
    if state['agent_execution_order']: 
        print(f"Agent Execution Order: {' -> '.join(state['agent_execution_order'])}") 
    if state['errors']: 
        print(f"Errors: {len(state['errors'])}") 
        for error in state['errors']: 
            print(f"  - {error}") 
     
    print("\n" + "="*80 + "\n") 
 
# ============================================================================ 
# MAIN EXECUTION (for testing) 
# ============================================================================ 
if __name__ == "__main__": 
    # Test the workflow with a sample ticker 
    ticker = "AAPL" 
    logger.info(f"Testing investment analysis workflow for {ticker}") 
     
    # Run the analysis 
    result = run_investment_analysis(ticker, user_query="Should I buy this stock?") 
     
    # Print the summary 
    print_analysis_summary(result)