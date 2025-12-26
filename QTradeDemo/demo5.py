import ccxt
import pandas as pd
import time
import schedule
import sys
from datetime import datetime

# ==========================================
# 🏛️ V14.2 [Spartan Simulation] 模拟盘专用
# ==========================================
# 初始配置
INITIAL_BALANCE = 2000.0   # 初始本金 2000U
current_balance = INITIAL_BALANCE

# 模拟持仓数据
positions = {} 
# 交易统计
trade_history = []

# --- 核心风控配置 ---
RISK_PER_TRADE = 0.03   # 每次交易承担 3% 风险 (复利引擎)
LEVERAGE_LIMIT = 5      # 模拟最大杠杆倍数 (用于检查仓位是否过大)

# --- 差异化参数 (BTC稳, SOL浪) ---
PAIRS = {
    'BTC/USDT': {
        'ema_fast': 144, 'ema_slow': 169, 
        'atr_len': 14, 
        'sl_atr': 1.8,     # BTC 止损窄一点
        'tp_trail': 2.0,   # 启动移动止盈的阈值 (2倍ATR)
    },
    'SOL/USDT': {
        'ema_fast': 144, 'ema_slow': 169, 
        'atr_len': 14, 
        'sl_atr': 2.5,     # SOL 止损宽一点
        'tp_trail': 3.0,   # SOL 让他跑远点再止盈 (3倍ATR)
    }
}

print(f"🏛️ [斯巴达] 4H 模拟盘启动...")
print(f"💰 初始本金: ${current_balance:.2f}")
print(f"📊 监控品种: {list(PAIRS.keys())}")
print("-" * 50)

# 初始化交易所 (仅用于获取公开行情，无需Key)
try:
    exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'future'}})
except Exception as e:
    print(f"❌ 交易所连接失败: {e}")
    sys.exit()

# --- 核心指标计算 ---
def calculate_indicators(df, cfg):
    # EMA 隧道
    df['ema_fast'] = df['close'].ewm(span=cfg['ema_fast'], adjust=False).mean()
    df['ema_slow'] = df['close'].ewm(span=cfg['ema_slow'], adjust=False).mean()
    
    # ATR 计算
    df['tr'] = pd.concat([
        abs(df['high'] - df['low']),
        abs(df['high'] - df['close'].shift()),
        abs(df['low'] - df['close'].shift())
    ], axis=1).max(axis=1)
    df['atr'] = df['tr'].rolling(cfg['atr_len']).mean()
    
    # RSI 计算
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.ewm(com=13, min_periods=14).mean()
    avg_loss = loss.ewm(com=13, min_periods=14).mean()
    df['rsi'] = 100 - (100 / (1 + avg_gain / avg_loss))
    
    return df

