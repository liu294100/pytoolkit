import ccxt
import pandas as pd
import time
import schedule
import requests
from datetime import datetime
import sys
import numpy as np

# ==========================================
# 🏆 V7.0 [Alpha Predator] 模拟盘专用版
# ==========================================
SIMULATION_MODE = True
FAKE_BALANCE = 1000.0
PUSHPLUS_TOKEN = '' 

# --- 全局风控 ---
RISK_PER_TRADE = 0.025   # 单笔 2.5%
MAX_OPEN_POSITIONS = 2   # 最大并发 2 单 (防止火烧连营)

# --- 选品配置 (ETH / SOL / DOGE / XAU) ---
PAIRS = {
    # 稳健型
    'ETH/USDT': {'rsi_len': 7, 'rsi_long': 25, 'rsi_short': 75, 'sl_atr': 2.5, 'tp_atr': 3.5, 'max_drop': 0.03, 'min_atr': 5},
    # 避险型 (黄金)
    'XAU/USDT': {'rsi_len': 7, 'rsi_long': 30, 'rsi_short': 70, 'sl_atr': 2.0, 'tp_atr': 3.0, 'max_drop': 0.02, 'min_atr': 1},
    # 激进型
    'SOL/USDT': {'rsi_len': 7, 'rsi_long': 20, 'rsi_short': 80, 'sl_atr': 3.0, 'tp_atr': 4.5, 'max_drop': 0.05, 'min_atr': 0.2},
    'DOGE/USDT': {'rsi_len': 7, 'rsi_long': 20, 'rsi_short': 80, 'sl_atr': 3.5, 'tp_atr': 5.0, 'max_drop': 0.05, 'min_atr': 0.0005}
}

print(f"🚀 启动 V7.0 [Alpha Predator]... 初始资金: {FAKE_BALANCE} U")

try:
    exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
    print("✅ 交易所连接成功 (行情数据)")
except:
    print("❌ 连接失败，请检查网络")
    sys.exit()

# 持仓结构
sim_positions = {} 

# --- 数学核心 (免安装库) ---
def calc_rsi(series, period):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.ewm(com=period-1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period-1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

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

# --- V7.0 核心管理逻辑 ---
def manage_positions(symbol, curr_price, atr_value):
    global FAKE_BALANCE, sim_positions
    if symbol not in sim_positions: return

    pos = sim_positions[symbol]
    pnl = 0
    closed = False
    reason = ""
    
    # 1. 计算浮盈
    if pos['side'] == 'buy':
        dist = curr_price - pos['entry']
        unrealized = dist * pos['qty']
    else:
        dist = pos['entry'] - curr_price
        unrealized = dist * pos['qty']

    # 2. 触发保本损 (Breakeven)
    if not pos.get('breakeven', False):
        if dist > (atr_value * 1.5):
            pos['sl'] = pos['entry']
            pos['breakeven'] = True
            send_msg(f"🛡️ 触发保本", f"{symbol} 浮盈不错，止损已移至开仓价")

    # 3. 时间止损 (持仓 > 3小时且利润微薄)
    bars_held = (time.time() - pos['open_time']) / 900
    if bars_held > 12 and dist < (atr_value * 0.5):
        closed = True
        reason = "时间止损(墨迹)"
        pnl = unrealized

    # 4. 常规止盈止损
    if not closed:
        if pos['side'] == 'buy':
            if curr_price <= pos['sl']: pnl, closed, reason = (pos['sl']-pos['entry'])*pos['qty'], True, "止损/保本"
            elif curr_price >= pos['tp']: pnl, closed, reason = (pos['tp']-pos['entry'])*pos['qty'], True, "止盈"
        else:
            if curr_price >= pos['sl']: pnl, closed, reason = (pos['entry']-pos['sl'])*pos['qty'], True, "止损/保本"
            elif curr_price <= pos['tp']: pnl, closed, reason = (pos['entry']-pos['tp'])*pos['qty'], True, "止盈"
            
    if closed:
        FAKE_BALANCE += pnl
        send_msg(f"🎮 平仓-{reason}", f"{symbol} 盈亏: {pnl:.2f} U\n当前余额: {FAKE_BALANCE:.2f}")
        del sim_positions[symbol]

def job():
    count = len(sim_positions)
    print(f"[{datetime.now().strftime('%H:%M')}] 监控中... 余额: {FAKE_BALANCE:.2f} | 持仓: {count}/{MAX_OPEN_POSITIONS}")
    
    for symbol in PAIRS.keys():
        df = fetch_data(symbol)
        if df is None: continue
        price = df.iloc[-1]['close']
        
        # 计算指标
        df['ema'] = df['close'].ewm(span=200, adjust=False).mean()
        df['rsi'] = calc_rsi(df['close'], PAIRS[symbol]['rsi_len'])
        df['atr'] = calc_atr(df, 14)
        
        atr_val = df.iloc[-1]['atr']
        if pd.isna(atr_val): continue

        # 管理持仓
        manage_positions(symbol, price, atr_val)
        
        # 开仓检查
        if symbol in sim_positions: continue
        if count >= MAX_OPEN_POSITIONS: continue

        prev = df.iloc[-2]
        cfg = PAIRS[symbol]

        # 过滤与熔断
        if atr_val < cfg['min_atr']: continue
        if (prev['open']-prev['close'])/prev['open'] > cfg['max_drop']: continue

        # 信号
        long_c = (prev['close']>prev['ema']) and (prev['rsi']<cfg['rsi_long']) and (prev['close']>prev['open'])
        short_c = (prev['close']<prev['ema']) and (prev['rsi']>cfg['rsi_short']) and (prev['close']<prev['open'])
        
        side = 'buy' if long_c else 'sell' if short_c else None
        
        if side:
            sl_dist = prev['atr'] * cfg['sl_atr']
            if sl_dist == 0: continue
            
            qty = (FAKE_BALANCE * RISK_PER_TRADE) / sl_dist
            sl = price - sl_dist if side == 'buy' else price + sl_dist
            tp = price + (sl_dist * cfg['tp_atr']) if side == 'buy' else price - (sl_dist * cfg['tp_atr'])
            
            sim_positions[symbol] = {
                'side': side, 'entry': price, 'qty': qty, 'sl': sl, 'tp': tp,
                'open_time': time.time(), 'breakeven': False
            }
            send_msg(f"🎮 组合开仓", f"{symbol} {side}\n价:{price} 损:{sl:.2f} 盈:{tp:.2f}\n(仓位: {count+1})")
            count += 1

schedule.every(1).minutes.do(job)
job()
while True:
    schedule.run_pending()
    time.sleep(1)
