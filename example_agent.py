import asyncio
import os
from llama_stack.apis.agents import AgentTurnCreateRequest, AgentConfig, ToolDefinition, BuiltinTool, Turn, UserMessage, CompletionMessage, Role
from llama_stack.apis.inference import InferenceAPI, SamplingParams, ChatCompletionResponseEventType, CompletionMessage, StopReason, Message
from llama_stack.providers.impls.meta_reference.agents.agent_instance import ChatAgent
from llama_stack.providers.impls.meta_reference.agents.tools.builtin import SearchEngineType, SearchToolDefinition
from llama_stack.providers.utils.kvstore import InmemoryKVStoreImpl
from llama_stack.apis.memory import MemoryAPI
from llama_stack.apis.memory_banks import MemoryBanksAPI
from llama_stack.apis.safety import SafetyAPI


# Dummy API implementations (replace with your actual APIs)
class DummyInferenceAPI(InferenceAPI):
    async def chat_completion(self, model, messages, tools=None, tool_prompt_format=None, stream=False, sampling_params=None):
        # Simulate a response that suggests using a tool
        yield ChatCompletionResponseEventType.start
        yield ChatCompletionResponseEventType.delta(CompletionMessage(content="I need to search for 'Llama Stack'"))
        yield ChatCompletionResponseEventType.complete

class DummyMemoryAPI(MemoryAPI):
    async def query_documents(self, bank_id, query, params):
        return []

class DummyMemoryBanksAPI(MemoryBanksAPI):
    async def register_memory_bank(self, memory_bank):
        pass

class DummySafetyAPI(SafetyAPI):
    async def run_shield(self, messages, shield_name):
        return []


async def main():
    # Agent Configuration
    agent_config = AgentConfig(
        model="dummy_model",  # Replace with your actual model
        tools=[
            SearchToolDefinition(
                type=BuiltinTool.brave_search.value,
                api_key="YOUR_BRAVE_SEARCH_API_KEY",  # Replace with your actual API key
                engine=SearchEngineType.brave,
            ),
        ],
        tool_prompt_format="Use the tool {tool_name} to answer the question.",
        tool_choice="required",
        sampling_params=SamplingParams(),
        instructions="You are a helpful assistant.",
    )

    # Initialize APIs
    inference_api = DummyInferenceAPI()
    memory_api = DummyMemoryAPI()
    memory_banks_api = DummyMemoryBanksAPI()
    safety_api = DummySafetyAPI()
    persistence_store = InmemoryKVStoreImpl()

    # Create the agent
    agent = ChatAgent(
        agent_id="example_agent",
        agent_config=agent_config,
        inference_api=inference_api,
        memory_api=memory_api,
        memory_banks_api=memory_banks_api,
        safety_api=safety_api,
        persistence_store=persistence_store,
    )

    # Create a session
    session_id = await agent.create_session("example_session")

    # Send a user message
    request = AgentTurnCreateRequest(
        session_id=session_id,
        messages=[UserMessage(content="Tell me about Llama Stack.")],
        stream=True,
    )

    # Execute the turn and process the stream
    async for chunk in agent.create_and_execute_turn(request):
        print(chunk)

if __name__ == "__main__":
    asyncio.run(main())

