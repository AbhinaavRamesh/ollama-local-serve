#!/usr/bin/env python3
"""
Test Suite for LangGraph ReAct Agent Example.

This script tests the langgraph_react_agent_example.py functionality:
1. Unit tests for individual tools (no LLM required)
2. Import and availability tests
3. Integration tests (requires Ollama running)

Usage:
    # Run all unit tests (no Ollama required)
    python test_langgraph_react_agent.py

    # Run integration tests (requires Ollama running)
    python test_langgraph_react_agent.py --integration

    # Run with verbose output
    python test_langgraph_react_agent.py -v
"""

import asyncio
import argparse
import sys
from datetime import datetime


class TestResult:
    """Simple test result tracking."""

    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.results = []

    def add_pass(self, name: str, message: str = ""):
        self.passed += 1
        self.results.append(("PASS", name, message))
        print(f"  [PASS] {name}")

    def add_fail(self, name: str, message: str = ""):
        self.failed += 1
        self.results.append(("FAIL", name, message))
        print(f"  [FAIL] {name}: {message}")

    def add_skip(self, name: str, message: str = ""):
        self.skipped += 1
        self.results.append(("SKIP", name, message))
        print(f"  [SKIP] {name}: {message}")

    def summary(self):
        total = self.passed + self.failed + self.skipped
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        print(f"Total: {total} | Passed: {self.passed} | Failed: {self.failed} | Skipped: {self.skipped}")
        if self.failed > 0:
            print("\nFailed tests:")
            for status, name, msg in self.results:
                if status == "FAIL":
                    print(f"  - {name}: {msg}")
        return self.failed == 0


def test_tool_imports(results: TestResult):
    """Test that tool setup function can be imported and called."""
    print("\n--- Testing Tool Imports ---")

    try:
        from langgraph_react_agent_example import setup_tools

        results.add_pass("Import setup_tools")
    except ImportError as e:
        results.add_fail("Import setup_tools", str(e))
        return

    try:
        tools = setup_tools()
        if len(tools) == 5:
            results.add_pass(f"setup_tools() returns 5 tools")
        else:
            results.add_fail("setup_tools() tool count", f"Expected 5, got {len(tools)}")
    except Exception as e:
        results.add_fail("setup_tools() execution", str(e))


def test_multiply_tool(results: TestResult):
    """Test the multiply tool."""
    print("\n--- Testing Multiply Tool ---")

    try:
        from langgraph_react_agent_example import setup_tools

        tools = setup_tools()
        multiply = next((t for t in tools if t.name == "multiply"), None)

        if multiply is None:
            results.add_fail("Find multiply tool", "Tool not found")
            return

        # Test cases
        test_cases = [
            ((2, 3), 6),
            ((0, 5), 0),
            ((-2, 3), -6),
            ((2.5, 4), 10.0),
        ]

        for args, expected in test_cases:
            result = multiply.invoke({"a": args[0], "b": args[1]})
            if result == expected:
                results.add_pass(f"multiply({args[0]}, {args[1]}) = {expected}")
            else:
                results.add_fail(f"multiply({args[0]}, {args[1]})", f"Expected {expected}, got {result}")

    except Exception as e:
        results.add_fail("Multiply tool tests", str(e))


def test_add_tool(results: TestResult):
    """Test the add tool."""
    print("\n--- Testing Add Tool ---")

    try:
        from langgraph_react_agent_example import setup_tools

        tools = setup_tools()
        add = next((t for t in tools if t.name == "add"), None)

        if add is None:
            results.add_fail("Find add tool", "Tool not found")
            return

        test_cases = [
            ((2, 3), 5),
            ((0, 0), 0),
            ((-2, 3), 1),
            ((2.5, 2.5), 5.0),
        ]

        for args, expected in test_cases:
            result = add.invoke({"a": args[0], "b": args[1]})
            if result == expected:
                results.add_pass(f"add({args[0]}, {args[1]}) = {expected}")
            else:
                results.add_fail(f"add({args[0]}, {args[1]})", f"Expected {expected}, got {result}")

    except Exception as e:
        results.add_fail("Add tool tests", str(e))


