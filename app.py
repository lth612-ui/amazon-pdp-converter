# Safe Streamlit Cloud launcher for the recovered app.
# It keeps the legacy application intact while making startup failures visible.

from pathlib import Path
import traceback

try:
    SOURCE = Path(__file__).with_name("main_recoverd.py")
    code = SOURCE.read_text(encoding="utf-8")

    # Patch stale Gemini model IDs without rewriting the recovered source file.
    code = code.replace(
        '"gemini-3.6-flash" if "Flash" in model_choice else "gemini-3.1-pro"',
        '"gemini-3.8-flash" if "Flash" in model_choice else "gemini-3.1-pro-preview"',
    )

    exec(compile(code, str(SOURCE), "exec"), globals(), globals())
except Exception as exc:
    # Import Streamlit only in the fallback path so a dependency failure in the
    # recovered app can still be displayed instead of killing the process.
    import streamlit as st

    try:
        st.set_page_config(page_title="Amazon PDP Converter · Recovery", page_icon="🛠️", layout="wide")
    except Exception:
        pass

    st.title("🛠️ Amazon PDP Converter 복구 진단")
    st.error(f"앱 시작 중 오류가 발생했습니다: {type(exc).__name__}: {exc}")
    st.caption("아래 진단 정보를 보내주면 다음 수정으로 바로 해결할 수 있습니다.")
    st.code(traceback.format_exc(), language="text")
