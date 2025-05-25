#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Hedge Fund CLI版本
基于ai-hedge-fund开源框架的命令行界面版本

这是一个教育性质的AI对冲基金模拟器CLI版本
不用于真实交易或投资建议
"""

import sys
import os
import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path

# 导入核心功能模块
from hedge_fund_core import AIHedgeFund
from config import API_CONFIG

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="AI Hedge Fund CLI")
    
    # 股票代码
    parser.add_argument(
        "--tickers", 
        type=str, 
        default="AAPL,MSFT,NVDA",
        help="股票代码，用逗号分隔 (默认: AAPL,MSFT,NVDA)"
    )
    
    # 日期范围
    parser.add_argument(
        "--start-days", 
        type=int, 
        default=30,
        help="开始日期，从今天往前推的天数 (默认: 30)"
    )
    
    parser.add_argument(
        "--end-days", 
        type=int, 
        default=0,
        help="结束日期，从今天往前推的天数 (默认: 0，即今天)"
    )
    
    # API密钥
    parser.add_argument(
        "--api-key", 
        type=str, 
        help="LLM API Key"
    )
    
    # 模型选择
    parser.add_argument(
        "--model", 
        type=str, 
        default="openai",
        choices=["openai", "deepseek", "claude", "gemini", "ollama"],
        help="要使用的LLM模型 (默认: openai)"
    )
    
    # 智能体选择
    parser.add_argument(
        "--agents", 
        type=str, 
        default="warren_buffett,cathie_wood,technical",
        help="要使用的智能体，用逗号分隔 (默认: warren_buffett,cathie_wood,technical)"
    )
    
    # 选项
    parser.add_argument(
        "--show-reasoning", 
        action="store_true", 
        default=True,
        help="显示推理过程 (默认: True)"
    )
    
    parser.add_argument(
        "--use-llm", 
        action="store_true", 
        default=False,
        help="使用LLM进行分析 (默认: False)"
    )
    
    return parser.parse_args()

def run_analysis(args):
    """运行分析"""
    print("\n===== AI Hedge Fund CLI =====\n")
    
    # 解析股票代码
    tickers = [ticker.strip() for ticker in args.tickers.split(",") if ticker.strip()]
    if not tickers:
        print("错误: 请提供有效的股票代码")
        return
    
    print(f"分析股票: {', '.join(tickers)}")
    print(f"日期范围: 从今天往前推 {args.start_days} 天到 {args.end_days} 天")
    
    # 设置API密钥环境变量
    if args.api_key:
        if args.model == "openai":
            os.environ["OPENAI_API_KEY"] = args.api_key
        elif args.model == "deepseek":
            os.environ["DEEPSEEK_API_KEY"] = args.api_key
        elif args.model == "claude":
            os.environ["CLAUDE_API_KEY"] = args.api_key
        elif args.model == "gemini":
            os.environ["GOOGLE_API_KEY"] = args.api_key
    
    # 解析智能体
    agent_names = [agent.strip() for agent in args.agents.split(",") if agent.strip()]
    if not agent_names:
        print("错误: 请选择至少一个智能体")
        return
    
    print(f"使用智能体: {', '.join(agent_names)}")
    print(f"使用模型: {args.model}")
    print(f"使用LLM进行分析: {'是' if args.use_llm else '否'}")
    
    # 获取模型配置
    model_config = API_CONFIG.get(args.model, {})
    
    # 创建AI对冲基金实例
    hedge_fund = AIHedgeFund(llm_provider=args.model, llm_config=model_config)
    
    # 运行分析
    print("\n正在获取市场数据...")
    try:
        # 分析投资组合
        results = hedge_fund.analyze_portfolio(tickers, agent_names, args.use_llm)
        
        # 显示结果
        print("\n===== 分析结果 =====\n")
        
        # 显示个股分析
        individual_analysis = results["individual_analysis"]
        for ticker, analysis in individual_analysis.items():
            print(f"\n股票: {ticker}")
            
            if "error" in analysis:
                print(f"分析错误: {analysis['error']}")
                continue
                
            # 市场数据
            market_data = analysis["market_data"]
            print(f"当前价格: ${market_data.current_price:.2f}")
            print(f"价格变化: ${market_data.price_change:.2f} ({market_data.price_change_percent:.2f}%)")
            
            # 最终决策
            final_decision = analysis["final_decision"]
            print(f"建议操作: {final_decision['decision']}")
            print(f"置信度: {final_decision['confidence']*100:.2f}%")
            
            if args.show_reasoning:
                print("\n智能体分析:")
                for decision in analysis["agent_decisions"]:
                    print(f"\n{decision.agent_name}:")
                    print(f"决策: {decision.decision}")
                    print(f"置信度: {decision.confidence*100:.2f}%")
                    print(f"推理: {decision.reasoning}")
        
        # 显示投资组合建议
        portfolio_summary = results["portfolio_summary"]
        print("\n===== 投资组合建议 =====\n")
        
        # 买入建议
        print("买入建议:")
        if portfolio_summary["buy_recommendations"]:
            for ticker, confidence in portfolio_summary["buy_recommendations"]:
                print(f"- {ticker}: 置信度 {confidence*100:.2f}%")
        else:
            print("- 无买入建议")
            
        # 卖出建议
        print("\n卖出建议:")
        if portfolio_summary["sell_recommendations"]:
            for ticker, confidence in portfolio_summary["sell_recommendations"]:
                print(f"- {ticker}: 置信度 {confidence*100:.2f}%")
        else:
            print("- 无卖出建议")
            
        # 持有建议
        print("\n持有建议:")
        if portfolio_summary["hold_recommendations"]:
            for ticker, confidence in portfolio_summary["hold_recommendations"]:
                print(f"- {ticker}: 置信度 {confidence*100:.2f}%")
        else:
            print("- 无持有建议")
        
    except Exception as e:
        print(f"\n分析过程中出错: {e}")
        import traceback
        traceback.print_exc()

def main():
    """主函数"""
    args = parse_args()
    run_analysis(args)

if __name__ == "__main__":
    main()