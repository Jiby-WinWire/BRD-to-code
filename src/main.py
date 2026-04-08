"""
BRD-to-Code Pipeline - Main Entry Point
Prompts user for requirements and generates complete API with BRD, Jira stories, code, and tests.
"""
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file in project root
project_root = Path(__file__).parent.parent
env_path = project_root / ".env"
load_dotenv(dotenv_path=env_path)

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from agents.orchestrator import react_pipeline


def main():
    """Main entry point for the BRD-to-Code pipeline"""
    print("=" * 80)
    print("🚀 BRD-to-Code AI Pipeline")
    print("=" * 80)
    print("\nThis tool will generate:")
    print("  ✅ Business Requirement Document (BRD) - JSON & text formats")
    print("  ✅ Jira User Stories - JSON & text formats")
    print("  ✅ Production-ready FastAPI Code")
    print("  ✅ Comprehensive Tests (all passing)")
    print("  ✅ Helper files (run.py, README.md, requirements.txt)")
    print("\n" + "=" * 80 + "\n")
    
    # Prompt user for input
    try:
        user_prompt = input("📝 Enter your API requirements (e.g., 'create a todo API with add and list tasks'):\n> ").strip()
        
        if not user_prompt:
            print("\n❌ Error: No input provided. Please enter your API requirements.")
            sys.exit(1)
        
        print("\n" + "=" * 80)
        print(f"🔄 Processing: {user_prompt}")
        print("=" * 80 + "\n")
        
        # Run the pipeline
        react_pipeline(user_prompt)
        
        print("\n" + "=" * 80)
        print("✅ Pipeline Complete!")
        print("=" * 80)
        print("\n📂 Generated files are in the 'output' directory:")
        print("   � docs/")
        print("      📄 brd.json & brd.txt           - Business Requirements Document")
        print("      📋 jira_stories.json & .txt     - Jira User Stories")
        print("   📁 src/api/")
        print("      💻 models.py, services.py, main.py - FastAPI Application Code")
        print("   📁 tests/")
        print("      🧪 test_api.py                   - Comprehensive Test Suite")
        print("   📦 run.py, README.md, requirements.txt - Helper Files")
        print("\n🚀 To run your API:")
        print("   cd output")
        print("   python run.py")
        print("\n📚 API Documentation:")
        print("   http://localhost:8000/docs")
        print("\n🧪 To run tests:")
        print("   pytest output/tests/ -v")
        print("\n" + "=" * 80 + "\n")
        
    except KeyboardInterrupt:
        print("\n\n❌ Pipeline cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
