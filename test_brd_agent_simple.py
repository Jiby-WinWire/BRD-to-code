"""
Simple BRD Generator Test - Standalone without A2A SDK
Run: python test_brd_agent_simple.py
"""

import os
import json
import asyncio
from dotenv import load_dotenv
from langchain_openai import AzureChatOpenAI

# Load environment
load_dotenv()

async def generate_brd_simple(user_prompt: str):
    """Generate BRD using Azure OpenAI"""
    
    # Initialize LLM
    llm = AzureChatOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
        azure_deployment=os.getenv("AZURE_OPENAI_MODEL_DEPLOYMENT"),
        temperature=0.2
    )
    
    # System prompt
    system_prompt = """You are a senior business analyst. Generate a comprehensive Business Requirements Document (BRD) in JSON format.

The BRD MUST include these sections:
- title: Clear project title
- description: 2-3 paragraph overview
- business_goals: List of strategic objectives (3-5 items)
- functional_requirements: Detailed features (8-15 items)
- non_functional_requirements: Performance, security, scalability
- stakeholders: Key stakeholders and roles
- acceptance_criteria: Measurable success criteria (5-8 items)
- assumptions: Technical and business assumptions
- constraints: Budget, timeline, technical constraints
- risks: Potential risks and mitigation

Return ONLY valid JSON, no markdown code blocks."""

    print("🔄 Generating BRD...")
    print(f"📝 Prompt: {user_prompt[:100]}...")
    
    # Generate BRD
    response = llm.invoke([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ])
    
    content = response.content
    
    # Extract JSON from markdown if needed
    if "```json" in content:
        import re
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
        if json_match:
            content = json_match.group(1)
    elif "```" in content:
        content = content.replace("```", "")
    
    # Parse JSON
    brd_json = json.loads(content.strip())
    
    print("✅ BRD Generated Successfully!")
    print(f"📊 Title: {brd_json.get('title', 'N/A')}")
    print(f"📦 Sections: {list(brd_json.keys())}")
    
    return brd_json

async def main():
    """Main test function"""
    
    # Test prompt
    test_prompt = """
    Create a BRD for a customer relationship management (CRM) system 
    that helps sales teams track leads, manage customer interactions, 
    and generate sales reports. The system should include contact management,
    deal pipeline tracking, email integration, and analytics dashboard.
    """
    
    print("=" * 80)
    print("🚀 BRD GENERATOR - SIMPLE TEST")
    print("=" * 80)
    
    try:
        # Generate BRD
        brd = await generate_brd_simple(test_prompt)
        
        # Save to file
        output_dir = "output/brd_test_simple"
        os.makedirs(output_dir, exist_ok=True)
        
        json_file = f"{output_dir}/brd.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(brd, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Saved to: {json_file}")
        
        # Display BRD
        print("\n" + "=" * 80)
        print("📄 GENERATED BRD")
        print("=" * 80)
        print(json.dumps(brd, indent=2, ensure_ascii=False)[:1000] + "...")
        print("=" * 80)
        print("✅ TEST COMPLETED SUCCESSFULLY!")
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
