"""
Sentiment & NLP Analysis Tools
Provides functions for sentiment analysis, entity extraction, topic analysis, and text summarization.
"""

from typing import Dict, List, Optional, Any
import re
from loguru import logger

from ..pipeline import FinancialNLPAnalyzer

_NLP = FinancialNLPAnalyzer()


def analyze_sentiment(text: str) -> Dict[str, float]:
    """
    Analyzes sentiment of text using transformers pipeline or fallback method.
    
    Args:
        text: Input text to analyze
    
    Returns:
        Dictionary with sentiment score (-1.0 to 1.0) and confidence (0.0 to 1.0)
    """
    try:
        result = _NLP.analyze_sentiment(text)
        return {
            "score": result.get("score", 0.0),
            "confidence": result.get("confidence", 0.0),
            "label": result.get("label", "NEUTRAL"),
        }
            
    except Exception as e:
        logger.error(f"Error in sentiment analysis: {str(e)}")
        return fallback_sentiment_analysis(text)


def fallback_sentiment_analysis(text: str) -> Dict[str, float]:
    """
    Fallback sentiment analysis using keyword matching.
    
    Args:
        text: Input text to analyze
    
    Returns:
        Dictionary with sentiment score and confidence
    """
    positive_words = ['good', 'great', 'excellent', 'strong', 'growth', 'profit', 'increase', 'beat', 'success', 'positive']
    negative_words = ['bad', 'poor', 'weak', 'decline', 'loss', 'decrease', 'miss', 'fail', 'negative', 'risk']
    
    text_lower = text.lower()
    words = re.findall(r'\w+', text_lower)
    
    positive_count = sum(1 for word in words if word in positive_words)
    negative_count = sum(1 for word in words if word in negative_words)
    
    total = positive_count + negative_count
    if total == 0:
        return {'score': 0.0, 'confidence': 0.5, 'label': 'NEUTRAL'}
    
    score = (positive_count - negative_count) / total
    confidence = min(total / 10, 1.0)  # More words = higher confidence
    
    label = 'POSITIVE' if score > 0 else 'NEGATIVE' if score < 0 else 'NEUTRAL'
    
    return {'score': score, 'confidence': confidence, 'label': label}


def analyze_news_sentiment(articles: List[Dict]) -> Dict[str, Any]:
    """
    Analyzes sentiment across multiple news articles.
    
    Args:
        articles: List of article dictionaries with 'content' field
    
    Returns:
        Dictionary with overall sentiment, breakdown by article, and summary
    """
    try:
        logger.info(f"Analyzing sentiment for {len(articles)} articles")
        
        if not articles:
            return {
                'overall_score': 0.0,
                'overall_confidence': 0.0,
                'sentiment_breakdown': {},
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0
            }
        
        sentiment_breakdown = {}
        scores = []
        confidences = []
        positive_count = 0
        negative_count = 0
        neutral_count = 0
        
        for idx, article in enumerate(articles):
            content = article.get('content', '') or article.get('title', '') or article.get('summary', '')
            if not content:
                continue
            
            sentiment = analyze_sentiment(content)
            sentiment_breakdown[f'article_{idx}'] = sentiment
            
            scores.append(sentiment['score'])
            confidences.append(sentiment['confidence'])
            
            if sentiment['label'] == 'POSITIVE':
                positive_count += 1
            elif sentiment['label'] == 'NEGATIVE':
                negative_count += 1
            else:
                neutral_count += 1
        
        if not scores:
            return {
                'overall_score': 0.0,
                'overall_confidence': 0.0,
                'sentiment_breakdown': {},
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0
            }
        
        overall_score = sum(scores) / len(scores)
        overall_confidence = sum(confidences) / len(confidences)
        
        logger.info(f"Sentiment analysis completed: score={overall_score:.2f}, confidence={overall_confidence:.2f}")
        
        return {
            'overall_score': overall_score,
            'overall_confidence': overall_confidence,
            'sentiment_breakdown': sentiment_breakdown,
            'positive_count': positive_count,
            'negative_count': negative_count,
            'neutral_count': neutral_count
        }
        
    except Exception as e:
        logger.error(f"Error analyzing news sentiment: {str(e)}")
        return {
            'overall_score': 0.0,
            'overall_confidence': 0.0,
            'sentiment_breakdown': {},
            'positive_count': 0,
            'negative_count': 0,
            'neutral_count': 0
        }


