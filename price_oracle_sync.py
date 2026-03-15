import os
import time
import pandas as pd
import ccxt

if not os.path.exists("audit_events.csv"):
    exit(0)

df = pd.read_csv("audit_events.csv")
exchange = ccxt.binance({'enableRateLimit': True})

print("⚡ [ORACLE] Alinhando K-lines (T+1) para aniquilação de Look-ahead Bias...")

prices_weth = []
prices_wbtc = []

for idx, row in df.iterrows():
    ts = int(row['timestamp'])
    since_ms = (ts + 60) * 1000 
    
    try:
        eth_kline = exchange.fetch_ohlcv('ETH/USDT', timeframe='1m', since=since_ms, limit=1)
        btc_kline = exchange.fetch_ohlcv('BTC/USDT', timeframe='1m', since=since_ms, limit=1)
        
        p_eth = eth_kline[0][4] if eth_kline else 0
        p_btc = btc_kline[0][4] if btc_kline else 0
        
        prices_weth.append(p_eth)
        prices_wbtc.append(p_btc)
    except Exception as e:
        print(f"🟡 [ORACLE] Rate Limit ou Falha no CCXT: {e}")
        prices_weth.append(0)
        prices_wbtc.append(0)
        
df['price_eth'] = prices_weth
df['price_btc'] = prices_wbtc

df = df[(df['price_eth'] > 0) & (df['price_btc'] > 0)].copy()

df.to_csv("audit_prices.csv", index=False)
print(f"🟢 [ORACLE] Preços históricos sincronizados. Matriz gerada: audit_prices.csv.")
