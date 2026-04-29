"""
Example: Using Mem0-Enhanced Supervisor
Demonstrates how to use memory management in your BRD-to-Code workflow
"""

import asyncio
import sys
from pathlib import Path

# Add necessary paths
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "src" / "agents"))

# Import the supervisor and memory integration
from supervisor import Supervisor
from src.agents.supervisor_mem0_integration import add_memory_to_supervisor


async def run_with_memory(user_requirement: str, user_id: str = "default_user", language: str = "python"):
    """
    Run the supervisor workflow with memory tracking enabled
    
    Args:
        user_requirement: User's requirement text
        user_id: Unique identifier for the user (for personalized memory)
        language: Programming language (python, csharp, etc.)
    """
    
    print("\n" + "="*80)
    print("🧠 MEMORY-ENHANCED SUPERVISOR WORKFLOW")
    print("="*80)
    
    # Step 1: Create supervisor instance
    print("\n1. Initializing Supervisor...")
    supervisor = Supervisor()
    
    # Step 2: Add memory capabilities
    print("2. Adding memory capabilities...")
    supervisor = add_memory_to_supervisor(supervisor, user_id=user_id)
    print(f"   ✓ Memory manager attached for user: {user_id}")
    print(f"   ✓ Session ID: {supervisor.session_id}")
    
    # Step 3: Check for relevant context from previous sessions
    print("\n3. Checking memory for relevant context...")
    context = supervisor.get_relevant_context(user_requirement, limit=3)
    
    if context:
        print("   ✓ Found relevant context from previous sessions:")
        print(context)
        
        # Optionally enhance the requirement with memory
        enhanced_requirement = supervisor.enhance_requirement_with_memory(user_requirement)
        print("\n   Enhanced requirement with memory context:")
        print(enhanced_requirement[:300] + "...")
    else:
        print("   ℹ No relevant context found (this might be a new type of request)")
        enhanced_requirement = user_requirement
    
    # Step 4: Store the initial requirement
    print("\n4. Storing user requirement in memory...")
    supervisor.remember_user_requirement(
        requirement=user_requirement,
        language=language
    )
    print("   ✓ Requirement saved to memory")
    
    # Step 5: Run the full workflow
    print("\n5. Running full workflow...")
    print("-"*80)
    
    try:
        result = await supervisor.run_full_workflow(
            requirement=enhanced_requirement,  # Use enhanced requirement
            save_output=True,
            language=language
        )
        
        # Step 6: Store workflow results in memory
        print("\n6. Storing workflow results in memory...")
        
        # Store each step's result
        for step in result.get("steps", []):
            step_num = step.get("step")
            step_result = step.get("result", {})
            agent_name = step.get("agent", "unknown")
            
            # Remember the workflow step
            supervisor.remember_workflow_step(
                step_number=step_num,
                step_name=agent_name,
                result=step_result
            )
            
            # Remember the agent interaction
            supervisor.remember_agent_interaction(
                agent_name=agent_name,
                input_data=user_requirement,
                output_data=step_result.get("message", ""),
                success=step_result.get("success", False),
                metadata={"step": step_num}
            )
        
        # Store generated files if available
        if result.get("files"):
            supervisor.remember_generated_files(result["files"])
        
        print("   ✓ Workflow results saved to memory")
        
        # Step 7: Display memory statistics
        print("\n7. Memory Statistics:")
        stats = supervisor.get_memory_stats()
        print(f"   Total memories stored: {stats.get('total_memories', 0)}")
        print(f"   Agents involved: {', '.join(stats.get('agents', []))}")
        print(f"   Memory types: {stats.get('memory_types', {})}")
        
        # Step 8: Show output location
        print("\n" + "="*80)
        print("✅ WORKFLOW COMPLETE WITH MEMORY TRACKING")
        print("="*80)
        
        if result.get("success", False):
            print(f"\n📁 Output Directory: {result.get('output_dir', 'N/A')}")
            print(f"🧠 Memory Session: {supervisor.session_id}")
            print("\nGenerated files are now linked to this session's memory.")
            print("Future requests will have access to this context!")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Error during workflow: {e}")
        
        # Store the error in memory for learning
        supervisor.remember_agent_interaction(
            agent_name="supervisor",
            input_data=user_requirement,
            output_data=f"Error: {str(e)}",
            success=False,
            metadata={"error_type": type(e).__name__}
        )
        
        raise


