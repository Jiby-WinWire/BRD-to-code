"""
BRD-to-Code Enterprise Application
Main entry point with language selection: Python or C#/.NET
"""

import sys
import subprocess
import asyncio
from pathlib import Path
from typing import Literal


class LanguageSelector:
    """Interactive entry point for language selection"""
    
    @staticmethod
    def display_menu():
        """Display language selection menu"""
        print("\n" + "="*60)
        print("[BRD-TO-CODE] ENTERPRISE GENERATOR")
        print("="*60)
        print("\nSelect your target language/framework:\n")
        print("  1. Python (FastAPI + HTML/CSS/JS)")
        print("  2. C# (.NET Framework + ASP.NET Core + SQL)")
        print("\n" + "="*60)
    
    @staticmethod
    def get_language_choice() -> Literal["python", "csharp"]:
        """Get user's language choice"""
        while True:
            choice = input("\nEnter choice (1 or 2): ").strip()
            if choice == "1":
                print("\n[OK] Selected: Python (FastAPI)")
                return "python"
            elif choice == "2":
                print("\n[OK] Selected: C# (.NET Framework)")
                return "csharp"
            else:
                print("[ERROR] Invalid choice. Please enter 1 or 2.")
    
    @staticmethod
    def get_user_description() -> str:
        """Get user's application description"""
        print("\n" + "-"*60)
        print("[INPUT] Describe your application requirements")
        print("-"*60)
        print("Examples:")
        print("  - Create a todo list app with create and delete tasks")
        print("  - Build an inventory management system with barcode scanning")
        print("  - Design an employee management portal with attendance tracking")
        print("-"*60 + "\n")
        
        description = input("Enter your requirements (or press Enter for demo): ").strip()
        
        if not description:
            # Return a default demo prompt
            description = "Create a simple Todo application with create, read, update and delete tasks capability. Include a beautiful UI with task completion tracking."
            print(f"\n[INFO] Using demo prompt: {description}")
        
        return description
    
    @staticmethod
    async def generate_code(language: str, description: str):
        """Generate code using supervisor with language parameter"""
        from supervisor_language import SupervisorWithLanguage
        
        print("\n" + "="*60)
        print(f"[GENERATING] {language.upper()} application...")
        print("="*60)
        
        supervisor = SupervisorWithLanguage(language)
        result = await supervisor.run(description)
        
        return result
    
    @classmethod
    async def run(cls):
        """Main application flow"""
        try:
            cls.display_menu()
            language = cls.get_language_choice()
            description = cls.get_user_description()
            
            print("\n[WAIT] This may take 60-90 seconds...")
            result = await cls.generate_code(language, description)
            
            if result:
                print("\n" + "="*60)
                print("[OK] APPLICATION GENERATED SUCCESSFULLY!")
                print("="*60)
                print(f"\nOutput Location: {result.get('output_dir')}")
                print("\nGenerated Components:")
                for item in result.get('files', []):
                    print(f"  * {item}")
                
                print("\nTo run your application:")
                print(f"   See: {result.get('output_dir')}/RUN_INSTRUCTIONS.txt")
                
            else:
                print("\n[ERROR] Generation failed. Check logs for details.")
                
        except KeyboardInterrupt:
            print("\n\n[CANCELLED] Generation cancelled by user.")
            sys.exit(1)
        except Exception as e:
            print(f"\n[ERROR] Error: {str(e)}")
            sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(LanguageSelector.run())
    except KeyboardInterrupt:
        print("\n\nExiting...")
        sys.exit(0)