def test_cube_tool(results: TestResult):
    """Test the cube tool."""
    print("\n--- Testing Cube Tool ---")

    try:
        from langgraph_react_agent_example import setup_tools

        tools = setup_tools()
        cube = next((t for t in tools if t.name == "cube"), None)

        if cube is None:
            results.add_fail("Find cube tool", "Tool not found")
            return

        test_cases = [
            (2, 8),
            (3, 27),
            (0, 0),
            (-2, -8),
            (1.5, 3.375),
        ]

        for x, expected in test_cases:
            result = cube.invoke({"x": x})
            if abs(result - expected) < 0.0001:
                results.add_pass(f"cube({x}) = {expected}")
            else:
                results.add_fail(f"cube({x})", f"Expected {expected}, got {result}")

    except Exception as e:
        results.add_fail("Cube tool tests", str(e))


def test_square_tool(results: TestResult):
    """Test the square tool."""
    print("\n--- Testing Square Tool ---")

    try:
        from langgraph_react_agent_example import setup_tools

        tools = setup_tools()
        square = next((t for t in tools if t.name == "square"), None)

        if square is None:
            results.add_fail("Find square tool", "Tool not found")
            return

        test_cases = [
            (2, 4),
            (3, 9),
            (0, 0),
            (-2, 4),
            (1.5, 2.25),
        ]

        for x, expected in test_cases:
            result = square.invoke({"x": x})
            if abs(result - expected) < 0.0001:
                results.add_pass(f"square({x}) = {expected}")
            else:
                results.add_fail(f"square({x})", f"Expected {expected}, got {result}")

    except Exception as e:
        results.add_fail("Square tool tests", str(e))


def test_get_word_length_tool(results: TestResult):
    """Test the get_word_length tool."""
    print("\n--- Testing Get Word Length Tool ---")

    try:
        from langgraph_react_agent_example import setup_tools

        tools = setup_tools()
        get_word_length = next((t for t in tools if t.name == "get_word_length"), None)

        if get_word_length is None:
            results.add_fail("Find get_word_length tool", "Tool not found")
            return

        test_cases = [
            ("hello", 5),
            ("", 0),
            ("LangGraph", 9),
            ("a", 1),
            ("test string", 11),
        ]

        for word, expected in test_cases:
            result = get_word_length.invoke({"word": word})
            if result == expected:
                results.add_pass(f"get_word_length('{word}') = {expected}")
            else:
                results.add_fail(f"get_word_length('{word}')", f"Expected {expected}, got {result}")

    except Exception as e:
        results.add_fail("Get word length tool tests", str(e))


def test_langgraph_availability(results: TestResult):
    """Test LangGraph import availability."""
    print("\n--- Testing LangGraph Availability ---")

    try:
        from langgraph_react_agent_example import LANGGRAPH_AVAILABLE

        if LANGGRAPH_AVAILABLE:
            results.add_pass("LangGraph is available")

            try:
                from langgraph.prebuilt import create_react_agent

                results.add_pass("create_react_agent import")
            except ImportError as e:
                results.add_fail("create_react_agent import", str(e))
        else:
            results.add_skip("LangGraph availability", "langgraph not installed")

    except Exception as e:
        results.add_fail("LangGraph availability check", str(e))


def test_ollama_service_imports(results: TestResult):
    """Test Ollama service imports."""
    print("\n--- Testing Ollama Service Imports ---")

    try:
        from ollama_local_serve import NetworkConfig

        results.add_pass("Import NetworkConfig")
    except ImportError as e:
        results.add_fail("Import NetworkConfig", str(e))

    try:
        from ollama_local_serve import OllamaService

        results.add_pass("Import OllamaService")
    except ImportError as e:
        results.add_fail("Import OllamaService", str(e))

    try:
        from ollama_local_serve import create_langchain_chat_client

        results.add_pass("Import create_langchain_chat_client")
    except ImportError as e:
        results.add_fail("Import create_langchain_chat_client", str(e))


