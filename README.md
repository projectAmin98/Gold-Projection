# Gold Investment Projection System

A modular web-based gold investment projection system built with FastAPI and vanilla HTML/CSS/JavaScript.

## Features

- Live gold pricing using Yahoo Finance market data
- Historical gold trend chart
- Current portfolio valuation
- Malaysia investment reference using spot price for analytics and dealer buyback for realistic sell value
- Profit/loss calculation
- AI-style projection for custom years using:
  - moving average
  - linear regression
  - CAGR trend
- Manual future value mode
- Optional USD to MYR conversion using live FX data
- Chart range switching for days, months, and years
- Gold calculator panel

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
  calculatorModule.js
  index.html
  style.css
  formModule.js
  chartModule.js
  apiService.js
example_dataset.json
requirements.txt
render.yaml
Procfile
```

## Local Run

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000
```

## GitHub Setup

Create a new empty GitHub repository, then run:

```bash
git init
git add .
git commit -m "Initial Gold Investment Projection System"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git push -u origin main
```

If the repo already exists locally:

```bash
git add .
git commit -m "Update project"
git push
```

## Render Deploy

This project is ready for Render deployment with [render.yaml](./render.yaml).

### Option 1: Blueprint Deploy

1. Push this project to GitHub.
2. Open [Render](https://render.com/).
3. Choose `New` -> `Blueprint`.
4. Select your GitHub repository.
5. Render will detect `render.yaml` and deploy automatically.

### Option 2: Manual Web Service

1. Push this project to GitHub.
2. Open [Render](https://render.com/).
3. Choose `New` -> `Web Service`.
4. Connect the repository.
5. Use these settings:

```text
Runtime: Python
Build Command: pip install -r requirements.txt
Start Command: uvicorn backend.app:app --host 0.0.0.0 --port $PORT
```

## Deploy Notes

- Live data depends on external market endpoints being available.
- Projection output is an estimate and not financial advice.
- Historical prices are sourced in USD per troy ounce and converted to price per gram in the selected display currency.
- Malaysia analytics logic uses spot/raw-material pricing, while realistic sell value uses dealer buyback pricing.
- GitHub Pages alone is not suitable for this project because the backend must run Python/FastAPI.
