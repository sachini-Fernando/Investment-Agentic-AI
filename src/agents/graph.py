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
