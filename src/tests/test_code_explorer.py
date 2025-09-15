"""
Tests for codebase explorer functionality
"""

from pathlib import Path
import pytest
from unittest.mock import Mock, patch

from code_explorer import (
  CodebaseExplorerAgent,
  CodebaseIndex,
  CodeEntity,
  SemanticSearchTool,
  DependencyAnalysisTool,
  ReadCodeTool,
  ArchitectureMapperTool
)
from code_explorer.utils import (
  should_skip_path,
  get_project_type,
  estimate_memory_usage,
  validate_codebase_path
)


class TestCodeEntity:
  """Test the CodeEntity data model"""

  def test_code_entity_creation(self):
    """Test creating a code entity"""
    entity = CodeEntity(
      path="test.py",
      type="function",
      name="test_func",
      content="def test_func(): pass"
    )

    assert entity.path == "test.py"
    assert entity.type == "function"
    assert entity.name == "test_func"
    assert entity.content == "def test_func(): pass"
    assert entity.dependencies == set()
    assert entity.metadata == {}


class TestUtils:
  """Test utility functions"""

  def test_should_skip_path(self):
    """Test path skipping logic"""
    # Should skip hidden directories
    assert should_skip_path(Path(".git/config"))
    assert should_skip_path(Path("project/.venv/lib"))

    # Should skip common build directories
    assert should_skip_path(Path("node_modules/package"))
    assert should_skip_path(Path("build/output.js"))

    # Should not skip normal source files
    assert not should_skip_path(Path("src/main.py"))
    assert not should_skip_path(Path("lib/utils.js"))

  def test_get_project_type(self, tmp_path):
    """Test project type detection"""
    # Python project
    (tmp_path / "pyproject.toml").touch()
    assert get_project_type(tmp_path) == "python"

    # JavaScript project
    (tmp_path / "package.json").touch()
    assert "javascript" in get_project_type(tmp_path)

    # Mixed project
    (tmp_path / "go.mod").touch()
    result = get_project_type(tmp_path)
    assert "mixed" in result

  def test_estimate_memory_usage(self):
    """Test memory usage estimation"""
    # Small project
    assert "KB" in estimate_memory_usage(10)

    # Medium project
    assert "MB" in estimate_memory_usage(1000)

  def test_validate_codebase_path(self, tmp_path):
    """Test codebase path validation"""
    # Valid path
    valid_path = validate_codebase_path(str(tmp_path))
    assert valid_path == tmp_path.resolve()

    # Invalid path
    with pytest.raises(ValueError, match="does not exist"):
      validate_codebase_path("/nonexistent/path")

    # File instead of directory
    file_path = tmp_path / "file.txt"
    file_path.touch()
    with pytest.raises(ValueError, match="not a directory"):
      validate_codebase_path(str(file_path))


class TestCodebaseIndex:
  """Test the codebase indexing system"""

  def test_index_creation(self, tmp_path):
    """Test creating a codebase index"""
    index = CodebaseIndex(str(tmp_path))

    assert index.root_path == tmp_path
    assert len(index.entities) == 0
    assert index.dependency_graph.number_of_nodes() == 0

  def test_index_python_file(self, tmp_path):
    """Test indexing a Python file"""
    # Create a simple Python file
    python_file = tmp_path / "test.py"
    python_file.write_text("""
def hello():
  return "world"

class TestClass:
  def method(self):
    pass
""")

    index = CodebaseIndex(str(tmp_path))
    index.build_index(show_progress=False)

    # Check that entities were created
    assert len(index.entities) > 0

    # Check for specific entities
    entities = list(index.entities.keys())
    assert any("test.py" in e for e in entities)

    # If tree-sitter is available, we should have more detailed entities
    if index.parser.__class__.__name__ == "TreeSitterParser":
      assert any("hello" in e for e in entities)
      assert any("TestClass" in e for e in entities)

  def test_dependency_resolution(self, tmp_path):
    """Test import dependency resolution"""
    # Create files with imports
    (tmp_path / "main.py").write_text("import utils")
    (tmp_path / "utils.py").write_text("def helper(): pass")

    index = CodebaseIndex(str(tmp_path))
    index.build_index(show_progress=False)

    # Check dependency graph
    assert index.dependency_graph.number_of_nodes() >= 2

    # Check for dependency edge
    if "main.py" in index.dependency_graph:
      successors = list(index.dependency_graph.successors("main.py"))
      assert any("utils" in s for s in successors)


