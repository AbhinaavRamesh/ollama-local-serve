"""
LangGraph ReAct Agent Example with Ollama Local Serve.

This script demonstrates how to use the Ollama Local Serve API with LangGraph's
prebuilt ReAct agent. The ReAct (Reasoning + Acting) agent combines reasoning
and tool use to solve complex problems.

Prerequisites:
    pip install ollama-local-serve[langchain]
    pip install langgraph
    pip install langchain-community
    pip install tavily-python  # Optional: for web search tool
"""

import asyncio
import logging

from ollama_local_serve import NetworkConfig, OllamaService, create_langchain_chat_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def setup_tools():
    """
    Set up tools for the ReAct agent.

    These are example tools that the agent can use to solve problems.
    You can add more tools based on your needs.
    """
    from langchain_core.tools import tool

    @tool
    def multiply(a: float, b: float) -> float:
        """Multiply two numbers together."""
        return a * b

    @tool
    def add(a: float, b: float) -> float:
        """Add two numbers together."""
        return a + b

    @tool
    def cube(x: float) -> float:
        """Calculate the cube (third power) of a number."""
        return x**3

    @tool
    def square(x: float) -> float:
        """Calculate the square (second power) of a number."""
        return x**2

    @tool
    def get_word_length(word: str) -> int:
        """Get the length of a word."""
        return len(word)

    return [multiply, add, cube, square, get_word_length]


async def create_react_agent_example():
    """
    Create and use a LangGraph ReAct agent with Ollama.

    This example demonstrates:
    1. Starting an Ollama service
    2. Creating a LangChain chat client
    3. Setting up tools for the agent
    4. Creating a ReAct agent with LangGraph
    5. Running queries through the agent
    """
    logger.info("=== LangGraph ReAct Agent Example ===")

    # Configure Ollama service
    config = NetworkConfig(
        host="0.0.0.0",
        port=11434,
        timeout=120,  # Longer timeout for LLM operations
        max_retries=3,
    )

    # Start the Ollama service
    async with OllamaService(config) as service:
        logger.info(f"Ollama service started at {service.base_url}")

        try:
            # Wait for service to be ready
            await asyncio.sleep(2)

            # Create LangChain chat client
            llm = create_langchain_chat_client(
                config=config,
                model="llama3.2",  # Change to your installed model
                temperature=0,  # Lower temperature for more deterministic responses
            )
            logger.info("LangChain chat client created")

            # Set up tools for the agent
            tools = setup_tools()
            logger.info(f"Created {len(tools)} tools for the agent")

            # Import LangGraph's prebuilt ReAct agent creator
            try:
                from langgraph.prebuilt import create_react_agent
            except ImportError:
                logger.error(
                    "langgraph is not installed. " "Install it with: pip install langgraph"
                )
                return

            # Create the ReAct agent
            logger.info("Creating ReAct agent...")
            agent_executor = create_react_agent(llm, tools)
            logger.info("ReAct agent created successfully!")

            # Example queries to demonstrate the agent's capabilities
            queries = [
                "What is 5 cubed?",
                "Calculate (3 + 4) * 2",
                "What is the length of the word 'LangGraph'?",
                "What is 10 squared plus 15?",
            ]

            # Run queries through the agent
            for query in queries:
                logger.info(f"\n{'=' * 60}")
                logger.info(f"Query: {query}")
                logger.info(f"{'=' * 60}")

                try:
                    # Invoke the agent with the query
                    response = await agent_executor.ainvoke({"messages": [("user", query)]})

                    # Extract and display the response
                    messages = response.get("messages", [])
                    if messages:
                        final_message = messages[-1]
                        logger.info(f"Agent Response: {final_message.content}")
                    else:
                        logger.info("No response from agent")

                except Exception as e:
                    logger.error(f"Error processing query: {e}", exc_info=True)

                # Brief pause between queries
                await asyncio.sleep(1)

            logger.info(f"\n{'=' * 60}")
            logger.info("All queries completed!")
            logger.info(f"{'=' * 60}")

        except ImportError as e:
            logger.error(f"Missing dependency: {e}")
            logger.info(
                "\nTo run this example, install required packages:\n"
                "  pip install ollama-local-serve[langchain]\n"
                "  pip install langgraph\n"
                "  pip install langchain-community"
            )
        except Exception as e:
            logger.error(f"Error in ReAct agent example: {e}", exc_info=True)


async def advanced_react_agent_example():
    """
    Advanced example showing agent with more complex tool usage.

    This demonstrates the agent's ability to chain multiple tool calls
    to solve more complex problems.
    """
    logger.info("\n\n=== Advanced ReAct Agent Example ===")

    config = NetworkConfig(
        host="0.0.0.0",
        port=11434,
        timeout=120,
    )

    async with OllamaService(config) as service:
        logger.info(f"Ollama service started at {service.base_url}")

        try:
            await asyncio.sleep(2)

            # Create LangChain chat client
            llm = create_langchain_chat_client(
                config=config,
                model="llama3.2",  # Change to your installed model
                temperature=0,
            )

            # Set up tools
            tools = setup_tools()

            # Import and create agent
            from langgraph.prebuilt import create_react_agent

            agent_executor = create_react_agent(llm, tools)

            # Complex multi-step query
            complex_query = (
                "I have three numbers: 2, 3, and 4. "
                "First cube the first number, then square the second number, "
                "then multiply the third number by 5, "
                "and finally add all three results together. "
                "What is the final answer?"
            )

            logger.info(f"\n{'=' * 60}")
            logger.info(f"Complex Query: {complex_query}")
            logger.info(f"{'=' * 60}")

            try:
                response = await agent_executor.ainvoke({"messages": [("user", complex_query)]})

                messages = response.get("messages", [])
                if messages:
                    # Show all reasoning steps
                    logger.info("\nAgent's Reasoning Process:")
                    for i, msg in enumerate(messages, 1):
                        logger.info(f"\nStep {i}: {msg.type}")
                        logger.info(f"Content: {msg.content[:200]}...")  # Truncate long messages

                    # Show final answer
                    final_message = messages[-1]
                    logger.info(f"\n{'=' * 60}")
                    logger.info(f"Final Answer: {final_message.content}")
                    logger.info(f"{'=' * 60}")

            except Exception as e:
                logger.error(f"Error processing complex query: {e}", exc_info=True)

        except ImportError as e:
            logger.error(f"Missing dependency: {e}")
        except Exception as e:
            logger.error(f"Error in advanced example: {e}", exc_info=True)


async def main():
    """Run all ReAct agent examples."""
    try:
        # Basic ReAct agent example
        await create_react_agent_example()

        # Wait a bit between examples
        await asyncio.sleep(3)

        # Advanced ReAct agent example
        await advanced_react_agent_example()

    except Exception as e:
        logger.error(f"Error in main: {e}", exc_info=True)


if __name__ == "__main__":
    logger.info("LangGraph ReAct Agent with Ollama Local Serve")
    logger.info("=" * 60)
    logger.info("Prerequisites:")
    logger.info("  1. Ollama must be installed on your system")
    logger.info("  2. Install required packages:")
    logger.info("     pip install ollama-local-serve[langchain]")
    logger.info("     pip install langgraph")
    logger.info("     pip install langchain-community")
    logger.info("  3. Pull a model: ollama pull llama3.2")
    logger.info("=" * 60 + "\n")

    asyncio.run(main())
