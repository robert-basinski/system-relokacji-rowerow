from pathlib import Path
import re

import pandas as pd
import textwrap
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
        <style id="system-responsive-layout-v1">
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

        .system-mini-card:nth-child(1) {
            border-color:#bfdbfe;
            border-bottom:4px solid #2563eb;
            background:linear-gradient(135deg,#eff6ff 0%,#ffffff 72%);
            box-shadow:0 12px 28px rgba(37,99,235,0.07);
        }
        .system-mini-card:nth-child(2) {
            border-color:#cbd5e1;
            border-bottom:4px solid #64748b;
            background:linear-gradient(135deg,#f8fafc 0%,#ffffff 72%);
            box-shadow:0 12px 28px rgba(100,116,139,0.07);
        }
        .system-mini-card:nth-child(3) {
            border-color:#c7d2fe;
            border-bottom:4px solid #4f46e5;
            background:linear-gradient(135deg,#eef2ff 0%,#ffffff 72%);
            box-shadow:0 12px 28px rgba(79,70,229,0.07);
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

        @media (max-width: 900px) {
            .system-goal-grid {
                grid-template-columns:1fr !important;
                gap:0.85rem !important;
                margin-bottom:1.35rem !important;
            }
            .system-goal-card {
                width:100% !important;
                min-height:auto !important;
                padding:1rem 1.05rem !important;
            }
            .system-goal-title {
                font-size:1.08rem !important;
                line-height:1.25 !important;
                margin-bottom:0.45rem !important;
                white-space:normal !important;
            }
            .system-goal-text {
                font-size:0.92rem !important;
                line-height:1.45 !important;
                white-space:normal !important;
            }
        }

        </style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div style="border:1px solid #cbd5e1; border-radius:24px; background:linear-gradient(135deg,#eff6ff 0%,#ffffff 60%,#f8fafc 100%); padding:1.7rem 1.9rem; margin-bottom:1.4rem; box-shadow:0 18px 42px rgba(37,99,235,0.10);">
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

    modules_html = (
        '<style>'
        '.system-modules-grid{display:grid;grid-template-columns:1fr;gap:0.48rem;margin:0.65rem 0 1.25rem 0;}'
        '.system-module-card{border:1px solid #cbd5e1;border-radius:16px;padding:0.62rem 0.85rem;background:linear-gradient(135deg,#ffffff 0%,#f8fafc 72%);box-shadow:0 8px 18px rgba(15,23,42,0.045);}'
        '.system-module-header{display:grid;grid-template-columns:260px 1fr;gap:1rem;align-items:start;}'
        '.system-module-name{font-size:0.98rem;font-weight:850;color:#0f172a;line-height:1.25;}'
        '.system-module-file{font-size:0.78rem;color:#64748b;margin-top:0.25rem;font-family:monospace;word-break:break-word;}'
        '.system-module-role{font-size:0.95rem;color:#475569;line-height:1.5;}'
        '@media (max-width:900px){.system-module-header{grid-template-columns:1fr;gap:0.45rem;}.system-module-card{padding:0.9rem 0.95rem;}.system-module-name{font-size:0.98rem;}.system-module-role{font-size:0.9rem;line-height:1.45;}}'
        '</style>'
        '<div class="system-modules-grid">'
        '<div class="system-module-card"><div class="system-module-header"><div><div class="system-module-name">Panel operacyjny dyspozytora</div><div class="system-module-file">app/1_Panel_Dyspozytora.py</div></div><div class="system-module-role">Plan relokacji, mapa stacji, priorytety, karta kierowcy oraz status realizacji zadań.</div></div></div>'
        '<div class="system-module-card"><div class="system-module-header"><div><div class="system-module-name">Panel techniczny dzień–stacja</div><div class="system-module-file">app/2_Panel_Techniczny.py</div></div><div class="system-module-role">Scoring, predykcje, diagnostyka modelu, kontrola danych oraz warstwa techniczna ML.</div></div></div>'
        '<div class="system-module-card"><div class="system-module-header"><div><div class="system-module-name">Panel główny aplikacji</div><div class="system-module-file">app/app_main.py</div></div><div class="system-module-role">Wspólna brama wejściowa do części operacyjnej, technicznej oraz opisu systemu.</div></div></div>'
        '</div>'
    )

    st.markdown(modules_html, unsafe_allow_html=True)

    st.markdown("### Przepływ działania")

    st.markdown(
        """
        <div class="system-flow-grid">
            <div class="system-flow-card" style="border:1px solid #cbd5e1; background:linear-gradient(135deg,#eff6ff 0%,#ffffff 72%); color:#0f172a;">Dane</div>
            <div class="system-flow-card" style="border:1px solid #ddd6fe; background:linear-gradient(135deg,#f5f3ff 0%,#ffffff 72%); color:#0f172a;">Walidacja</div>
            <div class="system-flow-card" style="border:1px solid #bae6fd; background:linear-gradient(135deg,#ecfeff 0%,#ffffff 72%); color:#0f172a;">Scoring</div>
            <div class="system-flow-card" style="border:1px solid #fecaca; background:linear-gradient(135deg,#fff1f2 0%,#ffffff 72%); color:#0f172a;">Priorytety</div>
            <div class="system-flow-card" style="border:1px solid #bbf7d0; background:linear-gradient(135deg,#f0fdf4 0%,#ffffff 72%); color:#0f172a;">Zadania</div>
            <div class="system-flow-card" style="border:1px solid #fde68a; background:linear-gradient(135deg,#fffbeb 0%,#ffffff 72%); color:#0f172a;">Status</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Jak czytać aplikację")

    reading_guide_html = (
        '<style>'
        '.reading-guide-grid{display:grid;grid-template-columns:1fr;gap:0.48rem;margin:0.65rem 0 1.25rem 0;}'
        '.reading-guide-card{border:1px solid #cbd5e1;border-radius:16px;padding:0.95rem 1.05rem;background:linear-gradient(135deg,#ffffff 0%,#f8fafc 72%);box-shadow:0 8px 18px rgba(15,23,42,0.045);}'
        '.reading-guide-row{display:grid;grid-template-columns:260px 1fr;gap:1rem;align-items:start;}'
        '.reading-guide-name{font-size:0.98rem;font-weight:850;color:#0f172a;line-height:1.25;}'
        '.reading-guide-text{font-size:0.95rem;color:#475569;line-height:1.5;}'
        '@media (max-width:900px){.reading-guide-row{grid-template-columns:1fr;gap:0.45rem;}.reading-guide-card{padding:0.9rem 0.95rem;}.reading-guide-name{font-size:0.98rem;}.reading-guide-text{font-size:0.9rem;line-height:1.45;}}'
        '</style>'
        '<div class="reading-guide-grid">'
        '<div class="reading-guide-card"><div class="reading-guide-row"><div class="reading-guide-name">Plan operacyjny</div><div class="reading-guide-text">Główny widok dyspozytora: priorytety relokacji, rejony miasta, mapa, lista stacji oraz szczegóły działań.</div></div></div>'
        '<div class="reading-guide-card"><div class="reading-guide-row"><div class="reading-guide-name">Karta kierowcy</div><div class="reading-guide-text">Widok zadań terenowych: gdzie jechać, co zrobić, ile rowerów relokować i jaki jest priorytet.</div></div></div>'
        '<div class="reading-guide-card"><div class="reading-guide-row"><div class="reading-guide-name">Status realizacji</div><div class="reading-guide-text">Historia statusów z terenu: zadania przyjęte, wykonane oraz oznaczone jako problematyczne.</div></div></div>'
        '<div class="reading-guide-card"><div class="reading-guide-row"><div class="reading-guide-name">Panel techniczny dzień–stacja</div><div class="reading-guide-text">Techniczny moduł modelu: scoring, predykcje, dane wejściowe i kontrola działania warstwy predykcyjnej.</div></div></div>'
        '</div>'
    )

    st.markdown(reading_guide_html, unsafe_allow_html=True)

    st.markdown("### Struktura systemu")

    structure_html = (
        '<style>'
        '.system-structure-grid{display:grid;grid-template-columns:1fr;gap:0.48rem;margin:0.65rem 0 1.25rem 0;}'
        '.system-structure-card{border:1px solid #cbd5e1;border-radius:16px;padding:0.62rem 0.85rem;background:linear-gradient(135deg,#ffffff 0%,#f8fafc 72%);box-shadow:0 8px 18px rgba(15,23,42,0.045);}'
        '.system-structure-row{display:grid;grid-template-columns:230px 250px 1fr;gap:0.75rem;align-items:start;}'
        '.system-structure-label{font-size:0.68rem;color:#64748b;margin-bottom:0.12rem;line-height:1.2;}'
        '.system-structure-name{font-size:0.86rem;font-weight:800;color:#0f172a;line-height:1.25;}'
        '.system-structure-file{font-size:0.82rem;color:#334155;line-height:1.25;font-family:monospace;word-break:break-word;}'
        '.system-structure-role{font-size:0.84rem;color:#475569;line-height:1.32;}'
        '@media (max-width:900px){.system-structure-row{grid-template-columns:1fr;gap:0.45rem;}.system-structure-card{padding:0.72rem 0.85rem;}.system-structure-name{font-size:0.9rem;}.system-structure-file{font-size:0.8rem;}.system-structure-role{font-size:0.84rem;line-height:1.35;}}'
        '</style>'
        '<div class="system-structure-grid">'
        '<div class="system-structure-card"><div class="system-structure-row"><div><div class="system-structure-label">Element</div><div class="system-structure-name">Panel główny</div></div><div><div class="system-structure-label">Plik / folder</div><div class="system-structure-file">app_main.py</div></div><div><div class="system-structure-label">Rola</div><div class="system-structure-role">Łączy moduł operacyjny, moduł techniczny i sekcję O systemie.</div></div></div></div>'
        '<div class="system-structure-card"><div class="system-structure-row"><div><div class="system-structure-label">Element</div><div class="system-structure-name">Moduł operacyjny</div></div><div><div class="system-structure-label">Plik / folder</div><div class="system-structure-file">1_Panel_Dyspozytora.py</div></div><div><div class="system-structure-label">Rola</div><div class="system-structure-role">Panel dyspozytora, karta kierowcy, status realizacji i widoki operacyjne.</div></div></div></div>'
        '<div class="system-structure-card"><div class="system-structure-row"><div><div class="system-structure-label">Element</div><div class="system-structure-name">Moduł techniczny</div></div><div><div class="system-structure-label">Plik / folder</div><div class="system-structure-file">2_Panel_Techniczny.py</div></div><div><div class="system-structure-label">Rola</div><div class="system-structure-role">Widok techniczny modelu, scoringu, predykcji i danych dzień–stacja.</div></div></div></div>'
        '<div class="system-structure-card"><div class="system-structure-row"><div><div class="system-structure-label">Element</div><div class="system-structure-name">Artefakty operacyjne</div></div><div><div class="system-structure-label">Plik / folder</div><div class="system-structure-file">outputs_panel_dyspozytora</div></div><div><div class="system-structure-label">Rola</div><div class="system-structure-role">Dane wykorzystywane przez panel operacyjny i widoki dyspozytora.</div></div></div></div>'
        '<div class="system-structure-card"><div class="system-structure-row"><div><div class="system-structure-label">Element</div><div class="system-structure-name">Artefakty dzień–stacja</div></div><div><div class="system-structure-label">Plik / folder</div><div class="system-structure-file">outputs_dzien_stacja</div></div><div><div class="system-structure-label">Rola</div><div class="system-structure-role">Dane i wyniki wykorzystywane przez moduł techniczny.</div></div></div></div>'
        '<div class="system-structure-card"><div class="system-structure-row"><div><div class="system-structure-label">Element</div><div class="system-structure-name">Pakiet modelu</div></div><div><div class="system-structure-label">Plik / folder</div><div class="system-structure-file">input_model_package</div></div><div><div class="system-structure-label">Rola</div><div class="system-structure-role">Zamrożone pliki modelu, konfiguracji i artefaktów scoringu.</div></div></div></div>'
        '<div class="system-structure-card"><div class="system-structure-row"><div><div class="system-structure-label">Element</div><div class="system-structure-name">Artefakty pomocnicze</div></div><div><div class="system-structure-label">Plik / folder</div><div class="system-structure-file">artifacts</div></div><div><div class="system-structure-label">Rola</div><div class="system-structure-role">Dodatkowe pliki pomocnicze aplikacji i pipeline.</div></div></div></div>'
        '</div>'
    )

    st.markdown(structure_html, unsafe_allow_html=True)

    st.markdown("### Dane historyczne a wersja produkcyjna")

    st.markdown(
        """
        <div style="border:1px solid #cbd5e1;  border-radius:18px; padding:1.05rem 1.15rem; background:linear-gradient(135deg,#eff6ff 0%,#ffffff 72%); box-shadow:0 10px 22px rgba(37,99,235,0.06); margin:0.7rem 0 1.4rem 0;">
            <div style="font-size:0.98rem; color:#334155; line-height:1.6;">
                Projekt działa jako <b>production-like batch ML system</b> oparty na publicznym zbiorze danych
                <b>Helsinki City Bikes</b>, obejmującym ponad <b>10 milionów przejazdów</b> z lat 2016–2020.
                System nie udaje aplikacji live, ponieważ pełna wersja produkcyjna wymagałaby dostępu do
                aktualnych danych operatora, takich jak bieżące stany rowerów, wolne miejsca, aktualne przejazdy,
                API oraz harmonogram aktualizacji.
                <br><br>
                Po podłączeniu takich źródeł danych ten sam przepływ można rozwinąć do systemu produkcyjnego
                działającego na aktualnych danych.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### Założenie wersji produkcyjnej")

    st.markdown(
        """
        <style>
        .production-assumption-grid {
            display:grid;
            grid-template-columns:repeat(2, minmax(0, 1fr));
            gap:1rem;
            margin:0.9rem 0 1.4rem 0;
        }
        .production-assumption-card {
            border:1px solid #e5e7eb;
            border-radius:18px;
            padding:1.05rem 1.15rem;
            background:linear-gradient(135deg,#ffffff 0%,#f8fafc 100%);
            box-shadow:0 10px 22px rgba(15,23,42,0.045);
        }
        .production-assumption-card:nth-child(1) {
            border-color:#bfdbfe;
            
            background:linear-gradient(135deg,#eff6ff 0%,#ffffff 72%);
        }
        .production-assumption-card:nth-child(2) {
            border-color:#bfdbfe;
            
            background:linear-gradient(135deg,#eff6ff 0%,#ffffff 72%);
        }
        .production-assumption-card:nth-child(3) {
            border-color:#bfdbfe;
            
            background:linear-gradient(135deg,#eff6ff 0%,#ffffff 72%);
        }
        .production-assumption-card:nth-child(4) {
            border-color:#bfdbfe;
            
            background:linear-gradient(135deg,#eff6ff 0%,#ffffff 72%);
        }
        .production-assumption-title {
            font-size:1rem;
            font-weight:850;
            color:#0f172a;
            margin-bottom:0.45rem;
            line-height:1.25;
        }
        .production-assumption-text {
            font-size:0.95rem;
            color:#475569;
            line-height:1.55;
        }
        @media (max-width: 900px) {
            .production-assumption-grid {
                grid-template-columns:1fr;
                gap:0.8rem;
            }
            .production-assumption-card {
                padding:1rem 1.05rem;
            }
            .production-assumption-title {
                font-size:1rem;
            }
            .production-assumption-text {
                font-size:0.9rem;
                line-height:1.45;
            }
        }
        </style>

        <div class="production-assumption-grid">
            <div class="production-assumption-card">
                <div class="production-assumption-title">Dane wejściowe</div>
                <div class="production-assumption-text">
                    System może być zasilany aktualnymi danymi o stacjach, pojemności, przejazdach,
                    pogodzie, kalendarzu i statusach technicznych.
                </div>
            </div>
            <div class="production-assumption-card">
                <div class="production-assumption-title">Monitoring</div>
                <div class="production-assumption-text">
                    Warstwa techniczna powinna kontrolować kompletność danych, zgodność kontraktu,
                    stabilność artefaktów i jakość predykcji.
                </div>
            </div>
            <div class="production-assumption-card">
                <div class="production-assumption-title">Pipeline</div>
                <div class="production-assumption-text">
                    Docelowy przepływ obejmuje dane wejściowe, walidację, feature engineering,
                    scoring modelu oraz publikację rekomendacji do aplikacji.
                </div>
            </div>
            <div class="production-assumption-card">
                <div class="production-assumption-title">Użycie operacyjne</div>
                <div class="production-assumption-text">
                    Dyspozytor otrzymuje priorytety, kierowca zadania terenowe,
                    a system zapisuje status realizacji działań.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
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
