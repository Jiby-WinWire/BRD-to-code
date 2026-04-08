"""Policy Manager for CodeToTest Agent

Validates agent execution against Discovery Service policies.
"""

import logging
import httpx
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PolicyResult:
    """Result of policy validation"""
    agent_policy: bool = False
    resource_policy: bool = False
    task_policy: bool = False

    @property
    def all_passed(self) -> bool:
        return self.agent_policy and self.resource_policy and self.task_policy


class PolicyManager:
    """Policy Manager for agent authorization and access control."""

    def __init__(
        self,
        discovery_app_url: str,
        client_id: str,
        agent_url: str,
        policy_types: Optional[Dict[str, Any]] = None,
        timeout: int = 10
    ):
        self.discovery_app_url = discovery_app_url.rstrip('/')
        self.client_id = client_id
        self.agent_url = agent_url
        self.timeout = timeout
        self.policy_types = policy_types or {
            "agent_policy": True,
            "resource_policy": True,
            "task_policy": True
        }

        logger.info(
            f"PolicyManager initialized: {self.discovery_app_url}, policies={self.policy_types}"
        )

    def validate_agent_policy(self, session_id: str, task_data: Dict[str, Any]) -> bool:
        if not self.policy_types.get("agent_policy", False):
            logger.info("Agent policy check disabled")
            return True

        try:
            url = f"{self.discovery_app_url}/policy/validate"
            payload = {
                "client_id": self.client_id,
                "session_id": session_id,
                "agent_url": self.agent_url,
                "policy_type": "agent",
                "task_data": task_data
            }
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()
                is_allowed = result.get("allowed", False)
                logger.info(f"Agent policy validation: {is_allowed}")
                return is_allowed
        except Exception as e:
            logger.error(f"Agent policy validation failed: {str(e)}")
            return False

    def validate_resource_policy(self, session_id: str, resources: list) -> bool:
        if not self.policy_types.get("resource_policy", False):
            logger.info("Resource policy check disabled")
            return True

        try:
            url = f"{self.discovery_app_url}/policy/validate"
            payload = {
                "client_id": self.client_id,
                "session_id": session_id,
                "agent_url": self.agent_url,
                "policy_type": "resource",
                "resources": resources
            }
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()
                is_allowed = result.get("allowed", False)
                logger.info(f"Resource policy validation: {is_allowed}")
                return is_allowed
        except Exception as e:
            logger.error(f"Resource policy validation failed: {str(e)}")
            return False

    def validate_task_policy(
        self,
        session_id: str,
        task_type: str,
        task_params: Optional[Dict[str, Any]] = None
    ) -> bool:
        if not self.policy_types.get("task_policy", False):
            logger.info("Task policy check disabled")
            return True

        try:
            url = f"{self.discovery_app_url}/policy/validate"
            payload = {
                "client_id": self.client_id,
                "session_id": session_id,
                "agent_url": self.agent_url,
                "policy_type": "task",
                "task_type": task_type,
                "task_params": task_params or {}
            }
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                result = response.json()
                is_allowed = result.get("allowed", False)
                logger.info(f"Task policy validation: {is_allowed}")
                return is_allowed
        except Exception as e:
            logger.error(f"Task policy validation failed: {str(e)}")
            return False

    def validate_all_policies(
        self,
        session_id: str,
        task_data: Optional[Dict[str, Any]] = None,
        resources: Optional[list] = None,
        task_type: Optional[str] = None,
        task_params: Optional[Dict[str, Any]] = None
    ) -> PolicyResult:
        result = PolicyResult()
        validations = []

        if self.policy_types.get("agent_policy", False):
            validations.append(
                ("agent", lambda: self.validate_agent_policy(session_id, task_data or {}))
            )
        else:
            result.agent_policy = True

        if self.policy_types.get("resource_policy", False):
            validations.append(
                ("resource", lambda: self.validate_resource_policy(session_id, resources or []))
            )
        else:
            result.resource_policy = True

        if self.policy_types.get("task_policy", False):
            validations.append(
                ("task", lambda: self.validate_task_policy(
                    session_id,
                    task_type or "code_generation",
                    task_params
                ))
            )
        else:
            result.task_policy = True

        if validations:
            with ThreadPoolExecutor(max_workers=len(validations)) as executor:
                futures = {
                    executor.submit(func): name
                    for name, func in validations
                }
                for future in futures:
                    policy_name = futures[future]
                    try:
                        is_allowed = future.result(timeout=self.timeout)
                        setattr(result, f"{policy_name}_policy", is_allowed)
                    except Exception as e:
                        logger.error(f"{policy_name} policy validation error: {str(e)}")
                        setattr(result, f"{policy_name}_policy", False)

        return result
