import ccxt
import pandas as pd
import time
import schedule
import requests
from datetime import datetime
import sys
import numpy as np

# ==========================================
# 🎮 V5.2 模拟盘 (免安装版 - 终极修复)
# ==========================================
SIMULATION_MODE = True
FAKE_BALANCE = 1000.0
PUSHPLUS_TOKEN = '' 

PAIRS = {
    'ETH/USDT': {'rsi_len': 7, 'rsi_long': 25, 'rsi_short': 75, 'sl_atr': 2.5, 'tp_atr': 3.5, 'max_drop': 0.03},
    'SOL/USDT': {'rsi_len': 7, 'rsi_long': 20, 'rsi_short': 80, 'sl_atr': 3.0, 'tp_atr': 4.5, 'max_drop': 0.05}
}

print(f"🚀 启动 V5.2 (免组件版)... 初始资金: {FAKE_BALANCE} U")

try:
    exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
    print("✅ 交易所连接成功")
except:
    print("❌ 连接失败，请检查网络")
    sys.exit()

sim_pos = {'ETH/USDT': None, 'SOL/USDT': None}

# --- 手写数学公式 (替代难装的库) ---
def calc_rsi(series, period):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.ewm(com=period-1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period-1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calc_atr(df, period):
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    return true_range.rolling(period).mean()

def send_msg(title, content):
    print(f"🔔 {title}: {content}")
    if PUSHPLUS_TOKEN:
        try: requests.post('http://www.pushplus.plus/send', json={"token": PUSHPLUS_TOKEN, "title": title, "content": content})
        except: pass

def fetch_data(symbol):
    try:
        bars = exchange.fetch_ohlcv(symbol, timeframe='15m', limit=200)
        df = pd.DataFrame(bars, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
        return df
    except: return None

def check_exit(symbol, price):
    global FAKE_BALANCE, sim_pos
    pos = sim_pos[symbol]
    if not pos: return

    pnl = 0
    closed = False
    
    if pos['side'] == 'buy':
        if price <= pos['sl']:
            pnl = (pos['sl'] - pos['entry']) * pos['qty']
            closed = True
            t = "止损"
        elif price >= pos['tp']:
            pnl = (pos['tp'] - pos['entry']) * pos['qty']
            closed = True
            t = "止盈"
    else:
        if price >= pos['sl']:
            pnl = (pos['entry'] - pos['sl']) * pos['qty']
            closed = True
            t = "止损"
        elif price <= pos['tp']:
            pnl = (pos['entry'] - pos['tp']) * pos['qty']
            closed = True
            t = "止盈"
            
    if closed:
        FAKE_BALANCE += pnl
        send_msg(f"🎮 平仓-{t}", f"{symbol} 盈亏: {pnl:.2f} U\n余额: {FAKE_BALANCE:.2f}")
        sim_pos[symbol] = None

def job():
    print(f"[{datetime.now().strftime('%H:%M')}] 监控中... 余额: {FAKE_BALANCE:.2f}")
    for symbol in PAIRS.keys():
        df = fetch_data(symbol)
        if df is None: continue
        price = df.iloc[-1]['close']
        
        check_exit(symbol, price)
        if sim_pos[symbol] is not None: continue

        # 计算指标
        df['ema'] = df['close'].ewm(span=200, adjust=False).mean()
        df['rsi'] = calc_rsi(df['close'], PAIRS[symbol]['rsi_len'])
        df['atr'] = calc_atr(df, 14)
        
        prev = df.iloc[-2]
        cfg = PAIRS[symbol]
        
        # 熔断
        drop = (prev['open'] - prev['close']) / prev['open']
        if drop > cfg['max_drop']: continue

        long_cond = (prev['close'] > prev['ema']) and (prev['rsi'] < cfg['rsi_long']) and (prev['close'] > prev['open'])
        short_cond = (prev['close'] < prev['ema']) and (prev['rsi'] > cfg['rsi_short']) and (prev['close'] < prev['open'])
        
        side = None
        if long_cond: side = 'buy'
        elif short_cond: side = 'sell'
        
        if side:
            sl_dist = prev['atr'] * cfg['sl_atr']
            if pd.isna(sl_dist) or sl_dist == 0: continue
            qty = (FAKE_BALANCE * 0.025) / sl_dist
            
            if side == 'buy':
                sl = price - sl_dist
                tp = price + (sl_dist * cfg['tp_atr'])
            else:
                sl = price + sl_dist
                tp = price - (sl_dist * cfg['tp_atr'])
                
            sim_pos[symbol] = {'side': side, 'entry': price, 'qty': qty, 'sl': sl, 'tp': tp}
            send_msg(f"🎮 开仓成功", f"{symbol} {side}\n价: {price}\n损: {sl:.4f}\n盈: {tp:.4f}")

schedule.every(1).minutes.do(job)
job()
while True:
    schedule.run_pending()
    time.sleep(1)