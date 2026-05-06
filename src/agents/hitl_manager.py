"""
Human-in-the-Loop (HITL) Manager
Manages human intervention at each agent call for review, validation, and clarification
Integrates with mem0 to learn from human decisions and avoid repetitive questions
"""

import sys
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from mem0_manager import Mem0Manager, create_memory_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HITLStage(Enum):
    """Stages where human intervention can occur"""
    PRE_AGENT = "pre_agent"  # Before sending to agent
    POST_AGENT = "post_agent"  # After receiving from agent
    CLARIFICATION = "clarification"  # When clarification is needed
    VALIDATION = "validation"  # For validating results


class HITLActionType(Enum):
    """Types of actions humans can take"""
    APPROVE = "approve"  # Proceed as-is
    MODIFY = "modify"  # Modify input/output
    REJECT = "reject"  # Reject and stop
    SKIP = "skip"  # Skip this agent
    RETRY = "retry"  # Retry with different input
    CLARIFY = "clarify"  # Need more information


@dataclass
class HITLPrompt:
    """Data class for prompts to humans"""
    stage: HITLStage
    agent_name: str
    title: str
    message: str
    data: Dict[str, Any]
    options: List[str]
    allow_modification: bool = True
    allow_skip: bool = False
    default_action: Optional[str] = None
    context: Optional[Dict[str, Any]] = None
    suggested_answer: Optional[str] = None  # From mem0 learning
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass
class HITLResponse:
    """Data class for human responses"""
    action: HITLActionType
    modified_data: Optional[Dict[str, Any]] = None
    feedback: Optional[str] = None
    clarifications: Optional[Dict[str, str]] = None
    skip_reason: Optional[str] = None
    timestamp: str = None
    confidence: float = 1.0  # 0.0 to 1.0
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass
class HITLConfig:
    """Configuration for HITL behavior"""
    enabled: bool = True
    auto_approve_threshold: float = 0.9  # Auto-approve if confidence > threshold
    learn_from_interactions: bool = True  # Store decisions in mem0
    batch_mode: bool = False  # Review multiple items at once
    require_feedback: bool = False  # Always ask for feedback
    timeout_seconds: int = 300  # Timeout for human response (5 min)
    skip_validation_steps: bool = False  # Skip validation agent reviews
    interactive_mode: bool = True  # Interactive CLI prompts vs API mode
    
    # Agent-specific settings
    agent_settings: Dict[str, Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.agent_settings is None:
            self.agent_settings = {}


class HITLManager:
    """
    Human-in-the-Loop Manager
    Manages human intervention at each step of the workflow with mem0 integration
    """
    
    def __init__(
        self,
        user_id: str = "default_user",
        session_id: Optional[str] = None,
        config: Optional[HITLConfig] = None
    ):
        """
        Initialize HITL Manager
        
        Args:
            user_id: User identifier for personalized memory
            session_id: Session identifier
            config: HITL configuration
        """
        self.user_id = user_id
        self.session_id = session_id or f"hitl-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.config = config or HITLConfig()
        
        # Initialize memory manager for learning
        if self.config.learn_from_interactions:
            self.memory = create_memory_manager(user_id=user_id)
            self.memory.set_session(self.session_id)
            logger.info(f"HITL Manager initialized with memory for user: {user_id}")
        else:
            self.memory = None
            logger.info("HITL Manager initialized without memory")
        
        # Track interactions in current session
        self.interactions: List[Dict[str, Any]] = []
        self.decisions_made: Dict[str, HITLResponse] = {}
    
    def _get_similar_past_interactions(
        self,
        agent_name: str,
        stage: HITLStage,
        current_data: Dict[str, Any],
        limit: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Query mem0 for similar past interactions to learn from
        
        Args:
            agent_name: Name of the agent
            stage: Current stage
            current_data: Current data being processed
            limit: Maximum number of similar interactions to retrieve
            
        Returns:
            List of similar past interactions
        """
        if not self.memory:
            return []
        
        try:
            # Create a search query based on agent and data
            query_parts = [
                f"Agent: {agent_name}",
                f"Stage: {stage.value}",
            ]
            
            # Add key data points to query
            if "requirement" in current_data:
                query_parts.append(f"Requirement: {str(current_data['requirement'])[:200]}")
            elif "message" in current_data:
                query_parts.append(f"Message: {str(current_data['message'])[:200]}")
            
            query = " | ".join(query_parts)
            
            # Search for similar interactions
            memories = self.memory.get_relevant_memories(
                query=query,
                limit=limit,
                agent_filter=f"hitl_{agent_name}"
            )
            
            return memories
        except Exception as e:
            logger.warning(f"Could not retrieve similar interactions: {e}")
            return []
    
    def _suggest_action_from_history(
        self,
        agent_name: str,
        stage: HITLStage,
        current_data: Dict[str, Any]
    ) -> Tuple[Optional[HITLActionType], float, Optional[str]]:
        """
        Suggest an action based on past interactions
        
        Args:
            agent_name: Name of the agent
            stage: Current stage
            current_data: Current data being processed
            
        Returns:
            Tuple of (suggested_action, confidence, explanation)
        """
        similar = self._get_similar_past_interactions(agent_name, stage, current_data, limit=5)
        
        if not similar:
            return None, 0.0, None
        
        # Analyze past decisions
        action_counts = {}
        total_actions = 0
        
        for mem in similar:
            metadata = mem.get("metadata", {})
            action = metadata.get("action")
            
            if action:
                action_counts[action] = action_counts.get(action, 0) + 1
                total_actions += 1
        
        if not action_counts:
            return None, 0.0, None
        
        # Find most common action
        most_common_action = max(action_counts.items(), key=lambda x: x[1])
        action_name, count = most_common_action
        
        confidence = count / total_actions if total_actions > 0 else 0.0
        
        explanation = (
            f"In {count}/{total_actions} similar cases, you chose to '{action_name}'. "
            f"(Confidence: {confidence:.1%})"
        )
        
        try:
            suggested_action = HITLActionType(action_name)
            return suggested_action, confidence, explanation
        except ValueError:
            return None, 0.0, None
    
    def _store_interaction(
        self,
        prompt: HITLPrompt,
        response: HITLResponse
    ):
        """
        Store interaction in mem0 for future learning
        
        Args:
            prompt: The prompt shown to human
            response: The human's response
        """
        if not self.memory:
            return
        
        try:
            # Create a memory of this interaction
            content = f"""HITL Interaction:
Agent: {prompt.agent_name}
Stage: {prompt.stage.value}
Title: {prompt.title}
Action Taken: {response.action.value}
Feedback: {response.feedback or 'None'}
Confidence: {response.confidence:.2f}
"""
            
            metadata = {
                "type": "hitl_interaction",
                "agent": f"hitl_{prompt.agent_name}",
                "stage": prompt.stage.value,
                "action": response.action.value,
                "confidence": response.confidence,
                "timestamp": response.timestamp
            }
            
            # Add clarifications if present
            if response.clarifications:
                metadata["clarifications"] = response.clarifications
            
            self.memory.add_conversation(
                role="user",
                content=content,
                agent_name=f"hitl_{prompt.agent_name}",
                metadata=metadata
            )
            
            logger.info(f"Stored HITL interaction for {prompt.agent_name} in mem0")
            
        except Exception as e:
            logger.error(f"Failed to store HITL interaction: {e}")
    
    def _format_data_for_display(self, data: Any, max_length: int = 500) -> str:
        """
        Format data for human-readable display
        
        Args:
            data: Data to format
            max_length: Maximum length of formatted string
            
        Returns:
            Formatted string
        """
        if isinstance(data, dict):
            formatted = json.dumps(data, indent=2)
        elif isinstance(data, str):
            formatted = data
        else:
            formatted = str(data)
        
        if len(formatted) > max_length:
            formatted = formatted[:max_length] + f"\n... ({len(formatted) - max_length} more characters)"
        
        return formatted
    
    async def request_human_input(
        self,
        prompt: HITLPrompt,
        auto_suggest: bool = True
    ) -> HITLResponse:
        """
        Request input from human with optional AI suggestions
        
        Args:
            prompt: Prompt to show to human
            auto_suggest: Whether to suggest actions based on history
            
        Returns:
            Human's response
        """
        # Check if HITL is enabled
        if not self.config.enabled:
            return HITLResponse(
                action=HITLActionType.APPROVE,
                feedback="HITL disabled - auto-approved"
            )
        
        # Get suggestions from past interactions
        suggested_action = None
        confidence = 0.0
        suggestion_explanation = None
        
        if auto_suggest and self.memory:
            suggested_action, confidence, suggestion_explanation = self._suggest_action_from_history(
                prompt.agent_name,
                prompt.stage,
                prompt.data
            )
            
            # Auto-approve if confidence is high enough
            if suggested_action and confidence >= self.config.auto_approve_threshold:
                logger.info(
                    f"Auto-approving {prompt.agent_name} based on history "
                    f"(confidence: {confidence:.1%})"
                )
                response = HITLResponse(
                    action=suggested_action,
                    feedback=f"Auto-approved based on history: {suggestion_explanation}",
                    confidence=confidence
                )
                self._store_interaction(prompt, response)
                return response
        
        # Interactive mode: Show prompt and get input
        if self.config.interactive_mode:
            return await self._interactive_prompt(
                prompt,
                suggested_action,
                confidence,
                suggestion_explanation
            )
        else:
            # API mode: Would integrate with a UI/API
            # For now, auto-approve in API mode
            return HITLResponse(
                action=HITLActionType.APPROVE,
                feedback="API mode - auto-approved"
            )
    
    async def _interactive_prompt(
        self,
        prompt: HITLPrompt,
        suggested_action: Optional[HITLActionType],
        confidence: float,
        suggestion_explanation: Optional[str]
    ) -> HITLResponse:
        """
        Show interactive prompt to user via CLI
        
        Args:
            prompt: Prompt to show
            suggested_action: Suggested action from history
            confidence: Confidence in suggestion
            suggestion_explanation: Explanation of suggestion
            
        Returns:
            User's response
        """
        print("\n" + "="*80)
        print(f"🔔 HUMAN INPUT REQUIRED - {prompt.title}")
        print("="*80)
        print(f"Agent: {prompt.agent_name}")
        print(f"Stage: {prompt.stage.value}")
        print(f"Time: {prompt.timestamp}")
        print("-"*80)
        print(f"\n{prompt.message}\n")
        
        # Show data
        print("📋 Data:")
        print(self._format_data_for_display(prompt.data))
        print()
        
        # Show suggestion if available
        if suggested_action and suggestion_explanation:
            print(f"💡 AI Suggestion: {suggested_action.value.upper()} (Confidence: {confidence:.1%})")
            print(f"   {suggestion_explanation}")
            print()
        
        # Show options
        print("Available Actions:")
        for i, option in enumerate(prompt.options, 1):
            marker = "→" if suggested_action and option.lower() == suggested_action.value else " "
            print(f"  {marker} {i}. {option}")
        
        if prompt.allow_modification:
            print(f"  {len(prompt.options) + 1}. Modify data")
        
        if prompt.allow_skip:
            print(f"  {len(prompt.options) + 2}. Skip this agent")
        
        print()
        
        # Get user input
        while True:
            try:
                user_input = input("Your choice (number or action name): ").strip()
                
                # Parse input
                if user_input.isdigit():
                    choice = int(user_input)
                    if 1 <= choice <= len(prompt.options):
                        action_name = prompt.options[choice - 1].lower()
                        action = HITLActionType(action_name)
                        break
                    elif choice == len(prompt.options) + 1 and prompt.allow_modification:
                        action = HITLActionType.MODIFY
                        break
                    elif choice == len(prompt.options) + 2 and prompt.allow_skip:
                        action = HITLActionType.SKIP
                        break
                else:
                    # Try to match action name
                    try:
                        action = HITLActionType(user_input.lower())
                        break
                    except ValueError:
                        pass
                
                print("❌ Invalid choice. Please try again.")
            except KeyboardInterrupt:
                print("\n⚠️ Interrupted by user")
                action = HITLActionType.REJECT
                break
            except Exception as e:
                print(f"❌ Error: {e}")
        
        # Handle modification
        modified_data = None
        if action == HITLActionType.MODIFY:
            print("\n📝 Modify data (enter JSON or text):")
            print("Current data:")
            print(json.dumps(prompt.data, indent=2))
            print("\nEnter modified data (or 'cancel' to abort):")
            
            modified_input = input("> ").strip()
            if modified_input.lower() != 'cancel':
                try:
                    modified_data = json.loads(modified_input)
                except json.JSONDecodeError:
                    # Treat as plain text
                    modified_data = {"modified_content": modified_input}
        
        # Get feedback
        feedback = None
        if self.config.require_feedback or action in [HITLActionType.REJECT, HITLActionType.SKIP]:
            print("\n💬 Provide feedback (optional, press Enter to skip):")
            feedback = input("> ").strip() or None
        
        # Get clarifications if needed
        clarifications = None
        if action == HITLActionType.CLARIFY:
            print("\n❓ What information do you need? (Enter key-value pairs, 'done' when finished)")
            clarifications = {}
            while True:
                key = input("Key (or 'done'): ").strip()
                if key.lower() == 'done':
                    break
                value = input(f"Value for '{key}': ").strip()
                clarifications[key] = value
        
        # Create response
        response = HITLResponse(
            action=action,
            modified_data=modified_data,
            feedback=feedback,
            clarifications=clarifications,
            confidence=1.0  # User-provided, full confidence
        )
        
        # Store interaction
        self._store_interaction(prompt, response)
        
        # Track in session
        self.interactions.append({
            "prompt": asdict(prompt),
            "response": asdict(response)
        })
        self.decisions_made[f"{prompt.agent_name}_{prompt.stage.value}"] = response
        
        print("\n✅ Response recorded")
        print("="*80 + "\n")
        
        return response
    
    async def review_before_agent(
        self,
        agent_name: str,
        input_data: Any,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Any, Optional[str]]:
        """
        Review and potentially modify input before sending to agent
        
        Args:
            agent_name: Name of the agent
            input_data: Data to be sent to agent
            context: Additional context
            
        Returns:
            Tuple of (should_proceed, modified_input, feedback)
        """
        prompt = HITLPrompt(
            stage=HITLStage.PRE_AGENT,
            agent_name=agent_name,
            title=f"Review Input for {agent_name}",
            message=f"About to send the following input to {agent_name}. Please review:",
            data={"input": input_data, "context": context or {}},
            options=["approve", "modify", "reject", "skip"],
            allow_modification=True,
            allow_skip=True,
            context=context
        )
        
        response = await self.request_human_input(prompt)
        
        if response.action == HITLActionType.APPROVE:
            return True, input_data, response.feedback
        elif response.action == HITLActionType.MODIFY:
            modified_input = response.modified_data.get("modified_content", input_data)
            return True, modified_input, response.feedback
        elif response.action == HITLActionType.SKIP:
            return False, None, f"Skipped by user: {response.skip_reason or response.feedback}"
        else:  # REJECT
            return False, None, f"Rejected by user: {response.feedback}"
    
    async def review_after_agent(
        self,
        agent_name: str,
        input_data: Any,
        output_data: Any,
        success: bool,
        context: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, Any, Optional[str]]:
        """
        Review agent output and decide whether to accept, retry, or reject
        
        Args:
            agent_name: Name of the agent
            input_data: Input that was sent to agent
            output_data: Output received from agent
            success: Whether agent execution was successful
            context: Additional context
            
        Returns:
            Tuple of (should_accept, modified_output, feedback)
        """
        status_emoji = "✅" if success else "❌"
        
        prompt = HITLPrompt(
            stage=HITLStage.POST_AGENT,
            agent_name=agent_name,
            title=f"Review Output from {agent_name} {status_emoji}",
            message=f"Agent {agent_name} has completed. Please review the output:",
            data={
                "input": input_data,
                "output": output_data,
                "success": success,
                "context": context or {}
            },
            options=["approve", "modify", "reject", "retry"],
            allow_modification=True,
            allow_skip=False,
            context=context
        )
        
        response = await self.request_human_input(prompt)
        
        if response.action == HITLActionType.APPROVE:
            return True, output_data, response.feedback
        elif response.action == HITLActionType.MODIFY:
            modified_output = response.modified_data.get("modified_content", output_data)
            return True, modified_output, response.feedback
        elif response.action == HITLActionType.RETRY:
            return False, None, f"Retry requested: {response.feedback}"
        else:  # REJECT
            return False, None, f"Rejected by user: {response.feedback}"
    
    async def request_clarification(
        self,
        agent_name: str,
        questions: List[str],
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """
        Request clarification from human when instructions are unclear
        
        Args:
            agent_name: Name of the agent requesting clarification
            questions: List of questions to ask
            context: Additional context
            
        Returns:
            Dictionary of question -> answer pairs
        """
        prompt = HITLPrompt(
            stage=HITLStage.CLARIFICATION,
            agent_name=agent_name,
            title=f"Clarification Needed for {agent_name}",
            message="The agent needs clarification on the following points:",
            data={"questions": questions, "context": context or {}},
            options=["clarify"],
            allow_modification=False,
            allow_skip=False,
            context=context
        )
        
        response = await self.request_human_input(prompt)
        
        return response.clarifications or {}
    
    def get_session_summary(self) -> Dict[str, Any]:
        """
        Get summary of all HITL interactions in current session
        
        Returns:
            Summary dictionary
        """
        action_counts = {}
        agent_interactions = {}
        
        for interaction in self.interactions:
            action = interaction["response"]["action"]
            agent = interaction["prompt"]["agent_name"]
            
            action_counts[action] = action_counts.get(action, 0) + 1
            
            if agent not in agent_interactions:
                agent_interactions[agent] = []
            agent_interactions[agent].append(interaction)
        
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "total_interactions": len(self.interactions),
            "action_counts": action_counts,
            "agent_interactions": agent_interactions,
            "config": asdict(self.config)
        }
    
    def save_session_report(self, output_path: Path):
        """
        Save detailed session report to file
        
        Args:
            output_path: Path to save report
        """
        summary = self.get_session_summary()
        
        report_lines = []
        report_lines.append("="*80)
        report_lines.append(f"HUMAN-IN-THE-LOOP SESSION REPORT")
        report_lines.append("="*80)
        report_lines.append(f"Session ID: {summary['session_id']}")
        report_lines.append(f"User ID: {summary['user_id']}")
        report_lines.append(f"Total Interactions: {summary['total_interactions']}")
        report_lines.append("")
        
        report_lines.append("Action Summary:")
        for action, count in summary['action_counts'].items():
            report_lines.append(f"  - {action}: {count}")
        report_lines.append("")
        
        report_lines.append("Agent-by-Agent Breakdown:")
        for agent, interactions in summary['agent_interactions'].items():
            report_lines.append(f"\n{agent}:")
            for i, interaction in enumerate(interactions, 1):
                prompt = interaction['prompt']
                response = interaction['response']
                report_lines.append(f"  Interaction {i}:")
                report_lines.append(f"    Stage: {prompt['stage']}")
                report_lines.append(f"    Action: {response['action']}")
                report_lines.append(f"    Feedback: {response['feedback'] or 'None'}")
        
        report_text = "\n".join(report_lines)
        
        output_path.write_text(report_text, encoding='utf-8')
        logger.info(f"Session report saved to: {output_path}")


def create_hitl_manager(
    user_id: str = "default_user",
    session_id: Optional[str] = None,
    config: Optional[HITLConfig] = None
) -> HITLManager:
    """
    Factory function to create HITL Manager
    
    Args:
        user_id: User identifier
        session_id: Session identifier
        config: HITL configuration
        
    Returns:
        Initialized HITLManager
    """
    return HITLManager(user_id=user_id, session_id=session_id, config=config)


# Example usage
if __name__ == "__main__":
    import asyncio
    
    async def test_hitl():
        """Test HITL Manager"""
        print("\n🧪 Testing HITL Manager\n")
        
        # Create manager
        config = HITLConfig(
            enabled=True,
            interactive_mode=True,
            learn_from_interactions=True
        )
        
        manager = create_hitl_manager(
            user_id="test_user",
            config=config
        )
        
        # Test pre-agent review
        print("Testing pre-agent review...")
        should_proceed, modified_input, feedback = await manager.review_before_agent(
            agent_name="BRD Generator",
            input_data="Create a todo list application",
            context={"language": "python"}
        )
        
        print(f"Result: proceed={should_proceed}, feedback={feedback}")
        
        # Get session summary
        summary = manager.get_session_summary()
        print(f"\nSession Summary:")
        print(f"Total interactions: {summary['total_interactions']}")
        print(f"Actions: {summary['action_counts']}")
    
    # Run test
    asyncio.run(test_hitl())
