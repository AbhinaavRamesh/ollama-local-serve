# LangChain Integration

## Basic Usage

```python
from ollama_local_serve import create_langchain_client, NetworkConfig

# Connect to a local or remote Ollama service
llm = create_langchain_client(
    base_url="http://192.168.1.100:11434",
    model="llama2",
    temperature=0.7
)

response = llm.invoke("What is the meaning of life?")
print(response)
```

## Advanced LLM Usage

### Using with Remote Ollama

Connect to Ollama running on a different machine:

```python
from ollama_local_serve import create_langchain_client

# Connect to remote Ollama service
llm = create_langchain_client(
    base_url="http://192.168.1.100:11434",  # Your Ollama server
    model="llama3.2",
    temperature=0.7,
    top_p=0.9
)

response = llm.invoke("Explain quantum computing in simple terms")
print(response)
```

### Streaming Responses

For real-time token streaming:

```python
from ollama_local_serve import create_langchain_client

llm = create_langchain_client(model="llama3.2", temperature=0.7)

# Stream tokens as they're generated
for chunk in llm.stream("Write a haiku about coding"):
    print(chunk, end="", flush=True)
print()
```

### Using as a Drop-in Replacement

The Ollama client works with any LangChain component expecting an LLM:

```python
from ollama_local_serve import create_langchain_client
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnablePassthrough

llm = create_langchain_client(model="llama3.2")

# Create a prompt template
template = """Answer the following question concisely:

Question: {question}

Answer:"""

prompt = ChatPromptTemplate.from_template(template)

# Build a chain
chain = (
    RunnablePassthrough.assign(question=lambda x: x["question"])
    | prompt
    | llm
)

result = chain.invoke({"question": "What is Python?"})
print(result)
```

### Model Configuration Options

```python
from ollama_local_serve import create_langchain_client

llm = create_langchain_client(
    base_url="http://localhost:11434",
    model="llama3.2",

    # Generation parameters
    temperature=0.5,        # 0 = deterministic, 1 = creative
    top_p=0.9,             # Nucleus sampling
    top_k=40,              # Top-k sampling

    # Request parameters
    timeout=30,            # Timeout in seconds
    max_retries=3,         # Number of retries
    streaming=False,       # Enable streaming responses
)

response = llm.invoke("Tell me a joke")
print(response)
```

## LangGraph ReAct Agent

For advanced use cases, use LangGraph's prebuilt ReAct agent with Ollama:

```python
from ollama_local_serve import OllamaService, NetworkConfig, create_langchain_chat_client
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

# Define custom tools for your agent
@tool
def cube(x: float) -> float:
    """Calculate the cube of a number."""
    return x ** 3

@tool
def add(a: float, b: float) -> float:
    """Add two numbers together."""
    return a + b

@tool
def multiply(a: float, b: float) -> float:
    """Multiply two numbers together."""
    return a * b

# Start Ollama service and create agent
config = NetworkConfig()
async with OllamaService(config) as service:
    llm = create_langchain_chat_client(config=config, model="llama3.2")
    agent = create_react_agent(llm, [cube, add, multiply])

    # Use the agent to solve problems
    result = await agent.ainvoke({
        "messages": [("user", "What is (5 cubed) plus (3 multiplied by 4)?")]
    })
    print(result["messages"][-1].content)
```

## RAG (Retrieval-Augmented Generation)

Build a RAG pipeline using Ollama:

```python
from ollama_local_serve import create_langchain_client
from langchain.vectorstores import FAISS
from langchain.text_splitters import CharacterTextSplitter
from langchain.embeddings import OllamaEmbeddings
from langchain.chains import RetrievalQA

# Initialize embeddings
embeddings = OllamaEmbeddings(base_url="http://localhost:11434")

# Create or load vector store
vectorstore = FAISS.load_local("faiss_index", embeddings)

# Create QA chain
llm = create_langchain_client(model="llama3.2")
qa = RetrievalQA.from_chain_type(
    llm=llm,
    chain_type="stuff",
    retriever=vectorstore.as_retriever(search_kwargs={"k": 3}),
    return_source_documents=True
)

# Query the knowledge base
result = qa({"query": "What is machine learning?"})
print(f"Answer: {result['result']}")
print(f"Sources: {result['source_documents']}")
```

