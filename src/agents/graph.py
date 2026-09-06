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
