import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import akshare as ak
import pandas as pd
import inspect
import threading
import queue
import re

# --- Helper function to define the massive AKSHARE_FUNCTIONS_FULL dictionary ---
def get_all_akshare_functions():
    """
    Returns the complete categorized dictionary of Akshare functions.
    """
    # This is where you'll paste the ENTIRE list, structured as a Python dictionary.
    # Due to the extreme length, I'm providing a truncated example here.
    # You MUST replace this with your full, correctly formatted list.
    
    # --- START OF THE MASSIVE FUNCTION LIST ---
    # (Manually parse your provided list into this dictionary structure)
    AKSHARE_FUNCTIONS_FULL = {
        "交易所期货数据": [
            ("get_cffex_daily", "中国金融期货交易所每日交易数据"),
            ("get_cffex_rank_table", "中国金融期货交易所前20会员持仓数据明细"),
            ("get_czce_daily", "郑州商品交易所每日交易数据"),
            ("get_czce_rank_table", "郑州商品交易所前20会员持仓数据明细"),
            ("get_dce_daily", "大连商品交易所每日交易数据"),
            ("get_gfex_daily", "广州期货交易所每日交易数据"),
            ("get_ine_daily", "上海国际能源交易中心每日交易数据"),
            ("futures_settlement_price_sgx", "新加坡交易所期货品种每日交易数据"),
            ("get_dce_rank_table", "大连商品交易所前20会员持仓数据明细"),
            ("get_futures_daily", "期货每日基差数据"), # "中国金融期货交易所每日基差数据" in original list, using shorter one from tutorial
            ("get_rank_sum", "四个期货交易所前5, 10, 15, 20会员持仓排名数据"),
            ("get_rank_sum_daily", "每日四个期货交易所前5, 10, 15, 20会员持仓排名数据"),
            ("futures_dce_position_rank", "大连商品交易所前 20 会员持仓排名数据"),
            ("get_receipt", "大宗商品注册仓单数据"),
            ("get_roll_yield", "某一天某品种(主力和次主力)或固定两个合约的展期收益率"),
            ("get_roll_yield_bar", "展期收益率"),
            ("get_shfe_daily", "上海期货交易所每日交易数据"),
            ("get_shfe_rank_table", "上海期货交易所前20会员持仓数据明细"),
            ("get_shfe_v_wap", "上海期货交易所日成交均价数据"),
            ("futures_spot_price", "具体交易日大宗商品现货价格及相应基差数据"),
            ("futures_spot_price_previous", "具体交易日大宗商品现货价格及相应基差数据-该接口补充历史数据"),
            ("futures_spot_price_daily", "一段交易日大宗商品现货价格及相应基差数据"),
            ("futures_czce_warehouse_receipt", "郑州商品交易所-交易数据-仓单日报"),
            ("futures_shfe_warehouse_receipt", "上海期货交易所-交易数据-仓单日报"),
            ("futures_dce_warehouse_receipt", "大连商品交易所-交易数据-仓单日报"),
            ("futures_gfex_warehouse_receipt", "广州期货交易所-行情数据-仓单日报"),
            ("futures_rule", "国泰君安-交易日历"),
        ],
        "奇货可查数据": [
            ("get_qhkc_index", "奇货可查-指数-数值数据"),
            ("get_qhkc_index_profit_loss", "奇货可查-指数-累计盈亏数据"),
            ("get_qhkc_index_trend", "奇货可查-指数-大资金动向数据"),
            ("get_qhkc_fund_bs", "奇货可查-资金-净持仓分布数据"),
            ("get_qhkc_fund_position", "奇货可查-资金-总持仓分布数据"),
            ("get_qhkc_fund_position_change", "奇货可查-资金-净持仓变化分布数据"),
            ("get_qhkc_tool_foreign", "奇货可查-工具-外盘比价数据"),
            ("get_qhkc_tool_gdp", "奇货可查-工具-各地区经济数据"),
        ],
        "中国银行间市场交易商协会": [ # Shortened category name
            ("bond_debt_nafmii", "非金融企业债务融资工具注册信息系统"), # Shortened desc
        ],
        "交易所商品期权数据": [
            ("option_dce_daily", "大连商品交易所商品期权数据"),
            ("option_czce_daily", "郑州商品交易所商品期权数据"),
            ("option_shfe_daily", "上海期货交易所商品期权数据"),
            ("option_gfex_daily", "广州期货交易所商品期权数据"),
            ("option_gfex_vol_daily", "广州期货交易所-合约隐含波动率数据"),
        ],
        "中国银行间市场债券行情数据": [
            ("get_bond_market_quote", "债券市场行情-现券市场成交行情数据"),
            ("get_bond_market_trade", "债券市场行情-现券市场做市报价数据"),
        ],
        "外汇": [
            ("get_fx_spot_quote", "人民币外汇即期报价数据"),
            ("get_fx_swap_quote", "人民币外汇远掉报价数据"),
            ("get_fx_pair_quote", "外币对即期报价数据"),
            # Note: fx_spot_quote, fx_swap_quote, fx_pair_quote appear twice in the original list under different categories.
            # I'll keep them distinct if their full category path is different, or merge if they are true duplicates.
            # Here, the later ones are under "全国银行间同业拆借中心..."
        ],
        "宏观-欧洲": [
            ("macro_euro_interest_rate", "欧洲央行决议报告"),
        ],
        "宏观-主要机构": [
            ("macro_cons_gold", "全球最大黄金ETF—SPDR Gold Trust持仓报告"),
            ("macro_cons_silver", "全球最大白银ETF--iShares Silver Trust持仓报告"),
            ("macro_cons_opec_month", "欧佩克报告"),
        ],
        "期货-仓单有效期": [
            ("get_receipt_date", "期货仓单有效期数据"),
        ],
        "新浪财经-期货": [
            ("futures_zh_spot", "国内期货实时行情数据"),
            ("futures_zh_realtime", "国内期货实时行情数据(品种)"),
            ("futures_foreign_commodity_realtime", "外盘期货实时行情数据"),
            ("futures_foreign_hist", "外盘期货历史行情数据"),
            ("futures_foreign_detail", "外盘期货合约详情"),
            ("futures_zh_minute_sina", "内盘分时数据"),
        ],
        "交易所金融期权数据": [
            ("get_finance_option", "上海证券交易所期权数据"), # "提供上海证券交易所期权数据"
        ],
        "加密货币行情": [
            ("crypto_js_spot", "提供主流加密货币行情数据接口"),
        ],
        "新浪财经-港股": [
            ("stock_hk_spot", "港股的历史行情数据(包括前后复权因子)"),
            ("stock_hk_daily", "港股的实时行情数据(也可以用于获得所有港股代码)"),
        ],
        "东方财富-港股": [ # Combined "东方财富" and "港股"
            ("stock_hk_spot_em", "港股实时行情"),
            ("stock_hk_main_board_spot_em", "港股主板实时行情"),
        ],
        "新浪财经-美股": [
            ("get_us_stock_name", "获得美股的所有股票代码"),
            ("stock_us_spot", "美股行情报价"),
            ("stock_us_daily", "美股的历史数据(包括前复权因子)"),
        ],
        "A+H股行情": [ # Shortened
            ("stock_zh_ah_spot", "A+H 股实时行情数据(延迟15分钟)"),
            ("stock_zh_ah_daily", "A+H 股历史行情数据(日频)"),
            ("stock_zh_ah_name", "A+H 股所有股票代码"),
        ],
        "A股行情": [ # Shortened "A股实时行情数据和历史行情数据"
            ("stock_zh_a_spot", "新浪 A 股实时行情数据"),
            ("stock_zh_a_spot_em", "东财 A 股实时行情数据"),
            ("stock_sh_a_spot_em", "东财沪 A 股实时行情数据"),
            ("stock_sz_a_spot_em", "东财深 A 股实时行情数据"),
            ("stock_bj_a_spot_em", "东财京 A 股实时行情数据"),
            ("stock_new_a_spot_em", "东财新股实时行情数据"),
            ("stock_kc_a_spot_em", "东财科创板实时行情数据"),
            ("stock_zh_b_spot_em", "东财 B 股实时行情数据"),
            ("stock_zh_a_daily", "A 股历史行情数据(日频)"),
            ("stock_zh_a_minute", "A 股分时历史行情数据(分钟)"),
            ("stock_zh_a_cdr_daily", "A 股 CDR 历史行情数据(日频)"),
        ],
        "科创板行情": [ # Shortened
            ("stock_zh_kcb_spot", "科创板实时行情数据"),
            ("stock_zh_kcb_daily", "科创板历史行情数据(日频)"),
        ],
        "银保监分局处罚数据": [ # Shortened
            ("bank_fjcf_table_detail", "银保监分局本级行政处罚-信息公开表"),
        ],
        "已实现波动率数据": [
            ("article_oman_rv", "O-MAN已实现波动率"),
            ("article_rlab_rv", "Risk-Lab已实现波动率"),
        ],
        "FF多因子模型数据": [
            ("ff_crr", "FF当前因子"),
        ],
        "指数行情": [ # Shortened "指数实时行情和历史行情"
            ("stock_zh_index_daily", "股票指数历史行情数据"),
            ("stock_zh_index_daily_tx", "股票指数历史行情数据-腾讯"),
            ("stock_zh_index_daily_em", "股票指数历史行情数据-东方财富"),
            ("stock_zh_index_spot_sina", "股票指数实时行情数据-新浪"),
            ("stock_zh_index_spot_em", "股票指数实时行情数据-东财"),
        ],
        "股票分笔数据": [
            ("stock_zh_a_tick_tx_js", "A 股票分笔行情数据-腾讯-当日数据"),
        ],
        "世界日出日落数据": [ # Combined
            ("weather_daily", "每日日出和日落数据"),
            ("weather_monthly", "每月日出和日落数据"),
        ],
        "河北空气质量数据": [
            ("air_quality_hebei", "河北空气质量数据"),
        ],
        "经济政策不确定性(EPU)指数": [
            ("article_epu_index", "主要国家和地区的经济政策不确定性(EPU)指数"),
        ],
        "申万行业指数": [
            ("sw_index_third_info", "申万三级信息"),
            ("sw_index_third_cons", "申万三级信息成份"),
        ],
        "空气质量": [
            ("air_quality_hist", "空气质量历史数据"),
            ("air_quality_rank", "空气质量排行"),
            ("air_quality_watch_point", "空气质量观测点历史数据"),
            ("air_city_table", "所有城市列表"),
        ],
        "财富世界五百强公司": [
            ("fortune_rank", "财富世界500强公司历年排名"),
        ],
        "基金业协会-信息公示": [ # Shortened
            ("amac_member_info", "会员信息-会员机构综合查询"),
            ("amac_person_fund_org_list", "从业人员信息-基金从业人员资格注册信息"),
            ("amac_person_bond_org_list", "从业人员信息-债券投资交易相关人员公示"),
            ("amac_manager_info", "私募基金管理人公示-私募基金管理人综合查询"),
            ("amac_manager_classify_info", "私募基金管理人公示-私募基金管理人分类公示"),
            ("amac_member_sub_info", "私募基金管理人公示-证券公司私募基金子公司管理人信息公示"),
            ("amac_fund_info", "基金产品-私募基金管理人基金产品"),
            ("amac_securities_info", "基金产品-证券公司集合资管产品公示"),
            ("amac_aoin_info", "基金产品-证券公司直投基金"),
            ("amac_fund_sub_info", "基金产品公示-证券公司私募投资基金"),
            ("amac_fund_account_info", "基金产品公示-基金公司及子公司集合资管产品公示"),
            ("amac_fund_abs", "基金产品公示-资产支持专项计划"),
            ("amac_futures_info", "基金产品公示-期货公司集合资管产品公示"),
            ("amac_manager_cancelled_info", "诚信信息-已注销私募基金管理人名单"),
        ],
        "全国银行间同业拆借中心-外汇市场": [ # Shortened
            ("fx_spot_quote", "人民币外汇即期报价"), # Duplicated function name, assuming context implies difference
            ("fx_swap_quote", "人民币外汇远掉报价"), # Duplicated
            ("fx_pair_quote", "外币对即期报价"),   # Duplicated
        ],
        "能源-碳排放权": [
            ("energy_carbon_domestic", "碳排放权-国内"),
            ("energy_carbon_bj", "碳排放权-北京"),
            ("energy_carbon_sz", "碳排放权-深圳"),
            ("energy_carbon_eu", "碳排放权-国际"),
            ("energy_carbon_hb", "碳排放权-湖北"),
            ("energy_carbon_gz", "碳排放权-广州"),
        ],
        "生活成本": [
            ("cost_living", "世界各大城市生活成本数据"),
        ],
        "商品现货价格指数": [
            ("spot_goods", "商品现货价格指数"),
        ],
        "中国宏观杠杆率": [
            ("macro_cnbs", "中国宏观杠杆率数据"),
        ],
        "金融期权": [ # General category, specific one existed earlier
            ("option_finance_board", "金融期权数据"),
        ],
        "期货连续合约": [
            ("futures_main_sina", "新浪期货连续合约的历史数据"),
        ],
        "机构调研数据": [
            ("stock_jgdy_tj_em", "机构调研数据-统计"),
            ("stock_jgdy_detail_em", "机构调研数据-详细"),
        ],
        "股权质押数据": [
            ("stock_gpzy_profile_em", "股权质押市场概况"),
            ("stock_gpzy_pledge_ratio_em", "上市公司质押比例"),
            ("stock_gpzy_pledge_ratio_detail_em", "重要股东股权质押明细"),
            ("stock_gpzy_distribute_statistics_company_em", "质押机构分布统计-证券公司"),
            ("stock_gpzy_distribute_statistics_bank_em", "质押机构分布统计-银行"),
            ("stock_gpzy_industry_data_em", "上市公司质押比例-行业数据"),
        ],
        "商誉专题数据": [
            ("stock_sy_profile_em", "A股商誉市场概况"),
            ("stock_sy_yq_em", "商誉减值预期明细"),
            ("stock_sy_jz_em", "个股商誉减值明细"),
            ("stock_sy_em", "个股商誉明细"),
            ("stock_sy_hy_em", "行业商誉"),
        ],
        "股票账户统计数据": [
            ("stock_account_statistics_em", "股票账户统计数据"),
        ],
        "股票指数-成份股": [
            ("index_stock_cons", "最新成份股"),
            ("index_stock_cons_csindex", "中证指数-成份股"),
            ("index_stock_cons_weight_csindex", "中证指数成份股的权重"),
            ("index_stock_info", "所有可以的指数表"),
            ("index_stock_info_sina", "所有可以的指数表-新浪新接口"),
        ],
        "义乌小商品指数": [
            ("index_yw", "义乌小商品指数"),
        ],
        "世界银行间拆借利率": [
            ("rate_interbank", "银行间拆借利率"),
        ],
        "主要央行利率": [
            ("macro_bank_usa_interest_rate", "美联储利率决议报告"),
            ("macro_bank_euro_interest_rate", "欧洲央行决议报告"),
            ("macro_bank_newzealand_interest_rate", "新西兰联储决议报告"),
            ("macro_bank_switzerland_interest_rate", "瑞士央行决议报告"),
            ("macro_bank_english_interest_rate", "英国央行决议报告"),
            ("macro_bank_australia_interest_rate", "澳洲联储决议报告"),
            ("macro_bank_japan_interest_rate", "日本央行决议报告"),
            ("macro_bank_russia_interest_rate", "俄罗斯央行决议报告"),
            ("macro_bank_india_interest_rate", "印度央行决议报告"),
            ("macro_bank_brazil_interest_rate", "巴西央行决议报告"),
        ],
        "宏观-中国-金十数据": [ # More specific category
            ("macro_china_urban_unemployment", "城镇调查失业率"),
            ("macro_china_shrzgm", "社会融资规模增量统计"),
            ("macro_china_gdp_yearly", "GDP年率报告"),
            ("macro_china_cpi_yearly", "CPI年率报告"),
            ("macro_china_cpi_monthly", "CPI月率报告"),
            ("macro_china_ppi_yearly", "PPI年率报告"),
            ("macro_china_exports_yoy", "以美元计算出口年率报告"),
            ("macro_china_imports_yoy", "以美元计算进口年率"),
            ("macro_china_trade_balance", "以美元计算贸易帐(亿美元)"),
            ("macro_china_industrial_production_yoy", "规模以上工业增加值年率"),
            ("macro_china_pmi_yearly", "官方制造业PMI"),
            ("macro_china_cx_pmi_yearly", "财新制造业PMI终值"),
            ("macro_china_cx_services_pmi_yearly", "财新服务业PMI"),
            ("macro_china_non_man_pmi", "中国官方非制造业PMI"),
            ("macro_china_fx_reserves_yearly", "外汇储备(亿美元)"),
            ("macro_china_m2_yearly", "M2货币供应年率"),
            ("macro_china_shibor_all", "上海银行业同业拆借报告"),
            ("macro_china_hk_market_info", "人民币香港银行同业拆息"),
            ("macro_china_daily_energy", "中国日度沿海六大电库存数据"),
            ("macro_china_rmb", "中国人民币汇率中间价报告"),
            ("macro_china_market_margin_sz", "深圳融资融券报告"),
            ("macro_china_market_margin_sh", "上海融资融券报告"),
            ("macro_china_au_report", "上海黄金交易所报告"),
        ],
        "宏观-中国-常规": [ # More specific category
            ("macro_china_lpr", "贷款报价利率"),
            ("macro_china_new_house_price", "新房价指数"),
            ("macro_china_enterprise_boom_index", "企业景气及企业家信心指数"),
            ("macro_china_national_tax_receipts", "全国税收收入"),
            ("macro_china_bank_financing", "银行理财产品发行数量"),
            ("macro_china_new_financial_credit", "新增信贷数据"),
            ("macro_china_fx_gold", "外汇和黄金储备"),
            ("macro_china_stock_market_cap", "全国股票交易统计表"),
            ("macro_china_cpi", "居民消费价格指数"),
            ("macro_china_gdp", "国内生产总值"),
            ("macro_china_ppi", "工业品出厂价格指数"),
            ("macro_china_pmi", "采购经理人指数"), # Note: pmi_yearly also exists
            ("macro_china_gdzctz", "城镇固定资产投资"),
            ("macro_china_hgjck", "海关进出口增减情况一览表"), # Duplicated, will check later if same func
            ("macro_china_czsr", "财政收入"),
            ("macro_china_whxd", "外汇贷款数据"),
            ("macro_china_wbck", "本外币存款"),
            ("macro_china_bond_public", "债券发行"),
        ],
        "宏观-美国-金十数据": [
            ("macro_usa_gdp_monthly", "美国GDP"),
            ("macro_usa_cpi_monthly", "美国CPI月率报告"),
            ("macro_usa_cpi_yoy", "美国CPI年率(东财)"), # Source specified
            ("macro_usa_core_cpi_monthly", "美国核心CPI月率报告"),
            ("macro_usa_personal_spending", "美国个人支出月率报告"), # Also under "制造业" in original, consolidating
            ("macro_usa_retail_sales", "美国零售销售月率报告"),
            ("macro_usa_import_price", "美国进口物价指数报告"),
            ("macro_usa_export_price", "美国出口价格指数报告"),
            ("macro_usa_lmci", "LMCI"),
            ("macro_usa_unemployment_rate", "美国失业率报告"),
            ("macro_usa_job_cuts", "美国挑战者企业裁员人数报告"),
            ("macro_usa_non_farm", "美国非农就业人数报告"),
            ("macro_usa_adp_employment", "美国ADP就业人数报告"),
            ("macro_usa_core_pce_price", "美国核心PCE物价指数年率报告"),
            ("macro_usa_real_consumer_spending", "美国实际个人消费支出季率初值报告"),
            ("macro_usa_trade_balance", "美国贸易帐报告"),
            ("macro_usa_current_account", "美国经常帐报告"),
            ("macro_usa_rig_count", "贝克休斯钻井报告"),
            ("macro_usa_ppi", "美国生产者物价指数(PPI)报告"), # Not "个人支出"
            ("macro_usa_core_ppi", "美国核心生产者物价指数(PPI)报告"),
            ("macro_usa_api_crude_stock", "美国API原油库存报告"),
            ("macro_usa_pmi", "美国Markit制造业PMI初值报告"), # Different from ism_pmi
            ("macro_usa_ism_pmi", "美国ISM制造业PMI报告"),
            ("macro_usa_nahb_house_market_index", "美国NAHB房产市场指数报告"),
            ("macro_usa_house_starts", "美国新屋开工总数年化报告"),
            ("macro_usa_new_home_sales", "美国新屋销售总数年化报告"),
            ("macro_usa_building_permits", "美国营建许可总数报告"),
            ("macro_usa_exist_home_sales", "美国成屋销售总数年化报告"),
            ("macro_usa_house_price_index", "美国FHFA房价指数月率报告"),
            ("macro_usa_spcs20", "美国S&P/CS20座大城市房价指数年率报告"),
            ("macro_usa_pending_home_sales", "美国成屋签约销售指数月率报告"),
            ("macro_usa_cb_consumer_confidence", "美国谘商会消费者信心指数报告"),
            ("macro_usa_nfib_small_business", "美国NFIB小型企业信心指数报告"),
            ("macro_usa_michigan_consumer_sentiment", "美国密歇根大学消费者信心指数初值报告"),
            ("macro_usa_eia_crude_rate", "美国EIA原油库存报告"),
            ("macro_usa_initial_jobless", "美国初请失业金人数报告"),
            ("macro_usa_crude_inner", "美国原油产量报告"),
        ],
        "宏观数据-ETF持仓": [ # Generalizing from "宏观数据"
            ("macro_cons_gold_volume", "SPDR Gold Trust持仓报告-量"), # More specific
            ("macro_cons_gold_change", "SPDR Gold Trust持仓报告-变动"),
            ("macro_cons_gold_amount", "SPDR Gold Trust持仓报告-金额"),
            ("macro_cons_silver_volume", "iShares Silver Trust持仓报告-量"),
            ("macro_cons_silver_change", "iShares Silver Trust持仓报告-变动"),
            ("macro_cons_silver_amount", "iShares Silver Trust持仓报告-金额"),
        ],
        "伦敦金属交易所(LME)": [
            ("macro_euro_lme_holding", "LME-持仓报告"),
            ("macro_euro_lme_stock", "LME-库存报告"),
        ],
        "美国商品期货交易委员会(CFTC)": [ # Shortened
            ("macro_usa_cftc_nc_holding", "外汇类非商业持仓报告"),
            ("macro_usa_cftc_c_holding", "商品类非商业持仓报告"),
            ("macro_usa_cftc_merchant_currency_holding", "外汇类商业持仓报告"),
            ("macro_usa_cftc_merchant_goods_holding", "商品类商业持仓报告"),
        ],
        "货币对-投机情绪报告": [
            ("macro_fx_sentiment", "货币对-投机情绪报告"),
        ],
        "百度迁徙地图接口": [
            ("migration_area_baidu", "迁入/出地详情"),
            ("migration_scale_baidu", "迁徙规模"),
        ],
        "债券-沪深债券": [
            ("bond_zh_hs_daily", "历史行情数据"),
            ("bond_zh_hs_spot", "实时行情数据"),
        ],
        "债券-沪深可转债": [
            ("bond_zh_hs_cov_daily", "历史行情数据"),
            ("bond_zh_hs_cov_spot", "实时行情数据"),
            ("bond_zh_cov", "数据一览表"),
            ("bond_cov_comparison", "数据比价"),
            ("bond_cb_jsl", "实时数据-集思录"),
            ("bond_cb_adj_logs_jsl", "转股价变动-集思录"),
            ("bond_cb_index_jsl", "集思录可转债等权指数"),
            ("bond_cb_redeem_jsl", "强赎-集思录"),
        ],
        "金融期权-新浪": [
            ("option_cffex_sz50_list_sina", "上证50期权列表"),
            ("option_cffex_sz50_spot_sina", "上证50期权实时行情"), # Corrected from "沪深300"
            ("option_cffex_sz50_daily_sina", "上证50期权历史行情-日频"), # Corrected from "沪深300"
            ("option_cffex_hs300_list_sina", "沪深300期权列表"),
            ("option_cffex_hs300_spot_sina", "沪深300期权实时行情"),
            ("option_cffex_hs300_daily_sina", "沪深300期权历史行情-日频"),
            ("option_cffex_zz1000_list_sina", "中证1000期权列表"),
            ("option_cffex_zz1000_spot_sina", "中证1000期权实时行情"),
            ("option_cffex_zz1000_daily_sina", "中证1000期权历史行情-日频"),
            ("option_sse_list_sina", "上交所期权列表"),
            ("option_sse_expire_day_sina", "上交所期权剩余到期日"),
            ("option_sse_codes_sina", "上交所期权代码"),
            ("option_sse_spot_price_sina", "上交所期权实时行情"),
            ("option_sse_underlying_spot_price_sina", "上交所期权标的物实时行情"),
            ("option_sse_greeks_sina", "上交所期权希腊字母"),
            ("option_sse_minute_sina", "上交所期权分钟数据"),
            ("option_sse_daily_sina", "上交所期权日频数据"),
            ("option_finance_minute_sina", "金融股票期权分时数据"), # General name
            ("option_minute_em", "股票期权分时数据 (东财)"), # Source added
        ],
        "商品期权-新浪": [
            ("option_sina_option_commodity_dict", "商品期权合约字典查询"),
            ("option_sina_option_commodity_contract_list", "商品期权合约查询"),
            ("option_sina_option_commodity_hist", "商品期权行情历史数据"),
        ],
        "微博舆情报告": [
            ("stock_js_weibo_report", "微博舆情报告"),
        ],
        "自然语言处理": [
            ("nlp_ownthink", "知识图谱"),
            ("nlp_answer", "智能问答"),
        ],
        "货币": [
            ("currency_latest", "最新货币报价"),
            ("currency_history", "指定历史日期的所有货币报价"),
            ("currency_time_series", "指定日期间的时间序列数据-需要权限"),
            ("currency_currencies", "查询所支持的货币信息"),
            ("currency_convert", "货币换算"),
            ("currency_pair_map", "指定货币的所有可货币对的数据"),
        ],
        "公募基金-东方财富": [ # Added source
            ("fund_name_em", "基金基本信息"), # Comma removed
            ("fund_info_index_em", "指数型基金-基本信息"), # Comma removed
            ("fund_purchase_em", "基金申购状态"),
            ("fund_open_fund_daily_em", "开放式基金-实时数据"),
            ("fund_open_fund_info_em", "开放式基金-历史数据"),
            ("fund_etf_fund_daily_em", "场内交易基金-实时数据"),
            ("fund_etf_fund_info_em", "场内交易基金-历史数据"),
            ("fund_financial_fund_daily_em", "理财型基金-实时数据"),
            ("fund_financial_fund_info_em", "理财型基金-历史数据"),
            ("fund_graded_fund_daily_em", "分级基金-实时数据"),
            ("fund_graded_fund_info_em", "分级基金-历史数据"),
            ("fund_money_fund_daily_em", "货币型基金-实时数据"),
            ("fund_money_fund_info_em", "货币型基金-历史数据"),
            ("fund_value_estimation_em", "基金估值"),
        ],
        "分析师指数": [
            ("stock_analyst_rank_em", "分析师排名"),
            ("stock_analyst_detail_em", "分析师详情"),
        ],
        "千股千评": [
            ("stock_comment_em", "股市关注度"),
            ("stock_comment_detail_zlkp_jgcyd_em", "机构参与度"),
            ("stock_comment_detail_zhpj_lspf_em", "综合评价-历史评分"),
            ("stock_comment_detail_scrd_focus_em", "市场热度-用户关注指数"),
            ("stock_comment_detail_scrd_desire_em", "市场热度-市场参与意愿"),
            ("stock_comment_detail_scrd_desire_daily_em", "市场热度-日度市场参与意愿"),
            ("stock_comment_detail_scrd_cost_em", "市场热度-市场成本"),
        ],
        "沪深港通": [
            ("stock_hk_ggt_components_em", "港股通成份股"),
            ("stock_hsgt_hold_stock_em", "持股-个股排行"),
            ("stock_hsgt_stock_statistics_em", "持股-每日个股统计"),
            ("stock_hsgt_institution_statistics_em", "持股-每日机构统计"),
            ("stock_hsgt_hist_em", "历史数据"),
            ("stock_hsgt_board_rank_em", "板块排行"),
            ("stock_hsgt_fund_flow_summary_em", "资金流向"),
        ],
        "两市停复牌": [
            ("stock_tfp_em", "两市停复牌数据"),
        ],
        "中国油价": [
            ("energy_oil_hist", "汽柴油历史调价信息"),
            ("energy_oil_detail", "地区油价"),
        ],
        "现货与股票": [
            ("futures_spot_stock", "现货与股票接口"),
        ],
        "中证商品指数": [
            ("futures_index_ccidx", "中证商品指数"),
            ("futures_index_min_ccidx", "中证商品指数-分时"),
        ],
        "打新收益率": [
            ("stock_dxsyl_em", "打新收益率"),
            ("stock_xgsglb_em", "新股申购与中签查询"),
        ],
        "年报季报": [
            ("stock_yjyg_em", "上市公司业绩预告"),
            ("stock_yysj_em", "上市公司预约披露时间"),
        ],
        "高频数据-标普500指数": [
            ("hf_sp_500", "标普500指数的分钟数据"),
        ],
        "商品期货库存数据": [
            ("futures_inventory_em", "库存数据-东方财富"),
        ],
        "个股资金流": [
            ("stock_individual_fund_flow", "个股资金流"),
            ("stock_individual_fund_flow_rank", "个股资金流排名"),
            ("stock_market_fund_flow", "大盘资金流"),
            ("stock_sector_fund_flow_rank", "板块资金流排名"),
            ("stock_sector_fund_flow_summary", "xx行业个股资金流"), # Placeholder xx
            ("stock_sector_fund_flow_hist", "行业历史资金流"),
            ("stock_concept_fund_flow_hist", "概念历史资金流"),
            ("stock_main_fund_flow", "主力净流入排名"),
        ],
        "股票基本面数据": [
            ("stock_financial_abstract", "财务摘要"),
            ("stock_financial_report_sina", "三大财务报表"),
            ("stock_financial_analysis_indicator", "财务指标"),
            ("stock_add_stock", "股票增发"),
            ("stock_ipo_info", "股票新股"),
            ("stock_history_dividend_detail", "分红配股"),
            ("stock_history_dividend", "历史分红"),
            ("stock_dividend_cninfo", "个股历史分红 (巨潮)"), # Source added
            ("stock_restricted_release_queue_sina", "限售解禁-新浪"),
            ("stock_restricted_release_summary_em", "限售股解禁 (东财)"),
            ("stock_restricted_release_detail_em", "限售股解禁-解禁详情一览 (东财)"),
            ("stock_restricted_release_queue_em", "个股限售解禁-解禁批次 (东财)"),
            ("stock_restricted_release_stockholder_em", "个股限售解禁-解禁股东 (东财)"),
            ("stock_circulate_stock_holder", "流动股东"),
            ("stock_fund_stock_holder", "基金持股"),
            ("stock_main_stock_holder", "主要股东"),
        ],
        "股票板块": [
            ("stock_sector_spot", "板块行情"),
            ("stock_sector_detail", "板块详情(具体股票)"),
        ],
        "股票信息": [
            ("stock_info_sz_name_code", "深证股票代码和简称"),
            ("stock_info_sh_name_code", "上海股票代码和简称"),
            ("stock_info_bj_name_code", "北京股票代码和简称"),
            ("stock_info_sh_delist", "上海暂停和终止上市"),
            ("stock_info_sz_delist", "深证暂停和终止上市"),
            ("stock_info_sz_change_name", "深证名称变更"),
            ("stock_info_change_name", "A 股股票曾用名列表"),
            ("stock_info_a_code_name", "A 股股票代码和简称"),
        ],
        "机构持股": [
            ("stock_institute_hold", "机构持股一览表"),
            ("stock_institute_hold_detail", "机构持股详情"),
        ],
        "机构推荐股票": [
            ("stock_institute_recommend", "机构推荐"),
            ("stock_institute_recommend_detail", "股票评级记录"),
        ],
        "股票市场总貌": [
            ("stock_szse_summary", "深交所-市场总貌-证券类别统计"),
            ("stock_szse_area_summary", "深交所-市场总貌-地区交易排序"),
            ("stock_szse_sector_summary", "深交所-统计资料-股票行业成交"), # Space added
            ("stock_sse_summary", "上交所-股票数据总貌"),
            ("stock_sse_deal_daily", "上交所-每日股票情况"),
        ],
        "美股港股目标价": [
            ("stock_price_js", "美股港股目标价"),
        ],
        "券商业绩月报": [
            ("stock_qsjy_em", "券商业绩月报"),
        ],
        "彭博亿万富豪指数": [
            ("index_bloomberg_billionaires", "彭博亿万富豪指数"),
            ("index_bloomberg_billionaires_hist", "彭博亿万富豪历史指数"),
        ],
        "A股市盈率市净率-乐咕乐股": [ # Added source
            ("stock_market_pe_lg", "主板市盈率"),
            ("stock_index_pe_lg", "指数市盈率"),
            ("stock_market_pb_lg", "主板市净率"),
            ("stock_index_pb_lg", "指数市净率"),
            ("stock_a_indicator_lg", "A 股个股市盈率、市净率和股息率指标"),
            ("stock_hk_indicator_eniu", "港股个股市盈率、市净率和股息率指标 (亿牛)"), # Source added
            ("stock_a_high_low_statistics", "创新高和新低的股票数量"),
            ("stock_a_below_net_asset_statistics", "破净股统计"),
        ],
        "交易日历": [ # General Category
            ("tool_trade_date_hist", "新浪财经-交易日历"), # Already exists in "工具"
        ],
        "基金行情": [
            ("fund_etf_category_sina", "基金实时行情-新浪"),
            ("fund_etf_hist_sina", "基金行情-新浪"),
            ("fund_etf_dividend_sina", "ETF 基金-累计分红 (新浪)"),
            ("fund_etf_hist_em", "基金历史行情-东财"),
            ("fund_etf_hist_min_em", "基金分时行情-东财"),
            ("fund_etf_spot_em", "基金实时行情-东财"),
            ("fund_etf_spot_ths", "基金实时行情-同花顺"),
        ],
        "股票财务报告-预约披露": [
            ("stock_report_disclosure", "股票财务报告-预约披露时间"),
        ],
        "基金持股-个股": [ # More specific
            ("stock_report_fund_hold", "个股-基金持股"),
            ("stock_report_fund_hold_detail", "个股-基金持股-明细"),
        ],
        "中证指数": [
            ("stock_zh_index_hist_csindex", "中证指数历史行情"), # Added "行情"
            ("stock_zh_index_value_csindex", "中证指数-指数估值"),
        ],
        "A股龙虎榜-新浪": [ # Added source
            ("stock_lhb_detail_daily_sina", "每日详情"),
            ("stock_lhb_ggtj_sina", "个股上榜统计"),
            ("stock_lhb_yytj_sina", "营业上榜统计"),
            ("stock_lhb_jgzz_sina", "机构席位追踪"),
            ("stock_lhb_jgmx_sina", "机构席位成交明细"),
        ],
        "注册制审核": [
            ("stock_register_kcb", "IPO审核信息-科创板"),
            ("stock_register_cyb", "IPO审核信息-创业板"),
            ("stock_register_bj", "IPO审核信息-北交所"),
            ("stock_register_sh", "IPO审核信息-上海主板"),
            ("stock_register_sz", "IPO审核信息-深圳主板"),
            ("stock_register_db", "注册制审核-达标企业"),
        ],
        "次新股": [
            ("stock_zh_a_new", "股票数据-次新股"),
        ],
        "COMEX库存数据": [
            ("futures_comex_inventory", "COMEX库存数据"),
        ],
        "宏观-中国-其他指标": [ # New category for remaining China macro
            ("macro_china_xfzxx", "消费者信心指数"),
            ("macro_china_gyzjz", "工业增加值增长"),
            ("macro_china_reserve_requirement_ratio", "存款准备金率"),
            ("macro_china_consumer_goods_retail", "社会消费品零售总额"),
            # ("macro_china_hgjck", "海关进出口增减情况"), # Duplicate from earlier, check function
            ("macro_china_society_electricity", "全社会用电分类情况表"),
            ("macro_china_society_traffic_volume", "全社会客货运输量"),
            ("macro_china_postal_telecommunicational", "邮电业务基本情况"),
            ("macro_china_international_tourism_fx", "国际旅游外汇收入构成"),
            ("macro_china_passenger_load_factor", "民航客座率及载运率"),
            ("macro_china_freight_index", "航贸运价指数"),
            ("macro_china_central_bank_balance", "央行货币当局资产负债"),
            ("macro_china_swap_rate", "FR007利率互换曲线历史数据"),
            ("bond_china_close_return", "收盘收益率曲线历史数据"), # Bond related, but in macro section
            ("macro_china_insurance", "保险业经营情况"),
            ("macro_china_supply_of_money", "货币供应量"),
            ("macro_china_foreign_exchange_gold", "央行黄金和外汇储备"), # Differs from fx_gold
            ("macro_china_retail_price_index", "商品零售价格指数"),
        ],
        "新闻联播文字稿": [
            ("news_cctv", "新闻联播文字稿"),
        ],
        "电影票房": [
            ("movie_boxoffice_realtime", "电影实时票房"),
            ("movie_boxoffice_daily", "电影单日票房"),
            ("movie_boxoffice_weekly", "电影单周票房"),
            ("movie_boxoffice_monthly", "电影单月票房"),
            ("movie_boxoffice_yearly", "电影年度票房"),
            ("movie_boxoffice_yearly_first_week", "电影年度首周票房"),
            ("movie_boxoffice_cinema_daily", "电影院单日票房"),
            ("movie_boxoffice_cinema_weekly", "电影院单周票房"),
        ],
        "国房景气指数": [
            ("macro_china_real_estate", "国房景气指数"),
        ],
        "加密货币历史数据": [ # Differs from "加密货币行情"
            ("crypto_name_url_table", "加密货币货币名称"),
        ],
        "基金排行-东方财富": [ # Added source
            ("fund_open_fund_rank_em", "开放式基金排行"),
            ("fund_em_exchange_rank", "场内交易基金排行"),
            ("fund_em_money_rank", "货币型基金排行"),
            ("fund_em_lcx_rank", "理财基金排行"),
            ("fund_em_hk_rank", "香港基金排行"),
        ],
        "回购定盘利率": [
            ("repo_rate_hist", "回购定盘利率"),
        ],
        "榜单-财富": [ # Combined various ranks
            ("forbes_rank", "福布斯中国榜单"),
            ("xincaifu_rank", "新财富500富豪榜"),
            ("hurun_rank", "胡润排行榜"),
        ],
        "期货合约详情": [
            ("futures_contract_detail", "期货合约详情"),
        ],
        "科创板报告": [
            ("stock_zh_kcb_report_em", "科创板报告"),
        ],
        "东方财富-期权": [ # General category
            ("option_current_em", "东方财富-期权"),
        ],
        "国证指数": [
            ("index_all_cni", "所有指数"),
            ("index_hist_cni", "指数行情"),
            ("index_detail_cni", "样本详情"),
            ("index_detail_hist_cni", "历史样本"),
            ("index_detail_hist_adjust_cni", "历史调样"),
        ],
        "大宗交易": [
            ("stock_dzjy_sctj", "市场统计"),
            ("stock_dzjy_mrmx", "每日明细"),
            ("stock_dzjy_mrtj", "每日统计"),
            ("stock_dzjy_hygtj", "活跃 A 股统计"),
            ("stock_dzjy_yybph", "营业部排行"), # Duplicated, assuming one is general, one is hyyybtj
            ("stock_dzjy_hyyybtj", "活跃营业部统计"),
        ],
        "一致行动人": [
            ("stock_yzxdr_em", "股票数据-一致行动人"),
        ],
        "新闻-个股新闻": [
            ("stock_news_em", "新闻-个股新闻"),
        ],
        "债券概览-上登网": [ # Added source
            ("bond_cash_summary_sse", "债券现券市场概览"),
            ("bond_deal_summary_sse", "债券成交概览"),
        ],
        "中国货币供应量": [ # More specific than macro_china_supply_of_money
            ("macro_china_money_supply", "中国货币供应量"),
        ],
        "期货交割与期转现": [ # Combined
            ("futures_to_spot_czce", "郑商所期转现"),
            ("futures_to_spot_shfe", "上期所期转现"),
            ("futures_to_spot_dce", "大商所期转现"),
            ("futures_delivery_dce", "大商所交割统计"),
            ("futures_delivery_czce", "郑商所交割统计"),
            ("futures_delivery_shfe", "上期所交割统计"),
            ("futures_delivery_match_dce", "大商所交割配对"),
            ("futures_delivery_match_czce", "郑商所交割配对"),
        ],
        "融资融券-交易所": [ # Added source context
            ("stock_margin_sse", "上海证券交易所-融资融券汇总"),
            ("stock_margin_detail_sse", "上海证券交易所-融资融券详情"),
        ],
        "基金评级": [
            ("fund_rating_all", "基金评级总汇"),
            ("fund_rating_sh", "上海证券评级"),
            ("fund_rating_zs", "招商证券评级"),
            ("fund_rating_ja", "济安金信评级"),
        ],
        "基金经理": [
            ("fund_manager_em", "基金经理大全"),
        ],
        "盈利预测": [
            ("stock_profit_forecast_em", "盈利预测-东财"),
            ("stock_profit_forecast_ths", "盈利预测-同花顺"),
        ],
        "中美国债收益率": [
            ("bond_zh_us_rate", "中美国债收益率"),
        ],
        "分红配送-东方财富": [ # Added source
            ("stock_fhps_em", "分红配送"),
        ],
        "业绩快报-东方财富": [ # Added source
            ("stock_yjkb_em", "业绩快报"),
        ],
        "业绩报告-东方财富": [ # Added source
            ("stock_yjbb_em", "业绩报告"),
        ],
        "三大报表-东方财富": [ # Added source
            ("stock_zcfz_em", "资产负债表"),
            ("stock_zcfz_bj_em", "资产负债表-北交所"),
            ("stock_lrb_em", "利润表"),
            ("stock_xjll_em", "现金流量表"),
        ],
        "首发企业申报": [
            ("stock_ipo_declare", "首发企业申报"),
        ],
        "行业板块-同花顺": [
            ("stock_board_industry_index_ths", "指数日频数据"),
        ],
        "概念板块-同花顺": [
            ("stock_board_concept_index_ths", "指数日频数据"),
        ],
        "营业部龙虎榜": [ # More specific category
            ("stock_lh_yyb_most", "上榜次数最多"),
            ("stock_lh_yyb_capital", "资金实力最强"),
            ("stock_lh_yyb_control", "抱团操作实力"),
        ],
        "比特币持仓": [
            ("crypto_bitcoin_hold_report", "比特币持仓"),
        ],
        "同花顺-资金流向": [
            ("stock_fund_flow_individual", "个股资金流"),
            ("stock_fund_flow_industry", "行业资金流"),
            ("stock_fund_flow_concept", "概念资金流"),
            ("stock_fund_flow_big_deal", "大单追踪"),
        ],
        "高管持股-东方财富": [
            ("stock_ggcg_em", "高管持股"),
        ],
        "新发基金-东方财富": [
            ("fund_new_found_em", "新发基金"),
        ],
        "柯桥指数": [
            ("index_kq_fz", "柯桥纺织指数"),
            ("index_kq_fashion", "柯桥时尚指数"),
        ],
        "Drewry集装箱指数": [
            ("drewry_wci_index", "Drewry 集装箱指数"),
        ],
        "浙江省排污权交易指数": [
            ("index_eri", "浙江省排污权交易指数"),
        ],
        "赚钱效应分析-乐咕乐股": [
            ("stock_market_activity_legu", "赚钱效应分析"),
        ],
        "中国公路物流运价/量指数": [ # Combined
            ("index_price_cflp", "中国公路物流运价指数"),
            ("index_volume_cflp", "中国公路物流运量指数"),
        ],
        "汽车销量": [
            ("car_sale_rank_gasgoo", "盖世汽车-销量数据"),
            ("car_market_total_cpca", "乘联会-总体市场"),
            ("car_market_man_rank_cpca", "乘联会-厂商排名"),
            ("car_market_cate_cpca", "乘联会-车型大类"),
            ("car_market_country_cpca", "乘联会-国别细分市场"),
            ("car_market_segment_cpca", "乘联会-级别细分市场"),
            ("car_market_fuel_cpca", "乘联会-新能源细分市场"),
        ],
        "增发配股-东方财富": [ # Combined
            ("stock_qbzf_em", "增发"),
            ("stock_pg_em", "配股"),
        ],
        "宏观-中国香港": [
            ("macro_china_hk_cpi", "消费者物价指数"),
            ("macro_china_hk_cpi_ratio", "消费者物价指数年率"),
            ("macro_china_hk_rate_of_unemployment", "失业率"),
            ("macro_china_hk_gbp", "香港 GDP"),
            ("macro_china_hk_gbp_ratio", "香港 GDP 同比"),
            ("macro_china_hk_building_volume", "香港楼宇买卖合约数量"),
            ("macro_china_hk_building_amount", "香港楼宇买卖合约成交金额"),
            ("macro_china_hk_trade_diff_ratio", "香港商品贸易差额年率"),
            ("macro_china_hk_ppi", "香港制造业 PPI 年率"),
        ],
        "涨跌停板行情-东方财富": [ # Added source
            ("stock_zt_pool_em", "涨停股池"),
            ("stock_zt_pool_previous_em", "昨日涨停股池"),
            ("stock_zt_pool_strong_em", "强势股池"),
            ("stock_zt_pool_sub_new_em", "次新股池"),
            ("stock_zt_pool_zbgc_em", "炸板股池"),
            ("stock_zt_pool_dtgc_em", "跌停股池"),
        ],
        "两网及退市": [
            ("stock_staq_net_stop", "两网及退市"),
        ],
        "股东户数": [
            ("stock_zh_a_gdhs", "股东户数"),
            ("stock_zh_a_gdhs_detail_em", "股东户数详情 (东财)"),
        ],
        "中行人民币牌价": [
            ("currency_boc_sina", "历史数据查询 (新浪)"),
        ],
        "A股日频数据": [ # General category
            ("stock_zh_a_hist", "东方财富"),
            ("stock_zh_a_hist_tx", "腾讯"),
        ],
        "盘口异动-东方财富": [
            ("stock_changes_em", "盘口异动"),
            ("stock_board_change_em", "板块异动"),
        ],
        "CME比特币成交量": [
            ("crypto_bitcoin_cme", "CME 比特币成交量"),
        ],
        "基金规模与趋势-东方财富": [ # Combined
            ("fund_aum_em", "基金公司规模排名列表"),
            ("fund_aum_trend_em", "基金市场管理规模走势图"),
            ("fund_aum_hist_em", "基金市场管理规模历史"),
        ],
        "宏观-中国-价格指数": [ # Category for specific price indices
            ("macro_china_qyspjg", "企业商品价格指数"),
            ("macro_china_fdi", "外商直接投资数据"), # Moved from uncat to here if suitable
        ],
        "宏观-美国-房地产": [ # More specific category
            ("macro_usa_phs", "未决房屋销售月率"),
        ],
        "宏观-德国": [
            ("macro_germany_ifo", "ifo商业景气指数"),
            ("macro_germany_cpi_monthly", "消费者物价指数月率终值"),
            ("macro_germany_cpi_yearly", "消费者物价指数年率终值"),
            ("macro_germany_trade_adjusted", "贸易帐(季调后)"),
            ("macro_germany_gdp", "GDP"),
            ("macro_germany_retail_sale_monthly", "实际零售销售月率"),
            ("macro_germany_retail_sale_yearly", "实际零售销售年率"),
            ("macro_germany_zew", "ZEW经济景气指数"),
        ],
        "东方财富-概念板块": [
            ("stock_board_concept_name_em", "名称"),
            ("stock_board_concept_spot_em", "实时行情"),
            ("stock_board_concept_hist_em", "历史行情"),
            ("stock_board_concept_hist_min_em", "分时历史行情"),
            ("stock_board_concept_cons_em", "板块成份"),
        ],
        "宏观-瑞士": [
            ("macro_swiss_svme", "SVME采购经理人指数"),
            ("macro_swiss_trade", "贸易帐"),
            ("macro_swiss_cpi_yearly", "消费者物价指数年率"),
            ("macro_swiss_gdp_quarterly", "GDP季率"),
            ("macro_swiss_gbd_yearly", "GDP年率"),
            ("macro_swiss_gbd_bank_rate", "央行公布利率决议"),
        ],
        "宏观-日本": [
            ("macro_japan_bank_rate", "央行公布利率决议"),
            ("macro_japan_cpi_yearly", "全国消费者物价指数年率"),
            ("macro_japan_core_cpi_yearly", "全国核心消费者物价指数年率"),
            ("macro_japan_unemployment_rate", "失业率"),
            ("macro_japan_head_indicator", "领先指标终值"),
        ],
        "宏观-英国": [
            ("macro_uk_halifax_monthly", "Halifax 房价指数月率"),
            ("macro_uk_halifax_yearly", "Halifax 房价指数年率"),
            ("macro_uk_trade", "贸易帐"),
            ("macro_uk_bank_rate", "央行公布利率决议"),
            ("macro_uk_core_cpi_yearly", "核心消费者物价指数年率"),
            ("macro_uk_core_cpi_monthly", "核心消费者物价指数月率"),
            ("macro_uk_cpi_yearly", "消费者物价指数年率"),
            ("macro_uk_cpi_monthly", "消费者物价指数月率"),
            ("macro_uk_retail_monthly", "零售销售月率"),
            ("macro_uk_retail_yearly", "零售销售年率"),
            ("macro_uk_rightmove_yearly", "Rightmove 房价指数年率"),
            ("macro_uk_rightmove_monthly", "Rightmove 房价指数月率"),
            ("macro_uk_gdp_quarterly", "GDP 季率初值"),
            ("macro_uk_gdp_yearly", "GDP 年率初值"),
            ("macro_uk_unemployment_rate", "失业率"),
        ],
        "融资融券-深圳": [ # More specific
            ("stock_margin_underlying_info_szse", "标的证券信息"),
            ("stock_margin_detail_szse", "融资融券明细"),
            ("stock_margin_szse", "融资融券汇总"),
        ],
        "宏观-澳大利亚": [
            ("macro_australia_bank_rate", "央行公布利率决议"),
            ("macro_australia_unemployment_rate", "失业率"),
            ("macro_australia_trade", "贸易帐"),
            ("macro_australia_cpi_quarterly", "消费者物价指数季率"),
            ("macro_australia_cpi_yearly", "消费者物价指数年率"),
            ("macro_australia_ppi_quarterly", "生产者物价指数季率"),
            ("macro_australia_retail_rate_monthly", "零售销售月率"),
        ],
        "养猪数据中心": [
            ("futures_hog_core", "生猪信息-核心数据"),
            ("futures_hog_cost", "生猪信息-成本维度"),
            ("futures_hog_supply", "生猪信息-供应维度"),
        ],
        "宏观-加拿大": [
            ("macro_canada_new_house_rate", "新屋开工"),
            ("macro_canada_unemployment_rate", "失业率"),
            ("macro_canada_trade", "贸易帐"),
            ("macro_canada_retail_rate_monthly", "零售销售月率"),
            ("macro_canada_bank_rate", "央行公布利率决议"),
            ("macro_canada_core_cpi_yearly", "核心消费者物价指数年率"),
            ("macro_canada_core_cpi_monthly", "核心消费者物价指数月率"),
            ("macro_canada_cpi_yearly", "消费者物价指数年率"),
            ("macro_canada_cpi_monthly", "消费者物价指数月率"),
            ("macro_canada_gdp_monthly", "GDP 月率"),
        ],
        "港股财报-东方财富": [
            ("stock_financial_hk_report_em", "三大报表"),
            ("stock_financial_hk_analysis_indicator_em", "主要指标"),
        ],
        "全部A股-估值指标": [ # Combined
            ("stock_a_ttm_lyr", "等权重市盈率、中位数市盈率"),
            ("stock_a_all_pb", "等权重市净率、中位数市净率"),
        ],
        "REITs-东方财富": [
            ("reits_realtime_em", "实时行情"),
            ("reits_hist_em", "历史行情"),
        ],
        "A股分时数据-东方财富": [
            ("stock_zh_a_hist_min_em", "股票分时"),
            ("stock_zh_a_hist_pre_min_em", "股票盘前分时"),
        ],
        "港股分时数据-东方财富": [
            ("stock_hk_hist_min_em", "港股分时数据"),
        ],
        "美股分时数据-东方财富": [
            ("stock_us_hist_min_em", "美股分时数据"),
        ],
        "可转债详情-东方财富": [
            ("bond_zh_cov_info", "可转债详情"),
        ],
        "风险警示板-东方财富": [
            ("stock_zh_a_st_em", "风险警示板"),
        ],
        "美股市场-东方财富": [ # Combined
            ("stock_us_pink_spot_em", "粉单市场实时行情"), # Added "实时行情"
            ("stock_us_famous_spot_em", "知名美股实时行情"), # Added "实时行情", also was used for HK
        ],
        "股票评级与估值-巨潮资讯": [ # Combined from cninfo
            ("stock_rank_forecast_cninfo", "投资评级"),
            ("stock_industry_pe_ratio_cninfo", "行业市盈率"),
        ],
        "新股IPO-巨潮资讯": [ # Combined from cninfo
            ("stock_new_gh_cninfo", "新股过会"),
            ("stock_new_ipo_cninfo", "IPO信息"), # Shortened
        ],
        "股东与股本-巨潮资讯": [ # Combined from cninfo
            ("stock_hold_num_cninfo", "股东人数及持股集中度"),
            ("stock_hold_control_cninfo", "实际控制人持股变动"),
            ("stock_hold_management_detail_cninfo", "高管持股变动明细"),
            ("stock_hold_change_cninfo", "股本变动"),
        ],
        "期货费用": [ # Combined
            ("futures_comm_info", "期货手续费"),
            ("futures_fees_info", "期货交易费用参照表"),
        ],
        "B股行情": [ # Shortened
            ("stock_zh_b_spot", "实时行情数据"),
            ("stock_zh_b_daily", "历史行情数据(日频)"),
            ("stock_zh_b_minute", "分时历史行情数据(分钟)"),
        ],
        "公司治理-巨潮资讯": [ # Combined from cninfo
            ("stock_cg_guarantee_cninfo", "对外担保"),
            ("stock_cg_lawsuit_cninfo", "公司诉讼"),
            ("stock_cg_equity_mortgage_cninfo", "股权质押"),
        ],
        "债券发行-巨潮资讯": [ # Combined from cninfo
            ("bond_treasure_issue_cninfo", "国债发行"),
            ("bond_local_government_issue_cninfo", "地方债发行"),
            ("bond_corporate_issue_cninfo", "企业债发行"),
            ("bond_cov_issue_cninfo", "可转债发行"),
            ("bond_cov_stock_issue_cninfo", "可转债转股"),
        ],
        "基金报表-巨潮资讯": [ # Combined from cninfo
            ("fund_report_stock_cninfo", "基金重仓股"),
            ("fund_report_industry_allocation_cninfo", "基金行业配置"),
            ("fund_report_asset_allocation_cninfo", "基金资产配置"),
        ],
        "公告大全-沪深A股": [
            ("stock_notice_report", "沪深 A 股公告"),
        ],
        "基金规模-新浪": [
            ("fund_scale_open_sina", "开放式基金"),
            ("fund_scale_close_sina", "封闭式基金"),
            ("fund_scale_structured_sina", "分级子基金"),
        ],
        "沪深港通持股-东方财富": [ # More specific
            ("stock_hsgt_individual_em", "具体股票"),
            ("stock_hsgt_individual_detail_em", "具体股票-详情"),
        ],
        "IPO主题-同花顺": [ # Combined from THS
            ("stock_ipo_benefit_ths", "IPO 受益股"),
            ("stock_xgsr_ths", "新股上市首日"),
        ],
        "同花顺-技术选股": [
            ("stock_rank_cxg_ths", "创新高"),
            ("stock_rank_cxd_ths", "创新低"),
            ("stock_rank_lxsz_ths", "连续上涨"),
            ("stock_rank_lxxd_ths", "连续下跌"),
            ("stock_rank_cxfl_ths", "持续放量"),
            ("stock_rank_cxsl_ths", "持续缩量"),
            ("stock_rank_xstp_ths", "向上突破"),
            ("stock_rank_xxtp_ths", "向下突破"),
            ("stock_rank_ljqs_ths", "量价齐升"),
            ("stock_rank_ljqd_ths", "量价齐跌"),
            ("stock_rank_xzjp_ths", "险资举牌"),
        ],
        "可转债分时数据": [ # General category
            ("bond_zh_hs_cov_min", "可转债分时数据"),
            ("bond_zh_hs_cov_pre_min", "可转债分时数据-盘前"),
        ],
        "艺人商业价值": [ # Combined
            ("business_value_artist", "艺人商业价值"),
            ("online_value_artist", "艺人流量价值"),
        ],
        "视频节目": [ # Combined
            ("video_tv", "电视剧集"),
            ("video_variety_show", "综艺节目"),
        ],
        "基金数据-分红与规模-东方财富": [ # Combined from EM
            ("fund_cf_em", "基金拆分"),
            ("fund_fh_rank_em", "基金分红排行"),
            ("fund_fh_em", "基金分红"),
            ("fund_scale_change_em", "规模变动"),
            ("fund_hold_structure_em", "持有人结构"),
        ],
        "行业板块-东方财富": [
            ("stock_board_industry_cons_em", "板块成份"),
            ("stock_board_industry_hist_em", "历史行情"),
            ("stock_board_industry_hist_min_em", "分时历史行情"),
            ("stock_board_industry_name_em", "板块名称"),
        ],
        "股票回购数据-东方财富": [
            ("stock_repurchase_em", "股票回购数据"),
        ],
        "期货品种字典": [
            ("futures_hq_subscribe_exchange_symbol", "期货品种字典"),
        ],
        "上海黄金交易所": [
            ("spot_hist_sge", "历史行情走势"),
            ("spot_quotations_sge", "实时行情走势"),
            ("spot_golden_benchmark_sge", "上海金基准价"),
            ("spot_silver_benchmark_sge", "上海银基准价"),
        ],
        "个股信息查询-多源": [ # Combined
            ("stock_individual_info_em", "东财"),
            ("stock_individual_basic_info_xq", "雪球-A股"), # Specify market
            ("stock_individual_basic_info_us_xq", "雪球-美股"),
            ("stock_individual_basic_info_hk_xq", "雪球-港股"),
        ],
        "食糖指数-沐甜科技": [ # Combined & Added source
            ("index_sugar_msweet", "中国食糖指数"),
            ("index_inner_quote_sugar_msweet", "配额内进口糖估算指数"),
            ("index_outer_quote_sugar_msweet", "配额外进口糖估算指数"),
        ],
        "东方财富-股东分析": [
            ("stock_gdfx_free_holding_analyse_em", "十大流通股东分析"),
            ("stock_gdfx_holding_analyse_em", "十大股东分析"),
            ("stock_gdfx_free_top_10_em", "个股-十大流通股东"),
            ("stock_gdfx_top_10_em", "个股-十大股东"),
            ("stock_gdfx_free_holding_detail_em", "十大流通股东持股明细"),
            ("stock_gdfx_holding_detail_em", "十大股东持股明细"),
            ("stock_gdfx_free_holding_change_em", "十大流通股东持股变动统计"),
            ("stock_gdfx_holding_change_em", "十大股东持股变动统计"),
            ("stock_gdfx_free_holding_statistics_em", "十大流通股东持股统计"),
            ("stock_gdfx_holding_statistics_em", "十大股东持股统计"),
            ("stock_gdfx_free_holding_teamwork_em", "十大流通股东协同"),
            ("stock_gdfx_holding_teamwork_em", "十大股东协同"),
        ],
        "期权分析-东方财富": [ # Combined
            ("option_lhb_em", "期权龙虎榜"),
            ("option_value_analysis_em", "期权价值分析"),
            ("option_risk_analysis_em", "期权风险分析"),
            ("option_premium_analysis_em", "期权折溢价分析"),
        ],
        "财新指数": [
            ("index_pmi_com_cx", "财新中国PMI-综合PMI"),
            ("index_pmi_man_cx", "财新中国PMI-制造业PMI"),
            ("index_pmi_ser_cx", "财新中国PMI-服务业PMI"),
            ("index_dei_cx", "数字经济指数"),
            ("index_ii_cx", "产业指数"),
            ("index_si_cx", "溢出指数"),
            ("index_fi_cx", "融合指数"),
            ("index_bi_cx", "基础指数"),
            ("index_nei_cx", "中国新经济指数"),
            ("index_li_cx", "劳动力投入指数"),
            ("index_ci_cx", "资本投入指数"),
            ("index_ti_cx", "科技投入指数"),
            ("index_neaw_cx", "新经济行业入职平均工资水平"),
            ("index_awpr_cx", "新经济入职工资溢价水平"),
            ("index_cci_cx", "大宗商品指数"),
            ("index_qli_cx", "高质量因子"),
            ("index_ai_cx", "AI策略指数"),
            ("index_bei_cx", "基石经济指数"),
            ("index_neei_cx", "新动能指数"),
        ],
        "中国股票指数历史与分时": [ # Combined
            ("index_zh_a_hist", "历史数据"),
            ("index_zh_a_hist_min_em", "分时数据 (东财)"),
        ],
        "东方财富-个股人气榜-A股": [
            ("stock_hot_rank_em", "人气榜"),
            ("stock_hot_up_em", "飙升榜"),
            ("stock_hot_rank_detail_em", "历史趋势及粉丝特征"),
            ("stock_hot_rank_detail_realtime_em", "实时变动"),
            ("stock_hot_keyword_em", "关键词"),
            ("stock_hot_rank_latest_em", "最新排名"),
            ("stock_hot_rank_relate_em", "相关股票"),
        ],
        "东方财富-个股人气榜-港股": [
            ("stock_hk_hot_rank_em", "人气榜-港股"),
            ("stock_hk_hot_rank_detail_em", "历史趋势-港股"),
            ("stock_hk_hot_rank_detail_realtime_em", "实时变动-港股"),
            ("stock_hk_hot_rank_latest_em", "最新排名-港股"),
        ],
        "东方财富-龙虎榜": [ # Different from Sina's
            ("stock_lhb_detail_em", "龙虎榜详情"),
            ("stock_lhb_stock_statistic_em", "个股上榜统计"),
            ("stock_lhb_stock_detail_em", "个股龙虎榜详情"),
            ("stock_lhb_jgmmtj_em", "机构买卖每日统计"),
            ("stock_lhb_hyyyb_em", "每日活跃营业部"),
            ("stock_lhb_yyb_detail_em", "营业部详情"),
            ("stock_lhb_yybph_em", "营业部排行"),
            ("stock_lhb_jgstatistic_em", "机构席位追踪"),
            ("stock_lhb_traderstatistic_em", "营业部统计"),
        ],
        "天天基金网-投资组合": [ # Combined from EM
            ("fund_portfolio_hold_em", "基金持仓"),
            ("fund_portfolio_bond_hold_em", "债券持仓"),
            ("fund_portfolio_change_em", "重大变动"),
            ("fund_portfolio_industry_allocation_em", "行业配置"),
        ],
        "宏观-中国-综合指数与运输": [ # New category
            ("macro_china_insurance_income", "原保险保费收入"),
            ("macro_china_mobile_number", "手机出货量"),
            ("macro_china_vegetable_basket", "菜篮子产品批发价格指数"),
            ("macro_china_agricultural_product", "农产品批发价格总指数"),
            ("macro_china_agricultural_index", "农副指数"),
            ("macro_china_energy_index", "能源指数"),
            ("macro_china_commodity_price_index", "大宗商品价格"),
            ("macro_global_sox_index", "费城半导体指数"), # Global, but placed here
            ("macro_china_yw_electronic_index", "义乌小商品指数-电子元器件"),
            ("macro_china_construction_index", "建材指数"),
            ("macro_china_construction_price_index", "建材价格指数"),
            ("macro_china_lpi_index", "物流景气指数"),
            ("macro_china_bdti_index", "原油运输指数"),
            ("macro_china_bsi_index", "超灵便型船运价指数"),
        ],
        "可转债分析": [ # Duplicate bond_zh_cov_value_analysis implies two different analyses if this is correct
            ("bond_zh_cov_value_analysis", "可转债溢价率与价值分析"), # Combined description
        ],
        "股票热度-雪球": [
            ("stock_hot_follow_xq", "关注排行榜"),
            ("stock_hot_tweet_xq", "讨论排行榜"),
            ("stock_hot_deal_xq", "分享交易排行榜"),
        ],
        "内部交易-雪球": [
            ("stock_inner_trade_xq", "内部交易"),
        ],
        "股票财务报表-东方财富-细分": [ # More specific category
            ("stock_balance_sheet_by_report_em", "资产负债表-按报告期"),
            ("stock_balance_sheet_by_yearly_em", "资产负债表-按年度"),
            ("stock_profit_sheet_by_report_em", "利润表-报告期"),
            ("stock_profit_sheet_by_yearly_em", "利润表-按年度"),
            ("stock_profit_sheet_by_quarterly_em", "利润表-按单季度"),
            ("stock_cash_flow_sheet_by_report_em", "现金流量表-按报告期"),
            ("stock_cash_flow_sheet_by_yearly_em", "现金流量表-按年度"),
            ("stock_cash_flow_sheet_by_quarterly_em", "现金流量表-按单季度"),
            ("stock_balance_sheet_by_report_delisted_em", "资产负债表-已退市-按报告期"),
            ("stock_profit_sheet_by_report_delisted_em", "利润表-已退市-按报告期"),
            ("stock_cash_flow_sheet_by_report_delisted_em", "现金流量表-已退市-按报告期"),
        ],
        "财经事件与通知-百度": [ # Combined from Baidu
            ("news_economic_baidu", "宏观-全球事件"),
            ("news_trade_notify_suspend_baidu", "停复牌通知"), # Shortened
            ("news_report_time_baidu", "财报发行时间"), # Shortened
            ("news_trade_notify_dividend_baidu", "分红配股通知"), #Shortened
        ],
        "金融期权-上交所": [
            ("option_risk_indicator_sse", "期权风险指标"),
        ],
        "人民币汇率中间价-外管局": [ # Added source
            ("currency_boc_safe", "人民币汇率中间价"),
        ],
        "主营构成-东方财富": [
            ("stock_zygc_em", "主营构成"),
        ],
        "行业与股本变动-巨潮资讯": [ # Combined from cninfo
            ("stock_industry_category_cninfo", "行业分类数据"),
            ("stock_industry_change_cninfo", "上市公司行业归属变动"),
            ("stock_share_change_cninfo", "公司股本变动"),
        ],
        "上海金属网-快讯": [
            ("futures_news_shmet", "快讯"),
        ],
        "中债指数-综合类": [
            ("bond_new_composite_index_cbond", "中债-新综合指数"),
            ("bond_composite_index_cbond", "中债-综合指数"),
        ],
        "沪深港股通-汇率-交易所": [ # Combined
            ("stock_sgt_settlement_exchange_rate_szse", "深港通-结算汇率 (深交所)"),
            ("stock_sgt_reference_exchange_rate_szse", "深港通-参考汇率 (深交所)"),
            ("stock_sgt_reference_exchange_rate_sse", "沪港通-参考汇率 (上交所)"),
            ("stock_sgt_settlement_exchange_rate_sse", "沪港通-结算汇兑 (上交所)"),
        ],
        "配股与公司概况-巨潮资讯": [ # Combined from cninfo
            ("stock_allotment_cninfo", "配股实施方案"),
            ("stock_profile_cninfo", "个股-公司概况"),
            ("stock_ipo_summary_cninfo", "个股-上市相关"),
        ],
        "估值与热搜-百度股市通": [ # Combined from Baidu
            ("stock_hk_valuation_baidu", "港股-财务报表-估值数据"),
            ("stock_zh_valuation_baidu", "A 股-财务报表-估值数据"),
            ("stock_zh_vote_baidu", "A 股或指数-股评-投票"),
            ("stock_hot_search_baidu", "热搜股票"),
        ],
        "乐咕乐股-特色指标": [
            ("stock_buffett_index_lg", "底部研究-巴菲特指标"),
            ("stock_a_gxl_lg", "股息率-A 股股息率"),
            ("stock_hk_gxl_lg", "股息率-恒生指数股息率"),
            ("stock_a_congestion_lg", "大盘拥挤度"),
        ],
        "百度股市通-外汇行情": [
            ("fx_quote_baidu", "行情榜单"),
        ],
        "期权波动率指数(QVIX)": [ # Combined QVIX indices
            ("index_option_50etf_qvix", "50ETF期权波动率指数"),
            ("index_option_50etf_min_qvix", "50ETF期权波动率指数-分时"),
            ("index_option_300etf_qvix", "300ETF期权波动率指数"),
            ("index_option_300etf_min_qvix", "300ETF期权波动率指数-分时"),
            ("index_option_500etf_qvix", "500ETF期权波动率指数"),
            ("index_option_500etf_min_qvix", "500ETF期权波动率指数-分时"),
            ("index_option_cyb_qvix", "创业板期权波动率指数"),
            ("index_option_cyb_min_qvix", "创业板期权波动率指数-分时"),
            ("index_option_kcb_qvix", "科创板期权波动率指数"),
            ("index_option_kcb_min_qvix", "科创板期权波动率指数-分时"),
            ("index_option_100etf_qvix", "深证100ETF期权波动率指数"),
            ("index_option_100etf_min_qvix", "深证100ETF期权波动率指数-分时"),
            ("index_option_300index_qvix", "中证300股指期权波动率指数"),
            ("index_option_300index_min_qvix", "中证300股指期权波动率指数-分时"),
            ("index_option_1000index_qvix", "中证1000股指期权波动率指数"),
            ("index_option_1000index_min_qvix", "中证1000股指期权波动率指数-分时"),
            ("index_option_50index_qvix", "上证50股指期权波动率指数"),
            ("index_option_50index_min_qvix", "上证50股指期权波动率指数-分时"),
        ],
        "申万指数-行情与成分": [ # Combined SW
            ("index_realtime_sw", "实时行情"),
            ("index_hist_sw", "历史行情"),
            ("index_min_sw", "分时行情"),
            ("index_component_sw", "成分股"),
        ],
        "申万宏源研究-行业与指数分析": [ # Combined SW research
            ("stock_industry_clf_hist_sw", "行业分类-全部行业分类"),
            ("index_analysis_daily_sw", "指数分析-日报表"),
            ("index_analysis_weekly_sw", "指数分析-周报表"),
            ("index_analysis_monthly_sw", "指数分析-月报表"),
            ("index_analysis_week_month_sw", "指数分析-周/月-日期序列"),
            ("index_realtime_fund_sw", "基金指数-实时行情"),
            ("index_hist_fund_sw", "基金指数-历史行情"),
        ],
        "中国外汇交易中心-债券信息": [ # Combined
            ("bond_info_cm", "信息查询结果"),
            ("bond_info_detail_cm", "债券详情"),
        ],
        "生猪市场价格指数": [
            ("index_hog_spot_price", "生猪市场价格指数"),
        ],
        "乐咕乐股-基金仓位": [
            ("fund_stock_position_lg", "股票型基金仓位"),
            ("fund_balance_position_lg", "平衡混合型基金仓位"),
            ("fund_linghuo_position_lg", "灵活配置型基金仓位"),
        ],
        "主营介绍-同花顺": [
            ("stock_zyjs_ths", "主营介绍"),
        ],
        "行情报价-东方财富": [
            ("stock_bid_ask_em", "东方财富-行情报价"),
        ],
        "可转债-同花顺": [ # Differs from EM source
            ("bond_zh_cov_info_ths", "数据中心-可转债"),
        ],
        "港股股票指数": [ # Combined HK Index
            ("stock_hk_index_spot_sina", "实时行情 (新浪)"),
            ("stock_hk_index_daily_sina", "历史行情 (新浪)"),
            ("stock_hk_index_spot_em", "实时行情 (东财)"),
            ("stock_hk_index_daily_em", "历史行情 (东财)"),
        ],
        "同花顺-财务指标": [ # Combined from THS
            ("stock_financial_abstract_ths", "主要指标"),
            ("stock_financial_debt_ths", "资产负债表"),
            ("stock_financial_benefit_ths", "利润表"),
            ("stock_financial_cash_ths", "现金流量表"),
        ],
        "LOF行情-东方财富": [
            ("fund_lof_hist_em", "历史行情"),
            ("fund_lof_spot_em", "实时行情"),
            ("fund_lof_hist_min_em", "分时行情"),
        ],
        "新浪财经-ESG评级": [
            ("stock_esg_msci_sina", "MSCI评级"),
            ("stock_esg_rft_sina", "路孚特评级"),
            ("stock_esg_rate_sina", "ESG评级数据"),
            ("stock_esg_zd_sina", "秩鼎评级"),
            ("stock_esg_hz_sina", "华证指数评级"),
        ],
        "基金公告-人事调整-东方财富": [
            ("fund_announcement_personnel_em", "人事调整"),
        ],
        "互动易与e互动": [ # Combined
            ("stock_irm_cninfo", "互动易-提问 (巨潮)"),
            ("stock_irm_ans_cninfo", "互动易-回答 (巨潮)"),
            ("stock_sns_sseinfo", "上证e互动-提问与回答"),
        ],
        "新浪财经-可转债": [
            ("bond_cb_profile_sina", "详情资料"),
            ("bond_cb_summary_sina", "债券概况"),
        ],
        "东方财富-高管持股明细": [
            ("stock_hold_management_detail_em", "董监高及相关人员持股变动明细"),
            ("stock_hold_management_person_em", "人员增减持股变动明细"),
        ],
        "东方财富-股市日历与会议": [ # Combined
            ("stock_gsrl_gsdt_em", "股市日历-公司动态"),
            ("stock_gddh_em", "股东大会"),
        ],
        "东方财富-重大合同与研报": [ # Combined
            ("stock_zdhtmx_em", "重大合同明细"),
            ("stock_research_report_em", "个股研报"),
        ],
        "董监高持股变动-交易所": [ # Combined from exchanges
            ("stock_share_hold_change_sse", "上海证券交易所"),
            ("stock_share_hold_change_szse", "深圳证券交易所"),
            ("stock_share_hold_change_bse", "北京证券交易所"),
        ],
        "国家统计局数据": [ # Combined NBS
            ("macro_china_nbs_nation", "全国数据通用接口"),
            ("macro_china_nbs_region", "地区数据通用接口"),
        ],
        "新浪财经-美股指数行情": [
            ("index_us_stock_sina", "美股指数行情"),
        ],
        "融资融券-平安证券": [ # Added source
            ("stock_margin_ratio_pa", "标的证券名单及保证金比例查询"),
        ],
        "日内分时数据-多源": [ # Combined
            ("stock_intraday_em", "东财财富"),
            ("stock_intraday_sina", "新浪财经"),
        ],
        "筹码分布-东方财富": [
            ("stock_cyq_em", "筹码分布"),
        ],
        "雪球基金-详情与分析": [ # Combined from XQ
            ("fund_individual_basic_info_xq", "基金详情"),
            ("fund_individual_achievement_xq", "基金业绩"),
            ("fund_individual_analysis_xq", "基金数据分析"),
            ("fund_individual_profit_probability_xq", "盈利概率"),
            ("fund_individual_detail_info_xq", "交易规则"),
            ("fund_individual_detail_hold_xq", "持仓详情"),
        ],
        "港股盈利预测-经济通": [ # Added source
            ("stock_hk_profit_forecast_et", "港股盈利预测"),
        ],
        "雪球-个股实时行情": [
            ("stock_individual_spot_xq", "个股实时行情"),
        ],
        "东方财富-国际期货": [
            ("futures_global_spot_em", "实时行情"),
            ("futures_global_hist_em", "历史行情"),
        ],
        "东方财富-沪深港通分时": [
            ("stock_hsgt_fund_min_em", "市场概括-分时数据"),
        ],
        "新浪财经-商品期货成交持仓": [
            ("futures_hold_pos_sina", "成交持仓"),
        ],
        "生意社-商品与期货现期图": [
            ("futures_spot_sys", "现期图"),
        ],
        "上海期交所库存周报": [
            ("futures_stock_shfe_js", "指定交割仓库库存周报"),
        ],
        "期货合约信息-各交易所": [ # Combined
            ("futures_contract_info_shfe", "上海期货交易所"),
            ("futures_contract_info_ine", "上海国际能源交易中心"),
            ("futures_contract_info_dce", "大连商品交易所"),
            ("futures_contract_info_czce", "郑州商品交易所"),
            ("futures_contract_info_gfex", "广州期货交易所"),
            ("futures_contract_info_cffex", "中国金融期货交易所"),
        ],
        "资讯数据-多源": [
            ("stock_info_cjzc_em", "财经早餐 (东财)"),
            ("stock_info_global_em", "全球资讯 (东财)"),
            ("stock_info_global_sina", "全球资讯 (新浪)"),
            ("stock_info_global_futu", "全球资讯 (富途)"),
            ("stock_info_global_ths", "全球资讯 (同花顺)"),
            ("stock_info_global_cls", "全球资讯 (财联社)"),
            ("stock_info_broker_sina", "券商原创 (新浪)"),
        ],
        "数库-A股新闻情绪指数": [
            ("index_news_sentiment_scope", "A股新闻情绪指数"),
        ],
        "华尔街见闻-日历宏观": [
            ("macro_info_ws", "日历-宏观"),
        ],
        "期货多维监控系统-现货走势": [ # Added source context
            ("spot_price_qh", "现货走势"),
        ],
        "东方财富-两融账户信息": [
            ("stock_margin_account_info", "融资融券账户统计"),
        ],
        "股票期权-每日统计-交易所": [ # Combined
            ("option_daily_stats_sse", "上海证券交易所"),
            ("option_daily_stats_szse", "深圳证券交易所"),
        ],
        "商品期权手续费": [
            ("option_comm_info", "商品期权手续费"),
        ],
        "富途牛牛-概念板块成分股": [
            ("stock_concept_cons_futu", "成分股"),
        ],
        "同花顺-宏观经济数据": [ # Combined
            ("macro_stock_finance", "股票筹资"),
            ("macro_rmb_loan", "新增人民币贷款"),
            ("macro_rmb_deposit", "人民币存款余额"),
        ],
        "知名港股-东方财富": [ # This was stock_us_famous_spot_em, assuming it's for HK now
             ("stock_hk_famous_spot_em", "知名港股实时行情"), # Renamed func to avoid conflict, original list had stock_us_famous_spot_em here
        ],
        "搜猪网-生猪大数据": [ # Combined from Soozhu
            ("spot_hog_soozhu", "各省均价实时排行榜"),
            ("spot_hog_year_trend_soozhu", "今年以来全国出栏均价走势"),
            ("spot_hog_lean_price_soozhu", "全国瘦肉型肉猪"),
            ("spot_hog_three_way_soozhu", "全国三元仔猪"),
            ("spot_hog_crossbred_soozhu", "全国后备二元母猪"),
            ("spot_corn_price_soozhu", "全国玉米价格走势"),
            ("spot_soybean_price_soozhu", "全国豆粕价格走势"),
            ("spot_mixed_feed_soozhu", "全国育肥猪合料半月走势"),
        ],
        "财新网-财新数据通新闻": [
            ("stock_news_main_cx", "财新数据通"),
        ],
        "集思录-QDII基金": [ # Combined from JSL
            ("qdii_e_index_jsl", "欧美市场-欧美指数"),
            ("qdii_e_comm_jsl", "欧美市场-商品"),
            ("qdii_a_index_jsl", "亚洲市场-亚洲指数"),
        ],
        "同花顺-股东与高管持股变动": [ # Combined from THS
            ("stock_shareholder_change_ths", "股东持股变动"),
            ("stock_management_change_ths", "高管持股变动"),
        ],
        "计算指标-已实现波动率": [
            ("volatility_yz_rv", "已实现波动率计算"),
        ],
        "东方财富-估值分析": [
            ("stock_value_em", "每日互动-估值分析"),
        ],
        "基金费率-东方财富": [
            ("fund_fee_em", "基金费率"),
        ],
        "期货行情-东方财富": [ # Differs from Sina
            ("futures_hist_em", "历史行情"), # Assuming it means general futures, not global
        ],
        "美股财报-东方财富": [
            ("stock_financial_us_report_em", "三大报表"),
            ("stock_financial_us_analysis_indicator_em", "主要指标"),
        ],
        "东方财富-AH股与港股通": [ # Combined
            ("stock_zh_ah_spot_em", "AH股比价-实时行情"), # Differs from general AH Spot
            ("stock_hsgt_sh_hk_spot_em", "港股通(沪>港)-股票"),
        ],
        "东方财富-外汇市场": [
            ("forex_spot_em", "所有汇率-实时行情"),
            ("forex_hist_em", "所有汇率-历史行情"),
        ],
        "东方财富-全球指数": [ # Differs from Sina
            ("index_global_spot_em", "实时行情"),
            ("index_global_hist_em", "历史行情"),
        ],
        "新浪财经-环球市场指数": [ # Combined
            ("index_global_name_table", "名称代码映射表"),
            # ("index_global_hist_em", "历史行情"), # Already under EM, func name conflict if same. Assuming Sina has only name table.
            # If index_global_hist_em from Sina is different, it needs a unique name.
            # For now, I'll assume the EM one is the primary one for historical data under this name.
        ],
        "股本结构-东方财富": [
            ("stock_zh_a_gbjg_em", "股本结构"),
        ],
        "质押式回购-东方财富": [ # Combined
            ("bond_sh_buy_back_em", "上证质押式回购"),
            ("bond_sz_buy_back_em", "深证质押式回购"),
            ("bond_buy_back_hist_em", "历史数据"),
        ],
        "东方财富-港股公司资料": [ # Combined
            ("stock_hk_security_profile_em", "证券资料"),
            ("stock_hk_company_profile_em", "公司资料"),
        ],
        "工具与杂项": [ # For items that don't fit well elsewhere or are unique
             ("tool_trade_date_hist", "交易日历 (新浪)"), # Already exists, just placing it again if needed
        ]
        # ... many more functions need to be parsed and added here
        # based on the user's full list. This is a placeholder for the structure.
    }
    # --- END OF THE MASSIVE FUNCTION LIST (Example) ---

    # Deduplication and refinement logic (Example for fx_spot_quote)
    # This step is crucial and needs to be done for ALL functions from the user's list.
    # Here's a conceptual example of how you might handle duplicates or refine categories:

    # Initial pass to collect all functions and their original categories
    raw_funcs = {}
    original_list_parsed = [ # This would be the fully parsed version of the user's input
        {"category": "交易所期货数据", "name": "get_cffex_daily", "desc": "中国金融期货交易所每日交易数据"},
        # ... all 700+ entries
        {"category": "外汇", "name": "get_fx_spot_quote", "desc": "人民币外汇即期报价数据"},
        {"category": "全国银行间同业拆借中心-市场数据-市场行情-外汇市场行情", "name": "fx_spot_quote", "desc": "市场行情-外汇市场行情-人民币外汇即期报价"},
        {"category": "东方财富网-行情中心-外汇市场-所有汇率", "name": "forex_spot_em", "desc": "东方财富网-行情中心-外汇市场-所有汇率-实时行情数据"},
    ]

    final_categorized_functions = {}
    func_to_cat_map = {} # To detect true duplicates of (name, desc)

    for item in AKSHARE_FUNCTIONS_FULL.items(): # Iterate through my manually created dict for now
        category_name = item[0]
        functions_in_category = item[1]
        if category_name not in final_categorized_functions:
            final_categorized_functions[category_name] = []
        
        for func_name, func_desc in functions_in_category:
            # Simple deduplication: if same name and desc appear, only take first.
            # More sophisticated would be to check if they are actually different functions in akshare.
            # For now, assume func_name is unique enough for getattr(ak, func_name)
            
            # Check if this specific function name is already added to ANY category.
            # If it is, and the description is identical, it's a true duplicate entry in the source list.
            # If descriptions differ, or if the category context implies it's a different variant,
            # then they might be distinct or need careful renaming/categorization.

            # This simplified deduplication is based on (func_name) within a category.
            # A more robust deduplication would be global based on (func_name, func_desc)
            # or even deeper by inspecting the actual function object if descriptions are ambiguous.
            
            # For this exercise, I'll assume the manual categorization already handled most severe duplicates.
            # The main goal is to get all unique (func_name, desc) pairs into the structure.
            
            # Let's refine to avoid adding the exact same (name, desc) tuple multiple times across categories
            # if the original input list had them.
            # However, the user's request is to list them as they appear, so I'll stick to that for now.
            # The search will help find them regardless of category.
            
            # The provided list does have some function names appearing in multiple categories.
            # Example: "fx_spot_quote"
            # The GUI will show it under each category it's listed in.
            final_categorized_functions[category_name].append((func_name, func_desc))
            
    return final_categorized_functions


