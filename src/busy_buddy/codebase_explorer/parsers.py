"""
Code parsers using tree-sitter for multi-language support
"""

from __future__ import annotations
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from .models import CodeEntity
from .config import LANGUAGE_QUERIES, EXTENSION_TO_LANGUAGE, ENTITY_TYPES

# Tree-sitter imports
# Predefine availability flags and safe stubs to avoid NameError / unbound warnings
TREE_SITTER_AVAILABLE = False
TREE_SITTER_BASIC = False
try:
  import tree_sitter  # type: ignore
  from tree_sitter import Language, Parser, Node  # type: ignore
  try:
    import tree_sitter_languages  # type: ignore
    TREE_SITTER_AVAILABLE = True
  except ImportError:
    print("Warning: tree-sitter-languages not installed. Install with: pip install tree-sitter-languages")
except ImportError:
  # Provide stub types so annotations resolve even without tree-sitter
  Language = Parser = Node = Any  # type: ignore
  print("Warning: tree-sitter not available. Using fallback regex parsing.")

# Fallback to basic tree-sitter if tree-sitter-languages not available but tree_sitter itself is present
if not TREE_SITTER_AVAILABLE:
  try:
    import tree_sitter  # type: ignore
    TREE_SITTER_BASIC = True
    print("Note: Using basic tree-sitter. For better language support, install tree-sitter-languages")
  except ImportError:
    # tree_sitter not installed; regex fallback will be used
    pass


class TreeSitterParser:
  """Universal parser using tree-sitter for accurate multi-language parsing"""

  def __init__(self):
    """Initialize tree-sitter parser with language support"""
    self.parsers = {}
    self.languages = {}

    if TREE_SITTER_AVAILABLE:
      # Use tree-sitter-languages which bundles many grammars
      from tree_sitter_languages import get_language, get_parser

      for ext, lang_name in EXTENSION_TO_LANGUAGE.items():
        try:
          self.languages[lang_name] = get_language(lang_name)
          self.parsers[lang_name] = get_parser(lang_name)
        except Exception:
          # Language not available in tree-sitter-languages
          pass

    elif TREE_SITTER_BASIC:
      # Manual setup for basic tree-sitter
      print("""
      To use tree-sitter with specific languages, you need to:
      1. Clone language repos:
         git clone https://github.com/tree-sitter/tree-sitter-python
         git clone https://github.com/tree-sitter/tree-sitter-javascript
         etc.
      2. Build language libraries using tree_sitter.Language.build_library()
      3. Load them with Language(lib_path, 'language_name')
      """)

  def get_parser_for_file(self, file_path: Path):
    """Get appropriate parser for a file based on its extension"""
    ext = file_path.suffix
    lang_name = EXTENSION_TO_LANGUAGE.get(ext)

    if lang_name and lang_name in self.parsers:
      return self.parsers[lang_name]
    return None

  def parse_file(self, content: str, file_path: str) -> Dict[str, CodeEntity]:
    """Parse file content and extract entities using tree-sitter"""
    entities = {}
    ext = Path(file_path).suffix
    lang_name = EXTENSION_TO_LANGUAGE.get(ext)

    if not lang_name or lang_name not in self.parsers:
      return entities

    parser = self.parsers[lang_name]
    tree = parser.parse(bytes(content, 'utf-8'))

    # Get language-specific queries
    queries = LANGUAGE_QUERIES.get(lang_name, {})

    # Extract definitions using tree-sitter queries if available
    if 'definitions' in queries and lang_name in self.languages:
      try:
        language = self.languages[lang_name]
        query = language.query(queries['definitions'])
        captures = query.captures(tree.root_node)

        for node, name in captures:
          if name.endswith('.name'):
            entity_type = name.split('.')[0]
            entity_name = content[node.start_byte:node.end_byte]
            entity_id = f"{file_path}::{entity_name}"

            # Get the full node (not just the name)
            parent = node.parent
            if parent:
              entities[entity_id] = CodeEntity(
                path=file_path,
                type=entity_type,
                name=entity_name,
                content=content[parent.start_byte:min(parent.end_byte, parent.start_byte + 300)],
                metadata={
                  'start_line': parent.start_point[0],
                  'end_line': parent.end_point[0],
                  'start_byte': parent.start_byte,
                  'end_byte': parent.end_byte
                }
              )
      except Exception as e:
        # Fallback to walking the tree manually
        entities.update(self._walk_tree(tree.root_node, content, file_path, lang_name))
    else:
      # Fallback to walking the tree manually
      entities.update(self._walk_tree(tree.root_node, content, file_path, lang_name))

    return entities

  def _walk_tree(self, node, content: str, file_path: str, lang_name: str) -> Dict[str, CodeEntity]:
    """Manually walk the AST tree to extract entities"""
    entities = {}
    lang_entity_types = ENTITY_TYPES.get(lang_name, {})

    def walk(node):
      if node.type in lang_entity_types:
        # Try to find the name node
        name_node = self._find_name_node(node, lang_name)
        if name_node:
          entity_name = content[name_node.start_byte:name_node.end_byte]
          entity_id = f"{file_path}::{entity_name}"

          entities[entity_id] = CodeEntity(
            path=file_path,
            type=lang_entity_types[node.type],
            name=entity_name,
            content=content[node.start_byte:min(node.end_byte, node.start_byte + 300)],
            metadata={
              'start_line': node.start_point[0],
              'end_line': node.end_point[0],
              'node_type': node.type
            }
          )

      # Recurse through children
      for child in node.children:
        walk(child)

    walk(node)
    return entities

  def _find_name_node(self, node, lang_name: str):
    """Find the name identifier node for different constructs"""
    # Look for common name patterns
    for child in node.children:
      if child.type in ['identifier', 'type_identifier', 'property_identifier', 'field_identifier']:
        return child
      elif child.type == 'name':
        return child

    # Language-specific patterns
    if lang_name == 'python':
      if node.type == 'class_definition' or node.type == 'function_definition':
        for child in node.children:
          if child.type == 'identifier':
            return child

    return None

  def extract_imports(self, content: str, file_path: str) -> List[str]:
    """Extract import statements using tree-sitter"""
    imports = []
    ext = Path(file_path).suffix
    lang_name = EXTENSION_TO_LANGUAGE.get(ext)

    if not lang_name or lang_name not in self.parsers:
      return imports

    parser = self.parsers[lang_name]
    tree = parser.parse(bytes(content, 'utf-8'))

    # Language-specific import extraction
    if lang_name == 'python':
      imports.extend(self._extract_python_imports(tree.root_node, content))
    elif lang_name in ['javascript', 'typescript']:
      imports.extend(self._extract_js_imports(tree.root_node, content))
    elif lang_name == 'java':
      imports.extend(self._extract_java_imports(tree.root_node, content))
    elif lang_name == 'go':
      imports.extend(self._extract_go_imports(tree.root_node, content))
    elif lang_name == 'rust':
      imports.extend(self._extract_rust_imports(tree.root_node, content))

    return imports

  def _extract_python_imports(self, node, content: str) -> List[str]:
    """Extract Python import statements"""
    imports = []

    def walk(node):
      if node.type == 'import_statement':
        for child in node.children:
          if child.type == 'dotted_name':
            imports.append(content[child.start_byte:child.end_byte])
      elif node.type == 'import_from_statement':
        for child in node.children:
          if child.type == 'dotted_name' or child.type == 'relative_import':
            imports.append(content[child.start_byte:child.end_byte])

      for child in node.children:
        walk(child)

    walk(node)
    return imports

  def _extract_js_imports(self, node, content: str) -> List[str]:
    """Extract JavaScript/TypeScript imports"""
    imports = []

    def walk(node):
      if node.type == 'import_statement':
        for child in node.children:
          if child.type == 'string':
            import_path = content[child.start_byte+1:child.end_byte-1]
            imports.append(import_path)
      elif node.type == 'call_expression':
        func_node = node.child_by_field_name('function')
        if func_node and content[func_node.start_byte:func_node.end_byte] == 'require':
          args_node = node.child_by_field_name('arguments')
          if args_node:
            for child in args_node.children:
              if child.type == 'string':
                import_path = content[child.start_byte+1:child.end_byte-1]
                imports.append(import_path)

      for child in node.children:
        walk(child)

    walk(node)
    return imports

  def _extract_java_imports(self, node, content: str) -> List[str]:
    """Extract Java imports"""
    imports = []

    def walk(node):
      if node.type == 'import_declaration':
        for child in node.children:
          if child.type == 'scoped_identifier' or child.type == 'identifier':
            imports.append(content[child.start_byte:child.end_byte])

      for child in node.children:
        walk(child)

    walk(node)
    return imports

  def _extract_go_imports(self, node, content: str) -> List[str]:
    """Extract Go imports"""
    imports = []

    def walk(node):
      if node.type == 'import_declaration':
        for child in node.children:
          if child.type == 'import_spec_list':
            for spec in child.children:
              if spec.type == 'import_spec':
                for path_node in spec.children:
                  if path_node.type == 'interpreted_string_literal':
                    import_path = content[path_node.start_byte+1:path_node.end_byte-1]
                    imports.append(import_path)

      for child in node.children:
        walk(child)

    walk(node)
    return imports

  def _extract_rust_imports(self, node, content: str) -> List[str]:
    """Extract Rust use statements"""
    imports = []

    def walk(node):
      if node.type == 'use_declaration':
        for child in node.children:
          if child.type == 'use_clause' or child.type == 'scoped_identifier':
            imports.append(content[child.start_byte:child.end_byte])

      for child in node.children:
        walk(child)

    walk(node)
    return imports