class TestTools:
  """Test the individual tools"""

  @pytest.fixture
  def mock_index(self):
    """Create a mock index with sample data"""
    index = Mock(spec=CodebaseIndex)
    index.entities = {
      "file1.py": CodeEntity(
        path="file1.py",
        type="file",
        name="file1.py",
        content="# File 1"
      ),
      "file1.py::func1": CodeEntity(
        path="file1.py",
        type="function",
        name="func1",
        content="def func1(): pass",
        metadata={"start_line": 1}
      ),
      "file2.py::ClassA": CodeEntity(
        path="file2.py",
        type="class",
        name="ClassA",
        content="class ClassA: pass",
        metadata={"start_line": 5}
      )
    }

    # Mock dependency graph
    import networkx as nx
    index.dependency_graph = nx.DiGraph()
    index.dependency_graph.add_edge("file1.py", "file2.py")

    # Mock tokenizer and model
    index.tokenizer = Mock()
    index.model = Mock()

    return index

  def test_semantic_search_tool(self, mock_index):
    """Test semantic search functionality"""
    tool = SemanticSearchTool(mock_index)

    # Mock the embedding generation
    with patch.object(tool, '_get_embedding', return_value=[0.1, 0.2, 0.3]):
      result = tool.forward("search query", max_results=2)

    assert result  # Should return some results
    assert isinstance(result, str)

  def test_dependency_analysis_tool(self, mock_index):
    """Test dependency analysis"""
    tool = DependencyAnalysisTool(mock_index)

    result = tool.forward("file1.py", direction="imports", depth=1)

    assert "Dependencies for file1.py" in result
    assert "file2.py" in result

  def test_read_code_tool(self, tmp_path, mock_index):
    """Test code reading functionality"""
    # Create a test file
    test_file = tmp_path / "test.py"
    test_file.write_text("def test():\n    return 42")

    tool = ReadCodeTool(mock_index, str(tmp_path))

    # Test full mode
    result = tool.forward("test.py", mode="full")
    assert "def test()" in result

  def test_architecture_mapper_tool(self, mock_index, tmp_path):
    """Test architecture mapping"""
    tool = ArchitectureMapperTool(mock_index, str(tmp_path))

    result = tool.forward()

    assert "Codebase Architecture" in result
    assert "Entry points" in result


class TestCodebaseExplorerAgent:
  """Test the main agent"""

  def test_agent_creation(self, tmp_path):
    """Test creating the agent"""
    # Create a minimal codebase
    (tmp_path / "test.py").write_text("print('hello')")

    with patch('code_explorer.agent.ToolCallingAgent'):
      agent = CodebaseExplorerAgent(str(tmp_path))

      assert agent.codebase_path == str(tmp_path)
      assert len(agent.tools) == 4
      assert len(agent.context_window) == 0

  def test_context_management(self, tmp_path):
    """Test context window and focus stack"""
    (tmp_path / "test.py").write_text("print('hello')")

    with patch('code_explorer.agent.ToolCallingAgent'):
      agent = CodebaseExplorerAgent(str(tmp_path))

      # Add queries to context
      agent.context_window.append("query1")
      agent.context_window.append("query2")

      assert len(agent.context_window) == 2

      # Reset context
      agent.reset_context()
      assert len(agent.context_window) == 0
      assert len(agent.focus_stack) == 0

  def test_detailed_analysis_detection(self, tmp_path):
    """Test detection of queries needing detailed analysis"""
    (tmp_path / "test.py").write_text("print('hello')")

    with patch('code_explorer.agent.ToolCallingAgent'):
      agent = CodebaseExplorerAgent(str(tmp_path))

      assert agent._needs_detailed_analysis("deep dive into the code")
      assert agent._needs_detailed_analysis("comprehensive analysis")
      assert not agent._needs_detailed_analysis("show me the main function")
