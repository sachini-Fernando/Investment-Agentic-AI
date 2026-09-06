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

##########################################
#add stock data fetching tools
#########################################
def fetch_stock_data(ticker: str, period: str = "1y") -> Optional[Dict]: 
    """ 
    Fetches stock data using yfinance. 
     
    Args: 
        ticker: Stock ticker symbol (e.g., 'AAPL') 
        period: Time period for data (e.g., '1y', '6mo', '1mo') 
     
    Returns: 
        Dictionary containing stock data or None if failed 
    """ 
    try: 
        logger.info(f"Fetching stock data for {ticker}") 
        snapshot = _INGESTION.fetch_yfinance_snapshot(ticker) 
        alpha_quote = _INGESTION.fetch_alpha_vantage_quote(ticker) 
        data = {**snapshot, **alpha_quote} 
        return data 
         
    except Exception as e: 
        logger.error(f"Error fetching stock data for {ticker}: {str(e)}") 
        return None 
 
def fetch_historical_prices(ticker: str, period: str = "1y", interval: str = 
"1d") -> Optional[List[Dict]]: 
    """ 
    Fetches historical price data using yfinance. 
     
    Args: 
        ticker: Stock ticker symbol 
        period: Time period (e.g., '1y', '6mo', '1mo') 
        interval: Data interval (e.g., '1d', '1h', '5m') 
     
    Returns: 
        List of dictionaries containing historical price data or None if failed 
    """ 
    try: 
        logger.info(f"Fetching historical prices for {ticker}") 
        historical_data = _INGESTION.fetch_yfinance_history(ticker, period=period, interval=interval) 
        logger.info(f"Successfully fetched {len(historical_data)} historical data points for {ticker}") 
        return historical_data 
         
    except Exception as e: 
        logger.error(f"Error fetching historical prices for {ticker}: {str(e)}") 
        return None 

##########################################
#Company & financial information
######################################### 
def fetch_company_info(ticker: str) -> Optional[Dict]: 
    """ 
    Fetches detailed company information using yfinance. 
     
    Args: 
        ticker: Stock ticker symbol 
     
    Returns: 
        Dictionary containing company information or None if failed 
    """ 
    try: 
        logger.info(f"Fetching company info for {ticker}") 
        bundle = _INGESTION.fetch_yfinance_fundamentals(ticker) 
        company_info = bundle.get("company_info", {}) 
        company_info.update(_INGESTION.fetch_alpha_vantage_overview(ticker)) 
        logger.info(f"Successfully fetched company info for {ticker}") 
        return company_info 
         
    except Exception as e: 
        logger.error(f"Error fetching company info for {ticker}: {str(e)}") 
        return None 
 
def fetch_financial_statements(ticker: str) -> Optional[Dict]: 
    """ 
    Fetches financial statements (income statement, balance sheet, cash flow). 
     
    Args: 
        ticker: Stock ticker symbol 
     
    Returns: 
        Dictionary containing financial statements or None if failed 
    """ 
    try: 
        logger.info(f"Fetching financial statements for {ticker}") 
        bundle = _INGESTION.fetch_yfinance_fundamentals(ticker) 
        financial_data = bundle.get("financial_statements") 
        logger.info(f"Successfully fetched financial statements for {ticker}") 
        return financial_data 
         
    except Exception as e: 
        logger.error(f"Error fetching financial statements for {ticker}: {str(e)}") 
        return None  
     
##########################################
#Company & financial information
######################################### 
def fetch_news_articles(ticker: str, limit: int = 10) -> Optional[List[Dict]]: 
    """ 
    Fetches recent news articles for a ticker using yfinance. 
     
    Args: 
        ticker: Stock ticker symbol 
        limit: Maximum number of articles to fetch 
     
    Returns: 
        List of dictionaries containing news articles or None if failed 
    """ 
    try: 
        logger.info(f"Fetching news articles for {ticker}") 
        company = fetch_company_info(ticker) or {} 
        articles = _INGESTION.fetch_newsapi_articles(ticker, company_name=company.get("name"), limit=limit) 
        if not articles: 
            articles = _INGESTION.fetch_yfinance_news(ticker, limit=limit) 
        logger.info(f"Successfully fetched {len(articles)} news articles for {ticker}") 
        return articles 
         
    except Exception as e: 
        logger.error(f"Error fetching news articles for {ticker}: {str(e)}") 
        return None 


##########################################
#Information Retrieval
#########################################    
def perform_ir_search(query: str, limit: int = 5) -> Optional[List[Dict]]: 
    """ 
    Performs Information Retrieval search for investment-related queries. 
    This is a placeholder - integrate with your preferred IR system (e.g., 
Elasticsearch, vector DB). 
     
    Args: 
        query: Search query 
        limit: Maximum number of results 
     
    Returns: 
        List of dictionaries containing search results or None if failed 
    """ 
    try: 
        logger.info(f"Performing IR search for query: {query}") 
        results = _VECTOR_STORE.search(query, limit=limit) 
        if results: 
            search_results = [ 
                { 
                    "query": query, 
                    "title": item.get("metadata", {}).get("article_id"), 
                    "snippet": item.get("document"), 
                    "source": item.get("metadata", {}).get("source"), 
                    "relevance_score": 1.0 / (1.0 + (item.get("distance") or 0.0)), 
                } 
                for item in results 
            ] 
        else: 
            search_results = [ 
                { 
                    "query": query, 
                    "title": f"Result 1 for {query}", 
                    "snippet": f"Relevant information about {query}...", 
                    "source": "investment_db", 
                    "relevance_score": 0.95, 
                } 
            ] 
 
        logger.info(f"IR search completed with {len(search_results)} results") 
        return search_results 
         
    except Exception as e: 
        logger.error(f"Error performing IR search for query {query}: {str(e)}") 
        return None  

##########################################
#Complete data pipeline
#########################################
def fetch_all_data(ticker: str) -> Dict[str, Any]: 
    """ 
    Fetches all available data for a ticker. 
     
    Args: 
        ticker: Stock ticker symbol 
     
    Returns: 
        Dictionary containing all fetched data 
    """ 
    logger.info(f"Fetching all data for {ticker}") 
     
    bundle = _INGESTION.fetch_all(ticker) 
    data = { 
        'ticker': ticker, 
        'stock_data': bundle.get('stock_data'), 
        'historical_prices': bundle.get('historical_prices'), 
        'company_info': bundle.get('company_info'), 
        'financial_statements': bundle.get('financial_statements'), 
        'news_articles': bundle.get('news_articles'), 
        'search_results': perform_ir_search(f"{ticker} financial analysis"), 
        'quality_report': bundle.get('quality_report') 
    } 
     
    logger.info(f"Completed fetching all data for {ticker}") 
    return data         