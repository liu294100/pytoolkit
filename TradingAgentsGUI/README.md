# TradingAgents GUI

🤖 **Multi-Agent Trading Framework with Graphical User Interface**

A modern GUI application for the [TradingAgents](https://github.com/TauricResearch/TradingAgents) multi-agent LLM financial trading framework. This interface provides real-time visualization of agent activities, trading decisions, and portfolio performance.

## 🌟 Features

### 🎯 Multi-Agent Visualization
- **Real-time Agent Status**: Monitor all 8 specialized agents simultaneously
- **Agent Cards**: Individual status cards for each agent with progress indicators
- **Live Updates**: Real-time status updates and output logs for each agent

### 📊 Trading Control Panel
- **Stock Selection**: Easy stock symbol input with validation
- **Date Configuration**: Flexible trading date selection
- **Model Selection**: Choose from multiple LLM models (GPT-4o, O1-preview, etc.)
- **Debate Rounds**: Configurable research debate intensity
- **API Management**: Secure API key configuration for OpenAI and FinnHub

### 📈 Results Dashboard
- **Trading Decisions**: Detailed decision analysis with confidence scores
- **System Logs**: Comprehensive logging with color-coded message levels
- **Performance Metrics**: Portfolio tracking with key financial indicators
- **Risk Assessment**: Real-time risk analysis and exposure monitoring

### 🎨 Modern UI Design
- **Dark Theme**: Professional dark interface optimized for trading environments
- **Responsive Layout**: Adaptive design that works on different screen sizes
- **Color-Coded Status**: Intuitive color system for agent states and alerts
- **Scrollable Panels**: Efficient space utilization with scrollable content areas

## 🏗️ Architecture

The GUI is built around the TradingAgents framework architecture <mcreference link="https://github.com/TauricResearch/TradingAgents" index="0">0</mcreference>:

### 👥 Agent Teams

#### 📊 **Analyst Team** (Parallel Execution)
- **Fundamental Analyst**: Evaluates company financials and performance metrics
- **Sentiment Analyst**: Analyzes social media and public sentiment
- **News Analyst**: Monitors global news and macroeconomic indicators  
- **Technical Analyst**: Uses technical indicators for price analysis

#### 🔬 **Research Team** (Debate Process)
- **Bull Researcher**: Provides optimistic market perspective and growth potential
- **Bear Researcher**: Focuses on risks and negative market signals

#### 💼 **Execution Team**
- **Trader Agent**: Makes informed trading decisions based on comprehensive analysis
- **Risk Manager**: Continuously evaluates portfolio risk and exposure

## 🚀 Installation

### Prerequisites
- Python 3.8 or higher
- Windows/macOS/Linux

### Quick Start

1. **Clone or Download**
   ```bash
   # If part of pytoolkit
   cd pytoolkit/TradingAgentsGUI
   
   # Or download files directly
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Application**
   ```bash
   python main.py
   ```

## 🔧 Configuration

### API Keys Setup

The application requires API keys for full functionality:

1. **OpenAI API Key**: Required for LLM agents
   - Get your key from [OpenAI Platform](https://platform.openai.com/api-keys)
   - Enter in the GUI's API Configuration section

2. **FinnHub API Key**: Required for financial data
   - Get free key from [FinnHub](https://finnhub.io/)
   - Enter in the GUI's API Configuration section

### Environment Variables (Optional)
```bash
# Create .env file in the project directory
OPENAI_API_KEY=your_openai_api_key_here
FINNHUB_API_KEY=your_finnhub_api_key_here
```
config api_keys.json
## 📖 Usage Guide

### 1. **Launch Application**
   - Run `python main.py`
   - The GUI will open with the main dashboard

### 2. **Configure Trading Parameters**
   - **Stock Symbol**: Enter ticker symbol (e.g., NVDA, AAPL, TSLA)
   - **Trading Date**: Select analysis date
   - **LLM Model**: Choose AI model for agents
   - **Debate Rounds**: Set research intensity (1-5 rounds)

### 3. **Set API Keys**
   - Enter OpenAI API key for LLM functionality
   - Enter FinnHub API key for market data

### 4. **Start Trading Analysis**
   - Click "🚀 Start Trading" button
   - Watch agents execute in real-time
   - Monitor progress through agent status cards

### 5. **Review Results**
   - **Trading Decision Tab**: View final recommendation
   - **System Logs Tab**: Check execution details
   - **Performance Tab**: Monitor portfolio metrics

## 🎮 Interface Overview

### Left Panel - Control Center
- Trading parameters configuration
- Model and API settings
- Start/Stop controls
- Real-time system status

### Center Panel - Agent Dashboard
- 8 agent status cards with live updates
- Progress indicators and output logs
- Color-coded status system
- Scrollable agent monitoring

### Right Panel - Results & Analytics
- Tabbed interface for different views
- Trading decisions with detailed analysis
- System logs with timestamp and levels
- Performance metrics and portfolio tracking

## 🔍 Agent Status Indicators

- **● IDLE** (Gray): Agent waiting for activation
- **● RUNNING** (Yellow): Agent actively processing
- **● COMPLETED** (Green): Agent finished successfully
- **● ERROR** (Red): Agent encountered an issue

## 📊 Sample Output

### Trading Decision Example
```
🎯 TRADING DECISION
==================================================

Symbol: NVDA
Date: 2024-01-15
Action: BUY
Quantity: 50 shares
Confidence: 85.2%

📊 ANALYSIS SUMMARY
------------------------------
Based on multi-agent analysis, the recommendation is to BUY 50 shares of NVDA.

🛡️ RISK ASSESSMENT
------------------------------
Medium risk with potential for moderate returns

📈 TECHNICAL SIGNALS
------------------------------
RSI: 65, MACD: Bullish crossover, Support: $150

📋 SCORES
------------------------------
Fundamental Score: 8.2/10
Sentiment Score: 0.65 (-1 to 1)
```

## 🛠️ Development

### Project Structure
```
TradingAgentsGUI/
├── main.py              # Main GUI application
├── requirements.txt     # Python dependencies
├── README.md           # This file
└── .env.example        # Environment variables template
```

### Key Components
- **TradingAgentsGUI Class**: Main application controller
- **Agent Management**: Real-time status tracking and updates
- **Threading**: Non-blocking UI with background processing
- **Logging System**: Comprehensive activity tracking

## 🔮 Future Enhancements

- [ ] **Real TradingAgents Integration**: Connect to actual framework
- [ ] **Live Market Data**: Real-time price feeds and indicators
- [ ] **Advanced Charting**: Interactive price charts and technical analysis
- [ ] **Portfolio Management**: Complete portfolio tracking and history
- [ ] **Alert System**: Configurable notifications and alerts
- [ ] **Export Functionality**: Save decisions and reports
- [ ] **Multi-Symbol Support**: Analyze multiple stocks simultaneously
- [ ] **Backtesting Module**: Historical strategy testing

## 🤝 Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is part of the pytoolkit collection. Please refer to the main repository license.

## 🙏 Acknowledgments

- **TradingAgents Team**: Original multi-agent framework <mcreference link="https://github.com/TauricResearch/TradingAgents" index="0">0</mcreference>
- **Tauric Research**: Framework development and research <mcreference link="https://arxiv.org/abs/2412.20138" index="1">1</mcreference>
- **Community**: Feedback and feature suggestions

## 📞 Support

For questions, issues, or feature requests:
- Create an issue in the repository
- Check existing documentation
- Review the TradingAgents original project
https://github.com/TauricResearch/TradingAgents
---

**Built with ❤️ for the trading and AI community**