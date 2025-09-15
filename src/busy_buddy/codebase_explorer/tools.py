"""
Tools for codebase exploration using smolagents
"""

from functools import lru_cache
from pathlib import Path
from collections import defaultdict
import numpy as np
import torch
import networkx as nx
from typing import Optional
from smolagents import Tool

from .index import CodebaseIndex
from .config import EXTENSION_TO_LANGUAGE

class SemanticSearchTool(Tool):
  """Semantic search across codebase using embeddings"""

  name = "semantic_search"
  description = "Search codebase semantically for concepts, patterns, or functionality"
  inputs = {
    "query": {"type": "string", "description": "Natural language search query"},
    "max_results": {"type": "integer", "description": "Maximum results to return", "nullable": True}
  }
  output_type = "string"

  def __init__(self, index: CodebaseIndex):
    super().__init__()
    self.index = index

  @lru_cache(maxsize=128)
  def _get_embedding(self, text: str) -> np.ndarray:
    """Generate embedding for text with caching"""
    inputs = self.index.tokenizer(text, return_tensors='pt', truncation=True, max_length=512)
    with torch.no_grad():
      outputs = self.index.model(**inputs)
    return outputs.last_hidden_state.mean(dim=1).numpy()[0]

  def forward(self, query: str, max_results: Optional[int] = 5) -> str:
    """Execute semantic search"""
    if max_results is None:
      max_results = 5
    query_embedding = self._get_embedding(query)

    # Calculate similarities
    similarities = []
    for entity_id, entity in self.index.entities.items():
      if entity.type != 'file':  # Skip file entities, focus on code constructs
        entity_text = f"{entity.name} {entity.content}"
        entity_embedding = self._get_embedding(entity_text)
        similarity = np.dot(query_embedding, entity_embedding) / (
          np.linalg.norm(query_embedding) * np.linalg.norm(entity_embedding)
        )
        similarities.append((similarity, entity_id, entity))

    # Sort and return top results
    similarities.sort(reverse=True, key=lambda x: x[0])

    results = []
    for score, entity_id, entity in similarities[:max_results]:
      results.append(f"[Score: {score:.2f}] {entity.type} {entity.name} in {entity.path}")
      if 'start_line' in entity.metadata:
        results.append(f"  Location: Line {entity.metadata['start_line']}")
      results.append(f"  Preview: {entity.content[:100]}...")

    return "\n".join(results) if results else "No relevant results found"


class DependencyAnalysisTool(Tool):
  """Analyze dependencies and relationships in code"""

  name = "analyze_dependencies"
  description = "Analyze dependencies, imports, and relationships between code entities"
  inputs = {
    "entity_path": {"type": "string", "description": "Path to file or entity (file.py or file.py::ClassName)"},
    "direction": {"type": "string", "description": "Direction: 'imports' (what it depends on) or 'importers' (what depends on it)", "default": "imports", "nullable": True},
    "depth": {"type": "integer", "description": "Depth of dependency tree to explore", "nullable": True}
  }
  output_type = "string"

  def __init__(self, index: CodebaseIndex):
    super().__init__()
    self.index = index

  def forward(self, entity_path: str, direction: Optional[str] = "imports", depth: Optional[int] = 2) -> str:
    """Analyze dependencies with configurable depth"""
    if direction is None:
      direction = "imports"
    if depth is None:
      depth = 2
    if entity_path not in self.index.dependency_graph:
      return f"Entity {entity_path} not found in dependency graph"

    visited = set()
    results = []

    def traverse(node: str, current_depth: int, indent: str = ""):
      if current_depth > depth or node in visited:
        return
      visited.add(node)

      if direction == "imports":
        neighbors = self.index.dependency_graph.successors(node)
      else:
        neighbors = self.index.dependency_graph.predecessors(node)

      for neighbor in neighbors:
        results.append(f"{indent}{'→' if direction == 'imports' else '←'} {neighbor}")
        traverse(neighbor, current_depth + 1, indent + "  ")

    results.append(f"Dependencies for {entity_path} ({direction}):")
    traverse(entity_path, 0)

    return "\n".join(results) if results else f"No dependencies found for {entity_path}"