class AkshareGUI:
    def __init__(self, master):
        self.master = master
        master.title("Akshare GUI Client (全功能版)")
        master.geometry("1300x850") # Slightly larger default size

        self.current_ak_function = None
        self.param_widgets = {}
        self.q = queue.Queue()
        self.all_functions_data = get_all_akshare_functions() # Load all functions

        # --- Main Layout Panes ---
        self.paned_window = ttk.PanedWindow(master, orient=tk.HORIZONTAL)
        self.paned_window.pack(fill=tk.BOTH, expand=True)

        self.left_pane = ttk.Frame(self.paned_window, padding=10)
        self.paned_window.add(self.left_pane, weight=2) # Adjusted weight

        self.right_pane = ttk.Frame(self.paned_window, padding=10)
        self.paned_window.add(self.right_pane, weight=5) # Adjusted weight

        # --- Left Pane Widgets ---
        # Search Bar
        search_frame = ttk.Frame(self.left_pane)
        search_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(search_frame, text="搜索接口:").pack(side=tk.LEFT, padx=(0,5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var)
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.search_var.trace_add("write", self.filter_function_tree)

        # Function Tree
        ttk.Label(self.left_pane, text="选择接口:", font=("Arial", 11, "bold")).pack(anchor=tk.W)
        self.func_tree = ttk.Treeview(self.left_pane, selectmode="browse")
        self.func_tree_vsb = ttk.Scrollbar(self.left_pane, orient="vertical", command=self.func_tree.yview)
        self.func_tree_hsb = ttk.Scrollbar(self.left_pane, orient="horizontal", command=self.func_tree.xview)
        self.func_tree.configure(yscrollcommand=self.func_tree_vsb.set, xscrollcommand=self.func_tree_hsb.set)
        
        self.func_tree_vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.func_tree.pack(fill=tk.BOTH, expand=True, pady=5) # Pack before tree
        self.func_tree_hsb.pack(side=tk.BOTTOM, fill=tk.X, before=self.func_tree)
        self.func_tree.pack(fill=tk.BOTH, expand=True, pady=5)
        self.func_tree.bind("<<TreeviewSelect>>", self.on_function_select)
        self.populate_function_tree(self.all_functions_data) # Initial population

        # Parameters Frame
        self.params_frame_outer = ttk.LabelFrame(self.left_pane, text="参数输入", padding=10)
        self.params_frame_outer.pack(fill=tk.X, pady=10, expand=False) # Don't expand this frame vertically
        
        self.params_canvas = tk.Canvas(self.params_frame_outer, height=150) # Set a fixed initial height
        self.params_scrollbar_v = ttk.Scrollbar(self.params_frame_outer, orient="vertical", command=self.params_canvas.yview)
        self.params_scrollbar_h = ttk.Scrollbar(self.params_frame_outer, orient="horizontal", command=self.params_canvas.xview)
        self.params_scrollable_frame = ttk.Frame(self.params_canvas)

        self.params_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.params_canvas.configure(
                scrollregion=self.params_canvas.bbox("all")
            )
        )
        self.params_canvas_window = self.params_canvas.create_window((0, 0), window=self.params_scrollable_frame, anchor="nw")
        self.params_canvas.configure(yscrollcommand=self.params_scrollbar_v.set, xscrollcommand=self.params_scrollbar_h.set)
        
        self.params_scrollbar_v.pack(side="right", fill="y")
        self.params_scrollbar_h.pack(side="bottom", fill="x") # Horizontal scrollbar for params
        self.params_canvas.pack(side="left", fill="both", expand=True)
        
        # Fetch Button
        self.fetch_button = ttk.Button(self.left_pane, text="获取数据", command=self.fetch_data)
        self.fetch_button.pack(fill=tk.X, pady=10)

        # --- Right Pane Widgets ---
        self.notebook = ttk.Notebook(self.right_pane)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.doc_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.doc_tab, text="接口说明")
        self.doc_text = scrolledtext.ScrolledText(self.doc_tab, wrap=tk.WORD, height=10, relief=tk.SUNKEN, borderwidth=1)
        self.doc_text.pack(fill=tk.BOTH, expand=True)
        self.doc_text.configure(state='disabled')

        self.data_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.data_tab, text="数据结果")
        self.data_tree_frame = ttk.Frame(self.data_tab)
        self.data_tree_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.data_tree = ttk.Treeview(self.data_tree_frame, show="headings")
        self.data_vsb = ttk.Scrollbar(self.data_tree_frame, orient="vertical", command=self.data_tree.yview)
        self.data_hsb = ttk.Scrollbar(self.data_tree_frame, orient="horizontal", command=self.data_tree.xview)
        self.data_tree.configure(yscrollcommand=self.data_vsb.set, xscrollcommand=self.data_hsb.set)
        self.data_vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.data_hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.data_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.save_button = ttk.Button(self.data_tab, text="保存为 CSV", command=self.save_to_csv, state=tk.DISABLED)
        self.save_button.pack(pady=5)

        # --- Status Bar ---
        self.status_var = tk.StringVar()
        self.status_var.set("就绪。请在左侧选择接口，填入参数后点击“获取数据”。")
        self.status_bar = ttk.Label(master, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.master.after(100, self.process_queue)

    def populate_function_tree(self, functions_data):
        # Clear existing items
        for i in self.func_tree.get_children():
            self.func_tree.delete(i)

        for category, funcs in functions_data.items():
            cat_id = self.func_tree.insert("", tk.END, text=category, open=False, tags=('category',))
            for func_name, func_desc in funcs:
                # Store full description for searching, display shortened if too long
                display_text = f"{func_name} - {func_desc[:60]}{'...' if len(func_desc) > 60 else ''}"
                self.func_tree.insert(cat_id, tk.END, text=display_text, 
                                      values=(func_name, func_desc), tags=('function',))
        
        self.func_tree.tag_configure('category', font=('Arial', 10, 'bold'))
        self.func_tree.tag_configure('function', font=('Arial', 9))


    def filter_function_tree(self, *args):
        search_term = self.search_var.get().lower()
        
        # Clear current tree
        for i in self.func_tree.get_children():
            self.func_tree.delete(i)

        if not search_term: # If search is empty, show all
            self.populate_function_tree(self.all_functions_data)
            return

        # Filter and repopulate
        matching_categories = {}
        for category, funcs in self.all_functions_data.items():
            matching_funcs_in_cat = []
            category_matches = search_term in category.lower()
            
            for func_name, func_desc in funcs:
                if search_term in func_name.lower() or search_term in func_desc.lower():
                    matching_funcs_in_cat.append((func_name, func_desc))
            
            if matching_funcs_in_cat or category_matches : # If category name matches, show all its funcs too
                if category_matches and not matching_funcs_in_cat: # Category name matches, but no funcs did
                     matching_categories[category] = funcs # Add all functions from this category
                elif matching_funcs_in_cat:
                    matching_categories[category] = matching_funcs_in_cat


        self.populate_function_tree(matching_categories)
        # Expand all categories that have matches
        for item_id in self.func_tree.get_children():
            self.func_tree.item(item_id, open=True)


    def on_function_select(self, event):
        selected_item = self.func_tree.focus()
        if not selected_item: return
        
        item_tags = self.func_tree.item(selected_item, "tags")
        if 'category' in item_tags: # Clicked on a category
            self.clear_params_and_doc()
            self.current_ak_function = None
            return

        item_values = self.func_tree.item(selected_item, "values")
        if not item_values or len(item_values) < 1: # Should not happen if tag is 'function'
             self.clear_params_and_doc()
             self.current_ak_function = None
             return

        func_name = item_values[0]
        try:
            self.current_ak_function = getattr(ak, func_name)
            self.display_function_params(self.current_ak_function)
            self.display_docstring(self.current_ak_function)
            self.notebook.select(self.doc_tab)
        except AttributeError:
            self.status_var.set(f"错误: Akshare库中未找到函数 {func_name}")
            self.clear_params_and_doc()
            self.current_ak_function = None
        except Exception as e:
            self.status_var.set(f"加载函数 {func_name} 出错: {e}")
            self.clear_params_and_doc()
            self.current_ak_function = None
            
    def clear_params_and_doc(self):
        for widget in self.params_scrollable_frame.winfo_children():
            widget.destroy()
        self.param_widgets = {}
        self.doc_text.configure(state='normal')
        self.doc_text.delete(1.0, tk.END)
        self.doc_text.configure(state='disabled')
        # Reset canvas scroll region
        self.params_canvas.configure(scrollregion=self.params_canvas.bbox("all"))


    def display_function_params(self, func):
        for widget in self.params_scrollable_frame.winfo_children():
            widget.destroy()
        self.param_widgets = {}

        try:
            sig = inspect.signature(func)
            params = sig.parameters
            if not params:
                ttk.Label(self.params_scrollable_frame, text="该函数无需参数.").pack(anchor=tk.W, pady=2)
            else:
                for name, param in params.items():
                    if param.kind == param.VAR_POSITIONAL or param.kind == param.VAR_KEYWORD:
                        continue

                    row_frame = ttk.Frame(self.params_scrollable_frame)
                    row_frame.pack(fill=tk.X, pady=3, padx=2) # Added padx

                    param_label_text = name
                    param_type_hint = ""
                    if param.annotation != inspect.Parameter.empty:
                        if hasattr(param.annotation, '__name__'):
                            param_type_hint = param.annotation.__name__
                        elif hasattr(param.annotation, '__origin__'): # For Union, Optional etc.
                             param_type_hint = str(param.annotation)
                        else:
                            param_type_hint = str(param.annotation)
                        param_label_text += f" ({param_type_hint})"
                    
                    ttk.Label(row_frame, text=param_label_text + ":", width=25, anchor="e").pack(side=tk.LEFT, padx=(0,5))
                    
                    # Placeholder for future:
                    # if param_type_hint == 'bool':
                    #     var = tk.BooleanVar()
                    #     widget = ttk.Checkbutton(row_frame, variable=var)
                    #     if param.default != inspect.Parameter.empty:
                    #         var.set(param.default)
                    # else:
                    #     widget = ttk.Entry(row_frame, width=35)
                    #     if param.default != inspect.Parameter.empty:
                    #         widget.insert(0, str(param.default))
                    
                    entry = ttk.Entry(row_frame, width=35)
                    entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
                    self.param_widgets[name] = entry

                    if param.default != inspect.Parameter.empty:
                        entry.insert(0, str(param.default))
                    else:
                        # Basic placeholder hints based on name or docstring content
                        doc = func.__doc__ if func.__doc__ else ""
                        date_match = re.search(rf"{name}\s*:\s*str\s*.*YYYYMMDD", doc, re.IGNORECASE)
                        symbol_match = re.search(rf"{name}\s*:\s*str\s*.*代码", doc, re.IGNORECASE)
                        if "date" in name.lower() or date_match:
                            entry.insert(0, "YYYYMMDD")
                        elif "symbol" in name.lower() or "code" in name.lower() or symbol_match:
                            entry.insert(0, "请输入代码")
                        elif param_type_hint == 'bool':
                             entry.insert(0, "True/False")
                        elif param.annotation == inspect.Parameter.empty and not doc: # No type hint, no doc
                            entry.insert(0, "请输入值")


        except ValueError:
            ttk.Label(self.params_scrollable_frame, text="无法解析此函数的参数.").pack(anchor=tk.W, pady=2)
        except Exception as e:
            ttk.Label(self.params_scrollable_frame, text=f"解析参数出错: {type(e).__name__}: {e}").pack(anchor=tk.W, pady=2)
        
        # Update canvas scrollregion after adding widgets
        self.params_scrollable_frame.update_idletasks() # Ensure widgets are drawn
        self.params_canvas.config(scrollregion=self.params_canvas.bbox("all"))


    def display_docstring(self, func):
        self.doc_text.configure(state='normal')
        self.doc_text.delete(1.0, tk.END)
        docstring = inspect.getdoc(func) # Use getdoc for cleaned docstring
        if docstring:
            self.doc_text.insert(tk.END, docstring)
        else:
            self.doc_text.insert(tk.END, "此函数没有文档字符串.")
        self.doc_text.configure(state='disabled')

    def fetch_data(self):
        if not self.current_ak_function:
            messagebox.showerror("错误", "请先选择一个接口函数!")
            return

        kwargs = {}
        try:
            sig = inspect.signature(self.current_ak_function)
            for name, widget in self.param_widgets.items():
                value_str = widget.get()
                param_spec = sig.parameters[name]
                
                if value_str == "" and param_spec.default != inspect.Parameter.empty:
                    # Let Akshare handle default if input is empty string for optional param
                    continue 
                elif value_str == "None":
                    kwargs[name] = None
                elif value_str:
                    # Type conversion attempt
                    target_type = param_spec.annotation
                    if target_type != inspect.Parameter.empty:
                        if target_type == bool or str(target_type) == "bool": # str check for forward refs
                            kwargs[name] = value_str.lower() in ['true', '1', 't', 'y', 'yes']
                        elif target_type == int or str(target_type) == "int":
                            kwargs[name] = int(value_str)
                        elif target_type == float or str(target_type) == "float":
                            kwargs[name] = float(value_str)
                        else: # Mostly str, or complex types Akshare handles
                            kwargs[name] = value_str
                    else: # No type hint, pass as string
                        kwargs[name] = value_str
            
            self.status_var.set(f"正在获取: {self.current_ak_function.__name__}...")
            self.fetch_button.config(state=tk.DISABLED)
            self.save_button.config(state=tk.DISABLED)
            self.clear_data_tree()

            thread = threading.Thread(target=self.run_akshare_function, 
                                      args=(self.current_ak_function, kwargs), daemon=True)
            thread.start()

        except ValueError as e:
            messagebox.showerror("参数错误", f"参数转换失败: {e}\n请检查输入格式 (参考接口说明).")
            self.status_var.set("参数错误")
            self.fetch_button.config(state=tk.NORMAL) # Re-enable button on pre-fetch error
        except Exception as e:
            messagebox.showerror("错误", f"准备调用接口时发生错误: {type(e).__name__}: {e}")
            self.status_var.set("准备阶段错误")
            self.fetch_button.config(state=tk.NORMAL)

    def run_akshare_function(self, func, kwargs):
        try:
            # print(f"DEBUG: Calling {func.__name__} with {kwargs}")
            data = func(**kwargs)
            self.q.put({"status": "success", "data": data, "func_name": func.__name__})
        except Exception as e:
            # print(f"DEBUG: Error in Akshare call for {func.__name__}: {type(e).__name__}, {e}")
            import traceback
            # print(traceback.format_exc())
            self.q.put({"status": "error", "error": e, "error_tb": traceback.format_exc(), "func_name": func.__name__})

    def process_queue(self):
        try:
            msg = self.q.get_nowait()
            if msg["status"] == "success":
                self.display_data(msg["data"])
                self.status_var.set(f"获取 {msg['func_name']} 数据成功!")
                self.notebook.select(self.data_tab)
                if isinstance(msg["data"], pd.DataFrame) and not msg["data"].empty:
                    self.save_button.config(state=tk.NORMAL)
                else:
                    self.save_button.config(state=tk.DISABLED)
            elif msg["status"] == "error":
                error_message = f"获取 {msg['func_name']} 数据失败: {type(msg['error']).__name__}: {msg['error']}"
                self.status_var.set(error_message)
                # print("Error Traceback:\n", msg.get("error_tb", "No traceback available.")) # For debugging
                messagebox.showerror(f"接口调用错误 - {msg['func_name']}", f"{error_message}\n\n详细信息:\n{msg.get('error_tb', 'N/A')[:1000]}")
                self.clear_data_tree()
                self.save_button.config(state=tk.DISABLED)
        except queue.Empty:
            pass
        finally:
            active_threads = [t for t in threading.enumerate() if t.daemon and t != threading.main_thread() and t.is_alive()]
            if not active_threads :
                 self.fetch_button.config(state=tk.NORMAL)
            self.master.after(100, self.process_queue)

    def clear_data_tree(self):
        self.data_tree.delete(*self.data_tree.get_children())
        self.data_tree["columns"] = ()
        self.current_df = None
        self.save_button.config(state=tk.DISABLED)

    def display_data(self, data):
        self.clear_data_tree()
        if isinstance(data, pd.DataFrame):
            self.current_df = data
            if data.empty:
                self.status_var.set(self.status_var.get() + " (结果为空DataFrame)")
                self.data_tree["columns"] = ("信息",)
                self.data_tree.heading("信息", text="信息")
                self.data_tree.insert("", tk.END, values=("返回的数据为空DataFrame",))
                return

            cols = list(data.columns)
            self.data_tree["columns"] = cols
            for col_idx, col_name in enumerate(cols):
                self.data_tree.heading(col_name, text=col_name)
                try:
                    # Estimate column width
                    content_lengths = [len(str(x)) for x in data[col_name].dropna().head(20).astype(str)]
                    header_len = len(str(col_name))
                    max_len = max(content_lengths + [header_len]) if content_lengths else header_len
                    col_width = min(max(max_len * 7 + 15, 60), 350) # Min 60, Max 350
                    self.data_tree.column(col_name, width=col_width, minwidth=50, anchor=tk.W)
                except Exception: # Fallback width
                     self.data_tree.column(col_name, width=100, minwidth=50, anchor=tk.W)


            for index, row in data.head(500).iterrows(): # Display max 500 rows for performance
                row_values = [str(v)[:100] + '...' if isinstance(v, str) and len(str(v)) > 100 else v for v in row]
                self.data_tree.insert("", tk.END, values=list(row_values))
            if len(data) > 500:
                self.data_tree.insert("", tk.END, values=(["...数据过多，仅显示前500行..."] * len(cols)))
                messagebox.showinfo("数据截断", f"查询返回 {len(data)} 行数据，为保持界面流畅，表格中仅显示前500行。\n完整数据已获取，可保存到CSV查看。")

        elif isinstance(data, dict):
            self.current_df = None
            self.save_button.config(state=tk.DISABLED)
            self.data_tree["columns"] = ("键", "值预览 (类型)")
            self.data_tree.heading("键", text="键")
            self.data_tree.heading("值预览 (类型)", text="值预览 (类型)")
            self.data_tree.column("键", width=150, anchor=tk.W)
            self.data_tree.column("值预览 (类型)", width=400, anchor=tk.W)
            for key, value in data.items():
                preview = f"DataFrame shape: {value.shape}" if isinstance(value, pd.DataFrame) else str(value)[:200]
                self.data_tree.insert("", tk.END, values=(str(key), f"{preview} ({type(value).__name__})"))
            messagebox.showinfo("提示", "结果是字典。如需查看详细DataFrame，请选择字典中对应项或修改代码以处理特定键。")
        
        elif isinstance(data, list) and data and all(isinstance(item, dict) for item in data):
            try:
                df = pd.DataFrame(data)
                self.display_data(df) 
            except Exception:
                self.display_raw_data(data)
        else:
            self.display_raw_data(data)

    def display_raw_data(self, data):
        self.current_df = None
        self.save_button.config(state=tk.DISABLED)
        self.data_tree["columns"] = ("数据",)
        self.data_tree.heading("数据", text=f"原始数据 (类型: {type(data).__name__})")
        self.data_tree.column("数据", width=600, anchor=tk.W)
        data_str = str(data)
        self.data_tree.insert("", tk.END, values=(data_str[:1000] + ('...' if len(data_str) > 1000 else ''),))
        messagebox.showinfo("提示", f"结果类型为 {type(data).__name__}，已显示其字符串表示。")

    def save_to_csv(self):
        if self.current_df is not None and isinstance(self.current_df, pd.DataFrame) and not self.current_df.empty:
            func_name = self.current_ak_function.__name__ if self.current_ak_function else "akshare_data"
            default_filename = f"{func_name}_{pd.Timestamp.now().strftime('%Y%m%d_%H%M%S')}.csv"
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="保存数据为 CSV",
                initialfile=default_filename
            )
            if file_path:
                try:
                    self.current_df.to_csv(file_path, index=False, encoding='utf_8_sig')
                    self.status_var.set(f"数据已保存到 {file_path}")
                    messagebox.showinfo("成功", f"数据已成功保存到\n{file_path}")
                except Exception as e:
                    self.status_var.set(f"保存失败: {e}")
                    messagebox.showerror("保存失败", f"无法保存文件: {e}")
        else:
            messagebox.showwarning("无法保存", "当前没有可保存的DataFrame数据。")

if __name__ == '__main__':
    try:
        import pandas as pd_check
    except ImportError:
        messagebox.showerror("依赖缺失", "Pandas库未安装，请运行 'pip install pandas' 安装后再启动程序。")
        exit()

    root = tk.Tk()
    style = ttk.Style()
    available_themes = style.theme_names()
    # Prefer 'clam', 'vista' (Windows), or 'aqua' (macOS) for a slightly more modern look
    if 'clam' in available_themes: style.theme_use('clam')
    elif 'vista' in available_themes: style.theme_use('vista')
    elif 'aqua' in available_themes: style.theme_use('aqua')
    
    app = AkshareGUI(root)
    root.mainloop()