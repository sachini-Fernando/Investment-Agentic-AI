# member 1 tools
""" 
Data Acquisition & Information Retrieval Tools 
Provides functions for fetching stock data, financial statements, news 
articles, and IR search. 
""" 
 
from typing import Dict, List, Optional, Any 
from loguru import logger 
 
from ..pipeline import MarketDataIngestion, NewsVectorStore 
 
_INGESTION = MarketDataIngestion() 
_VECTOR_STORE = NewsVectorStore()