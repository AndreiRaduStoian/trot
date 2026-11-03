import ccxt, time

# for e in ccxt.exchanges:
#     exchange = getattr(ccxt, e)()
#     try:
#         markets = exchange.fetchMarkets()
#         markets = list(markets)
#         for m in markets:
#             if m['base'] == "BTC":
#                 symbol = m['symbol']
#                 ohlcv = exchange.fetch_ohlcv(symbol,'1d',limit=100)
#                 print(exchange, symbol, ohlcv)
#     except:
#         print(exchange, "err")


kraken = getattr(ccxt, "kraken")()
markets = kraken.fetchMarkets()
for m in markets:
    if m['base'] == "BTC":
        symbol = m['symbol']
        print(symbol)
        time.sleep(0.01)
        # ohlcv = kraken.fetch_ohlcv(symbol,'1d',limit=100)
        # print(kraken, symbol, ohlcv)