## Chaining Multiple Models

Combine different Ollama models in a workflow:

```python
from ollama_local_serve import create_langchain_client
from langchain.schema.runnable import RunnableSequence

# Create separate LLM instances for different models
summarizer = create_langchain_client(model="mistral")  # Fast summarization
analyzer = create_langchain_client(model="llama3.2")   # Detailed analysis

# Workflow: Summarize then analyze
text = "Long document text here..."

# Step 1: Summarize with Mistral
summary = summarizer.invoke(f"Summarize this:\n{text}")
print(f"Summary: {summary}")

# Step 2: Analyze summary with Llama
analysis = analyzer.invoke(f"Analyze this summary:\n{summary}")
print(f"Analysis: {analysis}")
```

## Memory and Context Management

Maintain conversation history:

```python
from ollama_local_serve import create_langchain_client
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain

llm = create_langchain_client(model="llama3.2")

# Create memory to track conversation
memory = ConversationBufferMemory()

# Build conversation chain
conversation = ConversationChain(
    llm=llm,
    memory=memory,
    verbose=True
)

# Multi-turn conversation
print(conversation.run("Hello, what's your name?"))
print(conversation.run("Can you explain machine learning?"))
print(conversation.run("Can you provide an example of supervised learning?"))
# The model has context of previous messages
```

## Batch Processing

Process multiple prompts efficiently:

```python
from ollama_local_serve import create_langchain_client
import asyncio

llm = create_langchain_client(model="llama3.2")

# Process multiple prompts
prompts = [
    "What is Python?",
    "Explain Docker",
    "How does Kubernetes work?"
]

# Sequential processing
for prompt in prompts:
    response = llm.invoke(prompt)
    print(f"Q: {prompt}")
    print(f"A: {response}\n")

# For higher throughput with streaming
async def process_async(prompts):
    results = []
    for prompt in prompts:
        response = llm.invoke(prompt)
        results.append(response)
    return results

# results = asyncio.run(process_async(prompts))
```

## Integration with Other LangChain Components

### Document Loading

```python
from langchain.document_loaders import TextLoader, PDFLoader
from ollama_local_serve import create_langchain_client
from langchain.chains.summarize import load_summarize_chain
from langchain.text_splitters import CharacterTextSplitter

# Load a document
loader = TextLoader("document.txt")
documents = loader.load()

# Split into chunks
text_splitter = CharacterTextSplitter(chunk_size=1000)
chunks = text_splitter.split_documents(documents)

# Summarize
llm = create_langchain_client(model="llama3.2")
chain = load_summarize_chain(llm, chain_type="map_reduce")
summary = chain.run(chunks)
print(summary)
```

### Custom Prompt Templates

```python
from ollama_local_serve import create_langchain_client
from langchain.prompts import PromptTemplate

llm = create_langchain_client(model="llama3.2")

# Create a custom prompt
template = """You are a helpful coding assistant.

Question: {question}
Programming Language: {language}

Provide a code example and explanation."""

prompt = PromptTemplate(
    input_variables=["question", "language"],
    template=template
)

# Use the prompt
formatted = prompt.format(
    question="How do I read a file?",
    language="Python"
)
response = llm.invoke(formatted)
print(response)
```

## Monitoring LangChain Usage

Track your LangChain queries via the Ollama monitoring dashboard:

```bash
# Metrics are automatically captured by ollama-local-serve
# View in the dashboard: http://localhost:3000

# Or query the API:
curl http://localhost:8000/api/stats/current
curl http://localhost:8000/api/stats/logs  # See your LangChain prompts
```

See `langgraph_react_agent_example.py` for a complete working example with multiple tools.
