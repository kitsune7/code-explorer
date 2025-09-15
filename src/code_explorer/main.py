import os
from .agent import CodebaseExplorerAgent
from smolagents import OpenAIServerModel
import dotenv

def main():
  """
  Runs the Codebase Explorer agent
  """
  dotenv.load_dotenv()

  codebase_path = os.getenv("CODEBASE_PATH", "/Users/chris.bradshaw/Git/vac")

  model = OpenAIServerModel(
    model_id="gemini-2.0-flash-exp",
    api_base="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.getenv("GEMINI_API_KEY"),
  )

  print(f"Initializing Codebase Explorer for: {codebase_path}")
  explorer = CodebaseExplorerAgent(codebase_path, model)

  print("\n" + "="*50)
  print("Codebase Explorer is ready!")
  print(f"Exploring codebase at: {codebase_path}")
  print("="*50)
  print("\nExample queries:")
  print("- What is the overall architecture of this codebase?")
  print("- Find all tool implementations")
  print("- Show me the dependencies of the main module")
  print("- Search for API endpoints or HTTP handlers")
  print("- Deep dive into the smolagents integration")
  print("\nType 'exit' to quit, 'reset' to clear context")
  print("="*50 + "\n")

  while True:
    query = input("Explorer> ")

    if query.lower() == 'exit':
      break
    elif query.lower() == 'reset':
      explorer.reset_context()
      print("Context reset!")
      continue
    elif not query.strip():
      continue

    use_subagent = "deep dive" in query.lower() or "detailed" in query.lower()

    try:
      result = explorer.explore(query, use_subagent=use_subagent)
      print(f"\n{result}\n")
    except Exception as e:
      print(f"Error: {e}\n")

if __name__ == "__main__":
  main()
