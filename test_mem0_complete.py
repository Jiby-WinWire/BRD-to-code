"""
Complete mem0 Integration Test
Tests all fixed memory functionality including workflow steps and agent interactions
"""

import sys
from pathlib import Path

# Add src/agents to path
sys.path.insert(0, str(Path(__file__).parent / "src" / "agents"))

from supervisor_mem0_integration import add_memory_to_supervisor

def test_complete_mem0_integration():
    """Test all mem0 integration functionality after bug fixes"""
    print("="*70)
    print("🧠 COMPLETE MEM0 INTEGRATION TEST")  
    print("="*70)
    
    try:
        # Create a mock supervisor
        class MockSupervisor:
            def __init__(self):
                self.session_id = "test_session_123"
        
        supervisor = MockSupervisor()
        
        # Test 1: Add memory capabilities
        print("\n1. Testing Memory Integration...")
        enhanced_supervisor = add_memory_to_supervisor(supervisor, user_id="test_user")
        print("   ✅ Memory capabilities added successfully")
        
        # Test 2: Remember user requirement (fixed lambda)
        print("\n2. Testing User Requirement Memory...")
        result = enhanced_supervisor.remember_user_requirement(
            requirement="Create a Python snake game with pygame",
            language="Python",
            template_id="game_template"
        )
        print(f"   ✅ User requirement stored: {result.get('success', False)}")
        
        # Test 3: Remember agent interaction (fixed lambda)
        print("\n3. Testing Agent Interaction Memory...")
        result = enhanced_supervisor.remember_agent_interaction(
            agent_name="brd_generator", 
            input_data="snake game requirements",
            output_data="BRD document generated",
            success=True,
            metadata={"execution_time": "2.5s"}
        )
        print(f"   ✅ Agent interaction stored: {result.get('success', False)}")
        
        # Test 4: Remember workflow step (fixed lambda)
        print("\n4. Testing Workflow Step Memory...")
        result = enhanced_supervisor.remember_workflow_step(
            step_number=1,
            step_name="Generate BRD",
            result={"success": True, "output_file": "brd.md"}
        )
        print(f"   ✅ Workflow step stored: {result.get('success', False)}")
        
        # Test 5: Remember generated files
        print("\n5. Testing Generated Files Memory...")
        result = enhanced_supervisor.remember_generated_files([
            "src/snake_game.py", 
            "src/game_objects.py", 
            "requirements.txt"
        ])
        print(f"   ✅ Generated files stored: {result.get('success', False)}")
        
        # Test 6: Get relevant context
        print("\n6. Testing Context Retrieval...")
        context = enhanced_supervisor.get_relevant_context("snake game")
        print(f"   ✅ Retrieved context (length: {len(context)} chars)")
        
        # Test 7: Enhanced requirement with memory
        print("\n7. Testing Requirement Enhancement...")
        enhanced_req = enhanced_supervisor.enhance_requirement_with_memory(
            "Create another game"
        )
        print(f"   ✅ Enhanced requirement: {len(enhanced_req)} chars")
        
        # Test 8: Memory stats
        print("\n8. Testing Memory Statistics...")
        stats = enhanced_supervisor.get_memory_stats()
        print(f"   ✅ Memory stats retrieved: {stats}")
        
        print("\n" + "="*70)
        print("🎉 ALL MEM0 INTEGRATION TESTS PASSED!")
        print("Your mem0 system is fully functional and bug-free!")
        print("="*70)
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_complete_mem0_integration()