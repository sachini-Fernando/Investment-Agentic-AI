from src.tools.sentiment_tools import (
    analyze_all_sentiment,
    analyze_sentiment,
    fallback_sentiment_analysis,
    summarize_news,
)


def test_fallback_sentiment_analysis_positive_and_negative():
    positive = fallback_sentiment_analysis("The company reported strong growth and excellent profit.")
    negative = fallback_sentiment_analysis("The company reported weak decline and a large loss.")

    assert positive["label"] == "POSITIVE"
    assert negative["label"] == "NEGATIVE"


def test_analyze_sentiment_returns_structured_result():
    result = analyze_sentiment("Revenue growth was strong and the outlook improved.")

    assert "score" in result
    assert "confidence" in result
    assert "label" in result


def test_summarize_news_uses_article_content():
    summary = summarize_news([
        {"title": "Company posts earnings beat", "content": "Revenue rose sharply. Guidance improved."},
        {"title": "Analysts react", "content": "Sentiment remained positive."},
    ])

    assert "Company posts earnings beat" in summary


def test_analyze_all_sentiment_keeps_full_news_summary():
    articles = [
        {"title": "First event", "content": "Revenue increased."},
        {"title": "Second event", "content": "The company expanded operations."},
        {"title": "Third event", "content": "Management raised guidance."},
    ]

    result = analyze_all_sentiment(articles, ticker="AAPL")

    assert "First event" in result["news_summary"]
    assert "Second event" in result["news_summary"]
    assert "Third event" in result["news_summary"]


def test_analyze_all_sentiment_returns_expected_keys():
    results = analyze_all_sentiment(
        [{"title": "Earnings beat", "content": "Strong growth and profit"}],
        ticker="AAPL",
    )

    assert "sentiment_score" in results
    assert "news_summary" in results
    assert "annotated_articles" in results


def test_nested_yfinance_news_provides_text_for_sentiment(monkeypatch):
    from src.pipeline import market_data

    class FakeTicker:
        news = [{
            "id": "story-1",
            "content": {
                "title": "Company reports strong growth",
                "summary": "Profit beat expectations.",
                "pubDate": "2026-09-08T15:29:15Z",
                "provider": {"displayName": "Yahoo Finance"},
                "canonicalUrl": {"url": "https://example.com/story-1"},
            },
        }]

    monkeypatch.setattr(market_data.yf, "Ticker", lambda ticker: FakeTicker())
    articles = market_data.MarketDataIngestion().fetch_yfinance_news("AAPL", limit=1)

    assert articles[0]["title"] == "Company reports strong growth"
    assert articles[0]["content"] == "Profit beat expectations."
