# BRD to Jira user stories conversion logic
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

def brd_to_jira_stories(brd_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Convert BRD JSON to a list of Jira user story JSON objects.
    Supports both legacy and new BRD formats.
    """
    stories = []
    
    # Handle new BRD format from BRD generator
    if "functionalRequirements" in brd_json or "nonFunctionalRequirements" in brd_json:
        logger.info("Processing new BRD format with functionalRequirements")
        
        # Extract stakeholders/actors
        stakeholders = brd_json.get("stakeholders", [])
        default_actor = "User"
        if stakeholders and isinstance(stakeholders, list) and len(stakeholders) > 0:
            if isinstance(stakeholders[0], dict):
                default_actor = stakeholders[0].get("role", "User")
            else:
                default_actor = stakeholders[0]
        
        # Extract business goals
        business_goals = brd_json.get("businessGoals", [])
        default_business_value = business_goals[0] if business_goals else "improve the system"
        
        # Extract acceptance criteria
        acceptance_criteria_list = brd_json.get("acceptanceCriteria", [])
        
        # Process functional requirements
        functional_reqs = brd_json.get("functionalRequirements", [])
        for req in functional_reqs:
            req_id = req.get("id", "")
            description = req.get("description", "")
            
            # Create user story summary
            summary = f"As a {default_actor}, I want {description} so that {default_business_value}"
            
            # Find matching acceptance criteria by ID prefix
            matching_criteria = [
                ac.get("description", "") 
                for ac in acceptance_criteria_list 
                if isinstance(ac, dict) and ac.get("description")
            ]
            
            # Build description with acceptance criteria
            if matching_criteria:
                description_text = f"{summary}\n\nAcceptance Criteria:\n" + "\n".join(f"- {c}" for c in matching_criteria[:3])
            else:
                description_text = summary
            
            story = {
                "fields": {
                    "summary": f"{req_id}: {description[:80]}" if len(description) > 80 else f"{req_id}: {description}",
                    "description": description_text,
                    "priority": {"name": "Medium"},
                    "labels": ["generated", "autostory", "functional"],
                    "issuetype": {"name": "Story"},
                }
            }
            stories.append(story)
        
        # Process non-functional requirements as tasks/stories
        non_functional_reqs = brd_json.get("nonFunctionalRequirements", [])
        for req in non_functional_reqs:
            req_id = req.get("id", "")
            description = req.get("description", "")
            
            summary = f"NFR: {description}"
            
            story = {
                "fields": {
                    "summary": f"{req_id}: {description[:80]}" if len(description) > 80 else f"{req_id}: {description}",
                    "description": summary,
                    "priority": {"name": "High"},
                    "labels": ["generated", "autostory", "non-functional"],
                    "issuetype": {"name": "Story"},
                }
            }
            stories.append(story)
        
        logger.info(f"Generated {len(stories)} Jira stories from new BRD format")
        return stories
    
    # Handle legacy BRD format
    logger.info("Processing legacy BRD format with requirements")
    actor = brd_json.get("actors", ["User"])[0]
    module_to_epic = {m.get("name"): f"{m.get('name')} Epic" for m in brd_json.get("modules", [])}
    for req in brd_json.get("requirements", []):
        feature = req.get("feature") or req.get("description") or req.get("title")
        business_value = req.get("business_value") or (brd_json.get("business_goals") or [""])[0]
        summary = f"As a {actor}, I want {feature} so that {business_value}."
        acceptance_criteria = req.get("acceptance_criteria") or req.get("constraints") or req.get("success_conditions") or []
        if isinstance(acceptance_criteria, str):
            acceptance_criteria = [acceptance_criteria]
        description = f"{summary}\n\nAcceptance Criteria:\n" + "\n".join(f"- {c}" for c in acceptance_criteria)
        priority = req.get("criticality", "Medium")
        module = req.get("module")
        epic_link = module_to_epic.get(module) if module else None
        story = {
            "fields": {
                "summary": summary,
                "description": description,
                "priority": {"name": priority},
                "labels": ["generated", "autostory"],
                "issuetype": {"name": "Story"},
            }
        }
        if epic_link:
            story["fields"]["epic_link"] = epic_link
        stories.append(story)
    
    logger.info(f"Generated {len(stories)} Jira stories from legacy BRD format")
    return stories
