"""
Main agent for codebase exploration
"""

from collections import deque
from typing import Optional, List

from smolagents import CodeAgent, ToolCallingAgent, Tool

from .index import CodebaseIndex
from .tools import (
  SemanticSearchTool,
  DependencyAnalysisTool,
  SmartCodeReaderTool,
  ArchitectureMapperTool
)

class CodebaseExplorerAgent:
  """Main agent for codebase exploration with subagent support"""

  def __init__(self, codebase_path: str, model_name: str = "HuggingFaceH4/starchat2-15b-v0.1"):
    self.codebase_path = codebase_path
    self.index = CodebaseIndex(codebase_path)

    # Build index
    print("Building codebase index...")
    self.index.build_index()

    # Initialize tools
    self.tools = [
      SemanticSearchTool(self.index),
      DependencyAnalysisTool(self.index),
      SmartCodeReaderTool(self.index, codebase_path),
      ArchitectureMapperTool(self.index, codebase_path)
    ]

    # Initialize main agent
    self.agent = ToolCallingAgent(
      tools=self.tools,
      model=model_name,
      max_steps=10
    )

    # Context management
    self.context_window = deque(maxlen=5)
    self.focus_stack = []

  def explore(self, query: str, use_subagent: bool = False) -> str:
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

  def _delegate_to_subagent(self, query: str) -> str:
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
    prompt_parts = []

    if self.focus_stack:
      prompt_parts.append(f"Current focus: {self.focus_stack[-1]}")

    if len(self.context_window) > 1:
      recent = list(self.context_window)[-2:]
      prompt_parts.append(f"Recent queries: {', '.join(recent)}")

    prompt_parts.append(f"Query: {query}")
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