def extract_key_events(articles: List[Dict], ticker: str) -> List[str]:
    """
    Extracts key events from news articles using keyword extraction.
    
    Args:
        articles: List of article dictionaries
        ticker: Stock ticker symbol
    
    Returns:
        List of key event strings
    """
    try:
        logger.info(f"Extracting key events from {len(articles)} articles")
        
        event_keywords = [
            'earnings', 'revenue', 'profit', 'loss', 'launch', 'acquisition',
            'merger', 'dividend', 'split', 'guidance', 'forecast', 'upgrade',
            'downgrade', 'lawsuit', 'patent', 'approval', 'regulation', 'contract',
            'partnership', 'expansion', 'closure', 'layoff', 'hiring', 'ceo',
            'executive', 'board', 'shareholder', 'investor', 'market', 'sector'
        ]
        
        key_events = []
        
        for article in articles:
            content = (article.get('content', '') or article.get('title', '') or article.get('summary', '')).lower()
            title = article.get('title', '')
            
            for keyword in event_keywords:
                if keyword in content:
                    # Create event description
                    event = f"{keyword.title()}: {title[:50]}..."
                    if event not in key_events:
                        key_events.append(event)
                        break
        
        logger.info(f"Extracted {len(key_events)} key events")
        return key_events[:10]  # Return top 10 events
        
    except Exception as e:
        logger.error(f"Error extracting key events: {str(e)}")
        return []


def extract_entities(articles: List[Dict], ticker: str) -> Dict[str, float]:
    """
    Extracts entities and their associated sentiments from articles.
    
    Args:
        articles: List of article dictionaries
        ticker: Stock ticker symbol
    
    Returns:
        Dictionary mapping entity names to sentiment scores
    """
    try:
        logger.info(f"Extracting entities from {len(articles)} articles")
        
        entity_sentiments = {}
        
        entity_sentiments[ticker] = 0.0
        
        for article in articles:
            content = article.get('content', '') or article.get('title', '') or article.get('summary', '')
            if not content:
                continue

            entities = _NLP.extract_entities(content)
            sentiment = analyze_sentiment(content)
            
            for entity in entities:
                entity_name = entity.get("text") if isinstance(entity, dict) else str(entity)
                if not entity_name:
                    continue
                if entity_name not in entity_sentiments:
                    entity_sentiments[entity_name] = sentiment['score']
                else:
                    # Average the sentiment
                    entity_sentiments[entity_name] = (entity_sentiments[entity_name] + sentiment['score']) / 2
        
        logger.info(f"Extracted {len(entity_sentiments)} entities")
        return entity_sentiments
        
    except Exception as e:
        logger.error(f"Error extracting entities: {str(e)}")
        return {ticker: 0.0}


