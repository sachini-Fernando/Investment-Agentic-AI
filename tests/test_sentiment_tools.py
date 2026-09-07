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


def test_analyze_all_sentiment_returns_expected_keys():
    results = analyze_all_sentiment(
        [{"title": "Earnings beat", "content": "Strong growth and profit"}],
        ticker="AAPL",
    )

    assert "sentiment_score" in results
    assert "news_summary" in results
    assert "annotated_articles" in results
