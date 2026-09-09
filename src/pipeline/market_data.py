"""
Real-time market data ingestion from yFinance, Alpha Vantage, and NewsAPI.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


import requests
from loguru import logger

try:
    import pandas as pd

    PANDAS_AVAILABLE = True
except ImportError:
    pd = None  # type: ignore[assignment]
    PANDAS_AVAILABLE = False
    logger.warning(
        "pandas is not available. Some historical-data cleaning features will be limited."
    )

try:
    import yfinance as yf

    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logger.warning("yfinance is not available.")


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return float(value)
    except Exception:
        return None


def _safe_int(value: Any) -> Optional[int]:
    try:
        if value is None:
            return None
        if isinstance(value, str) and not value.strip():
            return None
        return int(float(value))
    except Exception:
        return None


def _hash_text(*parts: str) -> str:
    digest = hashlib.sha1()
    digest.update("||".join(part or "" for part in parts).encode("utf-8"))
    return digest.hexdigest()


####################################
# clean_price_frame()
####################################
def _clean_price_frame(frame: pd.DataFrame) -> pd.DataFrame:
    if not PANDAS_AVAILABLE:
        return frame

    if frame.empty:
        return frame

    frame = frame.copy()
    frame.columns = [str(col).lower() for col in frame.columns]

    for column in ["open", "high", "low", "close", "adj close", "volume"]:
        if column in frame.columns:
            frame[column] = pd.to_numeric(frame[column], errors="coerce")

    frame = frame.sort_index()
    numeric_columns = frame.select_dtypes(include=["number"]).columns
    frame[numeric_columns] = frame[numeric_columns].interpolate(limit_direction="both")
    frame[numeric_columns] = frame[numeric_columns].ffill().bfill()
    return frame


#######################################
# MarketDataIngestion
#######################################
@dataclass
class MarketDataIngestion:
    """
    Fetches and normalizes market data from multiple providers.
    """

    alpha_vantage_api_key: Optional[str] = None
    news_api_key: Optional[str] = None

    def __post_init__(self) -> None:
        self.alpha_vantage_api_key = self.alpha_vantage_api_key or os.getenv(
            "ALPHA_VANTAGE_API_KEY"
        )
        self.news_api_key = self.news_api_key or os.getenv("NEWS_API_KEY")

    ################################
    # yFinance Snapshot
    ################################
    def fetch_yfinance_snapshot(self, ticker: str) -> Dict[str, Any]:
        if not YFINANCE_AVAILABLE:
            return {}

        try:
            stock = yf.Ticker(ticker)
            info = stock.info or {}
            return {
                "ticker": ticker.upper(),
                "symbol": ticker.upper(),
                "current_price": _safe_float(
                    info.get("currentPrice") or info.get("regularMarketPrice")
                ),
                "previous_close": _safe_float(info.get("previousClose")),
                "open": _safe_float(info.get("open")),
                "high": _safe_float(info.get("dayHigh")),
                "low": _safe_float(info.get("dayLow")),
                "volume": _safe_int(info.get("volume")),
                "market_cap": _safe_float(info.get("marketCap")),
                "52_week_high": _safe_float(info.get("fiftyTwoWeekHigh")),
                "52_week_low": _safe_float(info.get("fiftyTwoWeekLow")),
                "avg_volume": _safe_int(info.get("averageVolume")),
                "shares_outstanding": _safe_int(info.get("sharesOutstanding")),
                "as_of": datetime.now(timezone.utc).isoformat(),
                "source": "yfinance",
            }
        except Exception as exc:
            logger.warning(f"yFinance quote fetch failed for {ticker}: {exc}")
            return {}

    #################################
    # yFinance history + fundamentals
    #################################
    def fetch_yfinance_history(
        self, ticker: str, period: str = "2y", interval: str = "1d"
    ) -> List[Dict[str, Any]]:
        if not YFINANCE_AVAILABLE:
            return []

        try:
            hist = yf.Ticker(ticker).history(
                period=period, interval=interval, auto_adjust=False
            )
            if hist.empty:
                return []

            hist = _clean_price_frame(hist)
            if "adj close" not in hist.columns and "close" in hist.columns:
                hist["adj close"] = hist["close"]

            records: List[Dict[str, Any]] = []
            for index, row in hist.reset_index().iterrows():
                date_value = row.get("Date") or row.get("Datetime") or row.get("index")
                if pd.isna(date_value):
                    continue

                records.append(
                    {
                        "date": pd.Timestamp(date_value).to_pydatetime().isoformat(),
                        "open": _safe_float(row.get("open")),
                        "high": _safe_float(row.get("high")),
                        "low": _safe_float(row.get("low")),
                        "close": _safe_float(row.get("close")),
                        "volume": _safe_int(row.get("volume")),
                        "adj_close": _safe_float(
                            row.get("adj close")
                            or row.get("adj_close")
                            or row.get("close")
                        ),
                        "source": "yfinance",
                    }
                )
            return records
        except Exception as exc:
            logger.warning(f"yFinance history fetch failed for {ticker}:{exc}")
            return []

    #################################
    # yFinance fundamentals fetching
    #################################

    def fetch_yfinance_fundamentals(self, ticker: str) -> Dict[str, Any]:
        if not YFINANCE_AVAILABLE:
            return {}

        try:
            stock = yf.Ticker(ticker)
            info = stock.info or {}
            financials = stock.financials
            balance_sheet = stock.balance_sheet
            cash_flow = stock.cashflow

            company_info = {
                "ticker": ticker.upper(),
                "name": info.get("longName") or info.get("shortName"),
                "sector": info.get("sector"),
                "industry": info.get("industry"),
                "description": info.get("longBusinessSummary"),
                "website": info.get("website"),
                "employees": _safe_int(info.get("fullTimeEmployees")),
                "country": info.get("country"),
                "currency": info.get("currency"),
                "exchange": info.get("exchange"),
                "pe_ratio": _safe_float(info.get("trailingPE")),
                "forward_pe": _safe_float(info.get("forwardPE")),
                "peg_ratio": _safe_float(info.get("pegRatio")),
                "pb_ratio": _safe_float(info.get("priceToBook")),
                "ps_ratio": _safe_float(info.get("priceToSalesTrailing12Months")),
                "eps": _safe_float(info.get("trailingEps")),
                "forward_eps": _safe_float(info.get("forwardEps")),
                "dividend_yield": _safe_float(info.get("dividendYield")),
                "dividend_rate": _safe_float(info.get("dividendRate")),
                "payout_ratio": _safe_float(info.get("payoutRatio")),
                "beta": _safe_float(info.get("beta")),
                "profit_margin": _safe_float(info.get("profitMargins")),
                "operating_margin": _safe_float(info.get("operatingMargins")),
                "return_on_assets": _safe_float(info.get("returnOnAssets")),
                "return_on_equity": _safe_float(info.get("returnOnEquity")),
                "revenue_per_share": _safe_float(info.get("revenuePerShare")),
                "quarterly_revenue_growth": _safe_float(
                    info.get("revenueQuarterlyGrowth")
                ),
                "earnings_growth": _safe_float(info.get("earningsQuarterlyGrowth")),
                "52_week_change": _safe_float(info.get("52WeekChange")),
                "market_cap": _safe_float(info.get("marketCap")),
                "shares_outstanding": _safe_int(info.get("sharesOutstanding")),
                "current_price": _safe_float(
                    info.get("currentPrice") or info.get("regularMarketPrice")
                ),
                "source": "yfinance",
            }

            latest_financials = (
                financials.iloc[:, 0].to_dict() if not financials.empty else {}
            )
            latest_balance = (
                balance_sheet.iloc[:, 0].to_dict() if not balance_sheet.empty else {}
            )
            latest_cash_flow = (
                cash_flow.iloc[:, 0].to_dict() if not cash_flow.empty else {}
            )

            return {
                "company_info": company_info,
                "financial_statements": {
                    "income_statement": {
                        "total_revenue": _safe_float(
                            latest_financials.get("Total Revenue")
                        ),
                        "cost_of_revenue": _safe_float(
                            latest_financials.get("Cost Of Revenue")
                        ),
                        "gross_profit": _safe_float(
                            latest_financials.get("Gross Profit")
                        ),
                        "operating_income": _safe_float(
                            latest_financials.get("Operating Income")
                        ),
                        "net_income": _safe_float(latest_financials.get("Net Income")),
                        "ebitda": _safe_float(latest_financials.get("EBITDA")),
                    },
                    "balance_sheet": {
                        "total_assets": _safe_float(latest_balance.get("Total Assets")),
                        "total_liabilities": _safe_float(
                            latest_balance.get("Total Liab")
                        ),
                        "shareholders_equity": _safe_float(
                            latest_balance.get("Total Stockholder Equity")
                        ),
                        "cash_and_equivalents": _safe_float(
                            latest_balance.get("Cash And Cash Equivalents")
                        ),
                        "total_debt": _safe_float(latest_balance.get("Total Debt")),
                    },
                    "cash_flow": {
                        "operating_cash_flow": _safe_float(
                            latest_cash_flow.get("Operating Cash Flow")
                        ),
                        "capital_expenditure": _safe_float(
                            latest_cash_flow.get("Capital Expenditure")
                        ),
                        "free_cash_flow": _safe_float(
                            latest_cash_flow.get("Free Cash Flow")
                        ),
                        "dividend_payments": _safe_float(
                            latest_cash_flow.get("Dividends Paid")
                        ),
                    },
                },
            }
        except Exception as exc:
            logger.warning(f"yFinance fundamentals fetch failed for {ticker}: {exc}")
            return {"company_info": {}, "financial_statements": {}}

    ############################################
    # add Alpha Vantage market overview fetching
    ############################################
    def fetch_alpha_vantage_quote(self, ticker: str) -> Dict[str, Any]:
        if not self.alpha_vantage_api_key:
            return {}

        try:
            response = requests.get(
                "https://www.alphavantage.co/query",
                params={
                    "function": "GLOBAL_QUOTE",
                    "symbol": ticker,
                    "apikey": self.alpha_vantage_api_key,
                },
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json().get("Global Quote", {})
            if not payload:
                return {}

            return {
                "ticker": ticker.upper(),
                "current_price": _safe_float(payload.get("05. price")),
                "open": _safe_float(payload.get("02. open")),
                "high": _safe_float(payload.get("03. high")),
                "low": _safe_float(payload.get("04. low")),
                "previous_close": _safe_float(payload.get("08. previous close")),
                "volume": _safe_int(payload.get("06. volume")),
                "change": _safe_float(payload.get("09. change")),
                "change_percent": payload.get("10. change percent"),
                "source": "alpha_vantage",
            }
        except Exception as exc:
            logger.warning(f"Alpha Vantage quote fetch failed for {ticker}: {exc}")
            return {}

    ########################################################
    # add Alpha Vantage overview
    ###################################################
    def fetch_alpha_vantage_overview(self, ticker: str) -> Dict[str, Any]:
        if not self.alpha_vantage_api_key:
            return {}

        try:
            response = requests.get(
                "https://www.alphavantage.co/query",
                params={
                    "function": "OVERVIEW",
                    "symbol": ticker,
                    "apikey": self.alpha_vantage_api_key,
                },
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json()
            if not payload or "Symbol" not in payload:
                return {}

            return {
                "ticker": ticker.upper(),
                "name": payload.get("Name"),
                "sector": payload.get("Sector"),
                "industry": payload.get("Industry"),
                "description": payload.get("Description"),
                "market_cap": _safe_float(payload.get("MarketCapitalization")),
                "ebitda": _safe_float(payload.get("EBITDA")),
                "pe_ratio": _safe_float(payload.get("PERatio")),
                "peg_ratio": _safe_float(payload.get("PEGRatio")),
                "pb_ratio": _safe_float(payload.get("PriceToBookRatio")),
                "ps_ratio": _safe_float(payload.get("PriceToSalesRatioTTM")),
                "eps": _safe_float(payload.get("EPS")),
                "profit_margin": _safe_float(payload.get("ProfitMargin")),
                "operating_margin": _safe_float(payload.get("OperatingMarginTTM")),
                "return_on_assets": _safe_float(payload.get("ReturnOnAssetsTTM")),
                "return_on_equity": _safe_float(payload.get("ReturnOnEquityTTM")),
                "dividend_yield": _safe_float(payload.get("DividendYield")),
                "quarterly_earnings_growth": _safe_float(
                    payload.get("QuarterlyEarningsGrowthYOY")
                ),
                "quarterly_revenue_growth": _safe_float(
                    payload.get("QuarterlyRevenueGrowthYOY")
                ),
                "beta": _safe_float(payload.get("Beta")),
                "52_week_high": _safe_float(payload.get("52WeekHigh")),
                "52_week_low": _safe_float(payload.get("52WeekLow")),
                "source": "alpha_vantage",
            }
        except Exception as exc:
            logger.warning(f"Alpha Vantage overview fetch failed for {ticker}: {exc}")
            return {}


    ##############################################
    # add Alpha Vantage historical price fetching
    ##############################################
    def fetch_alpha_vantage_history(
        self, ticker: str, outputsize: str = "compact"
    ) -> List[Dict[str, Any]]:
        if not self.alpha_vantage_api_key:
            return []

        try:
            response = requests.get(
                "https://www.alphavantage.co/query",
                params={
                    "function": "TIME_SERIES_DAILY_ADJUSTED",
                    "symbol": ticker,
                    "outputsize": outputsize,
                    "apikey": self.alpha_vantage_api_key,
                },
                timeout=20,
            )
            response.raise_for_status()
            payload = response.json().get("Time Series (Daily)", {})
            records: List[Dict[str, Any]] = []
            for date, values in payload.items():
                records.append(
                    {
                        "date": date,
                        "open": _safe_float(values.get("1. open")),
                        "high": _safe_float(values.get("2. high")),
                        "low": _safe_float(values.get("3. low")),
                        "close": _safe_float(values.get("4. close")),
                        "adjusted_close": _safe_float(values.get("5. adjusted close")),
                        "volume": _safe_int(values.get("6. volume")),
                        "source": "alpha_vantage",
                    }
                )
            return sorted(records, key=lambda item: item["date"])
        except Exception as exc:
            logger.warning(f"Alpha Vantage history fetch failed for {ticker}: {exc}")
            return []


    #######################################
    # add financial news fetching
    ########################################
    def fetch_newsapi_articles(
        self, ticker: str, company_name: Optional[str] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        if not self.news_api_key:
            return []

        query = f'"{ticker}"'
        if company_name:
            query = f'("{ticker}" OR "{company_name}")'

        try:
            response = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": query,
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": min(limit, 100),
                    "apiKey": self.news_api_key,
                },
                timeout=20,
            )
            response.raise_for_status()
            articles = []
            for item in response.json().get("articles", []):
                url = item.get("url")
                articles.append(
                    {
                        "article_id": _hash_text(
                            item.get("title", ""), url or "", item.get("publishedAt", "")
                        ),
                        "title": item.get("title"),
                        "source": (item.get("source") or {}).get("name"),
                        "date": item.get("publishedAt"),
                        "published_at": item.get("publishedAt"),
                        "url": url,
                        "content": item.get("content") or item.get("description"),
                        "summary": item.get("description"),
                        "thumbnail": item.get("urlToImage"),
                        "source_type": "newsapi",
                    }
                )
            return articles
        except Exception as exc:
            logger.warning(f"NewsAPI fetch failed for {ticker}: {exc}")
            return []


    def fetch_yfinance_news(self, ticker: str, limit: int = 20) -> List[Dict[str, Any]]:
        if not YFINANCE_AVAILABLE:
            return []

        try:
            news = yf.Ticker(ticker).news or []
            articles = []
            for item in news[:limit]:
                # yFinance now wraps story fields in `content`; retain support
                # for the older flat response shape as well.
                story = item.get("content") if isinstance(item.get("content"), dict) else item
                url = (
                    item.get("link")
                    or story.get("canonicalUrl", {}).get("url")
                    or story.get("clickThroughUrl", {}).get("url")
                )
                published_time = item.get("providerPublishTime")
                published_at = story.get("pubDate") or story.get("displayTime")
                title = story.get("title")
                summary = story.get("summary") or story.get("description")
                provider = story.get("provider") or {}
                thumbnail = story.get("thumbnail") or {}
                thumbnail_url = thumbnail.get("originalUrl")
                if not thumbnail_url:
                    resolutions = thumbnail.get("resolutions") or []
                    thumbnail_url = resolutions[0].get("url") if resolutions else None
                articles.append(
                    {
                        "article_id": _hash_text(
                            title or "", url or "", str(published_time or published_at or "")
                        ),
                        "title": title,
                        "source": item.get("publisher") or provider.get("displayName"),
                        "date": (
                            datetime.fromtimestamp(
                                published_time, tz=timezone.utc
                            ).isoformat()
                            if published_time
                            else published_at
                        ),
                        "published_at": (
                            datetime.fromtimestamp(
                                published_time, tz=timezone.utc
                            ).isoformat()
                            if published_time
                            else published_at
                        ),
                        "url": url,
                        "content": summary,
                        "summary": summary,
                        "thumbnail": thumbnail_url,
                        "source_type": "yfinance",
                    }
                )
            return articles
        except Exception as exc:
            logger.warning(f"yFinance news fetch failed for {ticker}: {exc}")
            return []


    ###################################
    #add multi-source data aggregation
    ###################################
    def build_quality_report(self, bundle: Dict[str, Any]) -> Dict[str, Any]:
        historical_prices = bundle.get("historical_prices") or []
        news_articles = bundle.get("news_articles") or []

        if PANDAS_AVAILABLE:
            price_frame = pd.DataFrame(historical_prices)
            missing_counts = (
                price_frame.isna().sum().to_dict() if not price_frame.empty else {}
            )
        else:
            missing_counts = {}
            for row in historical_prices:
                for key, value in row.items():
                    if value in (None, ""):
                        missing_counts[key] = missing_counts.get(key, 0) + 1

        return {
            "record_counts": {
                "historical_prices": len(historical_prices),
                "news_articles": len(news_articles),
            },
            "missing_counts": missing_counts,
            "sources_used": bundle.get("sources_used", []),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }


    def fetch_all(
        self, ticker: str, history_period: str = "2y", news_limit: int = 20
    ) -> Dict[str, Any]:
        ticker = ticker.upper().strip()
        logger.info(f"Fetching multi-source data for {ticker}")

        yfinance_snapshot = self.fetch_yfinance_snapshot(ticker)
        alpha_quote = self.fetch_alpha_vantage_quote(ticker)
        alpha_overview = self.fetch_alpha_vantage_overview(ticker)
        yfinance_fundamentals = self.fetch_yfinance_fundamentals(ticker)

        historical_prices = self.fetch_yfinance_history(
            ticker, period=history_period, interval="1d"
        )
        if len(historical_prices) < 30:
            alpha_history = self.fetch_alpha_vantage_history(ticker, outputsize="full")
            if alpha_history:
                historical_prices = alpha_history

        company_info = {}
        company_info.update(yfinance_fundamentals.get("company_info", {}))
        company_info.update(alpha_overview)
        company_info.update(alpha_quote)
        company_info.update(yfinance_snapshot)

        financial_statements = yfinance_fundamentals.get("financial_statements", {})

        news_articles = self.fetch_newsapi_articles(
            ticker, company_name=company_info.get("name"), limit=news_limit
        )
        if not news_articles:
            news_articles = self.fetch_yfinance_news(ticker, limit=news_limit)

        sources_used = {
            source
            for source in [
                yfinance_snapshot.get("source"),
                alpha_quote.get("source"),
                alpha_overview.get("source"),
            ]
            if isinstance(source, str) and source
        }
        sources_used.update(
            {
                article.get("source_type")
                for article in news_articles
                if isinstance(article.get("source_type"), str)
                and article.get("source_type")
            }
        )

        bundle = {
            "ticker": ticker,
            "stock_data": {
                **yfinance_snapshot,
                **alpha_quote,
            },
            "historical_prices": historical_prices,
            "company_info": company_info,
            "financial_statements": financial_statements,
            "news_articles": news_articles,
            "sources_used": sorted(sources_used),
        }

        bundle["quality_report"] = self.build_quality_report(bundle)
        return bundle
