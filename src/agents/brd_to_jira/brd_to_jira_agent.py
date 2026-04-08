import os
from dotenv import load_dotenv
from src.infrastructure.azure_clients import get_llm_client, get_llm_deployment_name

load_dotenv(override=False)

def main():
    llm_client = get_llm_client()
    deployment_name = get_llm_deployment_name()
    if not llm_client:
        print("Azure OpenAI client not configured. Exiting.")
        return
    print(f"[BRDToJiraAgent] Ready to use deployment: {deployment_name}")
    # Add your agent logic here using llm_client

if __name__ == "__main__":
    main()