def fetch_data(symbol):
    try:
        # 获取 4H K线，取最近 300 根以确保 EMA 计算准确
        bars = exchange.fetch_ohlcv(symbol, timeframe='4h', limit=300)
        df = pd.DataFrame(bars, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
        df['ts'] = pd.to_datetime(df['ts'], unit='ms')
        return df
    except Exception as e:
        print(f"⚠️ 获取 {symbol} 数据失败: {e}")
        return None

# --- 交易逻辑 ---
def run_simulation():
    global current_balance, positions
    
    # 打印心跳 (可选)
    # print(f"[{datetime.now().strftime('%H:%M:%S')}] 监控中... 余额: ${current_balance:.2f}")

    for symbol, cfg in PAIRS.items():
        df = fetch_data(symbol)
        if df is None: continue
        
        df = calculate_indicators(df, cfg)
        
        # curr = 当前最新 K线 (实时价格，未收盘)
        # prev = 上一根 K线 (已收盘，用于确认信号)
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        current_price = curr['close']
        current_atr = curr['atr'] # 使用最新的ATR
        
        # ---------------------------
        # 1. 持仓管理 (止损/移动止盈)
        # ---------------------------
        if symbol in positions:
            pos = positions[symbol]
            close_pos = False
            pnl = 0
            reason = ""
            
            # 更新最高/最低价 (用于移动止盈计算)
            if pos['side'] == 'buy':
                if current_price > pos['highest']: pos['highest'] = current_price
                
                # 移动止盈触发检查
                dist_from_entry = pos['highest'] - pos['entry']
                activation_dist = cfg['tp_trail'] * pos['entry_atr'] # 阈值
                
                if dist_from_entry > activation_dist:
                    # 动态止损线 = 最高价 - 风险距离
                    # 这里保持一定宽度的回撤空间
                    new_sl = pos['highest'] - (cfg['sl_atr'] * pos['entry_atr'])
                    if new_sl > pos['sl']:
                        pos['sl'] = new_sl
                        # print(f"  ⬆️ {symbol} 触发移动止盈，止损上移至 {new_sl:.2f}")

                # 检查价格是否触及止损
                if current_price <= pos['sl']:
                    close_pos = True
                    reason = "止损/移动止盈"
            
            else: # Short
                if current_price < pos['lowest']: pos['lowest'] = current_price
                
                dist_from_entry = pos['entry'] - pos['lowest']
                activation_dist = cfg['tp_trail'] * pos['entry_atr']
                
                if dist_from_entry > activation_dist:
                    new_sl = pos['lowest'] + (cfg['sl_atr'] * pos['entry_atr'])
                    if new_sl < pos['sl']:
                        pos['sl'] = new_sl
                        # print(f"  ⬇️ {symbol} 触发移动止盈，止损下移至 {new_sl:.2f}")

                if current_price >= pos['sl']:
                    close_pos = True
                    reason = "止损/移动止盈"
            
            # 执行平仓
            if close_pos:
                if pos['side'] == 'buy':
                    pnl = (pos['sl'] - pos['entry']) * pos['qty']
                else:
                    pnl = (pos['entry'] - pos['sl']) * pos['qty']
                
                # 扣除模拟手续费 (双向 0.05%)
                fee = (pos['qty'] * pos['entry'] + pos['qty'] * pos['sl']) * 0.0005
                net_pnl = pnl - fee
                
                current_balance += net_pnl
                
                print(f"🔴 [{symbol}] 平仓 ({reason})")
                print(f"   开仓价: {pos['entry']:.2f} -> 平仓价: {pos['sl']:.2f}")
                print(f"   净盈亏: {net_pnl:+.2f} U | 当前余额: ${current_balance:.2f}")
                print("-" * 50)
                
                del positions[symbol]
            
            # 如果有持仓，跳过开仓逻辑
            continue

        # ---------------------------
        # 2. 开仓信号检测 (V14.1 逻辑)
        # ---------------------------
        # 必须等待上一根K线收盘确认
        
        ema_high = max(prev['ema_fast'], prev['ema_slow'])
        ema_low = min(prev['ema_fast'], prev['ema_slow'])
        
        # 趋势判断
        bull_trend = prev['close'] > ema_high
        bear_trend = prev['close'] < ema_low
        
        # RSI 过滤 (宽松版)
        rsi_valid_long = prev['rsi'] < 75
        rsi_valid_short = prev['rsi'] > 25
        
        signal = None
        if bull_trend and rsi_valid_long:
            signal = 'buy'
        elif bear_trend and rsi_valid_short:
            signal = 'sell'
            
        if signal:
            # 计算 ATR 止损距离
            atr_val = prev['atr'] # 使用收盘K线的ATR
            if pd.isna(atr_val) or atr_val == 0: continue
            
            sl_dist = atr_val * cfg['sl_atr']
            
            # 复利仓位计算: 亏损金额 = 当前余额 * 3%
            risk_amount = current_balance * RISK_PER_TRADE
            qty = risk_amount / sl_dist
            
            # 止损价格
            sl_price = current_price - sl_dist if signal == 'buy' else current_price + sl_dist
            
            # 杠杆检查 (仅做提示，不阻止开仓，除非超出交易所限制)
            notional = qty * current_price
            leverage = notional / current_balance
            if leverage > LEVERAGE_LIMIT:
                # 强制降仓至最大杠杆限制 (模拟爆仓风险控制)
                qty = (current_balance * LEVERAGE_LIMIT) / current_price
                # 重新计算止损距离 (逻辑上保持风险一致不太可能，这里优先保本金)
                # 实际策略中，如果杠杆太高，说明ATR太小，可能需要跳过或接受高杠杆
            
            print(f"🟢 [{symbol}] 信号出现: {signal.upper()}")
            print(f"   价格: {current_price:.2f} | 止损: {sl_price:.2f} (ATR: {atr_val:.2f})")
            print(f"   仓位: {qty:.4f} (价值 ${qty*current_price:.1f}, 杠杆 {leverage:.1f}x)")
            
            positions[symbol] = {
                'side': signal,
                'entry': current_price,
                'qty': qty,
                'sl': sl_price,
                'entry_atr': atr_val,
                'highest': current_price,
                'lowest': current_price,
                'ts': datetime.now()
            }
            print(f"   ✅ 开仓成功 (模拟)")
            print("-" * 50)

# --- 任务调度 ---
# 每 1 分钟执行一次逻辑
# 注意：虽然是 4H 策略，但每分钟检查一次是为了移动止盈能及时触发
# 开仓逻辑里使用了 prev (上一根收盘K线)，所以每分钟跑也不会导致频繁重复开仓 (只要持仓没平)
schedule.every(1).minutes.do(run_simulation)

print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] 脚本已启动，正在扫描市场...")
# 立即运行一次
run_simulation()

while True:
    try:
        schedule.run_pending()
        time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 脚本已停止")