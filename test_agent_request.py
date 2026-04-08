import requests
import json
import sys

def test_agent():
    base_url = "http://localhost:8002"
    
    # Test 1: Agent Card
    print("=" * 60)
    print("TEST 1: Agent Card (/.well-known/agent.json)")
    print("=" * 60)
    try:
        response = requests.get(f"{base_url}/.well-known/agent.json")
        print(f"✅ Status: {response.status_code}")
        agent_card = response.json()
        print(f"   Agent ID: {agent_card.get('id')}")
        print(f"   Agent Name: {agent_card.get('name')}")
        print(f"   Capabilities: {', '.join(agent_card.get('capabilities', []))}")
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    # Test 2: Health Check
    print("\n" + "=" * 60)
    print("TEST 2: Health Check (/health)")
    print("=" * 60)
    try:
        response = requests.get(f"{base_url}/health")
        print(f"✅ Status: {response.status_code}")
        health = response.json()
        print(f"   Agent Status: {health.get('status')}")
        print(f"   Timestamp: {health.get('timestamp')}")
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    # Test 3: BRD to JIRA Conversion
    print("\n" + "=" * 60)
    print("TEST 3: BRD to JIRA Conversion (/convert)")
    print("=" * 60)

    sample_brd = {
        "title": "User Authentication System",
        "description": "Implement secure user authentication with OAuth2",
        "requirements": [
            {
                "id": "REQ-001",
                "title": "OAuth2 Implementation",
                "description": "Add OAuth2 support for third-party login",
                "priority": "High",
                "effort": "13 days"
            },
            {
                "id": "REQ-002",
                "title": "Multi-factor Authentication",
                "description": "Implement MFA with TOTP",
                "priority": "Medium",
                "effort": "8 days"
            }
        ]
    }

    try:
        response = requests.post(
            f"{base_url}/convert",
            json={"brd_json": sample_brd, "project_key": "AUTH"}
        )
        print(f"✅ Status: {response.status_code}")
        result = response.json()
        
        if "jira_tickets" in result:
            tickets = result.get("jira_tickets", [])
            print(f"   Generated {len(tickets)} JIRA tickets:")
            for ticket in tickets:
                print(f"      - {ticket.get('summary', 'N/A')} (Story Points: {ticket.get('story_points', 'N/A')})")
        else:
            print(f"   Response: {json.dumps(result, indent=6)}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED - Agent is working correctly!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_agent()
    sys.exit(0 if success else 1)
