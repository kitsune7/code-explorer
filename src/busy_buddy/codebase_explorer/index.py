"""
Codebase indexing system for efficient exploration
"""

import hashlib
from pathlib import Path
from typing import Dict, List, Optional

import networkx as nx
from pybloom_live import BloomFilter
from transformers import AutoTokenizer, AutoModel
import numpy as np

from .models import CodeEntity
from .config import EXTENSION_TO_LANGUAGE
from .parsers import TreeSitterParser, RegexFallbackParser, TREE_SITTER_AVAILABLE, TREE_SITTER_BASIC
from .utils import should_skip_path, estimate_memory_usage, get_project_type, count_files_to_index


class CodebaseIndex:
  """Efficient index for codebase exploration with tree-sitter parsing"""

  def __init__(self, root_path: str):
    self.root_path = Path(root_path)
    self.entities: Dict[str, CodeEntity] = {}
    self.dependency_graph = nx.DiGraph()
    self.bloom_filter = BloomFilter(capacity=10000, error_rate=0.001)
    self.embeddings_cache: Dict[str, np.ndarray] = {}
    self.summary_cache: Dict[str, str] = {}

    # Initialize parser
    if TREE_SITTER_AVAILABLE or TREE_SITTER_BASIC:
      self.parser = TreeSitterParser()
    else:
      self.parser = RegexFallbackParser()
      print("Using regex fallback parser. For better accuracy, install tree-sitter-languages")

    # Initialize embedding model for semantic search
    self.tokenizer = AutoTokenizer.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')
    self.model = AutoModel.from_pretrained('sentence-transformers/all-MiniLM-L6-v2')

  def build_index(self, extensions: Optional[List[str]] = None, show_progress: bool = True):
    """Build comprehensive index of the codebase"""
    if extensions is None:
      extensions = list(EXTENSION_TO_LANGUAGE.keys())

    # Detect project type
    project_type = get_project_type(self.root_path)

    # Count files first for progress estimation
    if show_progress:
      total_files = count_files_to_index(self.root_path, extensions)
      memory_estimate = estimate_memory_usage(total_files)
      print(f"Project type: {project_type}")
      print(f"Indexing {total_files} files (estimated memory: {memory_estimate})...")

    file_count = 0
    skipped_count = 0

    for file_path in self.root_path.rglob('*'):
      if file_path.is_file() and file_path.suffix in extensions:
        # Use utility function to check if we should skip
        if should_skip_path(file_path):
          skipped_count += 1
          continue

        self._index_file(file_path)
        file_count += 1

        # Show progress
        if show_progress and file_count % 10 == 0:
          print(f"  Indexed {file_count} files...", end='\r')

    if show_progress:
      print(f"\nIndexed {file_count} files with {len(self.entities)} entities")
      print(f"Skipped {skipped_count} files (build artifacts, dependencies, etc.)")
      print(f"Dependency graph: {self.dependency_graph.number_of_nodes()} nodes, {self.dependency_graph.number_of_edges()} edges")

  def _index_file(self, file_path: Path):
    """Index a single file using tree-sitter parsing"""
    try:
      content = file_path.read_text(encoding='utf-8')
      relative_path = str(file_path.relative_to(self.root_path))

      # Add to bloom filter
      self.bloom_filter.add(relative_path)

      # Create file entity
      file_entity = CodeEntity(
        path=relative_path,
        type='file',
        name=file_path.name,
        content=content[:500],
        ast_hash=hashlib.md5(content.encode()).hexdigest()
      )

      self.entities[relative_path] = file_entity
      self.dependency_graph.add_node(relative_path)

      # Parse file with tree-sitter
      entities = self.parser.parse_file(content, relative_path)
      for entity_id, entity in entities.items():
        self.entities[entity_id] = entity
        self.dependency_graph.add_node(entity_id)
        # Link entity to its file
        self.dependency_graph.add_edge(entity_id, relative_path)

      # Extract and process imports
      imports = self.parser.extract_imports(content, relative_path)
      for imp in imports:
        resolved = self._resolve_import(imp, file_path)
        if resolved:
          self.dependency_graph.add_edge(relative_path, resolved)
        else:
          self.dependency_graph.add_edge(relative_path, f"external:{imp}")

    except Exception as e:
      # Log but continue
      print(f"Error indexing {file_path}: {e}")

  def _resolve_import(self, import_name: str, from_file: Path) -> Optional[str]:
    """Resolve imports to local files"""
    import_name = import_name.strip('\'"')

    # Handle relative imports
    if import_name.startswith('.'):
      base_dir = from_file.parent

      # Navigate up for ../
      while import_name.startswith('../'):
        base_dir = base_dir.parent
        import_name = import_name[3:]

      import_name = import_name.lstrip('./')

      # Try common patterns
      for ext in EXTENSION_TO_LANGUAGE.keys():
        candidates = [
          base_dir / f"{import_name}{ext}",
          base_dir / import_name / f"index{ext}",
          base_dir / import_name / f"__init__{ext}",
        ]

        for candidate in candidates:
          if candidate.exists():
            return str(candidate.relative_to(self.root_path))

    # Try absolute imports from root
    else:
      parts = import_name.replace('.', '/').replace('::', '/').split('/')

      for ext in EXTENSION_TO_LANGUAGE.keys():
        candidates = [
          self.root_path / f"{'/'.join(parts)}{ext}",
          self.root_path / '/'.join(parts) / f"index{ext}",
          self.root_path / '/'.join(parts) / f"__init__{ext}",
        ]

        for candidate in candidates:
          if candidate.exists():
            return str(candidate.relative_to(self.root_path))

    return None

  def get_entity(self, entity_id: str) -> Optional[CodeEntity]:
    """Get an entity by its ID"""
    return self.entities.get(entity_id)

  def search_entities(self, query: str, entity_type: Optional[str] = None) -> List[CodeEntity]:
    """Search for entities by name or type"""
    results = []
    query_lower = query.lower()

    for entity_id, entity in self.entities.items():
      if entity_type and entity.type != entity_type:
        continue
      if query_lower in entity.name.lower() or query_lower in entity.path.lower():
        results.append(entity)

    return results

  def get_file_entities(self, file_path: str) -> List[CodeEntity]:
    """Get all entities in a specific file"""
    entities = []
    for entity_id, entity in self.entities.items():
      if entity.path == file_path or entity_id.startswith(f"{file_path}::"):
        entities.append(entity)
    return entities
