"""
Example usage of Ollama Local Serve.

This script demonstrates how to use the Ollama Local Serve library to:
1. Start an Ollama service on the network
2. Perform health checks
3. Create a LangChain client
4. Use the client for LLM inference
5. Properly shut down the service
"""

import asyncio
import logging
from ollama_local_serve import (
    OllamaService,
    NetworkConfig,
    create_langchain_client,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def basic_example():
    """Basic example: Start service, check health, and stop."""
    logger.info("=== Basic Example ===")

    # Create a network configuration for LAN accessibility
    config = NetworkConfig(
        host="0.0.0.0",  # Accessible from any network interface
        port=11434,  # Default Ollama port
        timeout=30,
        max_retries=3,
    )

    # Create and start the service
    service = OllamaService(config)

    try:
        # Start the service
        await service.start()
        logger.info(f"Service started at {service.base_url}")

        # Perform health check
        is_healthy = await service.health_check()
        logger.info(f"Service health check: {'PASSED' if is_healthy else 'FAILED'}")

        # Get available models
        try:
            models = await service.get_models()
            logger.info(f"Available models: {models}")
        except Exception as e:
            logger.warning(f"Could not fetch models: {e}")

    finally:
        # Always stop the service
        await service.stop()
        logger.info("Service stopped")


async def context_manager_example():
    """Example using async context manager."""
    logger.info("=== Context Manager Example ===")

    config = NetworkConfig(host="0.0.0.0", port=11434)

    # Using async context manager for automatic cleanup
    async with OllamaService(config) as service:
        logger.info(f"Service running at {service.base_url}")

        # Check if service is running
        if service.is_running:
            logger.info("Service is running!")

            # Perform health check
            await service.health_check()
            logger.info("Health check passed!")

    # Service is automatically stopped when exiting the context
    logger.info("Service automatically stopped")


async def langchain_integration_example():
    """Example showing LangChain integration."""
    logger.info("=== LangChain Integration Example ===")

    config = NetworkConfig(host="0.0.0.0", port=11434)

    async with OllamaService(config) as service:
        logger.info(f"Service started at {service.base_url}")

        # Wait for service to be fully ready
        await asyncio.sleep(2)

        try:
            # Create a LangChain client
            llm = create_langchain_client(
                config=config,
                model="llama2",  # Change to your installed model
                temperature=0.7,
            )
            logger.info("LangChain client created")

            # Note: Actual inference requires Ollama to have models installed
            # This is just a demonstration of the API
            logger.info("LangChain client ready for inference")
            logger.info(
                "To use: response = llm.invoke('Your prompt here')"
            )

        except Exception as e:
            logger.warning(f"Could not create LangChain client: {e}")
            logger.info(
                "This is expected if langchain-community is not installed "
                "or no models are available"
            )


async def error_handling_example():
    """Example demonstrating error handling."""
    logger.info("=== Error Handling Example ===")

    config = NetworkConfig(host="0.0.0.0", port=11434)
    service = OllamaService(config)

    try:
        # Try to connect before starting (should fail)
        await service.health_check(retries=1)
    except Exception as e:
        logger.info(f"Expected error (service not started): {e.__class__.__name__}")

    try:
        # Start the service
        await service.start()

        # This should succeed
        await service.health_check()
        logger.info("Health check succeeded after starting service")

    except Exception as e:
        logger.error(f"Error during service operation: {e}")
    finally:
        await service.stop()


async def network_accessible_example():
    """Example for setting up network-accessible service."""
    logger.info("=== Network Accessible Example ===")

    # Configuration for LAN accessibility
    config = NetworkConfig(
        host="0.0.0.0",  # Listen on all network interfaces
        port=11434,
        timeout=30,
    )

    service = OllamaService(config)

    try:
        await service.start()

        # Show connection information
        logger.info(f"Service is accessible at:")
        logger.info(f"  - Localhost: http://localhost:{config.port}")
        logger.info(f"  - LAN: http://<your-ip-address>:{config.port}")
        logger.info(f"  - Base URL: {service.base_url}")

        # Demonstrate creating a client that could connect from another machine
        logger.info("\nClients on the same network can connect using:")
        logger.info(
            f"  llm = create_langchain_client("
            f"base_url='http://<server-ip>:{config.port}')"
        )

        # Keep service running for a bit
        await asyncio.sleep(2)

    finally:
        await service.stop()


async def main():
    """Run all examples."""
    examples = [
        ("Basic Example", basic_example),
        ("Context Manager Example", context_manager_example),
        ("LangChain Integration Example", langchain_integration_example),
        ("Error Handling Example", error_handling_example),
        ("Network Accessible Example", network_accessible_example),
    ]

    for name, example_func in examples:
        try:
            logger.info(f"\n{'=' * 60}")
            logger.info(f"Running: {name}")
            logger.info(f"{'=' * 60}\n")
            await example_func()
            await asyncio.sleep(1)  # Brief pause between examples
        except Exception as e:
            logger.error(f"Error in {name}: {e}", exc_info=True)
        finally:
            logger.info(f"\nCompleted: {name}\n")

    logger.info("\n" + "=" * 60)
    logger.info("All examples completed!")
    logger.info("=" * 60)


if __name__ == "__main__":
    # Note: These examples assume Ollama is installed on the system
    # Install Ollama from: https://ollama.ai
    logger.info("Ollama Local Serve - Example Usage")
    logger.info("=" * 60)
    logger.info("Prerequisites:")
    logger.info("  1. Ollama must be installed on your system")
    logger.info("  2. Run: pip install -r requirements.txt")
    logger.info("=" * 60 + "\n")

    asyncio.run(main())
