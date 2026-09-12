from src.pipeline.orchestrator import InvestmentDataPipeline

class FakeIngestion:
    def fetch_all(self, ticker, history_period="2y", news_limit=20):
        historical_prices = [
            {
                "date": f"2026-01-{day:02d}",
                "open": 90 + day,
                "high": 91 + day,
                "low": 89 + day,
                "close": 90 + day,
                "volume": 1000 + day * 10,
            }
            for day in range(1, 36)
        ]
        return {
            "ticker": ticker,
            "stock_data": {"ticker": ticker, "current_price": 100.0},
            "historical_prices": historical_prices,
            "company_info": {"name": "Example Corp", "current_price": 100.0},
            "financial_statements": {
                "income_statement": {"total_revenue": 1000.0, "net_income": 200.0},
                "balance_sheet": {"total_assets": 2000.0, "total_liabilities": 500.0, "shareholders_equity": 1500.0},
                "cash_flow": {"free_cash_flow": 150.0},
            },
            "news_articles": [{"title": "Example gains traction", "content": "Strong growth in demand.", "article_id": "1"}],
            "quality_report": {"record_counts": {"historical_prices": 20, "news_articles": 1}},
            "sources_used": ["fake"],
        }

class FakeNLP:
    def annotate_articles(self, articles):
        return [
            {
                **article,
                "sentiment": {"label": "POSITIVE", "score": 0.7, "confidence": 0.9},
                "entities": [{"text": "Example", "label": "ORG"}],
            }
            for article in articles
        ]

    def embed_texts(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]

class FakeStore:
    def __init__(self):
        self.saved_bundle = None
        self.saved_quality = None
        self.saved_analysis = None

    def save_market_bundle(self, bundle):
        self.saved_bundle = bundle

    def save_quality_report(self, ticker, quality_report):
        self.saved_quality = (ticker, quality_report)

    def save_analysis_result(self, ticker, analysis):
        self.saved_analysis = (ticker, analysis)

class FakeVectorStore:
    def __init__(self):
        self.payload = None

    def upsert_articles(self, articles, embeddings):
        self.payload = (articles, embeddings)

    def search(self, query, limit=5, ticker=None):
        return []

def test_investment_pipeline_runs_with_injected_dependencies():
    pipeline = InvestmentDataPipeline(
        ingestion=FakeIngestion(),
        nlp=FakeNLP(),
        storage=FakeStore(),
        vector_store=FakeVectorStore(),
    )

    result = pipeline.run("AAPL")

    assert result["ticker"] == "AAPL"
    assert result["analysis"]["technical_indicators"]
    assert result["analysis"]["risk_metrics"]
    assert result["analysis"]["annotated_news"][0]["sentiment"]["label"] == "POSITIVE"
