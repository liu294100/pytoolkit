import ccxt
import pandas as pd
import time
import schedule
import requests
from datetime import datetime
import sys
import numpy as np

# ==========================================
# 🏛️ V10.0 [Titan] 模拟盘专用
# ==========================================
SIMULATION_MODE = True
FAKE_BALANCE = 1000.0
PUSHPLUS_TOKEN = '' # 填你的微信推送token

# --- 资金管理 ---
RISK_PER_TRADE = 0.03   # 3% 风险
MAX_OPEN_POSITIONS = 2  # 只有两类资产

# --- V10.0 核心配置 ---
PAIRS = {
    # 黄金 (稳健)
    'XAU/USDT': {'leverage': 5, 'ema': 144, 'rsi_len': 14, 'rsi_buy': 30, 'rsi_sell': 70, 'sl_atr': 2.0, 'tp_atr': 3.0},
    # SOL (激进)
    'SOL/USDT': {'leverage': 5, 'ema': 144, 'rsi_len': 14, 'rsi_buy': 30, 'rsi_sell': 70, 'sl_atr': 2.5, 'tp_atr': 4.0}
}

print(f"🏛️ 启动 V10.0 [Titan] 模拟盘... 初始资金: {FAKE_BALANCE} U")

try:
    exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
    print("✅ 交易所连接成功")
except:
    print("❌ 连接失败")
    sys.exit()

sim_positions = {} 

# --- 手写核心算法 ---
def calc_ema(series, span):
    return series.ewm(span=span, adjust=False).mean()

def calc_rsi(series, period):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.ewm(com=period-1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period-1, min_periods=period).mean()
    return 100 - (100 / (1 + (avg_gain / avg_loss)))

def calc_atr(df, period):
    h_l = df['high'] - df['low']
    h_c = (df['high'] - df['close'].shift()).abs()
    l_c = (df['low'] - df['close'].shift()).abs()
    return pd.concat([h_l, h_c, l_c], axis=1).max(axis=1).rolling(period).mean()

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

def manage_positions(symbol, curr_price, atr_value):
    global FAKE_BALANCE, sim_positions
    if symbol not in sim_positions: return
    pos = sim_positions[symbol]
    pnl, closed, reason = 0, False, ""
    
    # 浮盈计算
    dist = (curr_price - pos['entry']) if pos['side']=='buy' else (pos['entry'] - curr_price)
    pnl_raw = dist * pos['qty']

    # V10保本逻辑: 浮盈 > 1.5倍止损距离
    risk_dist = atr_value * PAIRS[symbol]['sl_atr']
    if not pos.get('breakeven', False):
        if dist > (risk_dist * 1.5):
            pos['sl'] = pos['entry']
            pos['breakeven'] = True
            send_msg(f"🛡️ 泰坦保本", f"{symbol} 浮盈达标，止损上移至开仓价")

    if pos['side'] == 'buy':
        if curr_price <= pos['sl']: closed, reason = True, "止损/保本"
        elif curr_price >= pos['tp']: closed, reason = True, "止盈"
    else:
        if curr_price >= pos['sl']: closed, reason = True, "止损/保本"
        elif curr_price <= pos['tp']: closed, reason = True, "止盈"
            
    if closed:
        if pos['side'] == 'buy':
            pnl = (pos['sl'] - pos['entry']) * pos['qty'] if "止损" in reason else (pos['tp'] - pos['entry']) * pos['qty']
        else:
            pnl = (pos['entry'] - pos['sl']) * pos['qty'] if "止损" in reason else (pos['entry'] - pos['tp']) * pos['qty']
        
        FAKE_BALANCE += pnl
        send_msg(f"💰 平仓-{reason}", f"{symbol} 盈亏: {pnl:.2f} U\n余额: {FAKE_BALANCE:.2f}")
        del sim_positions[symbol]

def job():
    count = len(sim_positions)
    print(f"[{datetime.now().strftime('%H:%M')}] 泰坦监控中... 余额: {FAKE_BALANCE:.2f}")
    
    for symbol in PAIRS.keys():
        df = fetch_data(symbol)
        if df is None: continue
        price = df.iloc[-1]['close']
        
        df['ema'] = calc_ema(df['close'], PAIRS[symbol]['ema'])
        df['rsi'] = calc_rsi(df['close'], PAIRS[symbol]['rsi_len'])
        df['atr'] = calc_atr(df, 14)
        atr_val = df.iloc[-1]['atr']
        if pd.isna(atr_val): continue

        manage_positions(symbol, price, atr_val)
        if symbol in sim_positions or count >= MAX_OPEN_POSITIONS: continue

        prev = df.iloc[-2]
        cfg = PAIRS[symbol]
        
        # --- V10 信号: 趋势+回调+确认 ---
        bull = prev['close'] > prev['ema']
        bear = prev['close'] < prev['ema']
        oversold = prev['rsi'] < cfg['rsi_buy']
        overbought = prev['rsi'] > cfg['rsi_sell']
        
        # K线确认: 必须收盘价 > 开盘价 (阳线) 才做多
        confirm_buy = prev['close'] > prev['open']
        confirm_sell = prev['close'] < prev['open']

        go_long = bull and oversold and confirm_buy
        go_short = bear and overbought and confirm_sell
        
        side = 'buy' if go_long else 'sell' if go_short else None
        
        if side:
            sl_dist = atr_val * cfg['sl_atr']
            if sl_dist == 0: continue
            qty = (FAKE_BALANCE * RISK_PER_TRADE) / sl_dist
            
            if side == 'buy':
                sl = price - sl_dist
                tp = price + (sl_dist * cfg['tp_atr'])
            else:
                sl = price + sl_dist
                tp = price - (sl_dist * cfg['tp_atr'])
            
            sim_positions[symbol] = {'side': side, 'entry': price, 'qty': qty, 'sl': sl, 'tp': tp, 'breakeven': False}
            send_msg(f"🚀 V10开仓", f"{symbol} {side}\n价:{price} 损:{sl:.2f} 盈:{tp:.2f}")
            count += 1

schedule.every(1).minutes.do(job)
job()
while True:
    schedule.run_pending()
    time.sleep(1)