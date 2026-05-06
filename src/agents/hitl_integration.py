"""
Supervisor HITL Integration
Extends the Supervisor with Human-in-the-Loop capabilities
Wraps agent calls to allow human review and intervention
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from hitl_manager import (
    HITLManager,
    HITLConfig,
    HITLStage,
    HITLActionType,
    HITLPrompt,
    create_hitl_manager
)
from mem0_manager import create_memory_manager

logger = logging.getLogger(__name__)


class SupervisorWithHITL:
    """
    Mixin class to add HITL capabilities to Supervisor
    Wraps all agent interactions with human review checkpoints
    """
    
    def __init__(
        self,
        user_id: str = "default_user",
        hitl_config: Optional[HITLConfig] = None
    ):
        """
        Initialize HITL integration for supervisor
        
        Args:
            user_id: User identifier
            hitl_config: Configuration for HITL behavior
        """
        # Create HITL manager
        self.hitl_manager = create_hitl_manager(
            user_id=user_id,
            config=hitl_config or HITLConfig()
        )
        
        # Track which agents have been reviewed
        self.reviewed_agents = set()
        
        logger.info("SupervisorWithHITL initialized")
    
    def set_hitl_session(self, session_id: str):
        """Set the session ID for HITL tracking"""
        self.hitl_manager.session_id = session_id
        if self.hitl_manager.memory:
            self.hitl_manager.memory.set_session(session_id)
        logger.info(f"HITL session set: {session_id}")
    
    async def send_task_with_hitl(
        self,
        agent_key: str,
        message: str,
        metadata: Optional[Dict] = None,
        template_id: Optional[str] = None,
        skip_pre_review: bool = False,
        skip_post_review: bool = False
    ) -> Dict[str, Any]:
        """
        Send task to agent with HITL checkpoints before and after
        
        Args:
            agent_key: Key identifying the agent
            message: Message to send
            metadata: Optional metadata
            template_id: Optional template ID
            skip_pre_review: Skip human review before sending
            skip_post_review: Skip human review after receiving
            
        Returns:
            Agent result with HITL metadata
        """
        agent_name = self.AGENTS[agent_key]["name"]
        
        logger.info(f"\n{'='*80}")
        logger.info(f"🔄 HITL-Enhanced Agent Call: {agent_name}")
        logger.info(f"{'='*80}")
        
        # Prepare input data
        input_data = {
            "message": message,
            "metadata": metadata or {},
            "template_id": template_id
        }
        
        context = {
            "agent_key": agent_key,
            "agent_name": agent_name,
            "session_id": getattr(self, 'session_id', 'unknown'),
            "timestamp": datetime.now().isoformat()
        }
        
        # PRE-AGENT REVIEW
        if not skip_pre_review:
            logger.info(f"👤 Requesting human review before {agent_name}...")
            
            should_proceed, modified_input, feedback = await self.hitl_manager.review_before_agent(
                agent_name=agent_name,
                input_data=input_data,
                context=context
            )
            
            if not should_proceed:
                logger.warning(f"❌ Human rejected {agent_name} execution: {feedback}")
                return {
                    "success": False,
                    "agent": agent_name,
                    "error": f"Rejected by human: {feedback}",
                    "hitl_stage": "pre_agent",
                    "hitl_feedback": feedback
                }
            
            # Use modified input if provided
            if modified_input and isinstance(modified_input, dict):
                message = modified_input.get("message", message)
                if "metadata" in modified_input:
                    metadata = modified_input["metadata"]
                if "template_id" in modified_input:
                    template_id = modified_input["template_id"]
                
                logger.info(f"✏️  Using human-modified input")
            
            if feedback:
                logger.info(f"💬 Human feedback: {feedback}")
                # Store feedback in context for agent
                if metadata is None:
                    metadata = {}
                metadata["human_feedback"] = feedback
        
        # SEND TO AGENT
        logger.info(f"📤 Sending to {agent_name}...")
        
        # Call the original send_task method (from Supervisor base class)
        result = await self.send_task(
            agent_key=agent_key,
            message=message,
            metadata=metadata,
            template_id=template_id
        )
        
        # POST-AGENT REVIEW
        if not skip_post_review:
            logger.info(f"👤 Requesting human review after {agent_name}...")
            
            output_data = {
                "success": result.get("success", False),
                "message": result.get("message", ""),
                "state": result.get("state", "unknown"),
                "duration": result.get("duration", 0.0)
            }
            
            should_accept, modified_output, feedback = await self.hitl_manager.review_after_agent(
                agent_name=agent_name,
                input_data=input_data,
                output_data=output_data,
                success=result.get("success", False),
                context=context
            )
            
            if not should_accept:
                logger.warning(f"❌ Human rejected {agent_name} output: {feedback}")
                return {
                    **result,
                    "success": False,
                    "error": f"Output rejected by human: {feedback}",
                    "hitl_stage": "post_agent",
                    "hitl_feedback": feedback
                }
            
            # Use modified output if provided
            if modified_output and isinstance(modified_output, dict):
                if "message" in modified_output:
                    result["message"] = modified_output["message"]
                logger.info(f"✏️  Using human-modified output")
            
            if feedback:
                logger.info(f"💬 Human feedback: {feedback}")
                result["hitl_feedback"] = feedback
        
        # Mark agent as reviewed
        self.reviewed_agents.add(agent_key)
        
        # Add HITL metadata to result
        result["hitl_reviewed"] = True
        result["hitl_pre_review"] = not skip_pre_review
        result["hitl_post_review"] = not skip_post_review
        
        return result
    
    async def request_clarification_for_agent(
        self,
        agent_name: str,
        questions: list,
        context: Optional[Dict] = None
    ) -> Dict[str, str]:
        """
        Request clarification from human when agent needs more information
        
        Args:
            agent_name: Name of the agent requesting clarification
            questions: List of questions to ask
            context: Additional context
            
        Returns:
            Dictionary of answers
        """
        logger.info(f"❓ {agent_name} is requesting clarification...")
        
        answers = await self.hitl_manager.request_clarification(
            agent_name=agent_name,
            questions=questions,
            context=context
        )
        
        # Store clarifications in mem0 for future reference
        if self.hitl_manager.memory:
            content = f"Clarifications for {agent_name}: " + json.dumps(answers, indent=2)
            self.hitl_manager.memory.add_conversation(
                role="user",
                content=content,
                agent_name=agent_name,
                metadata={
                    "type": "clarification",
                    "questions": questions,
                    "answers": answers
                }
            )
        
        return answers
    
    def save_hitl_report(self, output_dir: Optional[Path] = None):
        """
        Save HITL session report to file
        
        Args:
            output_dir: Directory to save report (defaults to self.output_dir)
        """
        if output_dir is None:
            output_dir = getattr(self, 'output_dir', Path('output'))
        
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        report_path = output_dir / "hitl_session_report.txt"
        self.hitl_manager.save_session_report(report_path)
        
        logger.info(f"📊 HITL report saved: {report_path}")
        
        return report_path


def add_hitl_to_supervisor(
    supervisor,
    user_id: str = "default_user",
    hitl_config: Optional[HITLConfig] = None
) -> Any:
    """
    Add HITL capabilities to an existing Supervisor instance
    
    Args:
        supervisor: Existing Supervisor instance
        user_id: User identifier
        hitl_config: HITL configuration
        
    Returns:
        Supervisor with HITL capabilities added
    """
    # Create HITL manager
    supervisor.hitl_manager = create_hitl_manager(
        user_id=user_id,
        session_id=getattr(supervisor, 'session_id', None),
        config=hitl_config or HITLConfig()
    )
    
    # Save original send_task method
    supervisor._original_send_task = supervisor.send_task
    
    # Create wrapper methods
    async def send_task_with_hitl(
        agent_key: str,
        message: str,
        metadata: Optional[Dict] = None,
        template_id: Optional[str] = None,
        skip_pre_review: bool = False,
        skip_post_review: bool = False
    ) -> Dict[str, Any]:
        """Wrapped send_task with HITL"""
        agent_name = supervisor.AGENTS[agent_key]["name"]
        
        # Prepare input data
        input_data = {
            "message": message,
            "metadata": metadata or {},
            "template_id": template_id
        }
        
        context = {
            "agent_key": agent_key,
            "agent_name": agent_name,
            "session_id": supervisor.session_id,
            "timestamp": datetime.now().isoformat()
        }
        
        # PRE-AGENT REVIEW
        if not skip_pre_review:
            should_proceed, modified_input, feedback = await supervisor.hitl_manager.review_before_agent(
                agent_name=agent_name,
                input_data=input_data,
                context=context
            )
            
            if not should_proceed:
                return {
                    "success": False,
                    "agent": agent_name,
                    "error": f"Rejected by human: {feedback}",
                    "hitl_stage": "pre_agent",
                    "hitl_feedback": feedback
                }
            
            if modified_input and isinstance(modified_input, dict):
                message = modified_input.get("message", message)
                if "metadata" in modified_input:
                    metadata = modified_input["metadata"]
                if "template_id" in modified_input:
                    template_id = modified_input["template_id"]
        
        # SEND TO AGENT (use original method)
        result = await supervisor._original_send_task(
            agent_key=agent_key,
            message=message,
            metadata=metadata,
            template_id=template_id
        )
        
        # POST-AGENT REVIEW
        if not skip_post_review:
            output_data = {
                "success": result.get("success", False),
                "message": result.get("message", ""),
                "state": result.get("state", "unknown"),
                "duration": result.get("duration", 0.0)
            }
            
            should_accept, modified_output, feedback = await supervisor.hitl_manager.review_after_agent(
                agent_name=agent_name,
                input_data=input_data,
                output_data=output_data,
                success=result.get("success", False),
                context=context
            )
            
            if not should_accept:
                return {
                    **result,
                    "success": False,
                    "error": f"Output rejected by human: {feedback}",
                    "hitl_stage": "post_agent",
                    "hitl_feedback": feedback
                }
            
            if modified_output and isinstance(modified_output, dict):
                if "message" in modified_output:
                    result["message"] = modified_output["message"]
            
            if feedback:
                result["hitl_feedback"] = feedback
        
        result["hitl_reviewed"] = True
        return result
    
    # Add clarification method
    async def request_clarification(
        agent_name: str,
        questions: list,
        context: Optional[Dict] = None
    ) -> Dict[str, str]:
        """Request clarification from human"""
        answers = await supervisor.hitl_manager.request_clarification(
            agent_name=agent_name,
            questions=questions,
            context=context
        )
        return answers
    
    # Add report method
    def save_hitl_report(output_dir: Optional[Path] = None):
        """Save HITL session report"""
        if output_dir is None:
            output_dir = supervisor.output_dir
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        report_path = output_dir / "hitl_session_report.txt"
        supervisor.hitl_manager.save_session_report(report_path)
        return report_path
    
    # Replace send_task method
    supervisor.send_task = send_task_with_hitl
    supervisor.request_clarification = request_clarification
    supervisor.save_hitl_report = save_hitl_report
    
    logger.info(f"✅ HITL capabilities added to Supervisor")
    logger.info(f"   User ID: {user_id}")
    logger.info(f"   HITL Enabled: {supervisor.hitl_manager.config.enabled}")
    logger.info(f"   Interactive Mode: {supervisor.hitl_manager.config.interactive_mode}")
    
    return supervisor


# Example usage
if __name__ == "__main__":
    import asyncio
    
    print("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    SUPERVISOR HITL INTEGRATION TEST                          ║
╚══════════════════════════════════════════════════════════════════════════════╝

This module adds Human-in-the-Loop capabilities to the Supervisor.

Key Features:
1. Pre-Agent Review: Review inputs before sending to agents
2. Post-Agent Review: Review outputs after agent execution
3. Clarification Requests: Ask users for additional information
4. Memory Integration: Learn from human decisions via mem0
5. Auto-Suggestions: Suggest actions based on past interactions

Usage in supervisor.py:
    from src.agents.hitl_integration import add_hitl_to_supervisor
    
    supervisor = Supervisor()
    supervisor = add_hitl_to_supervisor(supervisor, user_id="my_user")
    
    # Run workflow - HITL will automatically prompt at each agent
    result = await supervisor.run_full_workflow(requirement)

Configuration:
    config = HITLConfig(
        enabled=True,                      # Enable/disable HITL
        interactive_mode=True,             # CLI prompts vs API mode
        auto_approve_threshold=0.9,        # Auto-approve if confidence > 90%
        learn_from_interactions=True,      # Store decisions in mem0
        require_feedback=False             # Always ask for feedback
    )
    """)
