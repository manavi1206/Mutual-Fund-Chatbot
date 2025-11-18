# HDFC Mutual Fund FAQ Assistant

A RAG-based chatbot that answers factual questions about HDFC mutual fund schemes using verified sources from AMC, SEBI, and AMFI websites. Provides concise, citation-backed responses while strictly avoiding investment advice.

![Milestone 1](https://img.shields.io/badge/Milestone-1%20Complete-green)
![Sources](https://img.shields.io/badge/Sources-26%20Official-blue)
![Schemes](https://img.shields.io/badge/Schemes-4%20HDFC-orange)

---

## 📋 Project Overview

**Assignment**: Milestone 1 - Facts-Only MF Assistant  
**Scope**: HDFC Mutual Fund (4 schemes)  
**Technology**: RAG (Retrieval-Augmented Generation) with Gemini LLM  
**Sources**: 26 official documents from HDFC AMC, SEBI, AMFI, and Groww

### Covered Schemes
1. **HDFC Large Cap Fund** - Invests in large-cap stocks
2. **HDFC Flexi Cap Fund** - Flexible multi-cap allocation
3. **HDFC TaxSaver (ELSS)** - Equity Linked Savings Scheme with 3-year lock-in
4. **HDFC Hybrid Equity Fund** - 65:35 equity-debt hybrid

---

## ✨ Key Features

### Core Functionality
- ✅ **Factual Q&A**: Answers questions about expense ratios, exit loads, minimum SIP, lock-in periods, benchmarks, riskometer, fund managers, and more
- ✅ **Source Citations**: Every answer includes a source link and "Last updated" date
- ✅ **Refuses Investment Advice**: Politely declines "should I invest" questions with educational links
- ✅ **Clarification Handler**: Asks for fund specification when queries are ambiguous (e.g., "minimum SIP" → "Which fund?")
- ✅ **How-to Queries**: Explains procedures like downloading statements, redeeming units, etc.

### Advanced Features
- 🔍 Semantic search with FAISS vector indexing
- 🤖 Gemini LLM for natural language generation
- 🛡️ Safety filters and content validation
- 🎯 Query classification (metric, entity, how-to, comparison)
- ⚠️ Conflict detection between sources
- 💬 Conversation context tracking
- ⚡ Response caching for performance
- 📊 Metrics and logging

### User Interface
- 🎨 Groww-inspired design with modern UI
- 💬 Gemini-like chat interface
- 📱 Mobile-responsive
- 🔗 Clickable source citations
- 💡 5 example questions
- ⚠️ Clear disclaimer about investment advice

---

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Node.js 16+ (for web UI)
- Gemini API key

### 1. Install Dependencies

```bash
# Backend (Python)
pip install -r requirements.txt

# Frontend (Next.js)
cd web
npm install
cd ..
```

### 2. Set Up Environment

Create `.env` file:
```env
GEMINI_API_KEY=your_gemini_api_key_here
USE_LLM=true
LLM_PROVIDER=gemini
ENV=development
```

### 3. Start the Application

**Terminal 1 - Backend:**
```bash
python3 api_server.py
```
(Wait for "RAG system ready!" message)

**Terminal 2 - Frontend:**
```bash
cd web
npm run dev
```

**Open**: http://localhost:3000

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [SAMPLE_QA.md](SAMPLE_QA.md) | 10 example Q&A pairs with actual responses |
| [MILESTONE_CHECKLIST.md](MILESTONE_CHECKLIST.md) | Complete requirements checklist for Milestone 1 |
| [sources.csv](sources.csv) | List of 26 official sources used with URLs and dates |

---

## 📦 Data Sources

### Source Breakdown (26 total):

**HDFC AMC (12 sources):**
- Overview pages (4) - One per scheme
- Scheme Information Documents/SID (4) - Detailed scheme rules
- Key Information Memorandum/KIM (4) - Investor-friendly summaries
- Consolidated Factsheet (1) - Performance metrics

**Regulatory Bodies (7 sources):**
- AMFI - Introduction, Expense Ratio, Riskometer guides (5)
- SEBI - Categorization, ELSS guidelines (2)

**Groww Help Pages (4 sources):**
- How to download CAS (Consolidated Account Statement)
- Tax statements and reports
- Transaction history
- General MF help

See [sources.csv](sources.csv) for complete list with URLs and dates.

---

## 🎯 Sample Queries

Try these questions:

1. "What is the expense ratio of HDFC Large Cap Fund?"
2. "What is the exit load for HDFC ELSS?"
3. "What is the minimum SIP amount for HDFC Flexi Cap Fund?"
4. "What is the lock-in period of HDFC TaxSaver (ELSS)?"
5. "Who manages the HDFC Flexi Cap Fund?"
6. "What is the benchmark of HDFC Hybrid Equity Fund?"
7. "What is the riskometer level for HDFC Large Cap Fund?"
8. "How do I redeem my HDFC Large Cap Fund units?"
9. "How do I download my capital gains statement?"
10. "What is the investment strategy of HDFC Hybrid Equity Fund?"

**See full responses**: [SAMPLE_QA.md](SAMPLE_QA.md)

---

## 🛡️ Safety & Compliance

### Investment Advice Refusal
The system **refuses** to answer:
- "Should I invest in X?"
- "Which fund is better?"
- "Is now a good time to buy?"
- Any recommendation or personalized advice

**Response**: Polite refusal + link to AMFI investor education

### No PII Collection
The system does **NOT** accept or store:
- PAN, Aadhaar, account numbers
- OTPs, passwords
- Email addresses, phone numbers
- Personal financial data

### No Performance Claims
- Does not compute or compare returns
- Links to official factsheet when asked about performance
- Shows only factual metrics (expense ratio, exit load, etc.)

---

## 📊 System Architecture

```
┌─────────────┐
│   User UI   │  (Next.js Frontend)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  FastAPI    │  (api_server.py)
│   Server    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ RAG System  │  (rag_system.py)
└──────┬──────┘
       │
       ├──► Retriever (rag_retriever.py)
       │    └──► FAISS Index (1886 vectors)
       │
       ├──► Q&A LLM (rag_qa_llm.py)
       │    └──► Gemini API
       │
       ├──► Clarification (clarification_handler.py)
       ├──► Safety Filters (safety_filters.py)
       ├──► Conflict Detection (conflict_detector.py)
       └──► Query Classifier (query_classifier.py)
```

---

## 🧪 Testing

Run comprehensive test suite:

```bash
python3 test_queries.py
```

Tests cover:
- ✅ Metric queries (expense ratio, exit load, minimum SIP)
- ✅ Entity queries (fund managers, benchmarks)
- ✅ How-to queries (redemption, statements)
- ✅ Validation of answers (relevance, citations, length)
- ✅ Source URL verification

---

## ⚙️ Tech Stack

**Backend:**
- Python 3.8+
- FastAPI (API server)
- LangChain (RAG orchestration)
- FAISS (vector search)
- Sentence Transformers (embeddings)
- Google Gemini (LLM)

**Frontend:**
- Next.js 14
- React 18
- TypeScript
- CSS Modules

**Data:**
- 26 official sources (PDFs + HTML)
- ~1,886 semantic chunks
- FAISS vector index

---

## 📝 Known Limitations

1. **Scope**: Only covers 4 HDFC schemes (Large Cap, Flexi Cap, ELSS, Hybrid)
2. **Data Currency**: Sources last updated Nov 17-18, 2025
3. **No Real-time Data**: Cannot fetch live NAV or market prices
4. **No Performance Comparison**: Links to factsheet instead of computing returns
5. **Single Language**: English only
6. **Text-based**: No voice input/output
7. **No Document Upload**: Cannot process user-uploaded PDFs

---

## 🎓 Skills Demonstrated

### W1 - Thinking Like a Model
- ✅ Identifies exact facts asked
- ✅ Decides answer vs. refuse appropriately
- ✅ Handles ambiguous queries with clarification

### W2 - LLMs & Prompting
- ✅ Concise, instructional prompts
- ✅ Polite refusals with educational links
- ✅ Proper citation formatting

### W3 - RAG Systems
- ✅ Small-corpus retrieval (26 sources → 1,886 chunks)
- ✅ Accurate citations from AMC/SEBI/AMFI pages
- ✅ FAISS vector indexing with semantic search
- ✅ Reranking for improved relevance

---

## 📄 Disclaimer

**This is an educational project for demonstrating RAG-based Q&A systems.**

⚠️ **Important Notes:**
- This assistant provides **factual information only**, not investment advice
- For personalized investment guidance, consult a SEBI-registered financial advisor
- Information is based on sources dated November 2025 and may become outdated
- Always verify critical information with official AMC/SEBI sources
- Past performance does not guarantee future results

---

## 👨‍💻 Project Structure

```
Groww- MF ChatBot/
├── api_server.py              # FastAPI server
├── rag_system.py              # Main RAG orchestrator
├── rag_retriever.py           # FAISS-based retrieval
├── rag_qa_llm.py              # LLM-powered Q&A
├── clarification_handler.py   # Ambiguity detection
├── query_classifier.py        # Query type classification
├── safety_filters.py          # Content safety
├── conflict_detector.py       # Source conflict detection
├── conversation_manager.py    # Session management
├── sources.csv                # 26 official sources
├── data_raw/                  # Original PDFs and HTML
├── data_processed/            # Cleaned text
├── embeddings/                # FAISS index
├── web/                       # Next.js frontend
│   ├── app/
│   │   ├── page.tsx          # Main chat UI
│   │   └── api/query/route.ts # API endpoint
│   └── package.json
├── SAMPLE_QA.md              # Example Q&A pairs
├── MILESTONE_CHECKLIST.md    # Requirements checklist
├── README.md                 # This file
└── requirements.txt          # Python dependencies
```

---

## 📫 Contact & Support

For questions about this project:
- Review the [documentation](#-documentation)
- Check [SAMPLE_QA.md](SAMPLE_QA.md) for example Q&A
- See [Quick Start](#-quick-start) for setup instructions

---

## 📜 License

Educational project for RAG system demonstration.  
Sources remain property of respective organizations (HDFC AMC, SEBI, AMFI, Groww).

---

**Last Updated**: November 18, 2025  
**Version**: 1.0  
**Milestone**: 1 Complete ✅