def perform_topic_analysis(articles: List[Dict]) -> Dict[str, float]:
    """
    Performs topic analysis on news articles.
    
    Args:
        articles: List of article dictionaries
    
    Returns:
        Dictionary mapping topics to their weights
    """
    try:
        logger.info(f"Performing topic analysis on {len(articles)} articles")
        
        topic_keywords = {
            'earnings': ['earnings', 'revenue', 'profit', 'quarterly', 'fiscal'],
            'product': ['product', 'launch', 'release', 'innovation', 'feature'],
            'market': ['market', 'share', 'competition', 'sector', 'industry'],
            'management': ['ceo', 'executive', 'board', 'management', 'leadership'],
            'regulation': ['regulation', 'compliance', 'legal', 'lawsuit', 'approval'],
            'financial': ['financial', 'debt', 'cash', 'liquidity', 'balance'],
            'growth': ['growth', 'expansion', 'acquisition', 'merger', 'partnership'],
            'risk': ['risk', 'volatility', 'uncertainty', 'concern', 'challenge']
        }
        
        topic_counts = {topic: 0 for topic in topic_keywords.keys()}
        total_mentions = 0
        
        for article in articles:
            content = (article.get('content', '') or article.get('title', '') or article.get('summary', '')).lower()
            
            for topic, keywords in topic_keywords.items():
                count = sum(1 for keyword in keywords if keyword in content)
                topic_counts[topic] += count
                total_mentions += count
        
        if total_mentions == 0:
            return {topic: 0.125 for topic in topic_counts.keys()}  # Equal weights
        
        # Normalize to get weights
        topic_weights = {topic: count / total_mentions for topic, count in topic_counts.items()}
        
        logger.info(f"Topic analysis completed with weights: {topic_weights}")
        return topic_weights
        
    except Exception as e:
        logger.error(f"Error in topic analysis: {str(e)}")
        return {}


def summarize_news(articles: List[Dict], max_length: int = 200) -> str:
    """
    Summarizes news articles into a concise summary.
    
    Args:
        articles: List of article dictionaries
        max_length: Maximum length of summary in characters
    
    Returns:
        Summary string
    """
    try:
        logger.info(f"Summarizing {len(articles)} articles")
        
        if not articles:
            return "No news articles available."
        
        # Extract titles and content
        texts = []
        for article in articles:
            title = article.get('title', '')
            content = article.get('content', '')
            if title:
                texts.append(title)
            if content:
                texts.append(content[:100])  # First 100 chars of content
        
        if not texts:
            return "No content available for summarization."
        
        # Simple extractive summarization: take first few sentences
        all_text = ' '.join(texts)
        sentences = re.split(r'[.!?]+', all_text)
        
        # Filter empty sentences and take first few
        sentences = [s.strip() for s in sentences if s.strip()]
        summary = ' '.join(sentences[:3])
        
        # Truncate if too long
        if len(summary) > max_length:
            summary = summary[:max_length-3] + '...'
        
        logger.info(f"Generated summary: {summary[:50]}...")
        return summary
        
    except Exception as e:
        logger.error(f"Error summarizing news: {str(e)}")
        return "Error generating news summary."


def analyze_all_sentiment(articles: List[Dict], ticker: str) -> Dict[str, Any]:
    """
    Performs complete sentiment and NLP analysis on news articles.
    
    Args:
        articles: List of article dictionaries
        ticker: Stock ticker symbol
    
    Returns:
        Dictionary containing all sentiment analysis results
    """
    logger.info(f"Performing complete sentiment analysis for {ticker}")
    
    results = {
        'sentiment_score': None,
        'sentiment_confidence': None,
        'sentiment_breakdown': None,
        'news_summary': None,
        'key_events': None,
        'entity_sentiments': None,
        'topic_analysis': None,
        'annotated_articles': None,
    }
    
    # Analyze overall sentiment
    sentiment_results = analyze_news_sentiment(articles)
    results['sentiment_score'] = sentiment_results['overall_score']
    results['sentiment_confidence'] = sentiment_results['overall_confidence']
    results['sentiment_breakdown'] = sentiment_results['sentiment_breakdown']
    
    # Extract key events
    results['key_events'] = extract_key_events(articles, ticker)
    
    # Extract entities
    results['entity_sentiments'] = extract_entities(articles, ticker)
    
    # Topic analysis
    results['topic_analysis'] = perform_topic_analysis(articles)
    
    # Summarize news
    results['news_summary'] = summarize_news(articles)

    # Annotated articles for downstream storage / RAG
    results['annotated_articles'] = [_NLP.annotate_article(article) for article in articles]
    
    logger.info(f"Complete sentiment analysis completed for {ticker}")
    return results
