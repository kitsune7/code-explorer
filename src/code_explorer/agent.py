"""
Main agent for codebase exploration
"""

from collections import deque
from typing import Optional, List

from smolagents import CodeAgent, ToolCallingAgent, Tool, Model
from .custom_model import QwenInferenceClientModel

from .index import CodebaseIndex
from .tools import (
  SemanticSearchTool,
  DependencyAnalysisTool,
  ReadCodeTool,
  ArchitectureMapperTool
)

class CodebaseExplorerAgent:
  """Main agent for codebase exploration with subagent support"""

  def __init__(self, codebase_path: str, model: Optional[Model] = None):
    if model is None:
      model = QwenInferenceClientModel(model_id="Qwen/Qwen3-4B-Instruct-2507")

    self.codebase_path = codebase_path
    self.index = CodebaseIndex(codebase_path)

    # Build index
    print("Building codebase index...")
    self.index.build_index()

    # Initialize tools
    self.tools = [
      SemanticSearchTool(self.index),
      DependencyAnalysisTool(self.index),
      ReadCodeTool(self.index, codebase_path),
      ArchitectureMapperTool(self.index, codebase_path)
    ]

    # Initialize main agent
    self.agent = ToolCallingAgent(
      tools=self.tools,
      model=model,
      max_steps=20
    )

    # Context management
    self.context_window = deque(maxlen=5)
    self.focus_stack = []

  def explore(self, query: str, use_subagent: bool = False):
    """Main exploration method with optional subagent delegation"""

    # Add query to context
    self.context_window.append(query)

    # Determine if we need a subagent
    if use_subagent and self._needs_detailed_analysis(query):
      return self._delegate_to_subagent(query)

    # Prepare context-aware prompt
    prompt = self._build_context_aware_prompt(query)

    # Execute main agent
    result = self.agent.run(prompt)

    # Update focus stack
    if "analyze" in query.lower() or "explore" in query.lower():
      focus_area = self._extract_focus_area(query)
      if focus_area:
        self.focus_stack.append(focus_area)

    return result

  def _needs_detailed_analysis(self, query: str) -> bool:
    """Determine if query needs subagent delegation"""
    detailed_keywords = ['deep dive', 'detailed', 'comprehensive', 'all', 'every', 'complete']
    return any(keyword in query.lower() for keyword in detailed_keywords)

  def _delegate_to_subagent(self, query: str):
    """Create specialized subagent for detailed analysis"""
    subagent = CodeAgent(
      tools=[self.tools[1], self.tools[2]],  # Dependency and reader tools
      model=self.agent.model,
      max_steps=5
    )

    focused_query = f"Detailed analysis requested: {query}"
    return subagent.run(focused_query)

  def _build_context_aware_prompt(self, query: str) -> str:
    """Build prompt with context awareness"""
    prompt_parts = ["You are a code exploration assistant analyzing a codebase. Your goal is to help developers understand code structure, functionality, and implementation details.",
                    "Consider how the codebase as a whole is organized and how different components interact. Look at files that are commonly used in projects of this type (i.e. package.json in Node.js projects)."]

    if self.focus_stack:
      prompt_parts.append(f"Current focus: {self.focus_stack[-1]}")

    if len(self.context_window) > 1:
      recent = list(self.context_window)[-2:]
      prompt_parts.append(f"Recent queries: {', '.join(recent)}")

    prompt_parts.append(f"User Question: {query}\n")

    prompt_parts.append("Provide a clear, accurate explanation that:")
    prompt_parts.append("1. Directly answers the user's question")
    prompt_parts.append("2. References specific files and line numbers when relevant")
    prompt_parts.append("3. Explains any complex logic or patterns")
    prompt_parts.append("4. Highlights important relationships between components")
    prompt_parts.append("5. Uses appropriate technical terminology")

    prompt_parts.append("Note: Use tools efficiently, start with high-level overview if needed.")

    return "\n".join(prompt_parts)

  def _extract_focus_area(self, query: str) -> Optional[str]:
    """Extract focus area from query"""
    # Look for file paths or entity names
    for entity_path in self.index.entities:
      if entity_path.lower() in query.lower():
        return entity_path
    return None

  def reset_context(self):
    """Reset exploration context"""
    self.context_window.clear()
    self.focus_stack.clear()

  def get_tools(self) -> List[Tool]:
    """Get the list of available tools"""
    return self.tools

  def set_model(self, model):
    """Update the model used by the agent"""
    self.agent.model = model
    # Recreate agent with new model
    self.agent = ToolCallingAgent(
      tools=self.tools,
      model=model,
      max_steps=10
    )
