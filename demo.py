"""
Interactive Demo Script for BRD-to-Code System
Shows all 5 agents working together with visual progress

Usage: python demo.py
"""
import asyncio
import httpx
import uuid
import json
import sys
import time
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class DemoRunner:
    """Interactive demo with visual feedback"""
    
    AGENTS = [
        {
            "key": "brd_generator",
            "name": "BRD Generator",
            "url": "http://localhost:8001",
            "emoji": "📝",
            "timeout": 120.0
        },
        {
            "key": "brd_to_jira",
            "name": "BRD to JIRA",
            "url": "http://localhost:8002",
            "emoji": "📋",
            "timeout": 120.0
        },
        {
            "key": "code_to_test",
            "name": "Code to Test",
            "url": "http://localhost:8003",
            "emoji": "💻",
            "timeout": 180.0
        },
        {
            "key": "validation",
            "name": "Validation",
            "url": "http://localhost:8004",
            "emoji": "✅",
            "timeout": 120.0
        },
        {
            "key": "jira_to_code",
            "name": "JIRA to Code",
            "url": "http://localhost:8005",
            "emoji": "🔧",
            "timeout": 120.0
        }
    ]
    
    DEMO_SCENARIOS = [
        {
            "name": "Inventory Management System",
            "requirement": "Create an inventory management API with barcode scanning, stock tracking, low-stock alerts, and supplier management",
            "description": "Full-featured inventory system with real-time tracking"
        },
        {
            "name": "E-commerce Platform",
            "requirement": "Build an e-commerce API with product catalog, shopping cart, checkout, payment processing, and order tracking",
            "description": "Complete online shopping platform"
        },
        {
            "name": "Task Management System",
            "requirement": "Develop a task management API with project creation, task assignment, progress tracking, and team collaboration",
            "description": "Team collaboration and task tracking system"
        },
        {
            "name": "Blog Platform",
            "requirement": "Create a blog platform API with post creation, commenting, tagging, user profiles, and content moderation",
            "description": "Full-featured blogging platform"
        },
        {
            "name": "Custom Requirement",
            "requirement": None,
            "description": "Enter your own API requirement"
        }
    ]
    
    def __init__(self):
        self.context_id = str(uuid.uuid4())
        self.session_id = f"demo-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    def print_header(self):
        """Print demo header"""
        print("\n" + "="*80)
        print("🚀 BRD-to-Code System - Interactive Demo")
        print("="*80)
        print("This demo will show all 5 agents working together:")
        print("  1. 📝 BRD Generator  - Creates Business Requirements Document")
        print("  2. 📋 BRD to JIRA    - Converts BRD to JIRA tickets")
        print("  3. 💻 Code to Test   - Generates code and tests")
        print("  4. ✅ Validation     - Validates BRD quality")
        print("  5. 🔧 JIRA to Code   - Generates code snippets from JIRA")
        print("="*80 + "\n")
    
    async def check_agents_health(self) -> bool:
        """Check if all agents are running"""
        print("🔍 Checking agent status...\n")
        
        all_healthy = True
        async with httpx.AsyncClient(timeout=5.0) as client:
            for agent in self.AGENTS:
                try:
                    response = await client.get(f"{agent['url']}/health")
                    if response.status_code == 200:
                        print(f"  ✅ {agent['emoji']} {agent['name']:20s} - Running")
                    else:
                        print(f"  ❌ {agent['emoji']} {agent['name']:20s} - Unhealthy (Status: {response.status_code})")
                        all_healthy = False
                except Exception as e:
                    print(f"  ❌ {agent['emoji']} {agent['name']:20s} - Not reachable")
                    all_healthy = False
        
        print()
        return all_healthy
    
    def select_scenario(self) -> str:
        """Let user select a demo scenario"""
        print("📋 Select a demo scenario:\n")
        
        for i, scenario in enumerate(self.DEMO_SCENARIOS, 1):
            print(f"  {i}. {scenario['name']}")
            print(f"     {scenario['description']}\n")
        
        while True:
            try:
                choice = input("Enter your choice (1-5): ").strip()
                choice_num = int(choice)
                
                if 1 <= choice_num <= len(self.DEMO_SCENARIOS):
                    scenario = self.DEMO_SCENARIOS[choice_num - 1]
                    
                    if scenario["requirement"] is None:
                        print("\n" + "="*80)
                        print("💬 Enter your custom API requirement:")
                        print("="*80)
                        print("Example: Create a hotel booking API with room reservations and availability\n")
                        requirement = input("Your requirement: ").strip()
                        
                        if not requirement:
                            print("❌ No requirement provided. Please try again.\n")
                            continue
                        
                        return requirement
                    else:
                        return scenario["requirement"]
                else:
                    print(f"❌ Invalid choice. Please enter a number between 1 and {len(self.DEMO_SCENARIOS)}\n")
            except ValueError:
                print("❌ Invalid input. Please enter a number.\n")
            except KeyboardInterrupt:
                print("\n\n⚠️  Demo cancelled by user")
                sys.exit(0)
    
    async def send_task(self, agent: Dict, message: str) -> Dict[str, Any]:
        """Send task to an agent using A2A protocol"""
        
        jsonrpc_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/send",
            "params": {
                "message": {
                    "kind": "message",
                    "message_id": str(uuid.uuid4()),
                    "role": "user",
                    "parts": [{"kind": "text", "text": message}],
                    "context_id": None,
                    "task_id": None,
                    "metadata": None,
                    "reference_task_ids": None,
                    "extensions": None
                },
                "context_id": self.context_id,
                "metadata": {
                    "session_id": self.session_id,
                    "user_id": "demo"
                }
            }
        }
        
        start_time = datetime.now()
        
        async with httpx.AsyncClient(timeout=agent["timeout"]) as client:
            try:
                response = await client.post(
                    agent["url"],
                    json=jsonrpc_request,
                    headers={"Content-Type": "application/json"}
                )
                
                response.raise_for_status()
                result = response.json()
                duration = (datetime.now() - start_time).total_seconds()
                
                if "result" in result:
                    task_result = result["result"]
                    
                    if not isinstance(task_result, dict):
                        return {
                            "success": False,
                            "error": "Invalid task result type",
                            "duration": duration
                        }
                    
                    status = task_result.get("status", {})
                    state = status.get("state", "unknown")
                    
                    # Extract message text from parts
                    message_obj = status.get("message", {})
                    parts = message_obj.get("parts", [])
                    message_response = ""
                    
                    if parts and len(parts) > 0:
                        message_response = parts[0].get("text", "")
                    
                    return {
                        "success": True,
                        "state": state,
                        "message": message_response,
                        "duration": duration
                    }
                else:
                    return {
                        "success": False,
                        "error": "Invalid response format",
                        "duration": duration
                    }
                    
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                return {
                    "success": False,
                    "error": str(e),
                    "duration": duration
                }
    
    async def run_demo(self, requirement: str):
        """Run the complete demo workflow"""
        
        print("\n" + "="*80)
        print("🎬 Starting Demo Workflow")
        print("="*80)
        print(f"Requirement: {requirement}")
        print(f"Session ID: {self.session_id}")
        print("="*80 + "\n")
        
        input("Press Enter to start the demo...")
        
        workflow_data = {
            "brd": None,
            "jira": None,
            "code": None,
            "validation": None,
            "snippet": None
        }
        
        # Step 1: Generate BRD
        print("\n" + "─"*80)
        print(f"📝 STEP 1: Generating BRD from requirement")
        print("─"*80)
        print("⏳ Agent working...")
        
        brd_result = await self.send_task(self.AGENTS[0], requirement)
        
        if brd_result["success"]:
            print(f"✅ BRD Generated ({brd_result['duration']:.1f}s, {len(brd_result['message'])} chars)")
            workflow_data["brd"] = brd_result["message"]
            print(f"\n📄 Preview (first 200 chars):")
            print(f"   {brd_result['message'][:200]}...")
        else:
            print(f"❌ Failed: {brd_result.get('error', 'Unknown error')}")
            return
        
        input("\nPress Enter to continue to next step...")
        
        # Step 2: Convert BRD to JIRA
        print("\n" + "─"*80)
        print(f"📋 STEP 2: Converting BRD to JIRA tickets")
        print("─"*80)
        print("⏳ Agent working...")
        
        jira_result = await self.send_task(self.AGENTS[1], workflow_data["brd"])
        
        if jira_result["success"]:
            print(f"✅ JIRA Tickets Generated ({jira_result['duration']:.1f}s)")
            workflow_data["jira"] = jira_result["message"]
            
            # Try to count tickets
            try:
                jira_data = json.loads(jira_result["message"]) if jira_result["message"].startswith('[') else None
                if jira_data and isinstance(jira_data, list):
                    print(f"   📊 Generated {len(jira_data)} JIRA tickets")
            except:
                pass
        else:
            print(f"❌ Failed: {jira_result.get('error', 'Unknown error')}")
            return
        
        input("\nPress Enter to continue to next step...")
        
        # Step 3: Generate Code
        print("\n" + "─"*80)
        print(f"💻 STEP 3: Generating code and tests from JIRA tickets")
        print("─"*80)
        print("⏳ Agent working (this may take 30-60 seconds)...")
        
        code_result = await self.send_task(self.AGENTS[2], workflow_data["jira"])
        
        if code_result["success"]:
            print(f"✅ Code & Tests Generated ({code_result['duration']:.1f}s)")
            workflow_data["code"] = code_result["message"]
            print("   📁 Check output/ directory for generated files")
        else:
            print(f"❌ Failed: {code_result.get('error', 'Unknown error')}")
        
        input("\nPress Enter to continue to next step...")
        
        # Step 4: Validate BRD
        print("\n" + "─"*80)
        print(f"✅ STEP 4: Validating BRD quality")
        print("─"*80)
        print("⏳ Agent working...")
        
        validation_result = await self.send_task(self.AGENTS[3], workflow_data["brd"])
        
        if validation_result["success"]:
            print(f"✅ Validation Complete ({validation_result['duration']:.1f}s)")
            workflow_data["validation"] = validation_result["message"]
            print(f"\n📊 Validation Preview (first 200 chars):")
            print(f"   {validation_result['message'][:200]}...")
        else:
            print(f"⚠️  Validation skipped: {validation_result.get('error', 'Unknown error')}")
        
        input("\nPress Enter to continue to final step...")
        
        # Step 5: Generate Code Snippet (demo purposes)
        print("\n" + "─"*80)
        print(f"🔧 STEP 5: Generating code snippet from JIRA (demo)")
        print("─"*80)
        print("⏳ Agent working...")
        
        snippet_result = await self.send_task(
            self.AGENTS[4],
            "Create a REST API endpoint for user registration with email validation"
        )
        
        if snippet_result["success"]:
            print(f"✅ Code Snippet Generated ({snippet_result['duration']:.1f}s)")
            workflow_data["snippet"] = snippet_result["message"]
        else:
            print(f"⚠️  Snippet generation skipped: {snippet_result.get('error', 'Unknown error')}")
        
        # Save results
        self.save_results(workflow_data)
        
        # Print final summary
        print("\n" + "="*80)
        print("🎉 DEMO COMPLETE!")
        print("="*80)
        print(f"\n📂 All outputs saved to: output/{self.session_id}/")
        print(f"\nFiles generated:")
        print(f"  • brd.md              - Business Requirements Document")
        print(f"  • jira_tickets.json   - JIRA tickets")
        print(f"  • validation_report.md - BRD validation report")
        print(f"  • code_snippet.txt    - Sample code snippet")
        print(f"\n💻 Generated code files are in the output/ directory")
        print("="*80 + "\n")
    
    def save_results(self, workflow_data: Dict):
        """Save all workflow results"""
        output_dir = Path("output") / self.session_id
        output_dir.mkdir(parents=True, exist_ok=True)
        
        if workflow_data["brd"]:
            (output_dir / "brd.md").write_text(workflow_data["brd"], encoding='utf-8')
        
        if workflow_data["jira"]:
            (output_dir / "jira_tickets.json").write_text(workflow_data["jira"], encoding='utf-8')
        
        if workflow_data["validation"]:
            (output_dir / "validation_report.md").write_text(workflow_data["validation"], encoding='utf-8')
        
        if workflow_data["snippet"]:
            (output_dir / "code_snippet.txt").write_text(workflow_data["snippet"], encoding='utf-8')


async def main():
    """Main entry point"""
    demo = DemoRunner()
    
    try:
        demo.print_header()
        
        # Check if agents are running
        if not await demo.check_agents_health():
            print("❌ Not all agents are running!")
            print("\n💡 To start all agents, run:")
            print("   powershell -ExecutionPolicy Bypass -File start_all_agents.ps1\n")
            return
        
        print("✅ All agents are ready!\n")
        
        # Select scenario
        requirement = demo.select_scenario()
        
        # Run demo
        await demo.run_demo(requirement)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
