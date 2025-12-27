"""
LangChain integration for Ollama Local Serve.
"""

import logging
from typing import Any

from ollama_local_serve.config import NetworkConfig
from ollama_local_serve.exceptions import ConnectionError

logger = logging.getLogger(__name__)


def create_langchain_client(
    base_url: str | None = None,
    config: NetworkConfig | None = None,
    model: str = "llama2",
    **kwargs: Any,
) -> Any:
    """
    Create a LangChain Ollama client for remote LLM access.

    This function creates a LangChain-compatible client that connects to a
    remote Ollama service, allowing you to use Ollama models in LangChain pipelines.

    Args:
        base_url: The base URL of the Ollama service. If None, uses config.
        config: NetworkConfig object. If None and base_url is None, uses default config.
        model: The model name to use. Default is "llama2".
        **kwargs: Additional keyword arguments to pass to the Ollama client.

    Returns:
        A LangChain Ollama client instance.

    Raises:
        ConnectionError: If unable to create the client.
        ImportError: If langchain-community is not installed.

    Example:
        ```python
        from ollama_local_serve import create_langchain_client, NetworkConfig

        # Using NetworkConfig
        config = NetworkConfig(host="192.168.1.100", port=11434)
        llm = create_langchain_client(config=config, model="llama2")

        # Using direct URL
        llm = create_langchain_client(
            base_url="http://192.168.1.100:11434",
            model="mistral"
        )

        # Use with LangChain
        response = llm.invoke("What is the meaning of life?")
        print(response)
        ```
    """
    try:
        from langchain_community.llms import Ollama
    except ImportError:
        raise ImportError(
            "langchain-community is required for LangChain integration. "
            "Install it with: pip install langchain-community"
        )

    # Determine the base URL
    if base_url is None:
        if config is None:
            config = NetworkConfig()
        base_url = config.get_connection_url(localhost_fallback=True)

    logger.info(f"Creating LangChain Ollama client for {base_url} with model {model}")

    try:
        # Create the Ollama client
        client = Ollama(
            base_url=base_url,
            model=model,
            **kwargs,
        )
        logger.info("LangChain Ollama client created successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to create LangChain client: {e}")
        raise ConnectionError(f"Failed to create LangChain client: {e}")


def create_langchain_chat_client(
    base_url: str | None = None,
    config: NetworkConfig | None = None,
    model: str = "llama2",
    **kwargs: Any,
) -> Any:
    """
    Create a LangChain Chat Ollama client for conversational AI.

    This function creates a chat-specific LangChain client that supports
    conversational interfaces with message history.

    Args:
        base_url: The base URL of the Ollama service. If None, uses config.
        config: NetworkConfig object. If None and base_url is None, uses default config.
        model: The model name to use. Default is "llama2".
        **kwargs: Additional keyword arguments to pass to the ChatOllama client.

    Returns:
        A LangChain ChatOllama client instance.

    Raises:
        ConnectionError: If unable to create the client.
        ImportError: If langchain-community is not installed.

    Example:
        ```python
        from ollama_local_serve import create_langchain_chat_client
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = create_langchain_chat_client(
            base_url="http://192.168.1.100:11434",
            model="llama2"
        )

        messages = [
            SystemMessage(content="You are a helpful assistant."),
            HumanMessage(content="Tell me a joke."),
        ]
        response = llm.invoke(messages)
        print(response)
        ```
    """
    try:
        from langchain_ollama import ChatOllama
    except ImportError:
        # Fallback to community version for backwards compatibility
        try:
            from langchain_community.chat_models import ChatOllama
        except ImportError:
            raise ImportError(
                "langchain-ollama is required for LangChain integration. "
                "Install it with: pip install langchain-ollama"
            )

    # Determine the base URL
    if base_url is None:
        if config is None:
            config = NetworkConfig()
        base_url = config.get_connection_url(localhost_fallback=True)

    logger.info(f"Creating LangChain ChatOllama client for {base_url} with model {model}")

    try:
        # Create the ChatOllama client
        client = ChatOllama(
            base_url=base_url,
            model=model,
            **kwargs,
        )
        logger.info("LangChain ChatOllama client created successfully")
        return client
    except Exception as e:
        logger.error(f"Failed to create LangChain chat client: {e}")
        raise ConnectionError(f"Failed to create LangChain chat client: {e}")


async def test_langchain_connection(
    client: Any,
    test_prompt: str = "Hello, world!",
) -> bool:
    """
    Test a LangChain client connection by sending a simple prompt.

    Args:
        client: The LangChain client to test.
        test_prompt: The test prompt to send. Default is "Hello, world!".

    Returns:
        True if connection test succeeds, False otherwise.
    """
    try:
        logger.info(f"Testing LangChain connection with prompt: {test_prompt}")
        response = client.invoke(test_prompt)
        logger.info(f"Connection test successful. Response: {response[:100]}...")
        return True
    except Exception as e:
        logger.error(f"Connection test failed: {e}")
        return False
