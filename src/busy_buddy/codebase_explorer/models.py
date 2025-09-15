"""
Data models for codebase exploration
"""

from dataclasses import dataclass, field
from typing import Dict, Set, Optional, Any
import numpy as np


@dataclass
class CodeEntity:
  """Represents a code entity (file, class, function, etc.)"""
  path: str
  type: str  # 'file', 'class', 'function', 'method', 'interface', 'struct', etc.
  name: str
  content: str
  summary: Optional[str] = None
  dependencies: Set[str] = field(default_factory=set)
  ast_hash: Optional[str] = None
  embedding: Optional[np.ndarray] = None
  metadata: Dict[str, Any] = field(default_factory=dict)
