"""
Utility functions for codebase exploration
"""

import os
from pathlib import Path
from typing import List, Set, Optional
import logging

# Set up logging
logger = logging.getLogger(__name__)

def should_skip_path(path: Path, skip_patterns: Optional[Set[str]] = None) -> bool:
  """
  Determine if a path should be skipped during indexing

  Args:
    path: Path to check
    skip_patterns: Additional patterns to skip

  Returns:
    True if the path should be skipped
  """
  default_skip = {
    '.git', '.svn', '.hg',  # Version control
    'node_modules', 'bower_components',  # JS dependencies
    'venv', '.venv', 'env', '.env', '__pycache__',  # Python
    'target', 'build', 'dist', 'out',  # Build outputs
    '.pytest_cache', '.tox', '.coverage',  # Testing
    '.idea', '.vscode', '.settings',  # IDEs
    'vendor',  # Various dependency managers
    '.DS_Store', 'Thumbs.db',  # OS files
  }

  if skip_patterns:
    default_skip.update(skip_patterns)

  # Check each part of the path
  for part in path.parts:
    if part.startswith('.') and part != '.':
      return True
    if part in default_skip:
      return True

  # Check file extensions to skip
  skip_extensions = {'.pyc', '.pyo', '.so', '.dll', '.dylib', '.exe', '.bin'}
  if path.suffix in skip_extensions:
    return True

  return False


def estimate_memory_usage(file_count: int, avg_file_size: int = 5000) -> str:
  """
  Estimate memory usage for indexing

  Args:
    file_count: Number of files to index
    avg_file_size: Average file size in bytes

  Returns:
    Human-readable memory estimate
  """
  kbSize = 1024
  base_overhead = 100  # bytes per file for metadata
  entity_overhead = 500  # bytes per entity
  avg_entities_per_file = 10

  total_bytes = file_count * (avg_file_size + base_overhead + (entity_overhead * avg_entities_per_file))

  if total_bytes < kbSize:
    return f"{total_bytes} B"
  elif total_bytes < kbSize * kbSize:
    return f"{total_bytes / kbSize:.1f} KB"
  elif total_bytes < kbSize * kbSize * kbSize:
    return f"{total_bytes / (kbSize * kbSize):.1f} MB"
  else:
    return f"{total_bytes / (kbSize * kbSize * kbSize):.1f} GB"


def get_project_type(root_path: Path) -> str:
  """
  Detect the type of project based on configuration files

  Args:
    root_path: Root path of the project

  Returns:
    Project type string
  """
  indicators = {
    'python': ['pyproject.toml', 'setup.py', 'requirements.txt', 'Pipfile'],
    'javascript': ['package.json', 'yarn.lock', 'npm-shrinkwrap.json', 'pnpmfile.yaml'],
    'typescript': ['tsconfig.json'],
    'java': ['pom.xml', 'build.gradle', 'build.gradle.kts'],
    'rust': ['Cargo.toml'],
    'go': ['go.mod'],
    'ruby': ['Gemfile'],
    'php': ['composer.json'],
    'csharp': ['.csproj', '.sln'],
    'swift': ['Package.swift'],
  }

  detected = []
  for lang, files in indicators.items():
    for file in files:
      if (root_path / file).exists():
        detected.append(lang)
        break

  if not detected:
    return "unknown"
  elif len(detected) == 1:
    return detected[0]
  else:
    return f"mixed ({', '.join(detected)})"


def format_file_size(size_bytes: float) -> str:
  """
  Format file size in human-readable format

  Args:
    size_bytes: Size in bytes

  Returns:
    Human-readable size string
  """
  kbSize = 1024
  for unit in ['B', 'KB', 'MB', 'GB']:
    if size_bytes < kbSize:
      return f"{size_bytes:.1f} {unit}"
    size_bytes /= kbSize
  return f"{size_bytes:.1f} TB"


def count_files_to_index(root_path: Path, extensions: List[str]) -> int:
  """
  Count files that will be indexed

  Args:
    root_path: Root path to scan
    extensions: File extensions to include

  Returns:
    Number of files that will be indexed
  """
  count = 0
  for file_path in root_path.rglob('*'):
    if file_path.is_file() and file_path.suffix in extensions:
      if not should_skip_path(file_path):
        count += 1
  return count


def validate_codebase_path(path: str) -> Path:
  """
  Validate that a codebase path exists and is accessible

  Args:
    path: Path string to validate

  Returns:
    Validated Path object

  Raises:
    ValueError: If path is invalid
  """
  path_obj = Path(path).resolve()

  if not path_obj.exists():
    raise ValueError(f"Path does not exist: {path}")

  if not path_obj.is_dir():
    raise ValueError(f"Path is not a directory: {path}")

  if not os.access(path_obj, os.R_OK):
    raise ValueError(f"Path is not readable: {path}")

  return path_obj