def test_constants(results: TestResult):
    """Test that constants are defined correctly."""
    print("\n--- Testing Constants ---")

    try:
        from langgraph_react_agent_example import MAX_LOG_MESSAGE_LENGTH

        if MAX_LOG_MESSAGE_LENGTH == 200:
            results.add_pass("MAX_LOG_MESSAGE_LENGTH = 200")
        else:
            results.add_fail("MAX_LOG_MESSAGE_LENGTH", f"Expected 200, got {MAX_LOG_MESSAGE_LENGTH}")
    except ImportError as e:
        results.add_fail("Import MAX_LOG_MESSAGE_LENGTH", str(e))


async def test_integration_basic(results: TestResult):
    """Integration test - requires Ollama running."""
    print("\n--- Integration Test: Basic Agent ---")

    try:
        from langgraph_react_agent_example import LANGGRAPH_AVAILABLE

        if not LANGGRAPH_AVAILABLE:
            results.add_skip("Integration test", "langgraph not installed")
            return

        from langgraph_react_agent_example import setup_tools
        from ollama_local_serve import NetworkConfig, create_langchain_chat_client
        from langgraph.prebuilt import create_react_agent
        import aiohttp

        # Try to detect available models
        model = "llama3.2:1b"  # Default to a common small model variant
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://127.0.0.1:11434/api/tags") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        models = [m["name"] for m in data.get("models", [])]
                        # Prefer llama3.2 variants, fallback to any available model
                        for m in models:
                            if "llama3.2" in m:
                                model = m
                                break
                        else:
                            if models:
                                model = models[0]
                        print(f"  Using model: {model}")
        except Exception:
            pass  # Use default model

        config = NetworkConfig(host="127.0.0.1", port=11434, timeout=120)
        llm = create_langchain_chat_client(config=config, model=model, temperature=0)
        tools = setup_tools()
        agent = create_react_agent(llm, tools)

        results.add_pass("Create ReAct agent")

        # Test a simple query
        response = await agent.ainvoke({"messages": [("user", "What is 5 cubed?")]})
        messages = response.get("messages", [])

        if messages:
            final_message = messages[-1]
            content = final_message.content.lower()
            # 5 cubed = 125
            if "125" in content:
                results.add_pass("Agent computed 5 cubed correctly")
            else:
                results.add_fail("Agent computation", f"Expected 125 in response, got: {content[:100]}")
        else:
            results.add_fail("Agent response", "No messages in response")

    except ConnectionRefusedError:
        results.add_skip("Integration test", "Ollama not running on localhost:11434")
    except Exception as e:
        import traceback
        error_msg = str(e) if str(e) else f"{type(e).__name__}: {repr(e)}"
        print(f"  Error details: {traceback.format_exc()[:500]}")
        results.add_fail("Integration test", error_msg)


def run_unit_tests() -> TestResult:
    """Run all unit tests (no Ollama required)."""
    results = TestResult()

    print("=" * 60)
    print("LangGraph ReAct Agent Example - Unit Tests")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    test_tool_imports(results)
    test_multiply_tool(results)
    test_add_tool(results)
    test_cube_tool(results)
    test_square_tool(results)
    test_get_word_length_tool(results)
    test_langgraph_availability(results)
    test_ollama_service_imports(results)
    test_constants(results)

    return results


async def run_integration_tests(results: TestResult):
    """Run integration tests (requires Ollama)."""
    print("\n" + "=" * 60)
    print("LangGraph ReAct Agent Example - Integration Tests")
    print("=" * 60)

    await test_integration_basic(results)


async def main():
    parser = argparse.ArgumentParser(description="Test LangGraph ReAct Agent Example")
    parser.add_argument(
        "--integration",
        action="store_true",
        help="Run integration tests (requires Ollama running)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")

    args = parser.parse_args()

    # Run unit tests
    results = run_unit_tests()

    # Run integration tests if requested
    if args.integration:
        await run_integration_tests(results)

    # Print summary
    success = results.summary()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
