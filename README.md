# Code Explorer

Code Explorer is an AI agent that can answer questions about codebases. It can be used to explore unfamiliar code, understand complex logic, and find specific implementations or patterns.

## Setup

This agent uses Gemini under the hood to run its AI agent. You'll need to make sure you have a `GEMINI_API_KEY` set in your environment. If it's not already set in your shell by default, it's recommended that you add a `.env` file with your Gemini API key like this:

```shell
GEMINI_API_KEY=<your_gemini_api_key>
```

After that, setting up [uv](https://docs.astral.sh/uv/) and a virtual environment can ensure that things run smoothly and easily. It's possible to run without it, but it's not recommended.

### `uv` Setup

#### Mac OS / Linux

Just run `make setup` to take care of installing `uv` (if needed) and generating the virtual environment needed for package isolation.

#### Windows

You can find [installation instructions for `uv`](https://docs.astral.sh/uv/getting-started/installation/) on their website.

After installing `uv`, you'll want to set up the virtual environment by running `uv sync --frozen`.

## How to run

### With `uv`

As long as `uv` is installed, you can just run this.

```shell
uv run python -m src.busy_buddy.main
```

This works on any OS with `uv`.

If you have Make installed, you can also just run `make run`.

### Without `uv` (not recommended)

If you'd prefer not to install `uv`, then you can just use pip to install the dependencies from `pyproject.toml`. You can also set up a virtual environment if you'd like to isolate the dependencies.

Then just run `./run.py`.

## Running Tests

You can use uv to run tests.

To do this, first, you'll want to run

```shell
uv sync --group dev
```

to ensure dev dependencies are installed.

Then you can just run

```shell
uv run pytest -q
```
