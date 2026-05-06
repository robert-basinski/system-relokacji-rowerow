from pathlib import Path
import re

import streamlit as st


st.set_page_config(
    page_title="System relokacji rowerów",
    layout="wide",
)


APP_DIR = Path(__file__).resolve().parent

OPERATIONAL_APP_PATH = APP_DIR / "aplikacja_panel_dyspozytora_rowerow.py"
TECHNICAL_APP_PATH = APP_DIR / "aplikacja_dzien_stacja.py"

REQUIRED_LOCAL_DIRECTORIES = [
    APP_DIR / "outputs_panel_dyspozytora",
    APP_DIR / "outputs_dzien_stacja",
    APP_DIR / "input_model_package",
    APP_DIR / "artifacts",
]


def validate_system_structure() -> None:
    missing_paths = []

    for path in [OPERATIONAL_APP_PATH, TECHNICAL_APP_PATH] + REQUIRED_LOCAL_DIRECTORIES:
        if not path.exists():
            missing_paths.append(str(path))

    if missing_paths:
        st.error("Brakuje wymaganych elementów finalnej aplikacji.")
        st.write(missing_paths)
        st.stop()


def run_streamlit_module(module_path: Path) -> None:
    code = module_path.read_text(encoding="utf-8")

    code = re.sub(
        r"\n?st\.set_page_config\(\n(?:.|\n)*?\n\)\n\n",
        "\n\n",
        code,
        count=1,
    )

    exec(
        compile(code, str(module_path), "exec"),
        {
            "__file__": str(module_path),
            "__name__": f"embedded_{module_path.stem}",
        },
    )


validate_system_structure()


with st.sidebar:
    st.markdown("## System relokacji rowerów")
    st.markdown(
        "<div style='font-size:0.9rem;color:#6b7280;margin-top:-10px;margin-bottom:20px;'>Wspólna aplikacja operacyjna i techniczna</div>",
        unsafe_allow_html=True,
    )

    selected_panel = st.radio(
        "Wybierz moduł",
        [
            "Panel operacyjny dyspozytora",
            "Panel techniczny dzień-stacja",
        ],
        index=0,
    )

    with st.expander("Struktura systemu"):
        st.markdown("**Moduł operacyjny:**")
        st.code(OPERATIONAL_APP_PATH.name)

        st.markdown("**Moduł techniczny:**")
        st.code(TECHNICAL_APP_PATH.name)

        st.markdown("**Wymagane foldery artefaktów:**")
        for directory_path in REQUIRED_LOCAL_DIRECTORIES:
            st.code(directory_path.name)


if selected_panel == "Panel operacyjny dyspozytora":
    run_streamlit_module(OPERATIONAL_APP_PATH)

elif selected_panel == "Panel techniczny dzień-stacja":
    run_streamlit_module(TECHNICAL_APP_PATH)