from pathlib import Path
import re

import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="System relokacji rowerów",
    layout="wide",
)


APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR.parent

OPERATIONAL_APP_PATH = APP_DIR / "1_Panel_Dyspozytora.py"
TECHNICAL_APP_PATH = APP_DIR / "2_Panel_Techniczny.py"

REQUIRED_LOCAL_DIRECTORIES = [
    PROJECT_ROOT / "outputs_panel_dyspozytora",
    PROJECT_ROOT / "outputs_dzien_stacja",
    PROJECT_ROOT / "input_model_package",
    PROJECT_ROOT / "artifacts",
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


def render_system_info() -> None:
    st.markdown(
        """
        <style id="system-mobile-fix-v1">
        .system-mini-grid {
            display:grid;
            grid-template-columns:repeat(3, minmax(0, 1fr));
            gap:1rem;
            margin:1rem 0 1.6rem 0;
        }
        .system-mini-card {
            border:1px solid #e5e7eb;
            border-radius:18px;
            padding:0.95rem 1rem;
            background:#ffffff;
        }
        .system-mini-label {
            font-size:0.82rem;
            color:#64748b;
            font-weight:700;
            margin-bottom:0.35rem;
            line-height:1.25;
        }
        .system-mini-value {
            font-size:1.2rem;
            color:#111827;
            font-weight:900;
            line-height:1.25;
        }
        .system-flow-grid {
            display:grid;
            grid-template-columns:repeat(6, minmax(0, 1fr));
            gap:0.7rem;
            margin:0.8rem 0 1.5rem 0;
        }
        .system-flow-card {
            border-radius:16px;
            padding:0.9rem;
            text-align:center;
            font-weight:850;
            color:#0f172a;
            min-height:72px;
            display:flex;
            align-items:center;
            justify-content:center;
            line-height:1.15;
            overflow-wrap:anywhere;
        }

        .system-goal-grid {
            display:grid;
            grid-template-columns:repeat(3, minmax(0, 1fr));
            gap:1rem;
            margin-bottom:1.4rem;
        }
        .system-goal-card {
            border:1px solid #e5e7eb;
            border-radius:20px;
            padding:1.1rem 1.2rem;
            background:#ffffff;
            box-shadow:0 10px 24px rgba(15,23,42,0.04);
        }
        .system-goal-card:nth-child(1) {
            border-color:#bfdbfe;
            border-bottom:4px solid #2563eb;
            background:linear-gradient(135deg,#eff6ff 0%,#ffffff 70%);
            box-shadow:0 14px 30px rgba(37,99,235,0.08);
        }
        .system-goal-card:nth-child(2) {
            border-color:#bbf7d0;
            border-bottom:4px solid #16a34a;
            background:linear-gradient(135deg,#f0fdf4 0%,#ffffff 70%);
            box-shadow:0 14px 30px rgba(22,163,74,0.08);
        }
        .system-goal-card:nth-child(3) {
            border-color:#fed7aa;
            border-bottom:4px solid #f97316;
            background:linear-gradient(135deg,#fff7ed 0%,#ffffff 70%);
            box-shadow:0 14px 30px rgba(249,115,22,0.08);
        }
        .system-goal-title {
            font-size:1.15rem;
            font-weight:900;
            color:#0f172a;
            margin-bottom:0.45rem;
            line-height:1.25;
        }
        .system-goal-text {
            font-size:0.95rem;
            color:#64748b;
            line-height:1.5;
        }

        @media (max-width: 640px) {
            .system-mini-grid {
                grid-template-columns:repeat(3, minmax(0, 1fr));
                gap:0.55rem;
                margin:0.8rem 0 1.35rem 0;
            }
            .system-mini-card {
                border-radius:14px;
                padding:0.7rem 0.45rem;
                min-height:6.1rem;
                display:flex;
                flex-direction:column;
                justify-content:center;
                text-align:center;
            }
            .system-mini-label {
                font-size:0.66rem;
                line-height:1.15;
                margin-bottom:0.45rem;
            }
            .system-mini-value {
                font-size:0.9rem;
                line-height:1.18;
            }
            .system-flow-grid {
                grid-template-columns:repeat(3, minmax(0, 1fr));
                gap:0.55rem;
                margin:0.75rem 0 1.35rem 0;
            }
            .system-flow-card {
                border-radius:14px;
                padding:0.65rem 0.35rem;
                min-height:4.4rem;
                font-size:0.78rem;
                line-height:1.15;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div style="border:1px solid #bfdbfe; border-radius:24px; background:linear-gradient(135deg,#eff6ff 0%,#ffffff 60%,#f8fafc 100%); padding:1.7rem 1.9rem; margin-bottom:1.4rem; box-shadow:0 18px 42px rgba(37,99,235,0.10);">
            <div style="font-size:2.15rem; font-weight:950; color:#0f172a; margin-bottom:0.55rem;">
                O systemie
            </div>
            <div style="font-size:1.05rem; color:#64748b; line-height:1.6; max-width:1050px;">
                System relokacji rowerów łączy część operacyjną dla dyspozytora i kierowcy
                z technicznym modułem scoringu dzień–stacja. Aplikacja pokazuje, które stacje wymagają
                obsługi, jaki typ problemu występuje, jakie działanie jest rekomendowane oraz jak wygląda
                status realizacji zadań w terenie.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Cel systemu")

    st.markdown(
        """
        <div class="system-goal-grid">
            <div class="system-goal-card">
                <div class="system-goal-title">Planowanie relokacji</div>
                <div class="system-goal-text">System porządkuje stacje według priorytetu, ryzyka i potencjału operacyjnego.</div>
            </div>
            <div class="system-goal-card">
                <div class="system-goal-title">Obsługa kierowcy</div>
                <div class="system-goal-text">Karta kierowcy przekłada rekomendacje na konkretne zadania do wykonania w rejonach miasta.</div>
            </div>
            <div class="system-goal-card">
                <div class="system-goal-title">Kontrola realizacji</div>
                <div class="system-goal-text">Status realizacji pozwala śledzić przyjęte, wykonane i problematyczne zadania.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Charakter aplikacji")

    st.info(
        "To jest demonstracyjny system operacyjny oparty na historycznych danych z lat 2017–2020. "
        "Wybrana data oznacza dzień operacyjny z danych, a nie aktualny dzień live. "
        "Aplikacja nie udaje bieżącego stanu floty — pokazuje rekomendacje i statusy w trybie historycznego replayu."
    )

    st.markdown(
        """
        <div class="system-mini-grid">
            <div class="system-mini-card">
                <div class="system-mini-label">Typ aplikacji</div>
                <div class="system-mini-value">System<br>operacyjny</div>
            </div>
            <div class="system-mini-card">
                <div class="system-mini-label">Zakres danych</div>
                <div class="system-mini-value">2017–2020</div>
            </div>
            <div class="system-mini-card">
                <div class="system-mini-label">Tryb pracy</div>
                <div class="system-mini-value">Replay<br>historyczny</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Moduły systemu")

    module_df = pd.DataFrame(
        [
            {
                "Moduł": "Panel operacyjny dyspozytora",
                "Rola": "Plan relokacji, mapa stacji, priorytety, karta kierowcy i status realizacji.",
            },
            {
                "Moduł": "Panel techniczny dzień–stacja",
                "Rola": "Scoring, predykcje, diagnostyka modelu, kontrola danych i warstwa techniczna.",
            },
            {
                "Moduł": "Panel główny",
                "Rola": "Wspólna brama wejściowa do części operacyjnej, technicznej i opisu systemu.",
            },
        ]
    )

    st.dataframe(
        module_df,
        width="stretch",
        hide_index=True,
        column_config={
            "Moduł": st.column_config.TextColumn("Moduł", width=260),
            "Rola": st.column_config.TextColumn("Rola", width=900),
        },
    )

    st.markdown("### Przepływ działania")

    st.markdown(
        """
        <div class="system-flow-grid">
            <div class="system-flow-card" style="border:1px solid #dbeafe; background:#eff6ff; color:#1e3a8a;">Dane</div>
            <div class="system-flow-card" style="border:1px solid #e5e7eb; background:#ffffff; color:#0f172a;">Walidacja</div>
            <div class="system-flow-card" style="border:1px solid #e5e7eb; background:#ffffff; color:#0f172a;">Scoring</div>
            <div class="system-flow-card" style="border:1px solid #fee2e2; background:#fff1f2; color:#991b1b;">Priorytety</div>
            <div class="system-flow-card" style="border:1px solid #dcfce7; background:#f0fdf4; color:#166534;">Zadania</div>
            <div class="system-flow-card" style="border:1px solid #fef3c7; background:#fffbeb; color:#92400e;">Status</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Jak czytać aplikację")

    explanation_df = pd.DataFrame(
        [
            {
                "Element": "Plan operacyjny",
                "Znaczenie": "Główny widok dyspozytora: priorytety relokacji, rejony miasta, mapa, lista stacji i szczegóły działań.",
            },
            {
                "Element": "Karta kierowcy",
                "Znaczenie": "Widok zadań terenowych: gdzie jechać, co zrobić, ile rowerów relokować i jaki jest priorytet.",
            },
            {
                "Element": "Status realizacji",
                "Znaczenie": "Historia statusów z terenu: zadania przyjęte, wykonane oraz oznaczone jako problematyczne.",
            },
            {
                "Element": "Panel techniczny dzień–stacja",
                "Znaczenie": "Techniczny moduł modelu: scoring, predykcje, dane wejściowe i kontrola działania warstwy predykcyjnej.",
            },
        ]
    )

    st.dataframe(
        explanation_df,
        width="stretch",
        hide_index=True,
        column_config={
            "Element": st.column_config.TextColumn("Element", width=240),
            "Znaczenie": st.column_config.TextColumn("Znaczenie", width=920),
        },
    )

    st.markdown("### Struktura systemu")

    structure_df = pd.DataFrame(
        [
            {
                "Element": "Panel główny",
                "Plik / folder": "app_main.py",
                "Rola": "Łączy moduł operacyjny, moduł techniczny i sekcję O systemie.",
            },
            {
                "Element": "Moduł operacyjny",
                "Plik / folder": OPERATIONAL_APP_PATH.name,
                "Rola": "Panel dyspozytora, karta kierowcy, status realizacji i widoki operacyjne.",
            },
            {
                "Element": "Moduł techniczny",
                "Plik / folder": TECHNICAL_APP_PATH.name,
                "Rola": "Widok techniczny modelu, scoringu, predykcji i danych dzień–stacja.",
            },
            {
                "Element": "Artefakty operacyjne",
                "Plik / folder": "outputs_panel_dyspozytora",
                "Rola": "Dane wykorzystywane przez panel operacyjny i widoki dyspozytora.",
            },
            {
                "Element": "Artefakty dzień–stacja",
                "Plik / folder": "outputs_dzien_stacja",
                "Rola": "Dane i wyniki wykorzystywane przez moduł techniczny.",
            },
            {
                "Element": "Pakiet modelu",
                "Plik / folder": "input_model_package",
                "Rola": "Zamrożone pliki modelu, konfiguracji i artefaktów scoringu.",
            },
            {
                "Element": "Artefakty pomocnicze",
                "Plik / folder": "artifacts",
                "Rola": "Dodatkowe pliki pomocnicze aplikacji i pipeline.",
            },
        ]
    )

    st.dataframe(
        structure_df,
        width="stretch",
        hide_index=True,
        column_config={
            "Element": st.column_config.TextColumn("Element", width=230),
            "Plik / folder": st.column_config.TextColumn("Plik / folder", width=310),
            "Rola": st.column_config.TextColumn("Rola", width=720),
        },
    )

    st.markdown("### Założenie wersji produkcyjnej")

    prod_col_1, prod_col_2 = st.columns(2)

    with prod_col_1:
        st.markdown(
            """
            **Dane wejściowe**  
            System może być zasilany aktualnymi danymi o stacjach, pojemności, przejazdach,
            pogodzie, kalendarzu i statusach technicznych.

            **Pipeline**  
            Docelowy przepływ obejmuje dane wejściowe, walidację, feature engineering,
            scoring modelu oraz publikację rekomendacji do aplikacji.
            """
        )

    with prod_col_2:
        st.markdown(
            """
            **Monitoring**  
            Warstwa techniczna powinna kontrolować kompletność danych, zgodność kontraktu,
            stabilność artefaktów i jakość predykcji.

            **Użycie operacyjne**  
            Dyspozytor otrzymuje priorytety, kierowca zadania terenowe,
            a system zapisuje status realizacji działań.
            """
        )


with st.sidebar:
    st.markdown(
        """
        <div style="margin-bottom:1.7rem;">
            <div style="font-size:1.15rem; font-weight:900; color:#111827; line-height:1.25;">
                System relokacji rowerów
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div style="font-size:0.78rem; font-weight:900; color:#64748b; letter-spacing:0.05em; margin-bottom:0.7rem;">
            WYBIERZ MODUŁ
        </div>
        """,
        unsafe_allow_html=True,
    )

    selected_module = st.radio(
        label="Wybierz moduł",
        options=[
            "🖥️  Panel operacyjny dyspozytora",
            "⚙️  Panel techniczny dzień-stacja",
            "❗  O systemie",
        ],
        index=0,
        label_visibility="collapsed",
    )

    st.link_button(
        "🔗 GitHub projektu",
        "https://github.com/robert-basinski/system-relokacji-rowerow",
        use_container_width=True,
    )

    st.markdown(
        """
        <div style="height:1px; border-top:1px solid #d1d5db; margin:0.35rem 0 0.25rem 0;"></div>
        """,
        unsafe_allow_html=True,
    )

if selected_module == "🖥️  Panel operacyjny dyspozytora":
    run_streamlit_module(OPERATIONAL_APP_PATH)

elif selected_module == "⚙️  Panel techniczny dzień-stacja":
    run_streamlit_module(TECHNICAL_APP_PATH)

elif selected_module == "❗  O systemie":
    render_system_info()