class RegexFallbackParser:
  """Fallback parser using regex when tree-sitter is not available"""

  def parse_file(self, content: str, file_path: str) -> Dict[str, CodeEntity]:
    """Basic regex-based parsing as fallback"""
    entities = {}

    # Generic patterns that work across many languages
    patterns = [
      (r'class\s+(\w+)', 'class'),
      (r'struct\s+(\w+)', 'struct'),
      (r'interface\s+(\w+)', 'interface'),
      (r'(?:def|func|function|fn)\s+(\w+)', 'function'),
      (r'type\s+(\w+)', 'type'),
      (r'enum\s+(\w+)', 'enum'),
    ]

    for pattern, entity_type in patterns:
      for match in re.finditer(pattern, content):
        name = match.group(1)
        entity_id = f"{file_path}::{name}"
        start = match.start()
        entities[entity_id] = CodeEntity(
          path=file_path,
          type=entity_type,
          name=name,
          content=content[start:min(start+300, len(content))],
          metadata={'position': start}
        )

    return entities

  def extract_imports(self, content: str, file_path: str) -> List[str]:
    """Extract imports using regex patterns"""
    imports = []
    patterns = [
      r'import\s+([^\s;]+)',
      r'from\s+([^\s]+)\s+import',
      r'require\s*\(\s*[\'"]([^\'"]+)[\'"]\s*\)',
      r'#include\s*[<"]([^>"]+)[>"]',
      r'use\s+([^\s;]+)',
    ]

    for pattern in patterns:
      imports.extend(re.findall(pattern, content))

    return imports