async def interactive_mode():
    """
    Interactive mode: Ask user for requirements and track conversations
    """
    
    print("\n" + "="*80)
    print("🧠 MEMORY-ENHANCED BRD-TO-CODE - INTERACTIVE MODE")
    print("="*80)
    
    # Get user ID
    user_id = input("\nEnter your user ID (or press Enter for 'default_user'): ").strip()
    if not user_id:
        user_id = "default_user"
    
    print(f"\n✓ Using user ID: {user_id}")
    print("  (Your preferences and history will be remembered)")
    
    while True:
        print("\n" + "-"*80)
        print("What would you like to build?")
        print("-"*80)
        
        requirement = input("\nRequirement (or 'quit' to exit): ").strip()
        
        if requirement.lower() in ['quit', 'exit', 'q']:
            print("\n👋 Goodbye!")
            break
        
        if not requirement:
            print("❌ Please enter a requirement")
            continue
        
        # Select language
        print("\nSelect language:")
        print("  1. Python (FastAPI)")
        print("  2. C# (.NET)")
        
        lang_choice = input("Choice (1 or 2, default=1): ").strip() or "1"
        language = "python" if lang_choice == "1" else "csharp"
        
        # Run workflow with memory
        try:
            result = await run_with_memory(
                user_requirement=requirement,
                user_id=user_id,
                language=language
            )
            
            # Optional: Ask for feedback
            print("\n" + "-"*80)
            feedback = input("How was the result? (optional feedback): ").strip()
            
            if feedback:
                # Create temporary supervisor to store feedback
                temp_supervisor = Supervisor()
                temp_supervisor = add_memory_to_supervisor(temp_supervisor, user_id=user_id)
                temp_supervisor.remember_user_feedback(feedback)
                print("✓ Feedback saved to memory")
                
        except Exception as e:
            print(f"\n❌ Error: {e}")
            continue


async def demo_memory_benefits():
    """
    Demonstrate the benefits of memory by showing context retrieval
    """
    
    print("\n" + "="*80)
    print("🎯 DEMO: Memory Benefits")
    print("="*80)
    
    user_id = "demo_user"
    
    # Simulate multiple requests to show memory benefits
    requests = [
        {
            "requirement": "Create a todo list application with user authentication",
            "language": "python"
        },
        {
            "requirement": "Add task categories and priority levels to the todo app",
            "language": "python"
        },
        {
            "requirement": "Create a similar todo app but for C#",
            "language": "csharp"
        }
    ]
    
    for i, req_info in enumerate(requests, 1):
        print(f"\n{'='*80}")
        print(f"Request {i}/{len(requests)}")
        print(f"{'='*80}")
        
        await run_with_memory(
            user_requirement=req_info["requirement"],
            user_id=user_id,
            language=req_info["language"]
        )
        
        if i < len(requests):
            print("\n⏸ Press Enter to continue to next request...")
            input()


# Quick access functions

async def quick_run(requirement: str, language: str = "python", user_id: str = "default_user"):
    """
    Quick run without interactive prompts
    
    Args:
        requirement: User requirement text
        language: Programming language (python, csharp)
        user_id: User identifier for memory
    """
    return await run_with_memory(requirement, user_id, language)


if __name__ == "__main__":
    import sys
    
    # Check command line arguments
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == "demo":
            # Run demo
            asyncio.run(demo_memory_benefits())
            
        elif mode == "quick" and len(sys.argv) > 2:
            # Quick run with requirement from command line
            requirement = sys.argv[2]
            language = sys.argv[3] if len(sys.argv) > 3 else "python"
            user_id = sys.argv[4] if len(sys.argv) > 4 else "default_user"
            
            asyncio.run(quick_run(requirement, language, user_id))
            
        else:
            print("Usage:")
            print("  python supervisor_with_memory.py interactive  # Interactive mode")
            print("  python supervisor_with_memory.py demo         # Demo mode")
            print('  python supervisor_with_memory.py quick "requirement" [language] [user_id]')
            
    else:
        # Default to interactive mode
        asyncio.run(interactive_mode())
