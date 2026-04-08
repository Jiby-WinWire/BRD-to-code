"""Policy Manager reused for JiraToCode agent (adapted from BRD)."""

import logging
import httpx
from typing import Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PolicyResult:
    agent_policy: bool = False
    resource_policy: bool = False
    task_policy: bool = False

    @property
    def all_passed(self) -> bool:
        return self.agent_policy and self.resource_policy and self.task_policy


class PolicyManager:
    def __init__(self, discovery_app_url: str, client_id: str, agent_url: str, policy_types: Optional[Dict[str, Any]] = None, timeout: int = 10):
        self.discovery_app_url = discovery_app_url.rstrip('/')
        self.client_id = client_id
        self.agent_url = agent_url
        self.timeout = timeout
        self.policy_types = policy_types or {"agent_policy": True, "resource_policy": True, "task_policy": True}
        logger.info(f"PolicyManager initialized: {discovery_app_url}")

    def validate_agent_policy(self, session_id: str, task_data: Dict[str, Any]) -> bool:
        if not self.policy_types.get("agent_policy", False):
            return True
        try:
            url = f"{self.discovery_app_url}/policy/validate"
            payload = {"client_id": self.client_id, "session_id": session_id, "agent_url": self.agent_url, "policy_type": "agent", "task_data": task_data}
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                return resp.json().get("allowed", False)
        except Exception as e:
            logger.error(f"Agent policy validation failed: {e}")
            return False

    def validate_resource_policy(self, session_id: str, resources: list) -> bool:
        if not self.policy_types.get("resource_policy", False):
            return True
        try:
            url = f"{self.discovery_app_url}/policy/validate"
            payload = {"client_id": self.client_id, "session_id": session_id, "agent_url": self.agent_url, "policy_type": "resource", "resources": resources}
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                return resp.json().get("allowed", False)
        except Exception as e:
            logger.error(f"Resource policy validation failed: {e}")
            return False

    def validate_task_policy(self, session_id: str, task_type: str, task_params: Optional[Dict[str, Any]] = None) -> bool:
        if not self.policy_types.get("task_policy", False):
            return True
        try:
            url = f"{self.discovery_app_url}/policy/validate"
            payload = {"client_id": self.client_id, "session_id": session_id, "agent_url": self.agent_url, "policy_type": "task", "task_type": task_type, "task_params": task_params or {}}
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                return resp.json().get("allowed", False)
        except Exception as e:
            logger.error(f"Task policy validation failed: {e}")
            return False

    def validate_all_policies(self, session_id: str, task_data: Optional[Dict[str, Any]] = None, resources: Optional[list] = None, task_type: Optional[str] = None, task_params: Optional[Dict[str, Any]] = None) -> PolicyResult:
        res = PolicyResult()
        validations = []
        if self.policy_types.get("agent_policy", False):
            validations.append(("agent", lambda: self.validate_agent_policy(session_id, task_data or {})))
        else:
            res.agent_policy = True
        if self.policy_types.get("resource_policy", False):
            validations.append(("resource", lambda: self.validate_resource_policy(session_id, resources or [])))
        else:
            res.resource_policy = True
        if self.policy_types.get("task_policy", False):
            validations.append(("task", lambda: self.validate_task_policy(session_id, task_type or "jira_to_code", task_params)))
        else:
            res.task_policy = True

        if validations:
            with ThreadPoolExecutor(max_workers=len(validations)) as ex:
                futures = {ex.submit(func): name for name, func in validations}
                for fut in futures:
                    name = futures[fut]
                    try:
                        ok = fut.result(timeout=self.timeout)
                        setattr(res, f"{name}_policy", ok)
                    except Exception as e:
                        logger.error(f"{name} validation error: {e}")
                        setattr(res, f"{name}_policy", False)

        logger.info(f"Policy result: agent={res.agent_policy} resource={res.resource_policy} task={res.task_policy}")
        return res
