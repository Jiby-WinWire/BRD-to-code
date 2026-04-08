from langgraph.prebuilt.chat_agent_executor import create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_openai import AzureChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from typing import List, Optional
import os

# Import the base server class
from .a2a_server import BaseA2AServer
from .types import BaseAgentcard, AgentAccess
from a2a.types import AgentSkill, AgentCapabilities

class AgentClass:
    def __init__(
        self,
        agent_name: str,
        tools: List,
        config: dict,
        memory_backend: Optional[MemorySaver] = None,
        prompt: Optional[PromptTemplate] = None,
        a2a_enabled: bool = False,
        a2a_port: int = 10000,
        plugin_type: str = "agent",
        include_query_handler: bool = False,
    ):
        self.agent_name = agent_name
        self.memory = memory_backend or MemorySaver()
        self.tools = tools
        self.config = config or {}
        self.base_prompt = prompt
        self.llm = self._init_llm()
        self.agent = self._create_agent(self.base_prompt)

        if a2a_enabled:
            self._launch_a2a_server(a2a_port, plugin_type, include_query_handler)

    def _init_llm(self):
        return AzureChatOpenAI(
            azure_deployment=self.config["deployment_name"],
            model_name=self.config["model_name"],
            model_version=self.config["model_version"],
            api_key=self.config["api_key"],
            openai_api_version=self.config["api_version"],
            openai_api_type=self.config.get("openai_api_type", "azure"),
            azure_endpoint=self.config["azure_endpoint"],
            temperature=self.config.get("temperature", 0),
        )

    def _create_agent(self, prompt: Optional[PromptTemplate]):
        return create_react_agent(
            model=self.llm,
            tools=self.tools,
            store=self.memory,
            prompt=prompt,
            name=self.agent_name
        )


    def _launch_a2a_server(self, port, host, plugin_type, include_query_handler, agent_card, task_manager, agent_url):
        """Launch A2A server with option for test server"""
        # Check if we're in test mode (can be set via environment variable)
        use_test_server = os.getenv("USE_TEST_SERVER", "false").lower() == "true"
        
        if use_test_server:
            # Use test server implementation without auth
            from agent_base.test_a2a_server import TestA2AServer
            self.a2a_server = TestA2AServer(
                agent_card=agent_card,
                task_manager=task_manager,
                port=port,
                host=host,
                plugin_type=plugin_type,
                include_query_handler=include_query_handler,
                agent_url=agent_url
            )
        else:
            # Use production server with full auth
            from agent_base.a2a_server import BaseA2AServer
            self.a2a_server = BaseA2AServer(
                agent_card=agent_card,
                task_manager=task_manager,
                port=port,
                host=host,
                plugin_type=plugin_type,
                include_query_handler=include_query_handler,
                agent_url=agent_url
            )
        
        return self.a2a_server

    def _build_agent_card(self, name: str, description: str, url: str, skills: List[AgentSkill], capabilities: AgentCapabilities, visibility: AgentAccess) -> BaseAgentcard:
        """
        Constructs the AgentCard using the provided information.
        """
        return BaseAgentcard(
            name=name,
            description=description,
            url=url,
            version="1.0.0",  #  set a default version
            defaultInputModes=["text"],
            defaultOutputModes=["text"],
            skills=skills,
            capabilities=capabilities,
            visibility=visibility
        )

    # def _build_task_manager(self):
    #     # This must implement a handle_task(request) method
    #     # Or you can inject it externally in a real implementation
    #     from your_module.task_manager import SimpleTaskManager
    #     return SimpleTaskManager(agent=self)

    def update_prompt(self, new_prompt: PromptTemplate):
        self.base_prompt = new_prompt
        self.agent = self._create_agent(new_prompt)

    def get_agent(self):
        return self.agent