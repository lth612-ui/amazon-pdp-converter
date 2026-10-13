# Streamlit Cloud entry point
# The full application lives in main_recoverd.py.
# This launcher keeps compatibility with the original deployment path while
# patching stale Gemini model IDs at runtime.

from pathlib import Path

SOURCE = Path(__file__).with_name("main_recoverd.py")
code = SOURCE.read_text(encoding="utf-8")

# Keep the recovered app intact, but update model IDs to currently supported ones.
code = code.replace('"gemini-3.6-flash" if "Flash" in model_choice else "gemini-3.1-pro"',
                    '"gemini-3.8-flash" if "Flash" in model_choice else "gemini-3.1-pro-preview"')

exec(compile(code, str(SOURCE), "exec"), globals(), globals())
