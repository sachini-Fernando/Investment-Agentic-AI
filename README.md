# InvestSage: AI Investment Agent

InvestSage is an agentic AI system for explainable, risk-aware investment analysis. It combines market data, financial news, sentiment, quantitative indicators, and an LLM-generated recommendation in one workflow. The system is intended for research and education; it does not execute trades or replace a licensed financial adviser.

This project was developed for the Information Retrieval and Web Analytics (IT 3041) course.

## Features

- Four-agent LangGraph workflow for data acquisition, NLP, financial reasoning, and risk assessment.
- Multi-source market ingestion using yFinance, Alpha Vantage, and NewsAPI.
- Historical prices, company profiles, financial statements, and financial news retrieval.
- Technical indicators, fundamental analysis, volatility, Sharpe, Sortino, VaR, and other risk metrics.
- FinBERT sentiment analysis with a keyword fallback when the model is unavailable.
- spaCy named-entity recognition with a regex fallback.
- Sentence-transformer embeddings with a deterministic local fallback.
- ChromaDB persistence and semantic search for annotated news articles.
- Google Gemini reasoning with confidence, decision factors, summaries, and traceable reasoning.
- Input quality reports containing record counts, missing-value counts, and data sources.
- MongoDB persistence for market snapshots, agent state, analysis results, recommendations, risk assessments, and quality reports.
- Recent analysis summaries and searchable analysis history in the Streamlit dashboard.
- Optional conditional agent routing and MongoDB LangGraph checkpointing.
- Interactive Streamlit dashboard with stock data, sentiment, forecasts, risk metrics, execution details, backtesting, and portfolio views.
- Command-line execution for scripted analysis.

## Project Structure

```text
app/
  streamlit_app.py       Streamlit dashboard
  pages/                 Backtesting and portfolio pages
src/
  agents/                LangGraph state, nodes, and workflow
  pipeline/              Market ingestion, NLP, vector search, and MongoDB storage
  tools/                 Data, sentiment, quantitative, and LLM utilities
  utils/                 Configuration and serialization helpers
backtester/              Backtesting engine, metrics, reports, and utilities
models/                  Forecasting model implementations
scripts/                 Database setup and data utilities
tests/                   Automated tests
notebooks/               Exploration and modeling notebooks
main.py                  Command-line entry point
requirements.txt         Python dependencies
```

## Requirements

- Python 3.10 or newer
- Git
- MongoDB, if persistence or checkpointing is required
- API keys for the providers you want to use

The application can use yFinance without an API key. Alpha Vantage, NewsAPI, Gemini, and MongoDB features require their corresponding configuration.

## Installation

```bash
git clone https://github.com/your-username/investment-agent-ai.git
cd investment-agent-ai

python -m venv .venv

# Linux/macOS
source .venv/bin/activate

# Windows PowerShell
.venv\\Scripts\\Activate.ps1

pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the repository root. Never commit this file because it contains secrets.

```dotenv
GOOGLE_API_KEY=your_gemini_api_key

# Required for MongoDB persistence and LangGraph checkpointing
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB_NAME=investment_agent_db
MONGODB_COLLECTION_NAME=checkpoints

# Optional data providers
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
NEWS_API_KEY=your_newsapi_key
FMP_API_KEY=your_fmp_key

# Optional model and storage overrides
GEMINI_MODEL=gemini-1.5-flash
FINBERT_MODEL=ProsusAI/finbert
EMBEDDING_MODEL=all-MiniLM-L6-v2
CHROMA_PERSIST_DIR=data/chroma_db
```

`GOOGLE_API_KEY` and `MONGODB_URI` are required by `Config.validate()`. MongoDB is only needed when using persistence or checkpointing; analyses that do not enable those features can run without it. The ingestion and NLP layers also provide fallbacks when optional provider keys or local models are unavailable.

## Initialize Local Storage

The setup script creates local data directories, initializes the ChromaDB collection, and tests MongoDB when `MONGODB_URI` is configured:

```bash
python scripts/seed_database.py
```

## Run an Analysis

### Command line

```bash
python main.py AAPL
python main.py AAPL --query "Should I buy this stock?"
python main.py AAPL --conditional
python main.py AAPL --mongodb --thread-id aapl-demo-001
```

The `--thread-id` option is required when `--mongodb` is enabled. The command prints data acquisition, sentiment, financial reasoning, risk assessment, validation, and execution metadata.

### Streamlit dashboard

```bash
streamlit run app/streamlit_app.py
```

From the dashboard you can enter a ticker and question, choose conditional routing, enable MongoDB persistence, and inspect the resulting analysis. With MongoDB enabled, the dashboard also shows recent runs and searchable history. Additional pages provide backtesting and portfolio analysis.

## Data and Analysis Pipeline

1. Fetch and normalize market data, fundamentals, historical prices, and news.
2. Generate a data-quality report and record the sources used.
3. Annotate news with sentiment, entities, and embeddings.
4. Persist news embeddings in ChromaDB for semantic retrieval.
5. Calculate technical, fundamental, and risk metrics.
6. Use Gemini to synthesize the evidence into a recommendation.
7. Validate the recommendation against risk and compliance rules.
8. Save an auditable analysis run and its queryable result slices to MongoDB when enabled.

## Testing

Run the test suite from the repository root:

```bash
python -m pytest -q
```

The tests include agent behavior, data tools, sentiment tools, LLM helpers, quantitative calculations, environment handling, and the end-to-end pipeline with injected test dependencies.

## Responsible Use

InvestSage provides informational analysis only. Market data may be delayed or incomplete, model outputs can be wrong, and recommendations should be independently verified. Do not use the system as the sole basis for financial decisions, and do not commit API keys or other credentials to source control.

## License

See [LICENSE](LICENSE).
