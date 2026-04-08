"""
Agent to generate a BRD (Business Requirement Document) from a user prompt using LLM.
"""

import logging
from typing import Dict, Any
from src.infrastructure.azure_clients import get_llm_client, get_llm_deployment_name

logger = logging.getLogger("brd_generator_agent")


def generate_brd_from_prompt(user_prompt: str) -> Dict[str, Any]:
    """
    Generate a BRD JSON structure from a user prompt using LLM.
    """
    llm = get_llm_client()
    deployment_name = get_llm_deployment_name()
    system_prompt = (
        "You are a business analyst. Given a user request, generate a detailed Business Requirement Document (BRD) in JSON format. "
        "The BRD should include: title, description, business goals, functional requirements, non-functional requirements, stakeholders, and acceptance criteria. "
        "Return ONLY valid JSON, no markdown code blocks, no explanations, no additional text."
    )
    logger.info("Generating BRD from user prompt: %s", user_prompt)
    import json
    import re
    try:
        response = llm.chat.completions.create(
            model=deployment_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=2048
        )
        content = response.choices[0].message.content
        logger.debug("Raw LLM response:\n%s", content)
        
        # Try to extract JSON from markdown code blocks if present
        if "```json" in content or "```" in content:
            logger.info("Detected markdown code block, extracting JSON...")
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                content = json_match.group(1)
            else:
                # Try to find any JSON object in the response
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    content = json_match.group(0)
        
        brd_json = json.loads(content.strip())
        logger.info("Successfully generated BRD JSON with keys: %s", list(brd_json.keys()))
        return brd_json
    except json.JSONDecodeError as e:
        logger.error("Failed to parse BRD JSON: %s", e)
        logger.error("Raw content was:\n%s", content if 'content' in locals() else 'No content received')
        raise ValueError(f"LLM did not return valid JSON for BRD. Error: {e}")
    except Exception as e:
        logger.error("Failed to generate BRD: %s", e)
        raise ValueError(f"Failed to generate BRD from prompt: {e}")