class SmartCodeReaderTool(Tool):
  """Read code with intelligent chunking and summarization"""

  name = "read_code"
  description = "Read code files or entities with smart chunking and summarization"
  inputs = {
    "path": {"type": "string", "description": "File path or entity identifier"},
    "mode": {"type": "string", "description": "Mode: 'full', 'summary', 'structure', 'chunk'", "default": "summary", "nullable": True},
    "chunk_size": {"type": "integer", "description": "Size of chunks if mode is 'chunk'", "nullable": True}
  }
  output_type = "string"

  def __init__(self, index: CodebaseIndex, root_path: str):
    super().__init__()
    self.index = index
    self.root_path = Path(root_path)

  def forward(self, path: str, mode: Optional[str] = "summary", chunk_size: Optional[int] = 50) -> str:
    """Read code with different strategies"""
    if mode is None:
      mode = "summary"
    if chunk_size is None:
      chunk_size = 50
    file_path = self.root_path / path

    if not file_path.exists():
      return f"File {path} not found"

    content = file_path.read_text(encoding='utf-8')

    if mode == "full":
      return content[:2000] + ("..." if len(content) > 2000 else "")

    elif mode == "summary":
      return self._generate_summary(content, path)

    elif mode == "structure":
      return self._extract_structure(content, path)

    elif mode == "chunk":
      lines = content.split('\n')
      chunks = []
      for i in range(0, len(lines), chunk_size):
        chunk = '\n'.join(lines[i:i+chunk_size])
        chunks.append(f"[Lines {i+1}-{min(i+chunk_size, len(lines))}]:\n{chunk}")
      return f"File chunked into {len(chunks)} parts. First chunk:\n{chunks[0]}"

    return "Invalid mode specified"

  def _generate_summary(self, content: str, path: str) -> str:
    """Generate intelligent summary using tree-sitter parsing"""
    if path in self.index.summary_cache:
      return self.index.summary_cache[path]

    summary_parts = [f"File: {path}"]

    # Parse with tree-sitter
    entities = self.index.parser.parse_file(content, path)

    # Group entities by type
    by_type = defaultdict(list)
    for entity in entities.values():
      by_type[entity.type].append(entity.name)

    # Add entity counts
    for entity_type, names in by_type.items():
      summary_parts.append(f"{entity_type.capitalize()}s: {', '.join(names[:5])}")
      if len(names) > 5:
        summary_parts.append(f"  ... and {len(names) - 5} more")

    # Extract imports
    imports = self.index.parser.extract_imports(content, path)
    if imports:
      summary_parts.append(f"Imports: {', '.join(imports[:5])}")

    # Add line count
    lines = content.split('\n')
    summary_parts.append(f"Lines of code: {len(lines)}")

    summary = "\n".join(summary_parts)
    self.index.summary_cache[path] = summary
    return summary

  def _extract_structure(self, content: str, path: str) -> str:
    """Extract code structure using tree-sitter"""
    entities = self.index.parser.parse_file(content, path)

    if not entities:
      return "No structure found"

    # Organize by type and line number
    sorted_entities = sorted(
      entities.values(),
      key=lambda e: e.metadata.get('start_line', 0)
    )

    structure = []
    for entity in sorted_entities:
      indent = "  " if entity.type in ['method', 'function'] else ""
      line_info = f" (line {entity.metadata.get('start_line', '?')})" if 'start_line' in entity.metadata else ""
      structure.append(f"{indent}{entity.type} {entity.name}{line_info}")

    return "\n".join(structure)


class ArchitectureMapperTool(Tool):
  """Map high-level architecture and entry points"""

  name = "map_architecture"
  description = "Generate high-level architecture map and identify key entry points"
  inputs = {
    "focus_area": {"type": "string", "description": "Optional area to focus on", "default": "", "nullable": True}
  }
  output_type = "string"

  def __init__(self, index: CodebaseIndex, root_path: str):
    super().__init__()
    self.index = index
    self.root_path = Path(root_path)

  def forward(self, focus_area: Optional[str] = "") -> str:
    """Generate architecture overview"""
    if focus_area is None:
      focus_area = ""
    # Identify key directories
    dirs = defaultdict(list)
    for entity_path in self.index.entities:
      if '/' in entity_path:
        top_dir = entity_path.split('/')[0]
        dirs[top_dir].append(entity_path)

    # Find entry points
    entry_points = []
    for path in self.index.entities:
      if any(pattern in path.lower() for pattern in ['main.', '__main__', 'app.', 'index.', 'server.', 'cli.']):
        entry_points.append(path)

    # Build summary
    summary = ["=== Codebase Architecture ===\n"]

    summary.append("Top-level directories:")
    for dir_name, files in sorted(dirs.items())[:10]:
      # Count entity types in directory
      types_count = defaultdict(int)
      for file in files:
        if file in self.index.entities:
          types_count[self.index.entities[file].type] += 1

      type_summary = ", ".join([f"{count} {t}s" for t, count in types_count.items()])
      summary.append(f"  {dir_name}/ ({len(files)} files, {type_summary})")

    summary.append(f"\nEntry points: {', '.join(entry_points[:5])}")

    # Analyze connectivity
    if self.index.dependency_graph.number_of_nodes() > 0:
      # Most connected modules
      central_nodes = nx.degree_centrality(self.index.dependency_graph)
      top_central = sorted(central_nodes.items(), key=lambda x: x[1], reverse=True)[:5]
      summary.append("\nMost connected modules:")
      for node, centrality in top_central:
        if not node.startswith("external:"):
          summary.append(f"  {node} (centrality: {centrality:.3f})")

      # Identify clusters/components
      if nx.is_weakly_connected(self.index.dependency_graph):
        summary.append("\nCodebase is fully connected")
      else:
        components = list(nx.weakly_connected_components(self.index.dependency_graph))
        summary.append(f"\nCodebase has {len(components)} separate components")

    # Language distribution
    lang_count = defaultdict(int)
    for path in self.index.entities:
      if '::' not in path:  # Only count files, not entities
        ext = Path(path).suffix
        if ext in EXTENSION_TO_LANGUAGE:
          lang_count[EXTENSION_TO_LANGUAGE[ext]] += 1

    if lang_count:
      summary.append("\nLanguage distribution:")
      for lang, count in sorted(lang_count.items(), key=lambda x: x[1], reverse=True):
        summary.append(f"  {lang}: {count} files")

    return "\n".join(summary)
