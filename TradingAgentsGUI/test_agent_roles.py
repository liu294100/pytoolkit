#!/usr/bin/env python3
"""
Test script to verify AGENT_ROLES access
"""

import sys
import os

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from config import Config, AGENT_ROLES
    print("✓ Successfully imported Config and AGENT_ROLES")
    
    # Test Config instantiation
    config = Config()
    print("✓ Successfully created Config instance")
    
    # Test AGENT_ROLES access
    print(f"✓ AGENT_ROLES contains {len(AGENT_ROLES)} roles:")
    for role, info in AGENT_ROLES.items():
        print(f"  - {role}: {info.get('name', 'Unknown')}")
    
    # Test the specific code that was failing
    agents = {}
    for role, agent_info in AGENT_ROLES.items():
        agent_name = agent_info.get('name', f"{role.replace('_', ' ').title()} Agent")
        description = agent_info.get('description', f"Agent responsible for {role.replace('_', ' ')}")
        agents[role] = {'name': agent_name, 'description': description}
    
    print(f"✓ Successfully created {len(agents)} agent definitions")
    print("\n=== Test Results ===")
    print("All tests passed! The AGENT_ROLES issue should be resolved.")
    
except ImportError as e:
    print(f"✗ Import error: {e}")
except AttributeError as e:
    print(f"✗ Attribute error: {e}")
except Exception as e:
    print(f"✗ Unexpected error: {e}")

print("\nPress Enter to exit...")
input()