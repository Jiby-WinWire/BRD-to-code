"""
BRD-to-Code Pipeline - Main Entry Point
Prompts user for requirements and generates complete API with BRD, Jira stories, code, and tests.
Supports multiple programming languages: Python (FastAPI), C# (ASP.NET Core), .NET
"""
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file in project root
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

# Add src and root to path for imports
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(project_root))

# Import the supervisor for orchestration
import asyncio
from supervisor import Supervisor


def main():
    """Main entry point for the BRD-to-Code pipeline"""
    print("=" * 80)
    print("🚀 BRD-to-Code AI Pipeline")
    print("=" * 80)
    print("\nThis tool will generate:")
    print("  ✅ Business Requirement Document (BRD) - JSON & text formats")
    print("  ✅ Jira User Stories - JSON & text formats")
    print("  ✅ Production-ready Code")
    print("  ✅ Comprehensive Tests (all passing)")
    print("  ✅ Helper files (run.py, README.md, requirements.txt)")
    print("\n" + "=" * 80 + "\n")
    
    # Prompt user for input
    try:
        user_prompt = input("📝 Enter your APP requirements (e.g., 'create a todo APP with add and list tasks'):\n> ").strip()
        
        if not user_prompt:
            print("\n❌ Error: No input provided. Please enter your API requirements.")
            sys.exit(1)
        
        # Prompt for language selection
        print("\n" + "-" * 80)
        print("Select programming language:")
        print("  1. Python (FastAPI) - Default")
        print("  2. C# (ASP.NET Core)")
        print("  3. .NET (ASP.NET Core)")
        print("-" * 80)
        
        language_choice = input("Enter choice (1-3) [default: 1]: ").strip() or "1"
        
        language_map = {
            "1": "python",
            "2": "csharp",
            "3": "dotnet"
        }
        
        language = language_map.get(language_choice, "python")
        print(f"✅ Selected language: {language.upper()}")
        
        print("\n" + "=" * 80)
        print(f"🔄 Processing: {user_prompt}")
        print(f"📝 Language: {language.upper()}")
        print("=" * 80 + "\n")
        
        # Run the pipeline using Supervisor
        supervisor = Supervisor()
        results = asyncio.run(supervisor.run_full_workflow(user_prompt, language=language))
        
        print("\n" + "=" * 80)
        if results.get("success"):
            print("✅ Pipeline Complete!")
        else:
            print("⚠️  Pipeline completed with issues")
        print("=" * 80)
        print("\n📂 Generated files are in the 'output' directory:")
        print(f"   📁 output/{supervisor.session_id}/")
        print("      📄 docs/brd.json & brd.txt           - Business Requirements Document")
        print("      📋 docs/jira_stories.json & .txt     - Jira User Stories")
        print("      💻 src/api/                           - Generated code files")
        print("      🧪 tests/                             - Test suite")
        print("      📦 run.py, README.md, requirements.txt - Helper Files")
        print("\n🚀 To run your API:")
        print(f"   cd output/{supervisor.session_id}")
        if language == "python":
            print("   python run.py")
            print("\n📚 API Documentation:")
            print("   http://localhost:8000/docs")
        elif language in ["csharp", "dotnet"]:
            print("   dotnet run")
            print("   # OR")
            print("   dotnet watch run")
            print("\n📚 API Documentation:")
            print("   http://localhost:5000/swagger/ui")
        
        print("\n🧪 To run tests:")
        if language == "python":
            print(f"   pytest output/{supervisor.session_id}/tests/ -v")
        elif language in ["csharp", "dotnet"]:
            print("   dotnet test")
        
        print("\n" + "=" * 80 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n❌ Pipeline cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
