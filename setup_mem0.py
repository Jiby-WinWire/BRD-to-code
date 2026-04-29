# Quick Setup for Mem0 Integration
# Run this script to verify your mem0 setup

import sys
import os
from pathlib import Path

print("="*80)
print("🧠 MEM0 AI INTEGRATION - SETUP VERIFICATION")
print("="*80)

# Step 1: Check Python version
print("\n1. Checking Python version...")
py_version = sys.version_info
if py_version >= (3, 8):
    print(f"   ✅ Python {py_version.major}.{py_version.minor}.{py_version.micro}")
else:
    print(f"   ❌ Python {py_version.major}.{py_version.minor} (requires 3.8+)")
    sys.exit(1)

# Step 2: Check for required files
print("\n2. Checking required files...")
required_files = [
    "src/agents/mem0_manager.py",
    "src/agents/supervisor_mem0_integration.py",
    "supervisor_with_memory.py",
    "memory_utils.py",
    "MEM0_INTEGRATION_GUIDE.md",
    ".env"
]

for file in required_files:
    if Path(file).exists():
        print(f"   ✅ {file}")
    else:
        print(f"   ❌ {file} (missing)")

# Step 3: Check environment variables
print("\n3. Checking environment configuration...")
from dotenv import load_dotenv
load_dotenv()

mem0_key = os.getenv("mem0_key")
if mem0_key:
    print(f"   ✅ mem0_key found (length: {len(mem0_key)})")
else:
    print("   ❌ mem0_key not found in .env")
    print("   → Add: mem0_key=\"your-key-here\" to .env file")

# Check Azure OpenAI configuration (required for mem0)
azure_openai_key = os.getenv("AZURE_OPENAI_API_KEY")
azure_openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
if azure_openai_key and azure_openai_endpoint:
    print(f"   ✅ Azure OpenAI configured")
else:
    print("   ⚠️  Azure OpenAI not fully configured")
    print("   → Mem0 uses OpenAI for embeddings. Add AZURE_OPENAI_API_KEY and AZURE_OPENAI_ENDPOINT")

# Step 4: Check dependencies
print("\n4. Checking dependencies...")
try:
    import mem0
    print(f"   ✅ mem0ai installed (version: {mem0.__version__ if hasattr(mem0, '__version__') else 'unknown'})")
except ImportError:
    print("   ❌ mem0ai not installed")
    print("   → Run: pip install mem0ai")

try:
    import redis
    print(f"   ✅ redis installed")
except ImportError:
    print("   ⚠️  redis not installed (optional, but in requirements.txt)")

try:
    import langchain
    print(f"   ✅ langchain installed")
except ImportError:
    print("   ⚠️  langchain not installed (check requirements.txt)")

# Step 5: Test basic functionality
print("\n5. Testing basic mem0 functionality...")
if mem0_key:
    try:
        sys.path.insert(0, str(Path(__file__).parent / "src" / "agents"))
        from mem0_manager import create_memory_manager
        
        print("   Testing memory manager creation...")
        manager = create_memory_manager(user_id="setup_test", session_id="setup_001")
        print("   ✅ Memory manager created successfully")
        
        print("   Testing memory storage...")
        result = manager.add_conversation(
            role="system",
            content="Setup test message",
            agent_name="setup_script",
            metadata={"type": "test"}
        )
        
        if result.get("success"):
            print("   ✅ Memory stored successfully")
            
            print("   Testing memory retrieval...")
            memories = manager.get_relevant_memories("setup test", limit=1)
            if memories:
                print("   ✅ Memory retrieved successfully")
            else:
                print("   ⚠️  Memory retrieval returned no results (might be normal for new setup)")
        else:
            print(f"   ❌ Memory storage failed: {result.get('error')}")
            
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        print(f"   Error type: {type(e).__name__}")
else:
    print("   ⚠️  Skipped (no API key)")

# Summary
print("\n" + "="*80)
print("📋 SETUP SUMMARY")
print("="*80)
print("\nIf all checks passed (✅), you're ready to use Mem0!")
print("\nNext steps:")
print("  1. Read: MEM0_INTEGRATION_GUIDE.md")
print("  2. Try interactive mode: python supervisor_with_memory.py")
print("  3. View utilities: python memory_utils.py --help")
print("\nIf any checks failed (❌), please fix them before proceeding.")
print("="*80)
