from pathlib import Path
import json

import folium
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components


st.set_page_config(
    page_title="Panel dyspozytora relokacji rowerów",
    layout="wide",
)


APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent

PANEL_OUTPUTS_DIR = PROJECT_DIR / "outputs_panel_dyspozytora"

APP_CONTRACT_PATH = PANEL_OUTPUTS_DIR / "b6_49_dispatcher_app_contract.json"
TAB_CONTRACT_PATH = PANEL_OUTPUTS_DIR / "b6_49_dispatcher_app_tab_contract.parquet"
USER_LABELS_PATH = PANEL_OUTPUTS_DIR / "b6_52_dispatcher_app_user_labels.parquet"

MAP_STATION_LAYER_PATH = PANEL_OUTPUTS_DIR / "b6_45_map_station_layer.parquet"
MICROZONE_SUMMARY_PATH = PANEL_OUTPUTS_DIR / "b6_34_microzone_summary.parquet"
LOCAL_PAIRS_PATH = PANEL_OUTPUTS_DIR / "b6_35_microzone_local_pairs.parquet"
RELOCATION_LINE_LAYER_PATH = PANEL_OUTPUTS_DIR / "b6_48_relocation_line_layer.parquet"
ACTION_MAP_HTML_PATH = PANEL_OUTPUTS_DIR / "b6_47_action_map_top50.html"

DRIVER_TASK_LAYER_PATH = PANEL_OUTPUTS_DIR / "b6_57_driver_task_card_layer.parquet"
DAILY_DRIVER_CARDS_PATH = PANEL_OUTPUTS_DIR / "b6_58_daily_driver_task_cards.parquet"
FEEDBACK_LOG_PATH = PANEL_OUTPUTS_DIR / "b6_operational_feedback_log.json"
FEEDBACK_STATE_KEY = "operational_feedback_log"


