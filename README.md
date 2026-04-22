# Gold Investment Projection System

A modular web-based gold investment projection system built with FastAPI and vanilla HTML/CSS/JavaScript.

## Features

- Live gold pricing using Yahoo Finance market data
- Historical gold trend chart
- Current portfolio valuation
- Profit/loss calculation
- AI-style projection for 1, 3, and 5 years using:
  - moving average
  - linear regression
  - CAGR trend
- Manual future value mode
- Optional USD to MYR conversion using live FX data

## Project Structure

```text
backend/
  app.py
  routes/
    __init__.py
    forecast.py
    gold_data.py
  services/
    __init__.py
    gold_api_service.py
    prediction_service.py
frontend/
  index.html
  style.css
  formModule.js
  chartModule.js
  apiService.js
example_dataset.json
requirements.txt
```

## Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.app:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

## Notes

- Live data depends on external market endpoints being available.
- Projection output is an estimate and not financial advice.
- Historical prices are sourced in USD per troy ounce and converted to price per gram in the selected display currency.
