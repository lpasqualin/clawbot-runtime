# TOOLS.md — Belfort

## Market Data (No Key Required)
- mkts-market-data: stocks, crypto, ETFs, forex, screening
- yahoo-finance: fundamentals, earnings, options chain, dividends
- coingecko: crypto prices, market cap, trending
- crypto-market-data: crypto + stock data
- fred-navigator: macro — rates, inflation, GDP, housing

## Market Data (Key Required — add to /etc/openclaw.env)
- cmc-api-crypto: CoinMarketCap quotes, OHLCV, trending (CMC_API_KEY)
- cmc-api-market: global metrics, fear/greed index (CMC_API_KEY)
- cmc-api-onchain-data: DEX, on-chain, token security (CMC_API_KEY)

## Analysis
- stock-analysis: portfolio, watchlists, hot scanner, rumor detection
- fundamental-stock-analysis: equity scoring, peer ranking
- riskofficer: VaR, Monte Carlo, stress testing, portfolio risk

## Intelligence
- market-sentiment-pulse: news + social signals per ticker
- market-news: financial news feed
- sec-watcher: SEC EDGAR filings real-time
- polymarket-odds: prediction market odds (no key)

## Public APIs (via exec/fetch)
- CoinGecko: https://api.coingecko.com/api/v3
- Fear & Greed: https://api.alternative.me/fng/
- FRED: https://fred.stlouisfed.org/docs/api/fred/
- SEC EDGAR: https://data.sec.gov/
- Alpaca paper trading: https://paper-api.alpaca.markets (key needed)
