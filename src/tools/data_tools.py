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
     