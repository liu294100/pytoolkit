#!/usr/bin/env python3
"""
TradingAgents GUI - Main Application

A graphical user interface for the TradingAgents multi-agent trading system.
This application provides real-time visualization of agent activities,
trading controls, and performance monitoring.

Author: TradingAgents GUI Team
Version: 1.0.0
License: MIT
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
import threading
import time
import json
from datetime import datetime, timedelta
import queue
from typing import Dict, List, Optional, Any
import sys
import os

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import our custom modules
try:
    from config import Config, AGENT_ROLES, RISK_LEVELS
    from utils import (
        DataProvider, FinnHubProvider, MockDataProvider,
        TechnicalAnalysis, SentimentAnalyzer, PortfolioTracker,
        ThreadSafeLogger, format_currency, format_percentage,
        MarketData, TechnicalIndicators
    )
    from performance_optimizer import PerformanceOptimizer, MemoryManager, AsyncTaskManager
    from technical_indicators import TechnicalAnalyzer, OHLCV, IndicatorResult
    from api_integration import APIIntegrationManager
    from strategy_customization import StrategyManager
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please make sure all required files are in the same directory.")
    exit(1)


class TradingAgent:
    """Represents a single trading agent with its role and status."""
    
    def __init__(self, name: str, role: str, description: str):
        self.name = name
        self.role = role
        self.description = description
        self.status = "Idle"
        self.last_action = "Initialized"
        self.performance_score = 0.0
        self.is_active = False
        self.messages = []
    
    def update_status(self, status: str, action: str = None):
        """Update agent status and last action."""
        self.status = status
        if action:
            self.last_action = action
            self.messages.append({
                'timestamp': datetime.now(),
                'action': action,
                'status': status
            })
    
    def get_recent_messages(self, limit: int = 5) -> List[Dict]:
        """Get recent messages from this agent."""
        return self.messages[-limit:] if self.messages else []


class TradingAgentsGUI:
    """Main GUI application for TradingAgents system."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.config = Config()
        # Initialize logger with log level from config
        log_level = getattr(self.config, 'DEFAULT_SETTINGS', {}).get('log_level', 'INFO')
        self.logger = ThreadSafeLogger(log_level=log_level)
        
        # Initialize data providers
        self.data_provider: Optional[DataProvider] = None
        self.technical_analyzer = TechnicalAnalysis()
        self.sentiment_analyzer = SentimentAnalyzer()
        self.portfolio_tracker = PortfolioTracker()
        
        # Initialize performance optimization
        self.performance_optimizer = PerformanceOptimizer()
        self.technical_analyzer_advanced = TechnicalAnalyzer()
        self.api_manager = APIIntegrationManager()
        self.strategy_manager = StrategyManager()
        
        # Trading state
        self.is_trading = False
        self.current_symbol = tk.StringVar(value="AAPL")
        self.trading_thread = None
        self.update_queue = queue.Queue()
        
        # Performance monitoring
        self.last_update_time = time.time()
        self.update_counter = 0
        self.current_analysis = None
        
        # Initialize agents
        self.agents = self._initialize_agents()
        
        # Setup GUI
        self._setup_gui()
        self._setup_styles()
        
        # Start update loop and performance monitoring
        self.root.after(100, self._process_updates)
        self._start_performance_monitoring()
        
        self.logger.info("TradingAgents GUI initialized successfully")
    
    def get_text(self, key: str) -> str:
        """Get translated text for the given key."""
        return self.config.get_text(key)
    
    def _initialize_agents(self) -> Dict[str, TradingAgent]:
        """Initialize trading agents based on configuration."""
        agents = {}
        for role, agent_info in AGENT_ROLES.items():
            agent_name = agent_info.get('name', f"{role.replace('_', ' ').title()} Agent")
            description = agent_info.get('description', f"Agent responsible for {role.replace('_', ' ')}")
            agents[role] = TradingAgent(agent_name, role, description)
        return agents
    
    def _setup_gui(self):
        """Setup the main GUI layout."""
        self.root.title("TradingAgents - Multi-Agent Trading System")
        self.root.geometry("1400x900")
        
        # Configure root window background with fallback
        try:
            bg_color = getattr(self.config, 'COLOR_SCHEME', {}).get('background', '#f0f0f0')
            self.root.configure(bg=bg_color)
        except Exception as e:
            self.logger.warning(f"Could not set background color: {e}")
            self.root.configure(bg='#f0f0f0')  # Safe fallback color
        
        # Ensure window is visible
        self.root.update_idletasks()
        self.root.deiconify()
        
        # Create main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create top control panel
        self._create_control_panel(main_frame)
        
        # Create main content area with notebook
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        # Create tabs
        self._create_agents_tab()
        self._create_trading_tab()
        self._create_portfolio_tab()
        self._create_logs_tab()
        self._create_settings_tab()
        
        # Update tab texts with translations
        self._update_tab_texts()
    
    def _setup_styles(self):
        """Setup custom styles for the GUI."""
        style = ttk.Style()
        
        # Configure notebook style
        style.configure('TNotebook.Tab', padding=[20, 10])
        
        # Configure button styles
        style.configure('Success.TButton', foreground='red')
        style.configure('Danger.TButton', foreground='red')
    
    def _create_control_panel(self, parent):
        """Create the top control panel."""
        control_frame = ttk.LabelFrame(parent, text="Trading Control", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Left side - Symbol and API settings
        left_frame = ttk.Frame(control_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Symbol selection
        ttk.Label(left_frame, text=self.get_text("symbol")).grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        symbol_entry = ttk.Entry(left_frame, textvariable=self.current_symbol, width=10)
        symbol_entry.grid(row=0, column=1, padx=(0, 20))
        
        # API status indicators
        self.api_status_frame = ttk.Frame(left_frame)
        self.api_status_frame.grid(row=0, column=2, padx=(20, 0))
        
        try:
            error_color = getattr(self.config, 'STATUS_COLORS', {}).get('error', 'red')
        except Exception:
            error_color = 'red'
            
        self.openai_status = ttk.Label(self.api_status_frame, text="OpenAI: Not Connected", 
                                      foreground=error_color)
        self.openai_status.pack(side=tk.LEFT, padx=(0, 10))
        
        self.finnhub_status = ttk.Label(self.api_status_frame, text="FinnHub: Not Connected", 
                                       foreground=error_color)
        self.finnhub_status.pack(side=tk.LEFT)
        
        # Right side - Control buttons
        right_frame = ttk.Frame(control_frame)
        right_frame.pack(side=tk.RIGHT)
        
        self.start_button = ttk.Button(right_frame, text=self.get_text("start_trading"), 
                                      command=self._start_trading, style='Success.TButton')
        self.start_button.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_button = ttk.Button(right_frame, text=self.get_text("stop_trading"), 
                                     command=self._stop_trading, style='Danger.TButton', 
                                     state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT)
    
    def _create_agents_tab(self):
        """Create the agents monitoring tab."""
        agents_frame = ttk.Frame(self.notebook)
        self.notebook.add(agents_frame, text="Agents")
        
        # Create scrollable frame for agents
        try:
            bg_color = getattr(self.config, 'COLOR_SCHEME', {}).get('background', '#f0f0f0')
            canvas = tk.Canvas(agents_frame, bg=bg_color)
        except Exception:
            canvas = tk.Canvas(agents_frame, bg='#f0f0f0')  # Fallback
            
        scrollbar = ttk.Scrollbar(agents_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Create agent cards
        self.agent_widgets = {}
        for i, (role, agent) in enumerate(self.agents.items()):
            self._create_agent_card(scrollable_frame, agent, i)
    
    def _create_agent_card(self, parent, agent: TradingAgent, row: int):
        """Create a card widget for an agent."""
        # Main card frame
        card_frame = ttk.LabelFrame(parent, text=agent.name, padding=15)
        card_frame.grid(row=row//2, column=row%2, padx=10, pady=10, sticky="ew")
        
        # Configure grid weights
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=1)
        
        # Agent info
        info_frame = ttk.Frame(card_frame)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(info_frame, text="Role:", font=('Arial', 9, 'bold')).grid(row=0, column=0, sticky=tk.W)
        ttk.Label(info_frame, text=agent.role.replace('_', ' ').title()).grid(row=0, column=1, sticky=tk.W, padx=(10, 0))
        
        ttk.Label(info_frame, text="Status:", font=('Arial', 9, 'bold')).grid(row=1, column=0, sticky=tk.W)
        try:
            status_color = getattr(self.config, 'STATUS_COLORS', {}).get('idle', 'gray')
        except Exception:
            status_color = 'gray'
        status_label = ttk.Label(info_frame, text=agent.status, foreground=status_color)
        status_label.grid(row=1, column=1, sticky=tk.W, padx=(10, 0))
        
        # Description
        desc_text = tk.Text(card_frame, height=3, width=40, wrap=tk.WORD, 
                           font=('Arial', 8), state=tk.DISABLED)
        desc_text.pack(fill=tk.X, pady=(0, 10))
        desc_text.config(state=tk.NORMAL)
        desc_text.insert(tk.END, agent.description)
        desc_text.config(state=tk.DISABLED)
        
        # Last action
        action_label = ttk.Label(card_frame, text=f"Last Action: {agent.last_action}", 
                                font=('Arial', 8), foreground='gray')
        action_label.pack(anchor=tk.W)
        
        # Store widgets for updates
        self.agent_widgets[agent.role] = {
            'status_label': status_label,
            'action_label': action_label,
            'card_frame': card_frame
        }
    
    def _create_trading_tab(self):
        """Create the trading analysis tab."""
        trading_frame = ttk.Frame(self.notebook)
        self.notebook.add(trading_frame, text="Trading Analysis")
        
        # Create paned window for split layout
        paned = ttk.PanedWindow(trading_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left panel - Market data
        left_panel = ttk.LabelFrame(paned, text="Market Data", padding=10)
        paned.add(left_panel, weight=1)
        
        # Market data display
        self.market_data_text = scrolledtext.ScrolledText(left_panel, height=20, width=40)
        self.market_data_text.pack(fill=tk.BOTH, expand=True)
        
        # Right panel - Analysis results
        right_panel = ttk.LabelFrame(paned, text="Analysis Results", padding=10)
        paned.add(right_panel, weight=1)
        
        # Analysis results display
        self.analysis_text = scrolledtext.ScrolledText(right_panel, height=20, width=40)
        self.analysis_text.pack(fill=tk.BOTH, expand=True)
    
    def _create_portfolio_tab(self):
        """Create the portfolio monitoring tab."""
        portfolio_frame = ttk.Frame(self.notebook)
        self.notebook.add(portfolio_frame, text="Portfolio")
        
        # Portfolio summary
        summary_frame = ttk.LabelFrame(portfolio_frame, text="Portfolio Summary", padding=10)
        summary_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Summary labels
        self.portfolio_labels = {}
        labels = ['Total Value', 'Total P&L', 'Total Return %', 'Active Positions']
        for i, label in enumerate(labels):
            ttk.Label(summary_frame, text=f"{label}:", font=('Arial', 10, 'bold')).grid(row=i//2, column=(i%2)*2, sticky=tk.W, padx=(0, 10))
            value_label = ttk.Label(summary_frame, text="$0.00", font=('Arial', 10))
            value_label.grid(row=i//2, column=(i%2)*2+1, sticky=tk.W, padx=(0, 20))
            self.portfolio_labels[label.lower().replace(' ', '_').replace('%', 'pct')] = value_label
        
        # Positions table
        positions_frame = ttk.LabelFrame(portfolio_frame, text="Positions", padding=10)
        positions_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create treeview for positions
        columns = ('Symbol', 'Quantity', 'Avg Price', 'Current Price', 'P&L', 'P&L %')
        self.positions_tree = ttk.Treeview(positions_frame, columns=columns, show='headings', height=10)
        
        for col in columns:
            self.positions_tree.heading(col, text=col)
            self.positions_tree.column(col, width=100, anchor=tk.CENTER)
        
        # Scrollbar for treeview
        positions_scrollbar = ttk.Scrollbar(positions_frame, orient=tk.VERTICAL, command=self.positions_tree.yview)
        self.positions_tree.configure(yscrollcommand=positions_scrollbar.set)
        
        self.positions_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        positions_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _create_logs_tab(self):
        """Create the logs monitoring tab."""
        logs_frame = ttk.Frame(self.notebook)
        self.notebook.add(logs_frame, text="Logs")
        
        # Log controls
        controls_frame = ttk.Frame(logs_frame)
        controls_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(controls_frame, text="Clear Logs", command=self._clear_logs).pack(side=tk.LEFT)
        ttk.Button(controls_frame, text="Export Logs", command=self._export_logs).pack(side=tk.LEFT, padx=(10, 0))
        
        # Log level filter
        ttk.Label(controls_frame, text="Level:").pack(side=tk.LEFT, padx=(20, 5))
        self.log_level_var = tk.StringVar(value="ALL")
        log_level_combo = ttk.Combobox(controls_frame, textvariable=self.log_level_var, 
                                      values=["ALL", "DEBUG", "INFO", "WARNING", "ERROR"], width=10)
        log_level_combo.pack(side=tk.LEFT)
        
        # Logs display
        logs_container = ttk.Frame(logs_frame)
        logs_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        self.logs_text = scrolledtext.ScrolledText(logs_container, height=25, 
                                                  font=('Consolas', 9))
        self.logs_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure log colors
        try:
            log_colors = getattr(self.config, 'LOG_COLORS', {})
            self.logs_text.tag_configure("DEBUG", foreground=log_colors.get('DEBUG', 'gray'))
            self.logs_text.tag_configure("INFO", foreground=log_colors.get('INFO', 'green'))
            self.logs_text.tag_configure("WARNING", foreground=log_colors.get('WARNING', 'orange'))
            self.logs_text.tag_configure("ERROR", foreground=log_colors.get('ERROR', 'red'))
        except Exception:
            self.logs_text.tag_configure("DEBUG", foreground='gray')
            self.logs_text.tag_configure("INFO", foreground='green')
            self.logs_text.tag_configure("WARNING", foreground='orange')
            self.logs_text.tag_configure("ERROR", foreground='red')
    
    def _create_settings_tab(self):
        """Create the settings configuration tab."""
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text="Settings")
        
        # Create notebook for settings categories
        settings_notebook = ttk.Notebook(settings_frame)
        settings_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # API Settings
        self._create_api_settings_tab(settings_notebook)
        
        # Trading Settings
        self._create_trading_settings_tab(settings_notebook)
        
        # Agent Settings
        self._create_agent_settings_tab(settings_notebook)
        
        # Language Settings
        self._create_language_settings_tab(settings_notebook)
    
    def _create_api_settings_tab(self, parent):
        """Create API settings tab."""
        api_frame = ttk.Frame(parent)
        parent.add(api_frame, text=self.get_text("api_keys"))
        
        # API keys frame
        keys_frame = ttk.LabelFrame(api_frame, text=self.get_text("api_configuration"), padding=20)
        keys_frame.pack(fill=tk.X, padx=20, pady=20)
        
        # OpenAI API Key
        ttk.Label(keys_frame, text=self.get_text("openai_api_key"), font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        self.openai_key_var = tk.StringVar()
        openai_entry = ttk.Entry(keys_frame, textvariable=self.openai_key_var, width=50, show="*")
        openai_entry.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=(0, 10))
        
        # FinnHub API Key
        ttk.Label(keys_frame, text=self.get_text("finnhub_api_key"), font=('Arial', 10, 'bold')).grid(row=1, column=0, sticky=tk.W, pady=(0, 10))
        self.finnhub_key_var = tk.StringVar()
        finnhub_entry = ttk.Entry(keys_frame, textvariable=self.finnhub_key_var, width=50, show="*")
        finnhub_entry.grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(0, 10))
        
        # Buttons frame
        buttons_frame = ttk.Frame(keys_frame)
        buttons_frame.grid(row=2, column=0, columnspan=2, sticky=tk.W, pady=(10, 0))
        
        ttk.Button(buttons_frame, text=self.get_text("save_api_keys"), command=self._save_api_keys).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons_frame, text=self.get_text("load_api_keys"), command=self._load_api_keys).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(buttons_frame, text=self.get_text("test_connections"), command=self._test_api_connections).pack(side=tk.LEFT)
        
        # Use mock data option
        self.use_mock_data = tk.BooleanVar(value=True)
        ttk.Checkbutton(keys_frame, text=self.get_text("use_mock_data"), 
                       variable=self.use_mock_data).grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(20, 0))
        
        # Load existing API keys on startup
        self._load_api_keys()
    
    def _create_trading_settings_tab(self, parent):
        """Create trading settings tab."""
        trading_frame = ttk.Frame(parent)
        parent.add(trading_frame, text=self.get_text("trading"))
        
        # Trading parameters
        params_frame = ttk.LabelFrame(trading_frame, text=self.get_text("trading_parameters"), padding=20)
        params_frame.pack(fill=tk.X, padx=20, pady=20)
        
        # Risk tolerance
        ttk.Label(params_frame, text=self.get_text("risk_tolerance"), font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        self.risk_tolerance_var = tk.StringVar(value="medium")
        risk_combo = ttk.Combobox(params_frame, textvariable=self.risk_tolerance_var, 
                                 values=list(RISK_LEVELS.keys()), width=20)
        risk_combo.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=(0, 10))
        
        # Update interval
        ttk.Label(params_frame, text=self.get_text("update_interval"), font=('Arial', 10, 'bold')).grid(row=1, column=0, sticky=tk.W, pady=(0, 10))
        self.update_interval_var = tk.IntVar(value=30)
        ttk.Spinbox(params_frame, from_=5, to=300, textvariable=self.update_interval_var, width=20).grid(row=1, column=1, sticky=tk.W, padx=(10, 0), pady=(0, 10))
        
        # Max positions
        ttk.Label(params_frame, text=self.get_text("max_positions"), font=('Arial', 10, 'bold')).grid(row=2, column=0, sticky=tk.W, pady=(0, 10))
        self.max_positions_var = tk.IntVar(value=5)
        ttk.Spinbox(params_frame, from_=1, to=20, textvariable=self.max_positions_var, width=20).grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=(0, 10))
    
    def _create_agent_settings_tab(self, parent):
        """Create agent settings tab."""
        agent_frame = ttk.Frame(parent)
        parent.add(agent_frame, text=self.get_text("agents_tab"))
        
        # Agent configuration
        config_frame = ttk.LabelFrame(agent_frame, text=self.get_text("agent_configuration"), padding=20)
        config_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Agent enable/disable checkboxes
        self.agent_enabled_vars = {}
        for i, (role, agent) in enumerate(self.agents.items()):
            var = tk.BooleanVar(value=True)
            self.agent_enabled_vars[role] = var
            ttk.Checkbutton(config_frame, text=f"{self.get_text('enable')} {agent.name}", 
                           variable=var).grid(row=i, column=0, sticky=tk.W, pady=2)
    
    def _create_language_settings_tab(self, parent):
        """Create language settings tab."""
        language_frame = ttk.Frame(parent)
        parent.add(language_frame, text=self.get_text("language_tab"))
        
        # Language configuration
        config_frame = ttk.LabelFrame(language_frame, text=self.get_text("language_configuration"), padding=20)
        config_frame.pack(fill=tk.X, padx=20, pady=20)
        
        # Language selection
        ttk.Label(config_frame, text=self.get_text("select_language"), font=('Arial', 10, 'bold')).grid(row=0, column=0, sticky=tk.W, pady=(0, 10))
        
        self.language_var = tk.StringVar(value=self.config.get('language', 'en'))
        language_combo = ttk.Combobox(config_frame, textvariable=self.language_var, 
                                     values=['en', 'zh'], width=20, state='readonly')
        language_combo.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=(0, 10))
        
        # Language display mapping
        language_combo.configure(values=['en', 'zh'])
        
        # Custom display for combobox
        def format_language_display(event=None):
            current = self.language_var.get()
            if current == 'en':
                language_combo.set('English')
            elif current == 'zh':
                language_combo.set('中文')
        
        def on_language_select(event=None):
            selection = language_combo.get()
            if selection == 'English':
                self.language_var.set('en')
            elif selection == '中文':
                self.language_var.set('zh')
        
        # Set initial display
        format_language_display()
        
        # Update combobox values for display
        language_combo.configure(values=['English', '中文'])
        language_combo.bind('<<ComboboxSelected>>', on_language_select)
        
        # Apply button
        apply_button = ttk.Button(config_frame, text=self.get_text("apply_language"), 
                                 command=self._apply_language_change)
        apply_button.grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(20, 10))
        
        # Log level setting
        ttk.Label(config_frame, text="Log Level:").grid(row=2, column=0, sticky=tk.W, pady=(10, 5))
        self.log_level_setting_var = tk.StringVar(value=self.logger.log_level)
        log_level_setting_combo = ttk.Combobox(config_frame, textvariable=self.log_level_setting_var,
                                             values=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                                             width=20, state='readonly')
        log_level_setting_combo.grid(row=2, column=1, sticky=tk.W, padx=(10, 0), pady=(10, 5))
        log_level_setting_combo.bind('<<ComboboxSelected>>', self._on_log_level_change)
        
        # Info label
        info_label = ttk.Label(config_frame, text=self.get_text("restart_required"), 
                              font=('Arial', 9), foreground='gray')
        info_label.grid(row=3, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
    
    def _apply_language_change(self):
        """Apply language change."""
        new_language = 'en' if self.language_var.get() in ['en', 'English'] else 'zh'
        current_language = self.config.get('language', 'en')
        
        if new_language != current_language:
            self.config.set_language(new_language)
            messagebox.showinfo(
                self.get_text("info"), 
                self.get_text("restart_required")
            )
    
    def _on_log_level_change(self, event=None):
        """Handle log level change."""
        new_level = self.log_level_setting_var.get()
        self.logger.set_log_level(new_level)
        self.logger.info(f"Log level changed to: {new_level}")
        
        # Update config
        if hasattr(self.config, 'DEFAULT_SETTINGS'):
            self.config.DEFAULT_SETTINGS['log_level'] = new_level
        
        self._add_log("INFO", f"Log level set to: {new_level}")
    
    def _update_tab_texts(self):
        """Update tab texts with current language."""
        try:
            # Update main tabs
            tab_count = self.notebook.index("end")
            tab_keys = ["agents", "trading_analysis", "portfolio", "logs", "settings"]
            
            for i in range(min(tab_count, len(tab_keys))):
                self.notebook.tab(i, text=self.get_text(tab_keys[i]))
        except Exception as e:
            self.logger.error(f"Error updating tab texts: {e}")
     
    def _start_trading(self):
        """Start the trading system."""
        if self.is_trading:
            self.logger.debug("Trading already active, ignoring start request")
            return
        
        symbol = self.current_symbol.get()
        self.logger.debug(f"Initiating trading start for symbol: {symbol}")
        
        # Validate settings
        self.logger.debug("Validating settings...")
        if not self._validate_settings():
            self.logger.debug("Settings validation failed")
            return
        
        # Initialize data provider
        self.logger.debug("Initializing data provider...")
        self._initialize_data_provider()
        
        # Update UI
        self.is_trading = True
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.logger.debug("UI updated for trading state")
        
        # Start trading thread
        self.logger.debug("Starting trading thread...")
        self.trading_thread = threading.Thread(target=self._trading_loop, daemon=True)
        self.trading_thread.start()
        
        self.logger.info(f"Trading started for symbol: {symbol}")
        self.logger.debug("Trading system fully initialized and running")
        self._add_log("INFO", "Trading system started")
    
    def _stop_trading(self):
        """Stop the trading system."""
        if not self.is_trading:
            self.logger.debug("Trading not active, ignoring stop request")
            return
        
        self.logger.debug("Initiating trading stop...")
        self.is_trading = False
        
        self.logger.debug("Updating UI for stopped state...")
        self.start_button.config(state=tk.NORMAL)
        self.stop_button.config(state=tk.DISABLED)
        
        # Reset agent statuses
        self.logger.debug("Resetting agent statuses...")
        for agent in self.agents.values():
            agent.update_status("Idle", "Trading stopped")
        
        self.logger.info("Trading stopped")
        self.logger.debug("Trading system fully stopped")
        self._add_log("INFO", "Trading system stopped")
    
    def _validate_settings(self) -> bool:
        """Validate current settings before starting trading."""
        symbol = self.current_symbol.get().strip().upper()
        if not symbol:
            messagebox.showerror("Error", "Please enter a valid stock symbol")
            return False
        
        if not self.use_mock_data.get():
            if not self.openai_key_var.get().strip():
                messagebox.showerror("Error", "OpenAI API key is required (or enable mock data)")
                return False
            
            if not self.finnhub_key_var.get().strip():
                messagebox.showerror("Error", "FinnHub API key is required (or enable mock data)")
                return False
        
        return True
    
    def _initialize_data_provider(self):
        """Initialize the appropriate data provider."""
        if self.use_mock_data.get():
            self.data_provider = MockDataProvider()
            self._add_log("INFO", "Using mock data provider")
        else:
            try:
                self.data_provider = FinnHubProvider(self.finnhub_key_var.get())
                self._add_log("INFO", "Using FinnHub data provider")
            except Exception as e:
                self.logger.error(f"Failed to initialize FinnHub provider: {e}")
                self.data_provider = MockDataProvider()
                self._add_log("WARNING", "Fallback to mock data provider")
    
    def _trading_loop(self):
        """Main trading loop running in separate thread."""
        self.logger.debug("Trading loop started")
        while self.is_trading:
            try:
                symbol = self.current_symbol.get()
                self.logger.debug(f"Trading loop iteration for symbol: {symbol}")
                
                # Use performance optimizer for background tasks
                self.logger.debug("Submitting background agent activities task")
                self.performance_optimizer.submit_background_task(
                    lambda: self._simulate_agent_activities(symbol),
                    callback=lambda result: self.update_queue.put(('agent_update', result))
                )
                
                # Get market data
                self.logger.debug("Fetching market data...")
                market_data = self.data_provider.get_market_data(symbol)
                if market_data:
                    self.logger.debug(f"Market data received: {symbol} @ {market_data.price}")
                    self.update_queue.put(('market_data', market_data))
                else:
                    self.logger.debug("No market data received")
                
                # Perform analysis with caching
                self.logger.debug("Starting analysis with caching...")
                analysis_key = f"analysis_{symbol}_{int(time.time() // 60)}"  # Cache for 1 minute
                analysis = self.performance_optimizer.optimize_data_operation(
                    analysis_key,
                    lambda: self._perform_analysis(symbol, market_data)
                )
                if analysis:
                    self.logger.debug(f"Analysis completed: RSI={analysis.get('rsi', 'N/A')}, SMA={analysis.get('sma', 'N/A')}")
                    self.update_queue.put(('analysis', analysis))
                else:
                    self.logger.debug("Analysis failed or returned None")
                
                # Update portfolio
                self.logger.debug("Updating portfolio...")
                portfolio_summary = self.portfolio_tracker.get_summary()
                self.update_queue.put(('portfolio', portfolio_summary))
                
                # Process completed background tasks
                self.logger.debug("Processing background task results...")
                self.performance_optimizer.task_manager.process_results()
                
                # Sleep for update interval
                update_interval = self.update_interval_var.get()
                self.logger.debug(f"Trading loop iteration completed, sleeping for {update_interval} seconds")
                time.sleep(update_interval)
                
            except Exception as e:
                self.logger.error(f"Error in trading loop: {e}")
                self.logger.debug(f"Trading loop error details: {type(e).__name__}: {str(e)}")
                self.update_queue.put(('error', str(e)))
                time.sleep(5)  # Wait before retrying
    
    def _simulate_agent_activities(self, symbol: str):
        """Simulate agent activities for demonstration."""
        import random
        
        activities = [
            "Analyzing market trends",
            "Processing news sentiment",
            "Calculating technical indicators",
            "Evaluating risk factors",
            "Generating trading signals",
            "Monitoring portfolio performance",
            "Updating market models",
            "Assessing volatility patterns"
        ]
        
        # Randomly activate agents
        for role, agent in self.agents.items():
            if self.agent_enabled_vars.get(role, tk.BooleanVar(value=True)).get():
                if random.random() < 0.3:  # 30% chance of activity
                    activity = random.choice(activities)
                    status = random.choice(["Working", "Analyzing", "Processing"])
                    agent.update_status(status, f"{activity} for {symbol}")
                    self.update_queue.put(('agent_update', role))
    
    def _perform_analysis(self, symbol: str, market_data) -> Optional[Dict]:
        """Perform technical and sentiment analysis with advanced indicators."""
        if not market_data:
            self.logger.debug("No market data provided for analysis")
            return None
        
        try:
            self.logger.debug(f"Starting analysis for {symbol} at price {market_data.price}")
            
            # Create OHLCV data for technical analysis
            # In a real implementation, you would get historical data
            # For demo, we'll simulate some data
            self.logger.debug("Generating sample OHLCV data...")
            ohlcv_data = self._generate_sample_ohlcv_data(market_data)
            
            # Perform comprehensive technical analysis
            self.logger.debug("Performing advanced technical analysis...")
            analysis_results = self.technical_analyzer_advanced.analyze_ohlcv_data(ohlcv_data)
            
            # Generate trading signals
            self.logger.debug("Generating trading signals...")
            trading_signals = self.technical_analyzer_advanced.get_trading_signals(analysis_results)
            
            # Traditional technical analysis
            self.logger.debug("Calculating traditional technical indicators...")
            prices = [market_data.price] * 20  # Simplified for demo
            rsi = self.technical_analyzer.calculate_rsi(prices)
            sma = self.technical_analyzer.calculate_sma(prices, 10)
            self.logger.debug(f"Traditional indicators calculated: RSI={rsi}, SMA={sma}")
            
            # Sentiment analysis (mock)
            self.logger.debug("Performing sentiment analysis...")
            sentiment_score = self.sentiment_analyzer.analyze_text_sentiment(f"Analysis for {symbol}")
            self.logger.debug(f"Sentiment analysis completed: score={sentiment_score}")
            
            analysis = {
                'symbol': symbol,
                'timestamp': datetime.now(),
                'technical': {
                    'rsi': rsi,
                    'sma': sma,
                    'price': market_data.price
                },
                'advanced_technical': analysis_results,
                'trading_signals': trading_signals,
                'sentiment': {
                    'score': sentiment_score,
                    'label': 'Positive' if sentiment_score > 0.1 else 'Negative' if sentiment_score < -0.1 else 'Neutral'
                }
            }
            
            # Store analysis results
            self.current_analysis = analysis
            self.logger.debug(f"Analysis results stored for {symbol}")
            
            # Log significant signals
            if trading_signals and trading_signals.get('overall_signal') != 'NEUTRAL':
                confidence = trading_signals.get('confidence', 0)
                signal = trading_signals.get('overall_signal')
                self.logger.debug(f"Significant trading signal detected: {signal} (Confidence: {confidence:.2f})")
                self._add_log("INFO", f"Trading Signal: {signal} (Confidence: {confidence:.2f})")
            else:
                self.logger.debug("No significant trading signals detected")
            
            self.logger.debug(f"Analysis completed successfully for {symbol}")
            return analysis
            
        except Exception as e:
            self.logger.error(f"Error in analysis: {e}")
            self.logger.debug(f"Analysis error details: {type(e).__name__}: {str(e)}")
            return None
    
    def _process_updates(self):
        """Process updates from the trading thread."""
        try:
            while True:
                update_type, data = self.update_queue.get_nowait()
                
                if update_type == 'market_data':
                    self._update_market_data_display(data)
                elif update_type == 'analysis':
                    self._update_analysis_display(data)
                elif update_type == 'portfolio':
                    self._update_portfolio_display(data)
                elif update_type == 'agent_update':
                    self._update_agent_display(data)
                elif update_type == 'error':
                    self._add_log("ERROR", f"Trading error: {data}")
                    
        except queue.Empty:
            pass
        
        # Update logs display
        self._update_logs_display()
        
        # Schedule next update
        self.root.after(100, self._process_updates)
    
    def _update_market_data_display(self, market_data):
        """Update market data display."""
        self.market_data_text.delete(1.0, tk.END)
        
        data_text = f"""Symbol: {market_data.symbol}
Current Price: {format_currency(market_data.price)}
Volume: {market_data.volume:,}
Change: {format_currency(market_data.change)}
Change %: {format_percentage(market_data.change_percent)}

Last Updated: {datetime.now().strftime('%H:%M:%S')}"""
        
        self.market_data_text.insert(tk.END, data_text)
    
    def _update_analysis_display(self, analysis):
        """Update analysis results display."""
        self.analysis_text.delete(1.0, tk.END)
        
        analysis_text = f"""Technical Analysis for {analysis['symbol']}:
{'='*40}

RSI: {analysis['technical']['rsi']:.2f}
SMA (10): {format_currency(analysis['technical']['sma'])}
Current Price: {format_currency(analysis['technical']['price'])}

Sentiment Analysis:
{'='*20}
Score: {analysis['sentiment']['score']:.3f}
Label: {analysis['sentiment']['label']}

Timestamp: {analysis['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}

Trading Signals:
{'='*15}
"""
        
        # Add trading signals based on analysis
        if analysis['technical']['rsi'] > 70:
            analysis_text += "⚠️ RSI indicates overbought condition\n"
        elif analysis['technical']['rsi'] < 30:
            analysis_text += "📈 RSI indicates oversold condition\n"
        
        if analysis['sentiment']['score'] > 0.2:
            analysis_text += "😊 Positive sentiment detected\n"
        elif analysis['sentiment']['score'] < -0.2:
            analysis_text += "😟 Negative sentiment detected\n"
        
        self.analysis_text.insert(tk.END, analysis_text)
    
    def _update_portfolio_display(self, portfolio_summary):
        """Update portfolio display."""
        # Update summary labels
        self.portfolio_labels['total_value'].config(text=format_currency(portfolio_summary.get('total_value', 0)))
        self.portfolio_labels['total_p&l'].config(text=format_currency(portfolio_summary.get('total_pnl', 0)))
        self.portfolio_labels['total_return_pct'].config(text=format_percentage(portfolio_summary.get('total_return', 0)))
        self.portfolio_labels['active_positions'].config(text=str(portfolio_summary.get('active_positions', 0)))
        
        # Update positions tree
        for item in self.positions_tree.get_children():
            self.positions_tree.delete(item)
        
        for position in portfolio_summary.get('positions', []):
            self.positions_tree.insert('', tk.END, values=(
                position.get('symbol', ''),
                position.get('quantity', 0),
                format_currency(position.get('avg_price', 0)),
                format_currency(position.get('current_price', 0)),
                format_currency(position.get('pnl', 0)),
                format_percentage(position.get('pnl_pct', 0))
            ))
    
    def _update_agent_display(self, agent_role: str):
        """Update agent display."""
        if agent_role in self.agent_widgets:
            agent = self.agents[agent_role]
            widgets = self.agent_widgets[agent_role]
            
                # Update status label
            try:
                status_colors = getattr(self.config, 'STATUS_COLORS', {})
                status_color = status_colors.get(agent.status.lower(), 'black')
            except Exception:
                status_color = 'black'
            widgets['status_label'].config(text=agent.status, foreground=status_color)
            
            # Update action label
            widgets['action_label'].config(text=f"Last Action: {agent.last_action}")
    
    def _test_api_connections(self):
        """Test API connections."""
        # Test OpenAI connection (mock)
        openai_key = self.openai_key_var.get().strip()
        try:
            status_colors = getattr(self.config, 'STATUS_COLORS', {})
            success_color = status_colors.get('success', 'green')
            error_color = status_colors.get('error', 'red')
        except Exception:
            success_color = 'green'
            error_color = 'red'
            
        if openai_key:
            self.openai_status.config(text="OpenAI: Connected", 
                                     foreground=success_color)
        else:
            self.openai_status.config(text="OpenAI: Not Connected", 
                                     foreground=error_color)
        
        # Test FinnHub connection (mock)
        finnhub_key = self.finnhub_key_var.get().strip()
        if finnhub_key:
            self.finnhub_status.config(text="FinnHub: Connected", 
                                      foreground=success_color)
        else:
            self.finnhub_status.config(text="FinnHub: Not Connected", 
                                      foreground=error_color)
        
        messagebox.showinfo("Connection Test", "API connection test completed. Check status indicators.")
    
    def _update_api_status(self):
        """Update API status indicators."""
        # Get OpenAI key status
        openai_key = self.openai_key_var.get().strip()
        try:
            status_colors = getattr(self.config, 'STATUS_COLORS', {})
            success_color = status_colors.get('success', 'green')
            error_color = status_colors.get('error', 'red')
        except Exception:
            success_color = 'green'
            error_color = 'red'
            
        if openai_key:
            self.openai_status.config(text="OpenAI: Connected", 
                                     foreground=success_color)
        else:
            self.openai_status.config(text="OpenAI: Not Connected", 
                                     foreground=error_color)
        
        # Get FinnHub key status
        finnhub_key = self.finnhub_key_var.get().strip()
        if finnhub_key:
            self.finnhub_status.config(text="FinnHub: Connected", 
                                      foreground=success_color)
        else:
            self.finnhub_status.config(text="FinnHub: Not Connected", 
                                      foreground=error_color)
    
    def _update_logs_display(self):
        """Update logs display from ThreadSafeLogger."""
        try:
            # Get current log level filter
            selected_level = self.log_level_var.get()
            
            # Get all log entries
            if selected_level == "ALL":
                entries = self.logger.get_entries()
            else:
                entries = self.logger.get_entries(selected_level)
            
            # Get current content to avoid unnecessary updates
            current_content = self.logs_text.get(1.0, tk.END).strip()
            
            # Build new content
            new_content = ""
            for entry in entries:
                timestamp = entry['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                new_content += f"[{timestamp}] {entry['level']}: {entry['message']}\n"
            
            # Only update if content changed
            if new_content.strip() != current_content:
                self.logs_text.delete(1.0, tk.END)
                
                # Insert entries with proper tags
                for entry in entries:
                    timestamp = entry['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                    log_entry = f"[{timestamp}] {entry['level']}: {entry['message']}\n"
                    self.logs_text.insert(tk.END, log_entry, entry['level'])
                
                self.logs_text.see(tk.END)
                
        except Exception as e:
            # Fallback to old method if there's an error
            pass
    
    def _add_log(self, level: str, message: str):
        """Add a log message to the logs display."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] {level}: {message}\n"
        
        self.logs_text.insert(tk.END, log_entry, level)
        self.logs_text.see(tk.END)
    
    def _clear_logs(self):
        """Clear the logs display."""
        self.logs_text.delete(1.0, tk.END)
    
    def _export_logs(self):
        """Export logs to a file."""
        from tkinter import filedialog
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Export Logs"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.logs_text.get(1.0, tk.END))
                messagebox.showinfo("Export Complete", f"Logs exported to {filename}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export logs: {e}")
    
    def _start_performance_monitoring(self):
        """Start performance monitoring."""
        def monitor_performance():
            while True:
                try:
                    # Collect system metrics
                    status = self.performance_optimizer.get_system_status()
                    
                    # Perform maintenance if needed
                    maintenance_results = self.performance_optimizer.perform_maintenance()
                    
                    # Log performance issues
                    if status['performance_summary'].get('current_alerts'):
                        for alert in status['performance_summary']['current_alerts']:
                            self._add_log("WARNING", f"Performance Alert: {alert}")
                    
                    # Update performance display
                    self.root.after(0, lambda: self._update_performance_display(status))
                    
                    time.sleep(30)  # Check every 30 seconds
                    
                except Exception as e:
                    print(f"Performance monitoring error: {e}")
                    time.sleep(60)  # Wait longer on error
        
        # Start monitoring in background thread
        monitor_thread = threading.Thread(target=monitor_performance, daemon=True)
        monitor_thread.start()
    
    def _update_performance_display(self, status):
        """Update performance information in UI."""
        try:
            metrics = status['current_metrics']
            cache_stats = status['cache_stats']
            
            # Update status bar or performance panel if exists
            perf_info = (
                f"CPU: {metrics.cpu_usage:.1f}% | "
                f"Memory: {metrics.memory_usage:.1f}% | "
                f"Cache Hit Rate: {cache_stats['hit_rate']:.2f} | "
                f"Active Threads: {metrics.active_threads}"
            )
            
            # Add to logs if performance is concerning
            if metrics.cpu_usage > 80 or metrics.memory_usage > 80:
                self._add_log("WARNING", f"Performance Status: {perf_info}")
                
        except Exception as e:
            print(f"Performance display update error: {e}")
    
    def _generate_sample_ohlcv_data(self, market_data):
        """Generate sample OHLCV data for technical analysis."""
        # In a real implementation, this would fetch historical data
        # For demo purposes, we'll generate some sample data
        ohlcv_data = []
        base_price = market_data.price
        
        for i in range(50):  # Generate 50 data points
            # Simulate price movement
            price_change = (i - 25) * 0.01  # Gradual trend
            noise = (hash(str(i)) % 100 - 50) * 0.001  # Random noise
            
            current_price = base_price * (1 + price_change + noise)
            high = current_price * 1.02
            low = current_price * 0.98
            volume = 1000000 + (hash(str(i)) % 500000)
            
            ohlcv = OHLCV(
                open=current_price * 0.999,
                high=high,
                low=low,
                close=current_price,
                volume=volume,
                timestamp=datetime.now()
            )
            ohlcv_data.append(ohlcv)
        
        return ohlcv_data
    
    def run(self):
        """Start the GUI application."""
        try:
            self._add_log("INFO", "TradingAgents GUI Starting...")
            self._add_log("INFO", "Performance optimization enabled")
            self._add_log("INFO", "Technical analysis module loaded")
            self.root.mainloop()
        except KeyboardInterrupt:
            self.logger.info("Application interrupted by user")
        except Exception as e:
            self.logger.error(f"Application error: {e}")
            messagebox.showerror("Application Error", f"An error occurred: {e}")
        finally:
            self._cleanup()


    def _save_api_keys(self):
        """Save API keys to local file."""
        try:
            # Get values from GUI
            openai_key = self.openai_key_var.get().strip()
            finnhub_key = self.finnhub_key_var.get().strip()
            
            # Update config
            if openai_key:
                self.config.set_api_key('openai', openai_key)
            if finnhub_key:
                self.config.set_api_key('finnhub', finnhub_key)
            
            messagebox.showinfo("Success", "API keys saved successfully!")
            self._add_log("INFO", "API keys saved to local file")
            
            # Update API status
            self._update_api_status()
            
        except Exception as e:
            error_msg = f"Failed to save API keys: {e}"
            messagebox.showerror("Error", error_msg)
            self._add_log("ERROR", error_msg)
    
    def _load_api_keys(self):
        """Load API keys from local file."""
        try:
            # Load from config
            self.config.load_api_keys_from_file()
            
            # Update GUI
            self.openai_key_var.set(self.config.openai_api_key)
            self.finnhub_key_var.set(self.config.finnhub_api_key)
            
            self._add_log("INFO", "API keys loaded from local file")
            
            # Update API status
            self._update_api_status()
            
        except Exception as e:
            error_msg = f"Failed to load API keys: {e}"
            self._add_log("WARNING", error_msg)
    
    def _cleanup(self):
        """Clean up resources before closing."""
        if self.is_trading:
            self._stop_trading()
        
        # Wait for trading thread to finish
        if self.trading_thread and self.trading_thread.is_alive():
            self.trading_thread.join(timeout=5)
        
        # Shutdown performance optimizer
        try:
            self.performance_optimizer.shutdown()
            self._add_log("INFO", "Performance optimizer shutdown")
        except Exception as e:
            print(f"Performance optimizer shutdown error: {e}")
        
        self._add_log("INFO", "Application closed")


def main():
    """Main entry point."""
    try:
        app = TradingAgentsGUI()
        app.run()
    except Exception as e:
        print(f"Failed to start application: {e}")
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()