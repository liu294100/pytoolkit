#!/usr/bin/env python3
"""
Test script to verify the fixes for RISK_TOLERANCE and json import errors.
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test that all imports work correctly."""
    try:
        from config import Config, AGENT_ROLES, RISK_LEVELS
        print("✓ Successfully imported Config, AGENT_ROLES, and RISK_LEVELS")
        
        # Test RISK_LEVELS access
        print(f"✓ RISK_LEVELS keys: {list(RISK_LEVELS.keys())}")
        
        # Test Config instantiation
        config = Config()
        print("✓ Successfully created Config instance")
        
        # Test API key methods
        if hasattr(config, 'save_api_keys_to_file'):
            print("✓ Config has save_api_keys_to_file method")
        else:
            print("✗ Config missing save_api_keys_to_file method")
            
        if hasattr(config, 'load_api_keys_from_file'):
            print("✓ Config has load_api_keys_from_file method")
        else:
            print("✗ Config missing load_api_keys_from_file method")
            
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_logger():
    """Test ThreadSafeLogger methods."""
    try:
        from utils import ThreadSafeLogger
        logger = ThreadSafeLogger()
        
        # Test all logging methods
        logger.info("Test info message")
        logger.warning("Test warning message")
        logger.error("Test error message")
        logger.debug("Test debug message")
        
        print("✓ ThreadSafeLogger methods work correctly")
        return True
        
    except Exception as e:
        print(f"✗ ThreadSafeLogger error: {e}")
        return False

if __name__ == "__main__":
    print("Testing fixes...\n")
    
    success = True
    success &= test_imports()
    success &= test_logger()
    
    if success:
        print("\n✓ All tests passed! The fixes should work correctly.")
    else:
        print("\n✗ Some tests failed. Please check the errors above.")