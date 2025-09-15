# Codebase Explorer

An AI-powered code analysis and exploration tool built with smolagents and tree-sitter for multi-language support.

## Features

- **Multi-language Support**: Parse Python, JavaScript, TypeScript, Java, Go, Rust, C/C++, and more using tree-sitter
- **Semantic Search**: Find code by meaning, not just keywords
- **Dependency Analysis**: Track imports and relationships between modules
- **Smart Code Reading**: Multiple reading modes (summary, structure, chunks)
- **Architecture Mapping**: Understand codebase structure and entry points
- **Context Management**: Maintains exploration context across queries
- **Subagent Support**: Delegates complex queries to specialized agents

## Installation

The required dependencies are already in `pyproject.toml`:
```bash
pip install tree-sitter tree-sitter-languages networkx pybloom-live torch transformers
```

## Usage

### As a Standalone Module

```python
from busy_buddy.codebase_explorer import CodebaseExplorerAgent

# Initialize the explorer
explorer = CodebaseExplorerAgent("/path/to/codebase")

# Explore with queries
result = explorer.explore("What is the architecture of this codebase?")
print(result)

# Deep dive with subagent
result = explorer.explore("Deep dive into the authentication system", use_subagent=True)
print(result)
```

### Using Individual Tools

```python
from busy_buddy.codebase_explorer import CodebaseIndex, SemanticSearchTool

# Build index
index = CodebaseIndex("/path/to/codebase")
index.build_index()

# Use semantic search
search_tool = SemanticSearchTool(index)
results = search_tool.forward("authentication middleware", max_results=5)
print(results)
```

### Command Line Interface

```bash
# Run the explorer on current directory
python -m busy_buddy --explore

# Run on specific directory
python -m busy_buddy --explore /path/to/codebase

# Run the demo
python src/busy_buddy/codebase_explorer_demo.py
```

## Architecture

The module is organized into:

- `models.py`: Data structures (CodeEntity)
- `config.py`: Language configurations and query patterns
- `parsers.py`: Tree-sitter and regex fallback parsers
- `index.py`: Codebase indexing system
- `tools.py`: Smolagents tools for different exploration tasks
- `agent.py`: Main exploration agent with context management

## Tools Available

1. **SemanticSearchTool**: Search code by concepts and patterns
2. **DependencyAnalysisTool**: Analyze imports and dependencies
3. **SmartCodeReaderTool**: Read code with different strategies
4. **ArchitectureMapperTool**: Map high-level architecture

## Language Support

Fully supported with tree-sitter:
- Python
- JavaScript/TypeScript (including JSX/TSX)
- Java
- Go
- Rust
- C/C++

Basic support with regex fallback:
- Ruby, PHP, Swift, Kotlin, Scala, R, Objective-C

## Configuration

The module automatically:
- Skips hidden files and directories
- Ignores common non-source directories (node_modules, venv, etc.)
- Handles multiple file extensions per language
- Resolves relative and absolute imports

## Performance Considerations

- **Indexing**: Done once at initialization
- **Embeddings**: Computed lazily and cached
- **Bloom Filters**: Fast negative lookups
- **Context Window**: Limited to last 5 interactions
- **Summaries**: Cached to avoid recomputation

## Examples

```python
# Example queries
queries = [
    "Find all REST API endpoints",
    "Show me the test files",
    "What databases does this project use?",
    "Analyze the dependency tree of the main module",
    "Search for error handling patterns",
    "Map the microservices architecture"
]

for query in queries:
    result = explorer.explore(query)
    print(result)
```
