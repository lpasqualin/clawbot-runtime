---
name: fred-navigator
description: Query FRED (Federal Reserve Economic Data) for macroeconomic data. Use when Oracle needs interest rates, inflation, GDP, unemployment, housing data, or any US economic indicators. No API key required for basic access.
metadata: {"openclaw":{"emoji":"📊"}}
---

# FRED Navigator

Query the Federal Reserve Economic Data (FRED) database for macroeconomic indicators.
Free, no API key required for basic access.

## Base URL
```
https://fred.stlouisfed.org/graph/fredgraph.csv?id={SERIES_ID}
```

## Common Series IDs

### Interest Rates
- `FEDFUNDS` — Federal Funds Rate
- `DGS10` — 10-Year Treasury Rate
- `DGS30` — 30-Year Treasury Rate
- `MORTGAGE30US` — 30-Year Fixed Mortgage Rate

### Inflation
- `CPIAUCSL` — Consumer Price Index (CPI)
- `CPILFESL` — Core CPI (ex food & energy)
- `PCEPI` — PCE Price Index (Fed preferred)

### Economy
- `GDP` — Gross Domestic Product
- `GDPC1` — Real GDP
- `UNRATE` — Unemployment Rate
- `PAYEMS` — Total Nonfarm Payrolls

### Housing
- `HOUST` — Housing Starts
- `CSUSHPISA` — Case-Shiller Home Price Index
- `MSPUS` — Median Sales Price of Houses

### Money Supply
- `M2SL` — M2 Money Supply
- `M1SL` — M1 Money Supply

## Usage
```bash
# Get latest mortgage rates
curl "https://fred.stlouisfed.org/graph/fredgraph.csv?id=MORTGAGE30US" | tail -5

# Get unemployment rate
curl "https://fred.stlouisfed.org/graph/fredgraph.csv?id=UNRATE" | tail -5

# Get CPI data
curl "https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL" | tail -12
```

## With API Key (Optional — More Features)

Get a free key at https://fred.stlouisfed.org/docs/api/api_key.html
```bash
# Search for series
curl "https://api.stlouisfed.org/fred/series/search?search_text=mortgage&api_key={KEY}&file_type=json"

# Get series data with date range
curl "https://api.stlouisfed.org/fred/series/observations?series_id=MORTGAGE30US&observation_start=2024-01-01&api_key={KEY}&file_type=json"
```

## Output Format for Oracle

When reporting FRED data, always include:
- Series name and ID
- Latest value and date
- 3-month and 12-month trend
- What it means for the business context being researched
