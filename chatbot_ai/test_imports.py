# project_abegail/MCP/chatbot_ai/test_imports.py
"""
Test script to verify all imports work correctly
Run this before starting the app
"""
import sys

print("Testing imports in correct order...")
print("=" * 60)

try:
    print("\n1. Testing config.py (no dependencies)...")
    import config
    print("   ✓ config.py imported successfully")
    print(f"   - MCP_ENABLED: {config.MCP_ENABLED}")
    print(f"   - MCP_SERVER_URL: {config.MCP_SERVER_URL}")
except Exception as e:
    print(f"   ✗ Error importing config: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n2. Testing utils.py (no dependencies)...")
    from utils import async_route
    print("   ✓ utils.py imported successfully")
except Exception as e:
    print(f"   ✗ Error importing utils: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n3. Testing mcp_service.py (no module dependencies)...")
    from mcp_service import call_mcp_tool
    print("   ✓ mcp_service.py imported successfully")
    print("   - Function call_mcp_tool available")
except Exception as e:
    print(f"   ✗ Error importing mcp_service: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n4. Testing deepseek_service.py (depends on mcp_service)...")
    from deepseek_service import ask_deepseek_with_mcp
    print("   ✓ deepseek_service.py imported successfully")
    print("   - Function ask_deepseek_with_mcp available")
except Exception as e:
    print(f"   ✗ Error importing deepseek_service: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    print("\n5. Testing chatbot_service.py (depends on deepseek_service)...")
    from chatbot_service import get_response, is_company_question, initialize_nltk
    print("   ✓ chatbot_service.py imported successfully")
    print("   - Function get_response available")
    print("   - Function is_company_question available")
    print("   - Function initialize_nltk available")
except Exception as e:
    print(f"   ✗ Error importing chatbot_service: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "=" * 60)
print("✓ ALL IMPORTS SUCCESSFUL!")
print("=" * 60)
print("\n📋 Import order verified:")
print("   config.py → mcp_service.py → deepseek_service.py → chatbot_service.py")
print("\n✅ You can now run: python app.py")
print("-" * 60)