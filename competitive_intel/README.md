# 🎯 CompeteIQ — Automated Competitive Intelligence Pipeline

> A production-grade agentic pipeline that automatically researches competitors, analyzes them against your internal docs, scores threat levels, and generates a structured intelligence briefing — in under 2 minutes.

## 🏗️ Architecture

```
User Input (competitors + focus area)
            │
            ▼
    ┌───────────────┐
    │  🔍 Scraper   │  → Tavily web search for each competitor
    └───────┬───────┘
            ▼
    ┌───────────────┐
    │  🧠 Analyzer  │  → Compares against your ChromaDB docs
    └───────┬───────┘
            ▼
    ┌───────────────┐
    │  📊 Scorer    │  → Rates each competitor 1-10 threat level
    └───────┬───────┘
            ▼
    ┌───────────────┐
    │  ✍️ Reporter  │  → Writes structured intelligence brief
    └───────┬───────┘
            ▼
    📄 Downloadable PDF Brief
```

## 🚀 Setup

```bash
pip install -r requirements.txt
cp .env.example .env
# fill in your API keys
streamlit run app.py
```

## 🔑 Free API Keys
- Groq: https://console.groq.com
- Tavily: https://tavily.com
- LangSmith (optional): https://smith.langchain.com

## 💼 Business Problem Solved
Replaces 4-6 hours of manual weekly competitive research with a 2-minute automated pipeline.
