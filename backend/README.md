# SkyLark Business Intelligence AI Agent - Backend

A production-ready FastAPI backend for a founder-facing Business Intelligence AI agent that integrates with monday.com.

## Features

- **Dynamic monday.com Integration**: Connects to Deals and Work Orders boards via GraphQL API
- **Data Cleaning & Normalization**: Handles messy real-world data with comprehensive error handling
- **Business Metrics Computation**: Founder-level metrics including pipeline analysis, revenue tracking, and collection efficiency
- **AI-Powered Insights**: Uses Groq API for intent extraction and executive summary generation
- **Data Quality Tracking**: Identifies and reports data quality issues

## Project Structure

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Configuration and settings
│   ├── dependencies.py         # Dependency injection
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py          # Pydantic models
│   │
│   ├── monday_client/
│   │   ├── __init__.py
│   │   ├── client.py           # monday.com API client
│   │   └── queries.py          # GraphQL queries
│   │
│   ├── data_cleaner/
│   │   ├── __init__.py
│   │   └── cleaner.py          # Data normalization
│   │
│   ├── business_logic/
│   │   ├── __init__.py
│   │   └── metrics.py          # Metrics computation
│   │
│   ├── ai_service/
│   │   ├── __init__.py
│   │   ├── service.py          # Groq API integration
│   │   └── prompts.py          # Prompt templates
│   │
│   └── routers/
│       ├── __init__.py
│       └── ask.py              # API endpoints
│
├── tests/
│   └── ...
│
├── .env.example
├── requirements.txt
└── README.md
```

## Setup

### 1. Install Dependencies

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

Required environment variables:
- `MONDAY_API_KEY`: Your monday.com API key
- `DEALS_BOARD_ID`: ID of your Deals board
- `WORK_ORDERS_BOARD_ID`: ID of your Work Orders board
- `GROQ_API_KEY`: Your Groq API key

### 3. Run the Server

```bash
uvicorn app.main:app --reload --port 8000
```

## API Endpoints

### POST /ask
Process a natural language business question.

**Request:**
```json
{
    "question": "What's our pipeline value for the technology sector?",
    "include_raw_data": false
}
```

**Response:**
```json
{
    "insights": "Your technology sector pipeline is currently valued at $2.5M...",
    "key_metrics": [...],
    "data_quality_warnings": [...],
    "intent": {...},
    "confidence": 0.85,
    "requires_clarification": false,
    "processing_time_ms": 1234
}
```

### GET /health
Health check endpoint.

### GET /boards/summary
Get summary information about connected monday.com boards.

## Modules

### monday_client
- Connects to monday.com GraphQL API
- Handles pagination for large datasets
- Converts column_values to structured dictionaries
- Error handling for API failures

### data_cleaner
- Normalizes sector names (strip spaces, lowercase, resolve inconsistencies)
- Parses numeric values (including scientific notation, currencies)
- Parses date fields with multiple format support
- Tracks data quality warnings

### business_logic
Computes metrics:
- Total pipeline value
- Pipeline by sector
- Open vs closed deal ratio
- Revenue by sector
- Invoiced vs collected amounts
- Collection efficiency
- Pipeline vs revenue comparison

### ai_service
- Intent extraction from natural language queries
- Executive summary generation
- Clarification prompt handling

## Development

### Running Tests
```bash
pytest tests/ -v
```

### Code Formatting
```bash
black app/
isort app/
```

### Type Checking
```bash
mypy app/
```

## Expected Board Structure

### Deals Board
Expected columns (flexible naming):
- Deal name
- Sector/Industry
- Deal value/Amount
- Status
- Close date
- Owner

### Work Orders Board
Expected columns (flexible naming):
- Order name
- Sector/Industry
- Invoiced amount
- Collected amount
- Status
- Invoice date
- Collection date
