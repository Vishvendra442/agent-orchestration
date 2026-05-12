import subprocess
import sys
import tempfile
from pathlib import Path

from langchain_core.tools import tool

from app.runtime.tools.registry import register_tool


@tool
def code_executor(code: str) -> str:
    """Execute Python code in an isolated subprocess and return stdout/stderr. Max 30s timeout."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(code)
        tmp_path = Path(f.name)
    try:
        result = subprocess.run(
            [sys.executable, str(tmp_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        output = result.stdout
        if result.stderr:
            output += f"\n[STDERR]\n{result.stderr}"
        return output.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: code execution timed out (30s limit)"
    except Exception as exc:
        return f"Execution error: {exc}"
    finally:
        tmp_path.unlink(missing_ok=True)


register_tool("code_executor", code_executor)