@st.cache_data
def load_json_data(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json_data(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)



def initialize_feedback_log() -> dict:
    if FEEDBACK_STATE_KEY not in st.session_state:
        if FEEDBACK_LOG_PATH.exists():
            base_feedback_log = load_json_data(str(FEEDBACK_LOG_PATH))
        else:
            base_feedback_log = {"entries": []}

        st.session_state[FEEDBACK_STATE_KEY] = {
            "entries": list(base_feedback_log.get("entries", []))
        }

    return st.session_state[FEEDBACK_STATE_KEY]


def append_feedback_entry(entry: dict) -> None:
    feedback_data = initialize_feedback_log()
    feedback_entries = list(feedback_data.get("entries", []))

    feedback_entries.append(entry)
    feedback_data["entries"] = feedback_entries

    st.session_state[FEEDBACK_STATE_KEY] = feedback_data



def build_feedback_entry(status: str, row: pd.Series, selected_date: object) -> dict:
    return {
        "created_at_utc": pd.Timestamp.utcnow().isoformat(),
        "activity_date": str(selected_date),
        "task_rank": int(row.get("Lp.", 0)),
        "station_name": str(row.get("Stacja", "")),
        "microzone_id": str(row.get("Mikrostrefa", "")),
        "priority": str(row.get("Pilność", "")),
        "problem": str(row.get("Co grozi", "")),
        "recommended_action": str(row.get("Zalecane działanie", "")),
        "relocation": str(row.get("Szacowana relokacja", "")),
        "risk_hour": str(row.get("Godzina ryzyka", "")),
        "confidence": str(row.get("Pewność", "")),
        "status": status,
    }


def get_latest_feedback_status(feedback_log: dict, task_rank: int, station_name: str) -> str:
    feedback_entries = feedback_log.get("entries", [])

    if not feedback_entries:
        return ""

    matching_entries = [
        entry
        for entry in feedback_entries
        if int(entry.get("task_rank", -1)) == int(task_rank)
        and str(entry.get("station_name", "")) == str(station_name)
    ]

    if not matching_entries:
        return ""

    latest_entry = sorted(
        matching_entries,
        key=lambda entry: str(entry.get("created_at_utc", "")),
        reverse=True,
    )[0]

    return str(latest_entry.get("status", ""))


@st.cache_data
def load_parquet_data(path: str) -> pd.DataFrame:
    return pd.read_parquet(path)


@st.cache_data
def load_html_data(path: str) -> str:
    with open(path, "r", encoding="utf-8") as file:
        return file.read()


def require_paths(paths: list[Path]) -> None:
    missing_paths = [str(path) for path in paths if not path.exists()]

    if missing_paths:
        st.error("Brakuje wymaganych artefaktów aplikacji.")
        st.write(missing_paths)
        st.stop()


def format_number(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ")

def format_relocation_label(value: object) -> str:
    if pd.isna(value):
        return "brak danych"

    label = str(value).strip()

    if label == "check":
        return "sprawdź stan stacji"

    if label.startswith("deliver "):
        amount = label.replace("deliver ", "").replace("-", "-")
        return f"dowieź {amount} rowerów"

    if label.startswith("remove "):
        amount = label.replace("remove ", "").replace("-", "-")
        return f"zabierz {amount} rowerów"

    return label

def build_operational_view(df: pd.DataFrame) -> pd.DataFrame:
    priority_labels = {
        "very_high": "bardzo wysoki",
        "high": "wysoki",
        "medium": "średni",
        "low": "niski",
    }

    problem_type_labels = {
        "bike_shortage_risk": "ryzyko braku rowerów",
        "dock_shortage_risk": "ryzyko braku miejsc",
        "mixed_risk": "sytuacja mieszana",
        "no_clear_signal": "brak jednoznacznego sygnału",
    }

    action_labels = {
        "deliver_bikes": "dowieź rowery",
        "remove_bikes": "zabierz rowery",
        "check_station": "sprawdź stację",
        "check_station_state": "sprawdź stan stacji",
        "no_action": "bez działania",
    }

    confidence_labels = {
        "high": "wysoka",
        "medium": "średnia",
        "low": "niska",
    }

    view_df = df.copy()

    view_df["Pilność"] = (
        view_df["priority_level"]
        .map(priority_labels)
        .fillna(view_df["priority_level"])
    )

    view_df["Co grozi"] = (
        view_df["problem_type"]
        .map(problem_type_labels)
        .fillna(view_df["problem_type"])
    )

    view_df["Zalecane działanie"] = (
        view_df["recommended_action"]
        .map(action_labels)
        .fillna(view_df["recommended_action"])
    )

    view_df["Pewność"] = (
        view_df["recommendation_confidence_final"]
        .map(confidence_labels)
        .fillna(view_df["recommendation_confidence_final"])
    )

    view_df["Szacowana relokacja opis"] = view_df["estimated_relocation_label"].apply(
        format_relocation_label
    )

    display_columns = [
        "daily_plan_rank",
        "station_name",
        "microzone_id",
        "Pilność",
        "Co grozi",
        "Zalecane działanie",
        "Szacowana relokacja opis",
        "highest_risk_hour_label",
        "Pewność",
        "expected_business_impact",
    ]

    existing_columns = [column for column in display_columns if column in view_df.columns]
    view_df = view_df[existing_columns].copy()

    view_df = view_df.rename(
        columns={
            "daily_plan_rank": "Lp.",
            "station_name": "Stacja",
            "microzone_id": "Mikrostrefa",
            "Szacowana relokacja opis": "Szacowana relokacja",
            "highest_risk_hour_label": "Godzina ryzyka",
            "expected_business_impact": "Potencjał",
        }
    )

    if "Potencjał" in view_df.columns:
        view_df["Potencjał"] = view_df["Potencjał"].round(2)

    return view_df

def build_daily_plan_metrics(df: pd.DataFrame) -> dict:
    total_station_count = int(df["station_id"].nunique()) if "station_id" in df.columns else int(df.shape[0])

    urgent_count = int(df["priority_level"].isin(["very_high", "high"]).sum())
    bike_shortage_count = int((df["problem_type"] == "bike_shortage_risk").sum())
    dock_shortage_count = int((df["problem_type"] == "dock_shortage_risk").sum())
    mixed_risk_count = int((df["problem_type"] == "mixed_risk").sum())
    check_count = int((df["recommended_action"] == "check_station_state").sum())
    relocation_sum = int(df["estimated_relocation_units"].fillna(0).sum())
    expected_impact_sum = float(df["expected_business_impact"].fillna(0).sum())

    risk_counts = {
        "brak rowerów": bike_shortage_count,
        "brak miejsc": dock_shortage_count,
        "sytuacje mieszane": mixed_risk_count,
    }

    main_risk_label = max(risk_counts, key=risk_counts.get)

    return {
        "total_station_count": total_station_count,
        "urgent_count": urgent_count,
        "bike_shortage_count": bike_shortage_count,
        "dock_shortage_count": dock_shortage_count,
        "mixed_risk_count": mixed_risk_count,
        "check_count": check_count,
        "relocation_sum": relocation_sum,
        "expected_impact_sum": expected_impact_sum,
        "main_risk_label": main_risk_label,
    }

def render_daily_action_card(row: pd.Series) -> None:
    station_rank = int(row["Lp."])
    station_name = row["Stacja"]
    microzone_id = row["Mikrostrefa"]
    priority_label = row["Pilność"]
    risk_label = row["Co grozi"]
    relocation_label = row["Szacowana relokacja"]
    risk_hour_label = row["Godzina ryzyka"]
    confidence_label = row["Pewność"]
    impact_value = float(row["Potencjał"])

    priority_styles = {
        "bardzo wysoki": "background:#fee2e2; color:#991b1b; border:1px solid #fecaca;",
        "wysoki": "background:#ffedd5; color:#9a3412; border:1px solid #fed7aa;",
        "średni": "background:#fef3c7; color:#92400e; border:1px solid #fde68a;",
        "niski": "background:#dcfce7; color:#166534; border:1px solid #bbf7d0;",
    }

    priority_style = priority_styles.get(
        priority_label,
        "background:#f3f4f6; color:#374151; border:1px solid #e5e7eb;",
    )

    header_html = (
        '<div style="height:8.1rem; margin-bottom:0.85rem;">'
        f'<div style="font-size:1.35rem; font-weight:800; line-height:1.15; color:#111827; min-height:3.1rem; max-height:3.1rem; overflow:hidden; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical;">{station_rank}. {station_name}</div>'
        f'<div style="font-size:0.9rem; color:#6b7280; margin-top:0.35rem; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">Mikrostrefa {microzone_id}</div>'
        f'<div style="display:inline-block; margin-top:0.9rem; padding:0.25rem 0.55rem; border-radius:999px; font-size:0.78rem; font-weight:700; {priority_style}">{priority_label}</div>'
        '</div>'
    )

    task_html = (
        '<div style="padding:0.85rem 0.95rem; border-radius:14px; background:#f9fafb; border:1px solid #e5e7eb; height:6.8rem; margin-bottom:0.75rem;">'
        '<div style="font-size:0.82rem; color:#6b7280; margin-bottom:0.25rem;">Zadanie dla zespołu</div>'
        f'<div style="font-size:1.08rem; font-weight:800; color:#111827; line-height:1.35; max-height:3rem; overflow:hidden; display:-webkit-box; -webkit-line-clamp:2; -webkit-box-orient:vertical;">{relocation_label}</div>'
        '</div>'
    )

    st.markdown(header_html, unsafe_allow_html=True)
    st.markdown(task_html, unsafe_allow_html=True)

    with st.popover("Szczegóły zadania"):
        st.markdown(f"**Ryzyko:** {risk_label}")
        st.markdown(f"**Godzina ryzyka:** {risk_hour_label}")
        st.markdown(f"**Pewność rekomendacji:** {confidence_label}")
        st.markdown(f"**Potencjał operacyjny:** {impact_value:.2f}")

def render_kpi_card(title: str, value: object, caption: str, tone: str = "neutral", help_text: str | None = None) -> None:
    tone_styles = {
        "neutral": "background:linear-gradient(135deg,#f8fafc 0%,#ffffff 72%); border:1px solid #cbd5e1; border-bottom:3px solid #94a3b8; box-shadow:0 10px 22px rgba(100,116,139,0.06);",
        "warning": "background:linear-gradient(135deg,#fff7ed 0%,#ffffff 72%); border:1px solid #fed7aa; border-bottom:3px solid #fdba74; box-shadow:0 10px 22px rgba(249,115,22,0.06);",
        "danger": "background:linear-gradient(135deg,#fef2f2 0%,#ffffff 72%); border:1px solid #fecaca; border-bottom:3px solid #fca5a5; box-shadow:0 10px 22px rgba(239,68,68,0.06);",
        "success": "background:linear-gradient(135deg,#f0fdf4 0%,#ffffff 72%); border:1px solid #bbf7d0; border-bottom:3px solid #4ade80; box-shadow:0 10px 22px rgba(22,163,74,0.06);",
        "info": "background:linear-gradient(135deg,#eff6ff 0%,#ffffff 72%); border:1px solid #bfdbfe; border-bottom:3px solid #60a5fa; box-shadow:0 10px 22px rgba(37,99,235,0.06);",
    }

    card_style = tone_styles.get(tone, tone_styles["neutral"])
    tooltip = help_text if help_text else ""

    card_html = (
        f'<div title="{tooltip}" style="{card_style} border-radius:18px; padding:0.95rem 1rem; height:10.2rem; display:flex; flex-direction:column; justify-content:space-between;">'
        f'<div style="font-size:0.88rem; color:#6b7280; line-height:1.25; min-height:2.2rem;">{title}</div>'
        f'<div style="font-size:2.15rem; font-weight:800; line-height:1; color:#111827;">{value}</div>'
        f'<div style="font-size:0.78rem; color:#6b7280; line-height:1.25; min-height:2.1rem;">{caption}</div>'
        '</div>'
    )

    st.markdown(card_html, unsafe_allow_html=True)

def get_operational_table_column_config() -> dict:
     return {
        "Lp.": st.column_config.NumberColumn("Lp.", width="small"),
        "Stacja": st.column_config.TextColumn("Stacja", width="medium"),
        "Mikrostrefa": st.column_config.TextColumn("Mikrostrefa", width="small"),
        "Pilność": st.column_config.TextColumn("Pilność", width="small"),
        "Co grozi": st.column_config.TextColumn("Co grozi", width="medium"),
        "Zalecane działanie": st.column_config.TextColumn("Zalecane działanie", width="medium"),
        "Szacowana relokacja": st.column_config.TextColumn("Szacowana relokacja", width="medium"),
        "Godzina ryzyka": st.column_config.TextColumn("Godzina ryzyka", width="small"),
        "Pewność": st.column_config.TextColumn("Pewność", width="small"),
        "Potencjał": st.column_config.NumberColumn("Potencjał", format="%.2f", width="small"),
    }
def build_station_action_map(df: pd.DataFrame) -> folium.Map:
    map_df = df.dropna(subset=["station_latitude", "station_longitude"]).copy()

    if map_df.empty:
        raise ValueError("Brak współrzędnych stacji do wyświetlenia mapy.")

    center_latitude = float(map_df["station_latitude"].mean())
    center_longitude = float(map_df["station_longitude"].mean())

    action_map = folium.Map(
        location=[center_latitude, center_longitude],
        zoom_start=13,
        tiles="CartoDB positron",
    )

    priority_labels = {
        "very_high": "bardzo wysoki",
        "high": "wysoki",
        "medium": "średni",
        "low": "niski",
    }

    confidence_labels = {
        "high": "wysoka",
        "medium": "średnia",
        "low": "niska",
    }

    problem_labels = {
        "bike_shortage_risk": "ryzyko braku rowerów",
        "dock_shortage_risk": "ryzyko braku miejsc",
        "mixed_risk": "ryzyko mieszane",
        "no_clear_signal": "brak jednoznacznego sygnału",
    }

    action_labels = {
        "deliver_bikes": "dowieź rowery",
        "remove_bikes": "zabierz rowery",
        "check_station": "sprawdź stację",
        "no_action": "bez działania",
    }

    def translate_relocation_label(value: object) -> str:
        text = str(value)
        text = text.replace("deliver", "dowieź")
        text = text.replace("remove", "zabierz")
        text = text.replace("-", "–")

        if text.startswith("dowieź") or text.startswith("zabierz"):
            return f"{text} rowerów"

        return text

    top_map_df = (
        map_df.sort_values("daily_plan_rank")
        .head(80)
        .copy()
    )

    for _, row in top_map_df.iterrows():
        priority_label = priority_labels.get(row.get("priority_level"), row.get("priority_level"))
        problem_label = problem_labels.get(row.get("problem_type"), row.get("problem_type"))
        action_label = action_labels.get(row.get("recommended_action"), row.get("recommended_action"))
        relocation_label = translate_relocation_label(row.get("estimated_relocation_label", ""))
        confidence_label = confidence_labels.get(
            row.get("recommendation_confidence_final"),
            row.get("recommendation_confidence_final"),
        )

        popup_text = f"""
        <b>Stacja:</b> {row["station_name"]}<br>
        <b>Mikrostrefa:</b> {row["microzone_id"]}<br>
        <b>Priorytet:</b> {priority_label}<br>
        <b>Problem:</b> {problem_label}<br>
        <b>Działanie:</b> {action_label}<br>
        <b>Godzina ryzyka:</b> {row["highest_risk_hour_label"]}<br>
        <b>Relokacja:</b> {relocation_label}<br>
        <b>Potencjał:</b> {float(row["expected_business_impact"]):.2f}<br>
        <b>Pewność:</b> {confidence_label}
        """

        folium.CircleMarker(
            location=[
                float(row["station_latitude"]),
                float(row["station_longitude"]),
            ],
            radius=float(row.get("map_marker_size", 5)),
            color=str(row.get("map_priority_color", "blue")),
            fill=True,
            fill_color=str(row.get("map_priority_color", "blue")),
            fill_opacity=0.75,
            popup=folium.Popup(popup_text, max_width=340),
            tooltip=f"{int(row['daily_plan_rank'])}. {row['station_name']}",
        ).add_to(action_map)

    return action_map

required_paths = [
    APP_CONTRACT_PATH,
    TAB_CONTRACT_PATH,
    USER_LABELS_PATH,
    MAP_STATION_LAYER_PATH,
    MICROZONE_SUMMARY_PATH,
    LOCAL_PAIRS_PATH,
    RELOCATION_LINE_LAYER_PATH,
    DRIVER_TASK_LAYER_PATH,
    DAILY_DRIVER_CARDS_PATH,
    FEEDBACK_LOG_PATH,
]

require_paths(required_paths)

app_contract = load_json_data(str(APP_CONTRACT_PATH))
tab_contract_df = load_parquet_data(str(TAB_CONTRACT_PATH))
user_labels_df = load_parquet_data(str(USER_LABELS_PATH))

map_station_df = load_parquet_data(str(MAP_STATION_LAYER_PATH))
microzone_summary_df = load_parquet_data(str(MICROZONE_SUMMARY_PATH))
local_pairs_df = load_parquet_data(str(LOCAL_PAIRS_PATH))
relocation_line_df = load_parquet_data(str(RELOCATION_LINE_LAYER_PATH))
driver_task_df = load_parquet_data(str(DRIVER_TASK_LAYER_PATH))
daily_driver_cards_df = load_parquet_data(str(DAILY_DRIVER_CARDS_PATH))
feedback_log = initialize_feedback_log()

map_station_df["activity_date"] = pd.to_datetime(
    map_station_df["activity_date"],
    errors="coerce",
).dt.normalize()

daily_driver_cards_df["activity_date"] = pd.to_datetime(
    daily_driver_cards_df["activity_date"],
    errors="coerce",
).dt.normalize()

if "activity_date" in microzone_summary_df.columns:
    microzone_summary_df["activity_date"] = pd.to_datetime(
        microzone_summary_df["activity_date"],
        errors="coerce",
    ).dt.normalize()

available_dates = sorted(map_station_df["activity_date"].dropna().dt.date.unique().tolist())

if not available_dates:
    st.error("Brak dostępnych dat w warstwie operacyjnej.")
    st.stop()


st.markdown(
    """
<style>
div[data-testid="stTabs"] {
    margin-top: 0.9rem;
}

div[data-testid="stTabs"] div[role="tablist"] {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 1.05rem;
    border-bottom: 1px solid #e5e7eb;
    padding-bottom: 1.05rem;
    margin-top: 1rem;
    margin-bottom: 1.35rem;
}

div[data-testid="stTabs"] button[role="tab"] {
    position: relative;
    width: 100%;
    height: 12.2rem;
    min-height: 12.2rem;
    border: 1px solid #e5e7eb;
    border-radius: 18px;
    background: #ffffff;
    box-shadow: 0 12px 28px rgba(15, 23, 42, 0.055);
    padding: 0;
    overflow: hidden;
    transition: all 0.18s ease;
}

div[data-testid="stTabs"] button[role="tab"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 18px 36px rgba(15, 23, 42, 0.10);
}

div[data-testid="stTabs"] button[role="tab"] p {
    position: absolute;
    left: 1.55rem;
    right: 1.55rem;
    top: 5.9rem;
    margin: 0;
    font-size: 1.18rem;
    font-weight: 900;
    line-height: 1.2;
    color: #0f172a;
    text-align: left;
    white-space: normal;
    z-index: 3;
}

div[data-testid="stTabs"] button[role="tab"]::before {
    position: absolute;
    top: 0.65rem;
    left: 50%;
    transform: translateX(-50%);
    width: 4.25rem;
    height: 4.25rem;
    border-radius: 999px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.65rem;
    font-weight: 900;
    z-index: 2;
}

div[data-testid="stTabs"] button[role="tab"]::after {
    position: absolute;
    left: 1.55rem;
    right: 1.55rem;
    top: 8.15rem;
    font-size: 0.82rem;
    font-weight: 500;
    line-height: 1.45;
    color: #64748b;
    text-align: left;
    white-space: pre-line;
    z-index: 2;
}

div[data-testid="stTabs"] button[role="tab"]:nth-of-type(1) {
    border-bottom: 3px solid #ef4444;
}

div[data-testid="stTabs"] button[role="tab"]:nth-of-type(1)::before {
    content: "📅";
    background: #fee2e2;
}

div[data-testid="stTabs"] button[role="tab"]:nth-of-type(1)::after {
    content: "Zobacz priorytety relokacji,\\A rekomendacje działań i kluczowe\\A informacje na dzisiaj.";
}

div[data-testid="stTabs"] button[role="tab"]:nth-of-type(2) {
    border-bottom: 3px solid #1d8bea;
}

div[data-testid="stTabs"] button[role="tab"]:nth-of-type(2)::before {
    content: "👤";
    background: #dbeafe;
}

div[data-testid="stTabs"] button[role="tab"]:nth-of-type(2)::after {
    content: "Sprawdź swoje zadania, trasę\\A dnia i szczegóły realizacji\\A relokacji.";
}

div[data-testid="stTabs"] button[role="tab"]:nth-of-type(3) {
    border-bottom: 3px solid #22c55e;
}

div[data-testid="stTabs"] button[role="tab"]:nth-of-type(3)::before {
    content: "📈";
    color: #22c55e;
    background: #dcfce7;
}

div[data-testid="stTabs"] button[role="tab"]:nth-of-type(3)::after {
    content: "Monitoruj postęp realizacji zadań\\A i analizuj wyniki działań\\A w terenie.";
}

div[data-testid="stTabs"] button[role="tab"] span::after {
    content: "📈";
    position: absolute;
    right: 1.25rem;
    bottom: 1.05rem;
    width: 2.35rem;
    height: 2.35rem;
    border-radius: 999px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.35rem;
    font-weight: 700;
    background: #ffffff;
    z-index: 4;
}

div[data-testid="stTabs"] button[role="tab"]:nth-of-type(1) span::after {
    color: #ef4444;
    border: 1px solid #fecaca;
}

div[data-testid="stTabs"] button[role="tab"]:nth-of-type(2) span::after {
    color: #1d8bea;
    border: 1px solid #bfdbfe;
}

div[data-testid="stTabs"] button[role="tab"]:nth-of-type(3) span::after {
    color: #22c55e;
    border: 1px solid #bbf7d0;
}

div[data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
    box-shadow: 0 18px 38px rgba(15, 23, 42, 0.10);
}

.dispatcher-hero {
    border: 1px solid #cbd5e1;
    border-radius: 22px;
    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
    padding: 1.25rem 1.45rem;
    margin-bottom: 0.1rem;
    box-shadow: 0 12px 30px rgba(15, 23, 42, 0.06);
}

.dispatcher-hero-inner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1.5rem;
}

.dispatcher-hero-text {
    min-width: 0;
}

.dispatcher-hero-title {
    font-size: 2rem;
    font-weight: 850;
    line-height: 1.15;
    color: #0f172a;
    letter-spacing: -0.025em;
    white-space: normal;
}

.dispatcher-hero-subtitle {
    font-size: 1.02rem;
    color: #64748b;
    line-height: 1.45;
    margin-top: 0.45rem;
    white-space: normal;
}

.dispatcher-hero-visual {
    min-width: 170px;
    width: 170px;
    height: 88px;
    position: relative;
    flex: 0 0 170px;
}

.dispatcher-hero-visual svg {
    position: absolute;
    right: 0;
    bottom: 0;
    width: 170px;
    height: 88px;
}

.mobile-kpi-grid {
    display: grid;
    grid-template-columns: repeat(5, minmax(0, 1fr));
    gap: 0.7rem;
    margin: 0.7rem 0 1rem 0;
}

.mobile-kpi-card {
    border-radius: 18px;
    padding: 0.95rem 1rem;
    height: 10.2rem;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}

.mobile-kpi-title {
    font-size: 0.88rem;
    color: #6b7280;
    line-height: 1.25;
    min-height: 2.2rem;
}

.mobile-kpi-value {
    font-size: 2.15rem;
    font-weight: 800;
    line-height: 1;
    color: #111827;
}

.mobile-kpi-caption {
    font-size: 0.78rem;
    color: #6b7280;
    line-height: 1.25;
    min-height: 2.1rem;
}

@media (max-width: 640px) {
    .dispatcher-hero {
        padding: 0.75rem 0.8rem;
        border-radius: 16px;
        margin-bottom: 0.2rem;
    }

    .dispatcher-hero-inner {
        display: grid;
        grid-template-columns: minmax(0, 1fr) 72px;
        gap: 0.45rem;
        align-items: center;
    }

    .dispatcher-hero-title {
        font-size: 1.02rem;
        line-height: 1.12;
        letter-spacing: -0.015em;
    }

    .dispatcher-hero-subtitle {
        font-size: 0.72rem;
        line-height: 1.25;
        margin-top: 0.22rem;
    }

    .dispatcher-hero-visual {
        min-width: 72px;
        width: 72px;
        height: 48px;
        flex: 0 0 72px;
    }

    .dispatcher-hero-visual svg {
        width: 92px;
        height: 48px;
        right: -8px;
        bottom: 0;
    }

    div[data-testid="stTabs"] {
        margin-top: 0.45rem;
    }

    div[data-testid="stTabs"] div[role="tablist"] {
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.35rem;
        padding-bottom: 0.55rem;
        margin-top: 0.55rem;
        margin-bottom: 0.8rem;
        overflow: visible;
    }

    div[data-testid="stTabs"] button[role="tab"] {
        height: 9.45rem;
        min-height: 9.45rem;
        border-radius: 13px;
        box-shadow: 0 7px 16px rgba(15, 23, 42, 0.055);
    }

    div[data-testid="stTabs"] button[role="tab"]::before {
        top: 0.55rem;
        width: 1.65rem;
        height: 1.65rem;
        font-size: 0.9rem;
    }

    div[data-testid="stTabs"] button[role="tab"] p {
        left: 0.22rem;
        right: 0.22rem;
        top: 3.42rem;
        font-size: 0.68rem;
        line-height: 1.12;
        text-align: center;
        white-space: normal;
    }

    div[data-testid="stTabs"] button[role="tab"]::after {
        position: absolute;
        left: 0.34rem;
        right: 0.34rem;
        top: 4.78rem;
        display: block;
        font-size: 0.56rem;
        font-weight: 500;
        line-height: 1.18;
        color: #64748b;
        text-align: center;
        white-space: pre-line;
        z-index: 2;
    }

    div[data-testid="stTabs"] button[role="tab"] span::after {
        display: none;
    }

    .mobile-kpi-grid {
        grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: 0.28rem;
        margin: 0.45rem 0 0.7rem 0;
    }

    .mobile-kpi-card {
        border-radius: 11px;
        padding: 0.38rem 0.22rem;
        height: 4.8rem;
        align-items: center;
        text-align: center;
    }

    .mobile-kpi-title {
        font-size: 0.54rem;
        line-height: 1.05;
        min-height: 1.15rem;
    }

    .mobile-kpi-value {
        font-size: 0.95rem;
        line-height: 1;
    }

    .mobile-kpi-caption {
        font-size: 0.48rem;
        line-height: 1.05;
        min-height: 1.05rem;
    }
}

</style>

<div class="dispatcher-hero">
    <div class="dispatcher-hero-inner">
        <div class="dispatcher-hero-text">
            <div class="dispatcher-hero-title">Panel dyspozytora relokacji rowerów</div>
            <div class="dispatcher-hero-subtitle">Operacyjny system planowania, obsługi kierowcy i kontroli realizacji zadań.</div>
        </div>
        <div class="dispatcher-hero-visual">
            <svg width="170" height="88" viewBox="0 0 170 88" xmlns="http://www.w3.org/2000/svg">
                <rect x="76" y="18" width="92" height="62" rx="18" fill="#f1f5f9"/>
                <rect x="112" y="32" width="17" height="48" rx="3" fill="#dbe3ec"/>
                <rect x="134" y="44" width="20" height="36" rx="3" fill="#dbe3ec"/>
                <circle cx="50" cy="62" r="18" fill="none" stroke="#334155" stroke-width="4"/>
                <circle cx="104" cy="62" r="18" fill="none" stroke="#334155" stroke-width="4"/>
                <path d="M50 62 L72 38 L90 62 L66 62 L84 42 L104 62" fill="none" stroke="#334155" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M72 38 L66 29" stroke="#334155" stroke-width="4" stroke-linecap="round"/>
                <path d="M84 42 L100 34" stroke="#334155" stroke-width="4" stroke-linecap="round"/>
                <path d="M98 34 H112" stroke="#334155" stroke-width="4" stroke-linecap="round"/>
            </svg>
        </div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Filtry")

    selected_date = st.selectbox(
        "Dzień operacyjny",
        options=available_dates,
        index=0,
    )

    selected_date_ts = pd.to_datetime(selected_date).normalize()

    daily_source_df = map_station_df.loc[
        map_station_df["activity_date"] == selected_date_ts
    ].copy()

    microzone_options = ["Wszystkie"] + sorted(
        daily_source_df["microzone_id"].dropna().astype(str).unique().tolist()
    )

    priority_options = ["Wszystkie", "bardzo wysoki", "wysoki", "średni", "niski"]

    problem_options = [
        "Wszystkie",
        "ryzyko braku rowerów",
        "ryzyko braku miejsc",
        "sytuacja mieszana",
        "brak jednoznacznego sygnału",
    ]

    selected_microzone = st.selectbox("Rejon miasta", options=microzone_options, index=0)
    selected_priority = st.selectbox("Pilność", options=priority_options, index=0)
    selected_problem = st.selectbox("Typ problemu", options=problem_options, index=0)

    card_layout_options = {
        "Komputer — 3 kolumny": 3,
        "Tablet — 2 kolumny": 2,
        "Telefon — 1 kolumna": 1,
    }

    cards_per_row = 3

    kpi_cards_per_row = 5 if cards_per_row == 3 else cards_per_row

    st.divider()

daily_actions_df = (
    map_station_df.loc[map_station_df["activity_date"] == selected_date_ts]
    .copy()
    .sort_values("daily_plan_rank")
    .reset_index(drop=True)
)

if selected_microzone != "Wszystkie":
    daily_actions_df = daily_actions_df.loc[
        daily_actions_df["microzone_id"].astype(str) == selected_microzone
    ].copy()

priority_filter_map = {
    "bardzo wysoki": "very_high",
    "wysoki": "high",
    "średni": "medium",
    "niski": "low",
}

problem_filter_map = {
    "ryzyko braku rowerów": "bike_shortage_risk",
    "ryzyko braku miejsc": "dock_shortage_risk",
    "sytuacja mieszana": "mixed_risk",
    "brak jednoznacznego sygnału": "no_clear_signal",
}

if selected_priority != "Wszystkie":
    daily_actions_df = daily_actions_df.loc[
        daily_actions_df["priority_level"] == priority_filter_map[selected_priority]
    ].copy()

if selected_problem != "Wszystkie":
    daily_actions_df = daily_actions_df.loc[
        daily_actions_df["problem_type"] == problem_filter_map[selected_problem]
    ].copy()

daily_actions_view_df = build_operational_view(daily_actions_df)

daily_driver_df = (
    daily_driver_cards_df.loc[daily_driver_cards_df["activity_date"] == selected_date_ts]
    .copy()
    .sort_values("driver_card_order")
    .reset_index(drop=True)
)

tab_plan, tab_driver, tab_feedback = st.tabs(
    [
        "Plan operacyjny",
        "Karta kierowcy",
        "Status realizacji",
    ]
)


with tab_plan:
    st.subheader("Plan operacyjny")

    daily_plan_metrics = build_daily_plan_metrics(daily_actions_df)

    urgent_count = daily_plan_metrics["urgent_count"]
    bike_shortage_count = daily_plan_metrics["bike_shortage_count"]
    check_count = daily_plan_metrics["check_count"]
    relocation_sum = daily_plan_metrics["relocation_sum"]
    expected_impact_sum = daily_plan_metrics["expected_impact_sum"]

    plan_summary_html = "\n".join(
        [
            "<style>",
            ".plan-summary-card {",
            "border:1px solid #cbd5e1;",
            "border-bottom:4px solid #60a5fa;",
            "border-radius:22px;",
            "background:linear-gradient(135deg,#f8fafc 0%,#ffffff 72%);",
            "box-shadow:0 14px 32px rgba(15,23,42,0.06);",
            "padding:1.15rem 1.35rem;",
            "margin:0.55rem 0 1.15rem 0;",
            "}",
            ".plan-summary-top {",
            "display:flex;",
            "align-items:center;",
            "justify-content:space-between;",
            "gap:1rem;",
            "margin-bottom:0.75rem;",
            "}",
            ".plan-summary-date {",
            "font-size:0.92rem;",
            "color:#64748b;",
            "font-weight:750;",
            "line-height:1.25;",
            "}",
            ".plan-summary-badge {",
            "border:1px solid #bfdbfe;",
            "background:#eff6ff;",
            "color:#1d4ed8;",
            "border-radius:999px;",
            "padding:0.28rem 0.7rem;",
            "font-size:0.78rem;",
            "font-weight:850;",
            "white-space:nowrap;",
            "}",
            ".plan-summary-main {",
            "font-size:1.32rem;",
            "font-weight:900;",
            "line-height:1.22;",
            "color:#0f172a;",
            "letter-spacing:-0.015em;",
            "margin-bottom:0.95rem;",
            "}",
            ".plan-summary-grid {",
            "display:grid;",
            "grid-template-columns:repeat(3, minmax(0, 1fr));",
            "gap:0.65rem;",
            "}",
            ".plan-summary-item {",
            "border:1px solid #e5e7eb;",
            "border-radius:16px;",
            "background:#ffffff;",
            "padding:0.72rem 0.85rem;",
            "min-height:4.25rem;",
            "}",
            ".plan-summary-item:nth-child(1) {",
            "border-color:#fecaca;",
            "background:linear-gradient(135deg,#fef2f2 0%,#ffffff 72%);",
            "}",
            ".plan-summary-item:nth-child(2) {",
            "border-color:#fed7aa;",
            "background:linear-gradient(135deg,#fff7ed 0%,#ffffff 72%);",
            "}",
            ".plan-summary-item:nth-child(3) {",
            "border-color:#bbf7d0;",
            "background:linear-gradient(135deg,#f0fdf4 0%,#ffffff 72%);",
            "}",
            ".plan-summary-label {",
            "font-size:0.76rem;",
            "color:#64748b;",
            "font-weight:700;",
            "line-height:1.2;",
            "margin-bottom:0.22rem;",
            "}",
            ".plan-summary-value {",
            "font-size:1.02rem;",
            "color:#111827;",
            "font-weight:900;",
            "line-height:1.2;",
            "}",
            "@media (max-width: 640px) {",
            ".plan-summary-card {",
            "border-radius:18px;",
            "padding:0.9rem 0.95rem;",
            "margin:0.45rem 0 0.9rem 0;",
            "}",
            ".plan-summary-top {",
            "align-items:flex-start;",
            "margin-bottom:0.55rem;",
            "}",
            ".plan-summary-date {",
            "font-size:0.78rem;",
            "}",
            ".plan-summary-badge {",
            "font-size:0.66rem;",
            "padding:0.22rem 0.5rem;",
            "}",
            ".plan-summary-main {",
            "font-size:1rem;",
            "line-height:1.25;",
            "margin-bottom:0.72rem;",
            "}",
            ".plan-summary-grid {",
            "grid-template-columns:repeat(3, minmax(0, 1fr));",
            "gap:0.35rem;",
            "}",
            ".plan-summary-item {",
            "border-radius:12px;",
            "padding:0.5rem 0.35rem;",
            "min-height:3.8rem;",
            "text-align:center;",
            "}",
            ".plan-summary-label {",
            "font-size:0.55rem;",
            "line-height:1.1;",
            "margin-bottom:0.2rem;",
            "}",
            ".plan-summary-value {",
            "font-size:0.72rem;",
            "line-height:1.15;",
            "}",
            "}",
            "</style>",
            '<div class="plan-summary-card">',
            '<div class="plan-summary-top">',
            f'<div class="plan-summary-date">Plan operacyjny na {selected_date}</div>',
            '<div class="plan-summary-badge">aktywny widok</div>',
            "</div>",
            f'<div class="plan-summary-main">Widok obejmuje {daily_plan_metrics["total_station_count"]} stacji po aktualnych filtrach.</div>',
            '<div class="plan-summary-grid">',
            '<div class="plan-summary-item">',
            '<div class="plan-summary-label">Główne ryzyko</div>',
            f'<div class="plan-summary-value">{daily_plan_metrics["main_risk_label"]}</div>',
            "</div>",
            '<div class="plan-summary-item">',
            '<div class="plan-summary-label">Szacowana relokacja</div>',
            f'<div class="plan-summary-value">{daily_plan_metrics["relocation_sum"]} rowerów</div>',
            "</div>",
            '<div class="plan-summary-item">',
            '<div class="plan-summary-label">Potencjał operacyjny</div>',
            f'<div class="plan-summary-value">{format_number(daily_plan_metrics["expected_impact_sum"])}</div>',
            "</div>",
            "</div>",
            "</div>",
        ]
    )

    st.markdown(plan_summary_html, unsafe_allow_html=True)


    kpi_items = [
        {
            "title": "Stacje w widoku",
            "value": format_number(daily_plan_metrics["total_station_count"]),
            "caption": "Zakres po aktualnych filtrach",
            "tone": "neutral",
        },
        {
            "title": "Brak rowerów",
            "value": format_number(bike_shortage_count),
            "caption": "Stacje z ryzykiem braku rowerów",
            "tone": "danger",
        },
        {
            "title": "Do sprawdzenia",
            "value": format_number(check_count),
            "caption": "Stacje wymagające kontroli",
            "tone": "info",
        },
        {
            "title": "Relokacja rowerów",
            "value": format_number(relocation_sum),
            "caption": "Szacowana liczba rowerów",
            "tone": "warning",
        },
        {
            "title": "Potencjał operacyjny",
            "value": format_number(expected_impact_sum),
            "caption": "Priorytet biznesowy działań",
            "tone": "success",
        },
    ]

    kpi_tone_styles = {
        "neutral": "background:linear-gradient(135deg,#f8fafc 0%,#ffffff 72%); border:1px solid #cbd5e1; border-bottom:3px solid #94a3b8; box-shadow:0 10px 22px rgba(100,116,139,0.06);",
        "warning": "background:linear-gradient(135deg,#fff7ed 0%,#ffffff 72%); border:1px solid #fed7aa; border-bottom:3px solid #fdba74; box-shadow:0 10px 22px rgba(249,115,22,0.06);",
        "danger": "background:linear-gradient(135deg,#fef2f2 0%,#ffffff 72%); border:1px solid #fecaca; border-bottom:3px solid #fca5a5; box-shadow:0 10px 22px rgba(239,68,68,0.06);",
        "success": "background:linear-gradient(135deg,#f0fdf4 0%,#ffffff 72%); border:1px solid #bbf7d0; border-bottom:3px solid #4ade80; box-shadow:0 10px 22px rgba(22,163,74,0.06);",
        "info": "background:linear-gradient(135deg,#eff6ff 0%,#ffffff 72%); border:1px solid #bfdbfe; border-bottom:3px solid #60a5fa; box-shadow:0 10px 22px rgba(37,99,235,0.06);",
    }

    kpi_cards_html = ""

    for kpi_item in kpi_items:
        kpi_card_style = kpi_tone_styles.get(
            kpi_item["tone"],
            kpi_tone_styles["neutral"],
        )

        kpi_cards_html += (
            f'<div class="mobile-kpi-card" style="{kpi_card_style}">'
            f'<div class="mobile-kpi-title">{kpi_item["title"]}</div>'
            f'<div class="mobile-kpi-value">{kpi_item["value"]}</div>'
            f'<div class="mobile-kpi-caption">{kpi_item["caption"]}</div>'
            f'</div>'
        )

    st.markdown(
        f'<div class="mobile-kpi-grid">{kpi_cards_html}</div>',
        unsafe_allow_html=True,
    )

    if daily_actions_df.empty:
        st.info("Brak działań dla wybranych filtrów.")
    else:
        st.markdown("### Rejony miasta")

        plan_region_source_df = daily_actions_df.copy()

        plan_region_source_df["deliver_units_for_region"] = 0
        plan_region_source_df["remove_units_for_region"] = 0

        plan_region_source_df.loc[
            plan_region_source_df["recommended_action"] == "deliver_bikes",
            "deliver_units_for_region",
        ] = plan_region_source_df.loc[
            plan_region_source_df["recommended_action"] == "deliver_bikes",
            "estimated_relocation_units",
        ].fillna(0)

        plan_region_source_df.loc[
            plan_region_source_df["recommended_action"] == "remove_bikes",
            "remove_units_for_region",
        ] = plan_region_source_df.loc[
            plan_region_source_df["recommended_action"] == "remove_bikes",
            "estimated_relocation_units",
        ].fillna(0)

        plan_region_table_df = (
            plan_region_source_df.groupby("microzone_id", as_index=False)
            .agg(
                station_count=("microzone_id", "count"),
                estimated_deliver_units=("deliver_units_for_region", "sum"),
                estimated_remove_units=("remove_units_for_region", "sum"),
                expected_business_impact=("expected_business_impact", "sum"),
                top_daily_plan_rank=("daily_plan_rank", "min"),
            )
            .rename(
                columns={
                    "microzone_id": "Rejon miasta",
                    "station_count": "Stacje do obsługi",
                    "estimated_deliver_units": "Dowieźć",
                    "estimated_remove_units": "Zabrać",
                    "expected_business_impact": "Potencjał",
                    "top_daily_plan_rank": "Najwyższy priorytet",
                }
            )
        )

        plan_region_table_df["Liczba stacji"] = plan_region_table_df["Stacje do obsługi"]
        plan_region_table_df["Bilans"] = (
            plan_region_table_df["Zabrać"] - plan_region_table_df["Dowieźć"]
        )

        plan_region_table_df["Kierunek"] = "zbilansowany"
        plan_region_table_df.loc[
            plan_region_table_df["Bilans"] < 0,
            "Kierunek",
        ] = "potrzeba dowozu"
        plan_region_table_df.loc[
            plan_region_table_df["Bilans"] > 0,
            "Kierunek",
        ] = "potrzeba odbioru"

        plan_region_table_df = (
            plan_region_table_df.sort_values(
                ["Dowieźć", "Zabrać", "Bilans", "Potencjał"],
                ascending=[False, False, True, False],
            )
            .head(100)
            .copy()
            .reset_index(drop=True)
        )

        plan_region_table_df["Potencjał"] = plan_region_table_df["Potencjał"].round(2)

        plan_region_columns = [
            "Rejon miasta",
            "Liczba stacji",
            "Stacje do obsługi",
            "Dowieźć",
            "Zabrać",
            "Bilans",
            "Kierunek",
        ]

        plan_region_event = st.dataframe(
            plan_region_table_df[plan_region_columns],
            width="stretch",
            height=300,
            hide_index=True,
            key="plan_region_table",
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "Rejon miasta": st.column_config.TextColumn("Rejon miasta", width=125),
                "Liczba stacji": st.column_config.NumberColumn("Liczba stacji", width=95),
                "Stacje do obsługi": st.column_config.NumberColumn("Stacje do obsługi", width=130),
                "Dowieźć": st.column_config.NumberColumn("Dowieźć", width=85),
                "Zabrać": st.column_config.NumberColumn("Zabrać", width=85),
                "Bilans": st.column_config.NumberColumn("Bilans", width=85),
                "Kierunek": st.column_config.TextColumn("Kierunek", width=150),
            },
        )

        selected_plan_rows = plan_region_event.selection.rows

        selected_plan_region = None
        if selected_plan_rows:
            selected_plan_region = str(
                plan_region_table_df.iloc[selected_plan_rows[0]]["Rejon miasta"]
            )

        if selected_plan_region:
            plan_scope_df = daily_actions_df.loc[
                daily_actions_df["microzone_id"].astype(str) == selected_plan_region
            ].copy()
            plan_scope_label = f"Wybrany rejon: {selected_plan_region}"
        else:
            plan_scope_df = daily_actions_df.copy()
            plan_scope_label = "Wszystkie rejony z aktualnych filtrów"

        plan_scope_view_df = build_operational_view(plan_scope_df)

        st.markdown("### Kolejność zadań")

        if "plan_order_mode" not in st.session_state:
            st.session_state["plan_order_mode"] = "impact"

        order_col_1, order_col_2, order_col_3 = st.columns(3)

        with order_col_1:
            if st.button(
                "Potencjał operacyjny",
                use_container_width=True,
                type="primary" if st.session_state["plan_order_mode"] == "impact" else "secondary",
            ):
                st.session_state["plan_order_mode"] = "impact"
                st.rerun()

        with order_col_2:
            if st.button(
                "Pilność + godzina",
                use_container_width=True,
                type="primary" if st.session_state["plan_order_mode"] == "priority" else "secondary",
            ):
                st.session_state["plan_order_mode"] = "priority"
                st.rerun()

        with order_col_3:
            if st.button(
                "Godzina ryzyka",
                use_container_width=True,
                type="primary" if st.session_state["plan_order_mode"] == "hour" else "secondary",
            ):
                st.session_state["plan_order_mode"] = "hour"
                st.rerun()

        priority_sort_map = {
            "bardzo wysoki": 1,
            "wysoki": 2,
            "średni": 3,
            "niski": 4,
        }

        if not plan_scope_view_df.empty:
            plan_scope_view_df["priority_sort"] = (
                plan_scope_view_df["Pilność"]
                .map(priority_sort_map)
                .fillna(99)
                .astype(int)
            )

            plan_scope_view_df["risk_hour_sort"] = pd.to_datetime(
                plan_scope_view_df["Godzina ryzyka"].astype(str),
                format="%H:%M",
                errors="coerce",
            )

            if st.session_state["plan_order_mode"] == "priority":
                plan_scope_view_df = plan_scope_view_df.sort_values(
                    ["priority_sort", "risk_hour_sort", "Potencjał", "Lp."],
                    ascending=[True, True, False, True],
                ).copy()

            elif st.session_state["plan_order_mode"] == "hour":
                plan_scope_view_df = plan_scope_view_df.sort_values(
                    ["risk_hour_sort", "priority_sort", "Potencjał", "Lp."],
                    ascending=[True, True, False, True],
                ).copy()

            else:
                plan_scope_view_df = plan_scope_view_df.sort_values(
                    ["Potencjał", "priority_sort", "risk_hour_sort", "Lp."],
                    ascending=[False, True, True, True],
                ).copy()

            plan_scope_view_df = (
                plan_scope_view_df.drop(
                    columns=["priority_sort", "risk_hour_sort"],
                    errors="ignore",
                )
                .reset_index(drop=True)
            )

        plan_station_count = int(plan_scope_df.shape[0])
        plan_deliver_sum = int(
            plan_scope_df.loc[
                plan_scope_df["recommended_action"] == "deliver_bikes",
                "estimated_relocation_units",
            ]
            .fillna(0)
            .sum()
        )
        plan_remove_sum = int(
            plan_scope_df.loc[
                plan_scope_df["recommended_action"] == "remove_bikes",
                "estimated_relocation_units",
            ]
            .fillna(0)
            .sum()
        )
        plan_balance = plan_remove_sum - plan_deliver_sum

        st.markdown("### Widok wybranego zakresu")
        st.caption(plan_scope_label)

        st.markdown(
            f"""
            <div style="display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:0.7rem; margin:0.7rem 0 0.8rem 0;">
                <div style="border:1px solid #cbd5e1; border-bottom:3px solid #94a3b8; border-radius:14px; padding:0.65rem 0.85rem; background:linear-gradient(135deg,#f8fafc 0%,#ffffff 72%); box-shadow:0 10px 22px rgba(100,116,139,0.06);">
                    <div style="font-size:0.78rem; color:#6b7280;">Stacje</div>
                    <div style="font-size:1.45rem; font-weight:800; color:#111827;">{plan_station_count}</div>
                    <div style="font-size:0.72rem; color:#6b7280; min-height:2.05rem; line-height:1.25;">po aktualnym wyborze</div>
                </div>
                <div style="border:1px solid #fed7aa; border-bottom:3px solid #fdba74; border-radius:14px; padding:0.65rem 0.85rem; background:linear-gradient(135deg,#fff7ed 0%,#ffffff 72%); box-shadow:0 10px 22px rgba(249,115,22,0.06);">
                    <div style="font-size:0.78rem; color:#6b7280;">Dowieźć</div>
                    <div style="font-size:1.45rem; font-weight:800; color:#111827;">{plan_deliver_sum}</div>
                    <div style="font-size:0.72rem; color:#6b7280; min-height:2.05rem; line-height:1.25;">rowerów</div>
                </div>
                <div style="border:1px solid #bfdbfe; border-bottom:3px solid #60a5fa; border-radius:14px; padding:0.65rem 0.85rem; background:linear-gradient(135deg,#eff6ff 0%,#ffffff 72%); box-shadow:0 10px 22px rgba(37,99,235,0.06);">
                    <div style="font-size:0.78rem; color:#6b7280;">Zabrać</div>
                    <div style="font-size:1.45rem; font-weight:800; color:#111827;">{plan_remove_sum}</div>
                    <div style="font-size:0.72rem; color:#6b7280; min-height:2.05rem; line-height:1.25;">rowerów</div>
                </div>
                <div style="border:1px solid #cbd5e1; border-bottom:3px solid #64748b; border-radius:14px; padding:0.65rem 0.85rem; background:linear-gradient(135deg,#f8fafc 0%,#ffffff 72%); box-shadow:0 10px 22px rgba(100,116,139,0.06);">
                    <div style="font-size:0.78rem; color:#6b7280;">Bilans</div>
                    <div style="font-size:1.45rem; font-weight:800; color:#111827;">{plan_balance}</div>
                    <div style="font-size:0.72rem; color:#6b7280; min-height:2.05rem; line-height:1.25;">ujemny = potrzeba dowozu</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("### Mapa stacji")

        try:
            station_action_map = build_station_action_map(plan_scope_df)
            map_html = station_action_map.get_root().render()
            components.html(map_html, height=480, scrolling=False)
        except Exception as exc:
            st.warning("Nie udało się zbudować mapy stacji dla aktualnego widoku.")
            st.error(str(exc))

        st.markdown("### Stacje do obsługi")

        plan_task_columns = [
            "Lp.",
            "Stacja",
            "Mikrostrefa",
            "Pilność",
            "Zalecane działanie",
            "Szacowana relokacja",
            "Godzina ryzyka",
            "Potencjał",
        ]

        plan_task_columns = [
            column_name
            for column_name in plan_task_columns
            if column_name in plan_scope_view_df.columns
        ]

        plan_task_df = plan_scope_view_df[plan_task_columns].copy()

        st.dataframe(
            plan_task_df,
            width="stretch",
            height=420,
            hide_index=True,
            column_config=get_operational_table_column_config(),
        )

        st.markdown("### Szczegóły stacji")

        station_options = (
            plan_scope_df[["daily_plan_rank", "station_name"]]
            .dropna()
            .sort_values("daily_plan_rank")
            .assign(
                station_option=lambda df: (
                    df["daily_plan_rank"].astype(int).astype(str)
                    + ". "
                    + df["station_name"].astype(str)
                )
            )["station_option"]
            .tolist()
        )

        if station_options:
            selected_station_option = st.selectbox(
                "Wybierz stację",
                options=station_options,
                index=0,
                key="plan_station_details_select",
            )

            selected_station_rank = int(selected_station_option.split(".", 1)[0])

            station_details_df = plan_scope_df.loc[
                plan_scope_df["daily_plan_rank"] == selected_station_rank
            ].copy()

            station_view_df = build_operational_view(station_details_df)

            if not station_view_df.empty:
                station_row = station_view_df.iloc[0]
                raw_station_row = station_details_df.iloc[0]

                st.markdown(
                    f"""
                    <div style="padding:1rem 1.15rem; border:1px solid #e5e7eb; border-radius:18px; background:#f9fafb; margin-top:0.5rem;">
                        <div style="font-size:1.35rem; font-weight:850; color:#111827; margin-bottom:0.45rem;">
                            {station_row.get("Lp.", "")}. {station_row.get("Stacja", "")}
                        </div>
                        <div style="font-size:0.95rem; color:#6b7280; margin-bottom:0.7rem;">
                            Rejon miasta: <b>{station_row.get("Mikrostrefa", "")}</b>
                        </div>
                        <div style="font-size:1rem; color:#111827; margin-bottom:0.35rem;">
                            Zalecane działanie: <b>{station_row.get("Zalecane działanie", "")}</b>
                        </div>
                        <div style="font-size:1.15rem; font-weight:850; color:#111827; margin:0.45rem 0;">
                            {station_row.get("Szacowana relokacja", "")}
                        </div>
                        <div style="font-size:0.95rem; color:#374151;">
                            Godzina ryzyka: <b>{station_row.get("Godzina ryzyka", "")}</b> | 
                            Pilność: <b>{station_row.get("Pilność", "")}</b> | 
                            Pewność: <b>{station_row.get("Pewność", "")}</b>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                detail_col_1, detail_col_2, detail_col_3, detail_col_4 = st.columns(4)

                detail_col_1.metric("Potencjał", station_row.get("Potencjał", ""))
                detail_col_2.metric("Wyjazdy", int(raw_station_row.get("total_departures", 0)))
                detail_col_3.metric("Zwroty", int(raw_station_row.get("total_returns", 0)))
                detail_col_4.metric("Bilans dnia", int(raw_station_row.get("daily_net_flow", 0)))
        else:
            st.info("Brak stacji do pokazania w szczegółach.")


with tab_driver:
    st.subheader("Karta kierowcy")

    driver_intro_html = "\n".join(
        [
            "<style>",
            ".driver-intro-card {",
            "border:1px solid #cbd5e1;",
            "border-bottom:4px solid #1d8bea;",
            "border-radius:22px;",
            "background:linear-gradient(135deg,#f8fafc 0%,#ffffff 72%);",
            "box-shadow:0 14px 32px rgba(15,23,42,0.06);",
            "padding:1.15rem 1.35rem;",
            "margin:0.25rem 0 1.2rem 0;",
            "}",
            ".driver-intro-top {",
            "display:flex;",
            "align-items:center;",
            "justify-content:space-between;",
            "gap:1rem;",
            "margin-bottom:0.75rem;",
            "}",
            ".driver-intro-date {",
            "font-size:0.92rem;",
            "color:#64748b;",
            "font-weight:750;",
            "line-height:1.25;",
            "margin-bottom:0.75rem;",
            "}",
            ".driver-intro-title {",
            "font-size:1.32rem;",
            "font-weight:900;",
            "line-height:1.12;",
            "color:#0f172a;",
            "letter-spacing:-0.02em;",
            "margin-bottom:0.85rem;",
            "}",
            ".driver-intro-badge {",
            "border:1px solid #bfdbfe;",
            "background:#eff6ff;",
            "color:#1d4ed8;",
            "border-radius:999px;",
            "padding:0.28rem 0.7rem;",
            "font-size:0.78rem;",
            "font-weight:850;",
            "white-space:nowrap;",
            "}",
            ".driver-intro-text {",
            "font-size:1rem;",
            "line-height:1.55;",
            "color:#64748b;",
            "max-width:58rem;",
            "margin-bottom:1rem;",
            "}",
            ".driver-intro-flow {",
            "display:grid;",
            "grid-template-columns:repeat(3, minmax(0, 1fr));",
            "gap:0.65rem;",
            "}",
            ".driver-intro-step {",
            "border:1px solid #e5e7eb;",
            "border-radius:16px;",
            "background:#ffffff;",
            "padding:0.72rem 0.85rem;",
            "}",
            ".driver-intro-step:nth-child(1) {",
            "border-color:#bfdbfe;",
            "background:linear-gradient(135deg,#eff6ff 0%,#ffffff 72%);",
            "}",
            ".driver-intro-step:nth-child(2) {",
            "border-color:#dbeafe;",
            "background:linear-gradient(135deg,#f8fafc 0%,#ffffff 72%);",
            "}",
            ".driver-intro-step:nth-child(3) {",
            "border-color:#bbf7d0;",
            "background:linear-gradient(135deg,#f0fdf4 0%,#ffffff 72%);",
            "}",
            ".driver-intro-step-label {",
            "font-size:0.74rem;",
            "font-weight:750;",
            "color:#64748b;",
            "line-height:1.2;",
            "margin-bottom:0.25rem;",
            "}",
            ".driver-intro-step-value {",
            "font-size:0.98rem;",
            "font-weight:900;",
            "color:#111827;",
            "line-height:1.22;",
            "}",
            "@media (max-width: 640px) {",
            ".driver-intro-card {",
            "border-radius:18px;",
            "padding:0.9rem 0.95rem;",
            "margin:0.25rem 0 0.9rem 0;",
            "}",
            ".driver-intro-top {",
            "margin-bottom:0.55rem;",
            "}",
            ".driver-intro-title {",
            "font-size:1.18rem;",
            "line-height:1.15;",
            "margin-bottom:0.55rem;",
            "}",
            ".driver-intro-badge {",
            "font-size:0.64rem;",
            "padding:0.22rem 0.5rem;",
            "}",
            ".driver-intro-text {",
            "font-size:0.78rem;",
            "line-height:1.35;",
            "margin-bottom:0.7rem;",
            "}",
            ".driver-intro-flow {",
            "grid-template-columns:repeat(3, minmax(0, 1fr));",
            "gap:0.35rem;",
            "}",
            ".driver-intro-step {",
            "border-radius:12px;",
            "padding:0.5rem 0.35rem;",
            "text-align:center;",
            "}",
            ".driver-intro-step-label {",
            "font-size:0.54rem;",
            "line-height:1.1;",
            "}",
            ".driver-intro-step-value {",
            "font-size:0.68rem;",
            "line-height:1.15;",
            "}",
            "}",
            "</style>",
            '<div class="driver-intro-card">',
            '<div class="driver-intro-top">',
            f'<div class="driver-intro-date">Karta kierowcy na {selected_date}</div>',
            '<div class="driver-intro-badge">zadania terenowe</div>',
            "</div>",
            '<div class="driver-intro-title">Zadania dla kierowcy</div>',
            '<div class="driver-intro-text">Wybierz rejon do obsługi. Po wyborze system pokaże konkretne zadania dla kierowcy: gdzie jechać, co zrobić, ile rowerów relokować i w jakiej kolejności działać.</div>',
            '<div class="driver-intro-flow">',
            '<div class="driver-intro-step">',
            '<div class="driver-intro-step-label">Krok 1</div>',
            '<div class="driver-intro-step-value">Wybierz rejon</div>',
            "</div>",
            '<div class="driver-intro-step">',
            '<div class="driver-intro-step-label">Krok 2</div>',
            '<div class="driver-intro-step-value">Ustal kolejność</div>',
            "</div>",
            '<div class="driver-intro-step">',
            '<div class="driver-intro-step-label">Krok 3</div>',
            '<div class="driver-intro-step-value">Realizuj zadania</div>',
            "</div>",
            "</div>",
            "</div>",
        ]
    )

    st.markdown(driver_intro_html, unsafe_allow_html=True)

    if daily_actions_df.empty or daily_actions_view_df.empty:
        st.info("Brak zadań kierowcy dla aktualnych filtrów.")
    else:

        driver_region_source_df = daily_actions_df.copy()

        driver_region_source_df["deliver_units_for_region"] = 0
        driver_region_source_df["remove_units_for_region"] = 0

        driver_region_source_df.loc[
            driver_region_source_df["recommended_action"] == "deliver_bikes",
            "deliver_units_for_region",
        ] = driver_region_source_df.loc[
            driver_region_source_df["recommended_action"] == "deliver_bikes",
            "estimated_relocation_units",
        ].fillna(0)

        driver_region_source_df.loc[
            driver_region_source_df["recommended_action"] == "remove_bikes",
            "remove_units_for_region",
        ] = driver_region_source_df.loc[
            driver_region_source_df["recommended_action"] == "remove_bikes",
            "estimated_relocation_units",
        ].fillna(0)

        driver_region_table_df = (
            driver_region_source_df.groupby("microzone_id", as_index=False)
            .agg(
                station_count=("microzone_id", "count"),
                estimated_deliver_units=("deliver_units_for_region", "sum"),
                estimated_remove_units=("remove_units_for_region", "sum"),
                expected_business_impact=("expected_business_impact", "sum"),
                top_daily_plan_rank=("daily_plan_rank", "min"),
            )
            .rename(
                columns={
                    "microzone_id": "Rejon miasta",
                    "station_count": "Stacje do obsługi",
                    "estimated_deliver_units": "Dowieźć",
                    "estimated_remove_units": "Zabrać",
                    "expected_business_impact": "Potencjał",
                    "top_daily_plan_rank": "Najwyższy priorytet",
                }
            )
        )

        driver_region_table_df["Liczba stacji"] = driver_region_table_df["Stacje do obsługi"]
        driver_region_table_df["Bilans"] = (
            driver_region_table_df["Zabrać"] - driver_region_table_df["Dowieźć"]
        )

        driver_region_table_df["Kierunek"] = "zbilansowany"
        driver_region_table_df.loc[
            driver_region_table_df["Bilans"] < 0,
            "Kierunek",
        ] = "potrzeba dowozu"
        driver_region_table_df.loc[
            driver_region_table_df["Bilans"] > 0,
            "Kierunek",
        ] = "potrzeba odbioru"

        driver_region_table_df = (
            driver_region_table_df.sort_values(
                ["Dowieźć", "Zabrać", "Bilans", "Potencjał"],
                ascending=[False, False, True, False],
            )
            .head(100)
            .copy()
            .reset_index(drop=True)
        )

        driver_region_table_df["Potencjał"] = driver_region_table_df["Potencjał"].round(2)

        driver_region_columns = [
            "Rejon miasta",
            "Liczba stacji",
            "Stacje do obsługi",
            "Dowieźć",
            "Zabrać",
            "Bilans",
            "Kierunek",
        ]

        st.markdown("### Plan rejonów dla kierowcy")

        driver_region_event = st.dataframe(
            driver_region_table_df[driver_region_columns],
            width="stretch",
            height=300,
            hide_index=True,
            key="driver_region_table",
            on_select="rerun",
            selection_mode="single-row",
            column_config={
                "Rejon miasta": st.column_config.TextColumn("Rejon miasta", width=125),
                "Liczba stacji": st.column_config.NumberColumn("Liczba stacji", width=95),
                "Stacje do obsługi": st.column_config.NumberColumn("Stacje do obsługi", width=130),
                "Dowieźć": st.column_config.NumberColumn("Dowieźć", width=85),
                "Zabrać": st.column_config.NumberColumn("Zabrać", width=85),
                "Bilans": st.column_config.NumberColumn("Bilans", width=85),
                "Kierunek": st.column_config.TextColumn("Kierunek", width=150),
            },
        )

        selected_driver_rows = driver_region_event.selection.rows

        selected_driver_region = None
        if selected_driver_rows:
            selected_driver_region = str(
                driver_region_table_df.iloc[selected_driver_rows[0]]["Rejon miasta"]
            )

        if selected_driver_region:
            driver_scope_df = daily_actions_df.loc[
                daily_actions_df["microzone_id"].astype(str) == selected_driver_region
            ].copy()
            driver_scope_label = f"Wybrany rejon: {selected_driver_region}"
        else:
            driver_scope_df = daily_actions_df.copy()
            driver_scope_label = "Wszystkie rejony z aktualnych filtrów"

        driver_cards_df = build_operational_view(driver_scope_df)

        st.markdown("### Kolejność zadań kierowcy")

        if "driver_order_mode" not in st.session_state:
            st.session_state["driver_order_mode"] = "impact"

        driver_order_col_1, driver_order_col_2, driver_order_col_3 = st.columns(3)

        with driver_order_col_1:
            if st.button(
                "Potencjał operacyjny",
                use_container_width=True,
                type="primary" if st.session_state["driver_order_mode"] == "impact" else "secondary",
                key="driver_order_impact",
            ):
                st.session_state["driver_order_mode"] = "impact"
                st.rerun()

        with driver_order_col_2:
            if st.button(
                "Pilność + godzina",
                use_container_width=True,
                type="primary" if st.session_state["driver_order_mode"] == "priority" else "secondary",
                key="driver_order_priority",
            ):
                st.session_state["driver_order_mode"] = "priority"
                st.rerun()

        with driver_order_col_3:
            if st.button(
                "Godzina ryzyka",
                use_container_width=True,
                type="primary" if st.session_state["driver_order_mode"] == "hour" else "secondary",
                key="driver_order_hour",
            ):
                st.session_state["driver_order_mode"] = "hour"
                st.rerun()

        priority_sort_map = {
            "bardzo wysoki": 1,
            "wysoki": 2,
            "średni": 3,
            "niski": 4,
        }

        if not driver_cards_df.empty:
            driver_cards_df["priority_sort"] = (
                driver_cards_df["Pilność"]
                .map(priority_sort_map)
                .fillna(99)
                .astype(int)
            )

            driver_cards_df["risk_hour_sort"] = pd.to_datetime(
                driver_cards_df["Godzina ryzyka"].astype(str),
                format="%H:%M",
                errors="coerce",
            )

            if st.session_state["driver_order_mode"] == "priority":
                driver_cards_df = driver_cards_df.sort_values(
                    ["priority_sort", "risk_hour_sort", "Potencjał", "Lp."],
                    ascending=[True, True, False, True],
                ).copy()

            elif st.session_state["driver_order_mode"] == "hour":
                driver_cards_df = driver_cards_df.sort_values(
                    ["risk_hour_sort", "priority_sort", "Potencjał", "Lp."],
                    ascending=[True, True, False, True],
                ).copy()

            else:
                driver_cards_df = driver_cards_df.sort_values(
                    ["Potencjał", "priority_sort", "risk_hour_sort", "Lp."],
                    ascending=[False, True, True, True],
                ).copy()

            driver_cards_df = (
                driver_cards_df.drop(
                    columns=["priority_sort", "risk_hour_sort"],
                    errors="ignore",
                )
                .reset_index(drop=True)
            )

        driver_station_count = int(driver_scope_df.shape[0])
        driver_deliver_sum = int(
            driver_scope_df.loc[
                driver_scope_df["recommended_action"] == "deliver_bikes",
                "estimated_relocation_units",
            ]
            .fillna(0)
            .sum()
        )
        driver_remove_sum = int(
            driver_scope_df.loc[
                driver_scope_df["recommended_action"] == "remove_bikes",
                "estimated_relocation_units",
            ]
            .fillna(0)
            .sum()
        )
        driver_balance = driver_remove_sum - driver_deliver_sum

        st.markdown("### Zadania kierowcy")
        st.caption(
            f"{driver_scope_label}. Lista obejmuje {format_number(len(driver_cards_df))} zadań."
        )

        st.markdown(
            f"""
            <div style="display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:0.7rem; margin:0.7rem 0 0.8rem 0;">
                <div style="border:1px solid #cbd5e1; border-bottom:3px solid #94a3b8; border-radius:14px; padding:0.65rem 0.85rem; background:linear-gradient(135deg,#f8fafc 0%,#ffffff 72%); box-shadow:0 10px 22px rgba(100,116,139,0.06);">
                    <div style="font-size:0.78rem; color:#6b7280;">Stacje</div>
                    <div style="font-size:1.45rem; font-weight:800; color:#111827;">{driver_station_count}</div>
                    <div style="font-size:0.72rem; color:#6b7280;">do obsługi</div>
                </div>
                <div style="border:1px solid #fed7aa; border-bottom:3px solid #fdba74; border-radius:14px; padding:0.65rem 0.85rem; background:linear-gradient(135deg,#fff7ed 0%,#ffffff 72%); box-shadow:0 10px 22px rgba(249,115,22,0.06);">
                    <div style="font-size:0.78rem; color:#6b7280;">Dowieźć</div>
                    <div style="font-size:1.45rem; font-weight:800; color:#111827;">{driver_deliver_sum}</div>
                    <div style="font-size:0.72rem; color:#6b7280;">rowerów</div>
                </div>
                <div style="border:1px solid #bfdbfe; border-bottom:3px solid #60a5fa; border-radius:14px; padding:0.65rem 0.85rem; background:linear-gradient(135deg,#eff6ff 0%,#ffffff 72%); box-shadow:0 10px 22px rgba(37,99,235,0.06);">
                    <div style="font-size:0.78rem; color:#6b7280;">Zabrać</div>
                    <div style="font-size:1.45rem; font-weight:800; color:#111827;">{driver_remove_sum}</div>
                    <div style="font-size:0.72rem; color:#6b7280;">rowerów</div>
                </div>
                <div style="border:1px solid #cbd5e1; border-bottom:3px solid #64748b; border-radius:14px; padding:0.65rem 0.85rem; background:linear-gradient(135deg,#f8fafc 0%,#ffffff 72%); box-shadow:0 10px 22px rgba(100,116,139,0.06);">
                    <div style="font-size:0.78rem; color:#6b7280;">Bilans</div>
                    <div style="font-size:1.45rem; font-weight:800; color:#111827;">{driver_balance}</div>
                    <div style="font-size:0.72rem; color:#6b7280;">ujemny = dowóz</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if driver_cards_df.empty:
            st.info("Brak zadań kierowcy dla wybranego rejonu.")
        else:
            driver_cards_per_row = 1 if cards_per_row == 1 else 2

            for row_index in range(0, len(driver_cards_df), driver_cards_per_row):
                card_columns = st.columns(driver_cards_per_row)

                for card_column, (_, row) in zip(
                    card_columns,
                    driver_cards_df.iloc[row_index:row_index + driver_cards_per_row].iterrows(),
                ):
                    with card_column:
                        task_rank = row.get("Lp.", row_index + 1)
                        station_name = row.get("Stacja", "")
                        microzone_id = row.get("Mikrostrefa", "")
                        priority_label = row.get("Pilność", "")
                        action_label = row.get("Zalecane działanie", "")
                        relocation_label = row.get("Szacowana relokacja", "")
                        risk_hour = row.get("Godzina ryzyka", "")
                        confidence_label = row.get("Pewność", "")
                        impact_value_raw = row.get("Potencjał", "")
                        impact_value = (
                            f"{float(impact_value_raw):.2f}"
                            if pd.notna(impact_value_raw) and impact_value_raw != ""
                            else "brak danych"
                        )

                        latest_feedback_status = get_latest_feedback_status(
                            feedback_log=feedback_log,
                            task_rank=int(task_rank),
                            station_name=station_name,
                        )

                        card_html = (
                            "<div style='min-height:245px;'>"
                            f"<div style='font-size:1.35rem; font-weight:850; color:#111827; margin-bottom:0.75rem;'>Zadanie {task_rank}</div>"
                            f"<div style='font-size:1.05rem; color:#111827; margin-bottom:0.5rem;'><b>Jedź do:</b> {station_name}</div>"
                            f"<div style='font-size:0.98rem; color:#6b7280; margin-bottom:0.5rem;'><b>Rejon miasta:</b> {microzone_id}</div>"
                            f"<div style='font-size:1.02rem; color:#111827; margin-bottom:0.5rem;'><b>Działanie:</b> {action_label}</div>"
                            f"<div style='font-size:1.15rem; font-weight:850; color:#111827; margin-bottom:0.55rem;'>{relocation_label}</div>"
                            f"<div style='font-size:0.98rem; color:#374151; margin-bottom:0.35rem;'><b>Godzina ryzyka:</b> {risk_hour}</div>"
                            f"<div style='font-size:0.98rem; color:#374151; margin-bottom:0.35rem;'><b>Pilność:</b> {priority_label}</div>"
                            f"<div style='font-size:0.98rem; color:#374151;'><b>Pewność:</b> {confidence_label} | <b>Potencjał:</b> {impact_value}</div>"
                            "</div>"
                        )

                        with st.container(border=True):
                            st.markdown(card_html, unsafe_allow_html=True)

                            if latest_feedback_status:
                                status_styles = {
                                    "przyjęte": {
                                        "background": "#eff6ff",
                                        "color": "#1d4ed8",
                                        "border": "#bfdbfe",
                                    },
                                    "wykonane": {
                                        "background": "#dcfce7",
                                        "color": "#166534",
                                        "border": "#bbf7d0",
                                    },
                                    "błąd w terenie": {
                                        "background": "#fee2e2",
                                        "color": "#991b1b",
                                        "border": "#fecaca",
                                    },
                                }

                                status_style = status_styles.get(
                                    latest_feedback_status,
                                    {
                                        "background": "#f3f4f6",
                                        "color": "#374151",
                                        "border": "#d1d5db",
                                    },
                                )

                                status_html = (
                                    f"<div style='margin:0.55rem 0 0.75rem 0; padding:0.5rem 0.7rem; "
                                    f"border-radius:0.75rem; background:{status_style['background']}; "
                                    f"color:{status_style['color']}; border:1px solid {status_style['border']}; "
                                    f"font-weight:700;'>Status zadania: {latest_feedback_status}</div>"
                                )

                                st.markdown(status_html, unsafe_allow_html=True)

                            button_col_1, button_col_2, button_col_3 = st.columns(3)

                            if button_col_1.button(
                                "Przyjęte",
                                key=f"accepted_{task_rank}_{row_index}",
                                use_container_width=True,
                            ):
                                append_feedback_entry(
                                    build_feedback_entry(
                                        status="przyjęte",
                                        row=row,
                                        selected_date=selected_date,
                                    )
                                )
                                st.rerun()

                            if button_col_2.button(
                                "Wykonane",
                                key=f"done_{task_rank}_{row_index}",
                                use_container_width=True,
                            ):
                                append_feedback_entry(
                                    build_feedback_entry(
                                        status="wykonane",
                                        row=row,
                                        selected_date=selected_date,
                                    )
                                )
                                st.rerun()

                            if button_col_3.button(
                                "Błąd",
                                key=f"issue_{task_rank}_{row_index}",
                                use_container_width=True,
                            ):
                                append_feedback_entry(
                                    build_feedback_entry(
                                        status="błąd w terenie",
                                        row=row,
                                        selected_date=selected_date,
                                    )
                                )
                                st.rerun()

with tab_feedback:
    st.subheader("Status realizacji")

    status_context_html = "\n".join(
        [
            '<div style="border:1px solid #cbd5e1; border-bottom:4px solid #22c55e; border-radius:22px; background:linear-gradient(135deg,#f0fdf4 0%,#ffffff 72%); box-shadow:0 14px 32px rgba(22,163,74,0.06); padding:1rem 1.25rem; margin:0.45rem 0 1rem 0;">',
            '<div style="display:flex; align-items:center; justify-content:space-between; gap:1rem; margin-bottom:0.55rem;">',
            f'<div style="font-size:0.92rem; color:#64748b; font-weight:750;">Dzień operacyjny: {selected_date}</div>',
            '<div style="border:1px solid #bbf7d0; background:#dcfce7; color:#166534; border-radius:999px; padding:0.25rem 0.65rem; font-size:0.76rem; font-weight:850; white-space:nowrap;">status zadań</div>',
            '</div>',
            '<div style="font-size:1.15rem; font-weight:900; color:#0f172a; line-height:1.25; margin-bottom:0.35rem;">Realizacja zadań dla wybranego dnia historycznego</div>',
            '<div style="font-size:0.92rem; color:#64748b; line-height:1.45;">Kolumna <b>Dzień operacyjny</b> pokazuje datę zadania z danych historycznych. Kolumna <b>Czas</b> pokazuje moment kliknięcia statusu w aplikacji.</div>',
            '</div>',
        ]
    )

    st.markdown(status_context_html, unsafe_allow_html=True)

    selected_operational_date_label = str(selected_date)

    feedback_entries = feedback_log.get("entries", [])

    if not feedback_entries:
        st.info("Brak zapisanych statusów z terenu.")
    else:
        feedback_df = pd.DataFrame(feedback_entries).copy()

        if "created_at_utc" in feedback_df.columns:
            feedback_df["_sort_time"] = pd.to_datetime(
                feedback_df["created_at_utc"],
                errors="coerce",
                utc=True,
            )

            feedback_df = feedback_df.sort_values(
                "_sort_time",
                ascending=False,
                na_position="last",
            ).copy()

            feedback_df["Czas"] = (
                feedback_df["_sort_time"]
                .dt.tz_convert("Europe/Warsaw")
                .dt.strftime("%Y-%m-%d %H:%M")
            ).fillna("")
        else:
            feedback_df["_sort_time"] = pd.NaT
            feedback_df["Czas"] = ""

        if "activity_date" in feedback_df.columns:
            feedback_activity_date = pd.to_datetime(
                feedback_df["activity_date"],
                errors="coerce",
            )

            feedback_df["Dzień operacyjny"] = (
                feedback_activity_date.dt.strftime("%Y-%m-%d")
            )

            feedback_df["Dzień operacyjny"] = feedback_df["Dzień operacyjny"].fillna(
                feedback_df["activity_date"].fillna("").astype(str)
            )
        else:
            feedback_df["Dzień operacyjny"] = ""

        all_feedback_history_df = feedback_df.copy()

        feedback_df = feedback_df.loc[
            feedback_df["Dzień operacyjny"] == selected_operational_date_label
        ].copy()

        def get_feedback_value(row: pd.Series, column_name: str, default_value: str = "") -> str:
            if column_name in row.index and pd.notna(row[column_name]):
                return str(row[column_name])
            return default_value

        def format_feedback_task(value: object) -> str:
            try:
                return f"Zadanie {int(value)}"
            except (TypeError, ValueError):
                return "Zadanie"

        latest_feedback_df = (
            feedback_df.sort_values("_sort_time", ascending=False, na_position="last")
            .drop_duplicates(subset=["task_rank", "station_name"], keep="first")
            .copy()
        )

        active_region_ids = (
            latest_feedback_df["microzone_id"]
            .dropna()
            .astype(str)
            .drop_duplicates()
            .tolist()
            if "microzone_id" in latest_feedback_df.columns
            else []
        )

        if not active_region_ids:
            st.info("Brak aktywnych rejonów ze statusem realizacji.")
        else:
            active_plan_df = daily_actions_df.loc[
                daily_actions_df["microzone_id"].astype(str).isin(active_region_ids)
            ].copy()

            active_plan_view_df = build_operational_view(active_plan_df)

            latest_status_map = {}

            for _, feedback_row in latest_feedback_df.iterrows():
                task_rank = get_feedback_value(feedback_row, "task_rank")
                station_name = get_feedback_value(feedback_row, "station_name")
                latest_status_map[(task_rank, station_name)] = {
                    "status": get_feedback_value(feedback_row, "status", "brak statusu"),
                    "time": get_feedback_value(feedback_row, "Czas"),
                    "operational_date": get_feedback_value(feedback_row, "Dzień operacyjny"),
                }

            status_summary_rows = []

            for region_id in active_region_ids:
                region_plan_df = active_plan_view_df.loc[
                    active_plan_view_df["Mikrostrefa"].astype(str) == region_id
                ].copy()

                if region_plan_df.empty:
                    continue

                region_total = int(region_plan_df.shape[0])
                accepted_count = 0
                done_count = 0
                issue_count = 0

                for _, task_row in region_plan_df.iterrows():
                    task_key = (
                        str(task_row.get("Lp.", "")),
                        str(task_row.get("Stacja", "")),
                    )

                    task_status = latest_status_map.get(task_key, {}).get("status", "")

                    if task_status == "przyjęte":
                        accepted_count += 1
                    elif task_status == "wykonane":
                        done_count += 1
                    elif task_status == "błąd w terenie":
                        issue_count += 1

                started_count = accepted_count + done_count + issue_count
                waiting_count = max(region_total - started_count, 0)

                status_summary_rows.append(
                    {
                        "Dzień operacyjny": selected_operational_date_label,
                        "Rejon miasta": region_id,
                        "Stacje w rejonie": region_total,
                        "Przyjęte": accepted_count,
                        "Wykonane": done_count,
                        "Błąd": issue_count,
                        "Oczekuje": waiting_count,
                    }
                )

            region_status_df = pd.DataFrame(status_summary_rows)

            if region_status_df.empty:
                st.info("Brak aktywnych rejonów do pokazania.")
            else:
                total_regions = int(region_status_df.shape[0])
                total_started = int(
                    region_status_df["Przyjęte"].sum()
                    + region_status_df["Wykonane"].sum()
                    + region_status_df["Błąd"].sum()
                )
                total_done = int(region_status_df["Wykonane"].sum())
                total_waiting = int(region_status_df["Oczekuje"].sum())

                st.markdown(
                    f"""
                    <div style="display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:0.7rem; margin:0.7rem 0 1rem 0;">
                        <div style="border:1px solid #c7d2fe; border-bottom:3px solid #818cf8; border-radius:14px; padding:0.65rem 0.85rem; background:linear-gradient(135deg,#eef2ff 0%,#ffffff 72%); box-shadow:0 10px 22px rgba(79,70,229,0.06);">
                            <div style="font-size:0.78rem; color:#6b7280; min-height:2.05rem; line-height:1.25;">Aktywne<br>rejony</div>
                            <div style="font-size:1.45rem; font-weight:800; color:#111827;">{total_regions}</div>
                            <div style="font-size:0.72rem; color:#6b7280;">z ruchem w terenie</div>
                        </div>
                        <div style="border:1px solid #bfdbfe; border-bottom:3px solid #60a5fa; border-radius:14px; padding:0.65rem 0.85rem; background:linear-gradient(135deg,#eff6ff 0%,#ffffff 72%); box-shadow:0 10px 22px rgba(37,99,235,0.06);">
                            <div style="font-size:0.78rem; color:#6b7280; min-height:2.05rem; line-height:1.25;">Podjęte</div>
                            <div style="font-size:1.45rem; font-weight:800; color:#111827;">{total_started}</div>
                            <div style="font-size:0.72rem; color:#6b7280;">przyjęte / wykonane / błąd</div>
                        </div>
                        <div style="border:1px solid #bbf7d0; border-bottom:3px solid #22c55e; border-radius:14px; padding:0.65rem 0.85rem; background:linear-gradient(135deg,#f0fdf4 0%,#ffffff 72%); box-shadow:0 10px 22px rgba(22,163,74,0.06);">
                            <div style="font-size:0.78rem; color:#6b7280; min-height:2.05rem; line-height:1.25;">Wykonane</div>
                            <div style="font-size:1.45rem; font-weight:800; color:#111827;">{total_done}</div>
                            <div style="font-size:0.72rem; color:#6b7280;">zamknięte zadania</div>
                        </div>
                        <div style="border:1px solid #fed7aa; border-bottom:3px solid #fdba74; border-radius:14px; padding:0.65rem 0.85rem; background:linear-gradient(135deg,#fff7ed 0%,#ffffff 72%); box-shadow:0 10px 22px rgba(249,115,22,0.06);">
                            <div style="font-size:0.78rem; color:#6b7280; min-height:2.05rem; line-height:1.25;">Oczekuje</div>
                            <div style="font-size:1.45rem; font-weight:800; color:#111827;">{total_waiting}</div>
                            <div style="font-size:0.72rem; color:#6b7280;">jeszcze bez statusu</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                st.markdown("### Aktywne rejony w realizacji")

                st.dataframe(
                    region_status_df,
                    width="stretch",
                    height=240,
                    hide_index=True,
                    column_config={
                        "Dzień operacyjny": st.column_config.TextColumn("Dzień operacyjny", width=125),
                        "Rejon miasta": st.column_config.TextColumn("Rejon miasta", width=125),
                        "Stacje w rejonie": st.column_config.NumberColumn("Stacje w rejonie", width=125),
                        "Przyjęte": st.column_config.NumberColumn("Przyjęte", width=95),
                        "Wykonane": st.column_config.NumberColumn("Wykonane", width=100),
                        "Błąd": st.column_config.NumberColumn("Błąd", width=80),
                        "Oczekuje": st.column_config.NumberColumn("Oczekuje", width=100),
                    },
                )

                st.markdown("### Szczegóły realizacji według rejonów")

                for _, region_summary_row in region_status_df.iterrows():
                    region_id = str(region_summary_row["Rejon miasta"])

                    region_plan_df = active_plan_view_df.loc[
                        active_plan_view_df["Mikrostrefa"].astype(str) == region_id
                    ].copy()

                    region_task_rows = []

                    for _, task_row in region_plan_df.iterrows():
                        task_key = (
                            str(task_row.get("Lp.", "")),
                            str(task_row.get("Stacja", "")),
                        )

                        latest_status = latest_status_map.get(task_key, {})

                        region_task_rows.append(
                            {
                                "Dzień operacyjny": latest_status.get("operational_date", selected_operational_date_label),
                                "Zadanie": format_feedback_task(task_row.get("Lp.", "")),
                                "Stacja": task_row.get("Stacja", ""),
                                "Status": latest_status.get("status", "oczekuje"),
                                "Czas statusu": latest_status.get("time", ""),
                                "Relokacja": task_row.get("Szacowana relokacja", ""),
                                "Godzina ryzyka": task_row.get("Godzina ryzyka", ""),
                                "Pilność": task_row.get("Pilność", ""),
                            }
                        )

                    region_task_status_df = pd.DataFrame(region_task_rows)

                    with st.expander(
                        f"{region_id} — wykonane: {int(region_summary_row['Wykonane'])}, "
                        f"przyjęte: {int(region_summary_row['Przyjęte'])}, "
                        f"oczekuje: {int(region_summary_row['Oczekuje'])}, "
                        f"błąd: {int(region_summary_row['Błąd'])}"
                    ):
                        st.dataframe(
                            region_task_status_df,
                            width="stretch",
                            hide_index=True,
                            column_config={
                                "Dzień operacyjny": st.column_config.TextColumn("Dzień operacyjny", width=125),
                                "Zadanie": st.column_config.TextColumn("Zadanie", width=100),
                                "Stacja": st.column_config.TextColumn("Stacja", width=170),
                                "Status": st.column_config.TextColumn("Status", width=120),
                                "Czas statusu": st.column_config.TextColumn("Czas statusu", width=140),
                                "Relokacja": st.column_config.TextColumn("Relokacja", width=180),
                                "Godzina ryzyka": st.column_config.TextColumn("Godzina ryzyka", width=120),
                                "Pilność": st.column_config.TextColumn("Pilność", width=120),
                            },
                        )

        st.markdown("### Ostatnie zgłoszenia z terenu")

        compact_feedback_df = pd.DataFrame(
            {
                "Dzień operacyjny": feedback_df["Dzień operacyjny"],
                "Czas": feedback_df["Czas"],
                "Status": feedback_df["status"].fillna("").astype(str)
                if "status" in feedback_df.columns
                else "",
                "Rejon miasta": feedback_df["microzone_id"].fillna("").astype(str)
                if "microzone_id" in feedback_df.columns
                else "",
                "Zadanie": feedback_df["task_rank"].apply(format_feedback_task)
                if "task_rank" in feedback_df.columns
                else "",
                "Stacja": feedback_df["station_name"].fillna("").astype(str)
                if "station_name" in feedback_df.columns
                else "",
                "Relokacja": feedback_df["relocation"].fillna("").astype(str)
                if "relocation" in feedback_df.columns
                else "",
                "Godzina": feedback_df["risk_hour"].fillna("").astype(str)
                if "risk_hour" in feedback_df.columns
                else "",
            }
        )

        st.dataframe(
            compact_feedback_df.head(30),
            width="stretch",
            height=260,
            hide_index=True,
            column_config={
                "Dzień operacyjny": st.column_config.TextColumn("Dzień operacyjny", width=125),
                "Czas": st.column_config.TextColumn("Czas", width=135),
                "Status": st.column_config.TextColumn("Status", width=120),
                "Rejon miasta": st.column_config.TextColumn("Rejon miasta", width=120),
                "Zadanie": st.column_config.TextColumn("Zadanie", width=105),
                "Stacja": st.column_config.TextColumn("Stacja", width=170),
                "Relokacja": st.column_config.TextColumn("Relokacja", width=180),
                "Godzina": st.column_config.TextColumn("Godzina", width=90),
            },
        )

        st.markdown("### Historia realizacji — podsumowanie dni operacyjnych")

        history_source_df = all_feedback_history_df.copy()

        if history_source_df.empty:
            st.info("Brak historycznych statusów realizacji.")
        else:
            history_source_df["status"] = (
                history_source_df["status"].fillna("").astype(str)
                if "status" in history_source_df.columns
                else ""
            )

            history_source_df["is_accepted"] = history_source_df["status"].eq("przyjęte").astype(int)
            history_source_df["is_done"] = history_source_df["status"].eq("wykonane").astype(int)
            history_source_df["is_issue"] = history_source_df["status"].eq("błąd w terenie").astype(int)

            history_summary_df = (
                history_source_df.groupby("Dzień operacyjny", as_index=False)
                .agg(
                    zgłoszenia=("status", "count"),
                    rejony=("microzone_id", "nunique"),
                    zadania=("task_rank", "nunique"),
                    przyjęte=("is_accepted", "sum"),
                    wykonane=("is_done", "sum"),
                    błędy=("is_issue", "sum"),
                    ostatni_zapis=("Czas", "max"),
                )
                .rename(
                    columns={
                        "zgłoszenia": "Zgłoszenia",
                        "rejony": "Rejony",
                        "zadania": "Zadania",
                        "przyjęte": "Przyjęte",
                        "wykonane": "Wykonane",
                        "błędy": "Błędy",
                        "ostatni_zapis": "Ostatni zapis",
                    }
                )
                .sort_values("Dzień operacyjny", ascending=False)
                .reset_index(drop=True)
            )

            history_regions_df = (
                history_source_df.groupby("Dzień operacyjny")["microzone_id"]
                .apply(
                    lambda values: ", ".join(
                        sorted(values.dropna().astype(str).unique().tolist())
                    )
                )
                .reset_index()
                .rename(columns={"microzone_id": "Rejony miasta"})
            )

            history_summary_df = history_summary_df.merge(
                history_regions_df,
                on="Dzień operacyjny",
                how="left",
            )

            history_summary_df["Rejony miasta"] = (
                history_summary_df["Rejony miasta"].fillna("").astype(str)
            )

            history_summary_df = history_summary_df[
                [
                    "Dzień operacyjny",
                    "Rejony miasta",
                    "Zgłoszenia",
                    "Rejony",
                    "Zadania",
                    "Przyjęte",
                    "Wykonane",
                    "Błędy",
                    "Ostatni zapis",
                ]
            ].copy()

            total_history_days = int(history_summary_df["Dzień operacyjny"].nunique())
            total_history_reports = int(history_summary_df["Zgłoszenia"].sum())
            total_history_done = int(history_summary_df["Wykonane"].sum())
            total_history_issues = int(history_summary_df["Błędy"].sum())

            st.markdown(
                f"""
                <div style="display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:0.7rem; margin:0.7rem 0 1rem 0;">
                    <div style="border:1px solid #cbd5e1; border-bottom:3px solid #94a3b8; border-radius:14px; padding:0.65rem 0.85rem; background:linear-gradient(135deg,#f8fafc 0%,#ffffff 72%); box-shadow:0 10px 22px rgba(100,116,139,0.06);">
                        <div style="font-size:0.78rem; color:#6b7280;">Dni operacyjne</div>
                        <div style="font-size:1.45rem; font-weight:800; color:#111827;">{total_history_days}</div>
                        <div style="font-size:0.72rem; color:#6b7280;">z historią działań</div>
                    </div>
                    <div style="border:1px solid #bfdbfe; border-bottom:3px solid #60a5fa; border-radius:14px; padding:0.65rem 0.85rem; background:linear-gradient(135deg,#eff6ff 0%,#ffffff 72%); box-shadow:0 10px 22px rgba(37,99,235,0.06);">
                        <div style="font-size:0.78rem; color:#6b7280;">Zgłoszenia</div>
                        <div style="font-size:1.45rem; font-weight:800; color:#111827;">{total_history_reports}</div>
                        <div style="font-size:0.72rem; color:#6b7280;">łącznie w historii</div>
                    </div>
                    <div style="border:1px solid #bbf7d0; border-bottom:3px solid #22c55e; border-radius:14px; padding:0.65rem 0.85rem; background:linear-gradient(135deg,#f0fdf4 0%,#ffffff 72%); box-shadow:0 10px 22px rgba(22,163,74,0.06);">
                        <div style="font-size:0.78rem; color:#6b7280;">Wykonane</div>
                        <div style="font-size:1.45rem; font-weight:800; color:#111827;">{total_history_done}</div>
                        <div style="font-size:0.72rem; color:#6b7280;">zamknięte zadania</div>
                    </div>
                    <div style="border:1px solid #fecaca; border-bottom:3px solid #fca5a5; border-radius:14px; padding:0.65rem 0.85rem; background:linear-gradient(135deg,#fef2f2 0%,#ffffff 72%); box-shadow:0 10px 22px rgba(239,68,68,0.06);">
                        <div style="font-size:0.78rem; color:#6b7280;">Błędy</div>
                        <div style="font-size:1.45rem; font-weight:800; color:#111827;">{total_history_issues}</div>
                        <div style="font-size:0.72rem; color:#6b7280;">problemy w terenie</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.caption(
                "To jest zbiorcza historia demo z różnych dni operacyjnych. "
                "Bieżące kliknięcia użytkownika działają tylko w jego sesji i resetują się po odświeżeniu."
            )

            st.dataframe(
                history_summary_df.head(12),
                width="stretch",
                height=260,
                hide_index=True,
                column_config={
                    "Dzień operacyjny": st.column_config.TextColumn("Dzień operacyjny", width=125),
                    "Rejony miasta": st.column_config.TextColumn("Rejony miasta", width=220),
                    "Zgłoszenia": st.column_config.NumberColumn("Zgłoszenia", width=105),
                    "Rejony": st.column_config.NumberColumn("Rejony", width=85),
                    "Zadania": st.column_config.NumberColumn("Zadania", width=90),
                    "Przyjęte": st.column_config.NumberColumn("Przyjęte", width=95),
                    "Wykonane": st.column_config.NumberColumn("Wykonane", width=100),
                    "Błędy": st.column_config.NumberColumn("Błędy", width=80),
                    "Ostatni zapis": st.column_config.TextColumn("Ostatni zapis", width=135),
                },
            )


