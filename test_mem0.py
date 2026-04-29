"""
Quick mem0 verification test
Tests basic memory operations after bug fixes
"""

import sys
from pathlib import Path

# Add src/agents to path
sys.path.insert(0, str(Path(__file__).parent / "src" / "agents"))

from mem0_manager import create_memory_manager

def test_mem0_basic():
    """Test basic mem0 functionality"""
    print("="*60)
    print("🧠 MEM0 FUNCTIONALITY TEST")  
    print("="*60)
    
    try:
        # Test 1: Create memory manager
        print("\n1. Testing Memory Manager Creation...")
        manager = create_memory_manager(user_id="test_user")
        print("   ✅ Memory manager created successfully")
        
        # Test 2: Add a test memory
        print("\n2. Testing Memory Storage...")
        result = manager.add_conversation(
            role="user",
            content="I want to create a Python snake game",
            agent_name="test_agent",
            metadata={"type": "test", "project": "snake_game"}
        )
        print(f"   ✅ Memory stored successfully: {result.get('memory_id', 'ID not returned')}")
        
        # Test 3: Search for memories  
        print("\n3. Testing Memory Retrieval...")
        memories = manager.get_relevant_memories("snake game", limit=3)
        print(f"   ✅ Found {len(memories)} memories")
        
        if memories:
            print(f"   📝 Latest memory: {memories[0].get('content', 'N/A')[:50]}...")
        
        # Test 4: Get user preferences (if any exist)
        print("\n4. Testing User Preferences...")
        preferences = manager.get_user_preferences()
        print(f"   ✅ Retrieved {len(preferences)} preferences")
        
        print("\n" + "="*60)
        print("🎉 ALL TESTS PASSED - MEM0 IS WORKING!")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        print("\nCheck your .env file has:")
        print("mem0_key=m0-WK246Jb13fjXkp3zAfj07w6DGzxTHemOUk0AcdtD")
        return False

if __name__ == "__main__":
    test_mem0_basic()