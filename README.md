# 🤖 InvestSage - AI Investment Agent

**An Agentic AI System for Intelligent Investment Decision-Making**

## 📖 Overview

**What	it	is -** InvestSage	is	a	multi-agent	AI	investment	advisory	assistant	that	turns	scattered	financial
news	and	sentiment	into	a	single,	personalized,	explainable,	risk-aware	recommendation	—	with	every claim	traceable	to	a	source	and	every	output	checked	against	compliance	rules	before	reaching	the	user.

**What problem it solves -** It	closes	the	gap	between	"raw	information	overload"	and	"actionable,
trustworthy	guidance,"	without	pretending	to	replace	a	licensed	advisor	and	without	executing	trades
autonomously.

**What	it	does.**
1.	User	asks	a	natural-language	investment	question	through	a	simple	chat	interface.
2.	The	system	retrieves	relevant	recent	news/filings,	extracts	key entities,	scores	sentiment,	and	generates	a	recommendation	tailored	to	the	user's	declared	risk	profile
(conservative/moderate/aggressive).
3.	Every	recommendation	shows	its	sources	and	a	plain-language rationale,	and	carries	a	mandatory	advisory	disclaimer.
4.	All	of	this	happens	behind	an	authentication	+ input-sanitization	+	compliance-validation	layer	that	a	single	chatbot	wouldn't	have.
   
**Value	provided.**	
- Time	saved	(no	manual	cross-referencing	of	news/filings)
- better-calibrated	decisions (grounded	in	retrieved	evidence,	not	the	LLM's	memory)
- trust	(transparency	into	why	a recommendation	was	made,	not	just	what	it	is)
  
This project was developed as part of the **Information Retrieval and Web Analytics (IT 3041)** course and demonstrates:
- Seamless integration of 4 specialized AI agents
- Advanced NLP techniques (Sentiment Analysis, NER, Summarization)
- Information Retrieval via RAG (Retrieval-Augmented Generation)
- Enterprise-grade security and Responsible AI practices
- A clear commercialization strategy with freemium pricing

## ✨ Key Features

| Feature | Description |
|---------|-------------|
| **🧠 Multi-Agent Architecture** | 4 specialized agents collaborate to analyze stocks |
| **📊 Real-Time Market Data** | Fetches live stock prices, fundamentals, and technical indicators |
| **📰 Sentiment Analysis** | FinBERT-powered NLP analysis of financial news |
| **📈 Quantitative Analysis** | RSI, MACD, volatility, Sharpe ratio, VaR calculations |
| **🤖 LLM-Powered Decision Making** | Google Gemini synthesizes all inputs into actionable recommendations |
| **🔐 Enterprise Security** | Input sanitization, API key encryption, authentication |
| **📱 Interactive Dashboard** | Streamlit UI with real-time visualizations |
| **📝 Explainable AI** | Full reasoning traceability for every decision |
| **💰 Commercialization Ready** | Freemium pricing model with clear target market |

# 🛠️ Technology Stack

### Core Technologies
| Category | Technology | Purpose |
|----------|------------|---------|
| **Orchestration** | LangGraph | Agent workflow and state management |
| **LLM** | Google Gemini 1.5 Flash | Decision synthesis and reasoning |
| **NLP** | FinBERT, spaCy | Sentiment analysis, NER, summarization |
| **Information Retrieval** | ChromaDB, RAG | News storage and semantic search |
| **Data Processing** | pandas, numpy | Data manipulation and analysis |
| **Machine Learning** | TensorFlow, scikit-learn | LSTM models, technical indicators |
| **Visualization** | Streamlit, Plotly | Interactive dashboard |
| **Security** | python-dotenv | API key management |

### APIs & Data Sources
| Service | Purpose | Free Tier |
|---------|---------|-----------|
| Google Gemini | LLM reasoning | 15 req/min, 1,500/day |
| yFinance | Market data | Unlimited (unofficial) |
| Alpha Vantage | Historical data | 5 req/min, 500/day |
| Financial Modeling Prep | Fundamentals | 250 calls/day |
| NewsAPI | Financial news | 100 calls/day |

## 💻 Installation
### Prerequisites
- Python 3.10 or higher
- Git
- Virtual environment (recommended)

### Step 1: Clone the Repository
```bash
git clone https://github.com/your-username/investment-agent-ai.git
cd investment-agent-ai

### Step 2: Create Virtual Environment 
python -m venv .venv
source .venv/bin/activate        # On Linux/Mac
# OR
.venv\Scripts\activate           # On Windows

### Step 3: Install Dependencies
pip install -r requirements.txt

### Step 4: Set Up Environment Variables
cp .env.example .env

### Step 5: Initialize Databases
python scripts/seed_database.py

### Step: How to run
python main.py

### Step 8: Run web interface
 streamlit run app/streamlit_app.py

