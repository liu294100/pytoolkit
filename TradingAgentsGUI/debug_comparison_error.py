#!/usr/bin/env python3
"""
Debug script to identify the comparison error.
"""

import sys
import os
import tkinter as tk

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_tkinter_version():
    """Test tkinter version comparison."""
    try:
        print(f"Tkinter version: {tk.TkVersion}")
        print(f"Tkinter version type: {type(tk.TkVersion)}")
        
        # Test potential problematic comparisons
        if hasattr(tk, 'TkVersion'):
            version = tk.TkVersion
            print(f"Testing version comparisons...")
            
            # These might cause issues if version is float and compared to string
            try:
                result = version > "8.6"
                print(f"version > '8.6': {result}")
            except TypeError as e:
                print(f"ERROR in version > '8.6': {e}")
                
            try:
                result = version > 8.6
                print(f"version > 8.6: {result}")
            except TypeError as e:
                print(f"ERROR in version > 8.6: {e}")
                
    except Exception as e:
        print(f"Error testing tkinter version: {e}")

def test_config_imports():
    """Test config imports and potential comparison issues."""
    try:
        from config import Config, AGENT_ROLES, RISK_LEVELS
        print("✓ Config imports successful")
        
        config = Config()
        print("✓ Config instance created")
        
        # Test risk settings
        risk_settings = config.get_risk_settings()
        print(f"✓ Risk settings: {risk_settings}")
        
    except Exception as e:
        print(f"Error in config: {e}")
        import traceback
        traceback.print_exc()

def test_main_imports():
    """Test main.py imports."""
    try:
        # Test individual imports
        modules = [
            'config',
            'utils', 
            'performance_optimizer',
            'technical_indicators',
            'api_integration',
            'strategy_customization'
        ]
        
        for module in modules:
            try:
                __import__(module)
                print(f"✓ {module} imported successfully")
            except Exception as e:
                print(f"✗ {module} import failed: {e}")
                
    except Exception as e:
        print(f"Error testing imports: {e}")

if __name__ == "__main__":
    print("=== Debugging Comparison Error ===")
    print(f"Python version: {sys.version}")
    print(f"Working directory: {os.getcwd()}")
    print()
    
    print("1. Testing Tkinter version...")
    test_tkinter_version()
    print()
    
    print("2. Testing config imports...")
    test_config_imports()
    print()
    
    print("3. Testing main imports...")
    test_main_imports()
    print()
    
    print("=== Debug Complete ===")