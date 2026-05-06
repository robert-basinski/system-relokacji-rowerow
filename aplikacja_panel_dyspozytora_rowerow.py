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
PANEL_OUTPUTS_DIR = APP_DIR / "outputs_panel_dyspozytora"

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


@st.cache_data
def load_json_data(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json_data(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def append_feedback_entry(entry: dict) -> None:
    if FEEDBACK_LOG_PATH.exists():
        feedback_data = load_json_data(str(FEEDBACK_LOG_PATH))
    else:
        feedback_data = {"entries": []}

    feedback_entries = feedback_data.get("entries", [])
    feedback_entries.append(entry)
    feedback_data["entries"] = feedback_entries

    save_json_data(FEEDBACK_LOG_PATH, feedback_data)
    load_json_data.clear()

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
        amount = label.replace("deliver ", "").replace("-", "–")
        return f"dowieź {amount} rowerów"

    if label.startswith("remove "):
        amount = label.replace("remove ", "").replace("-", "–")
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
        "neutral": "background:#f9fafb; border:1px solid #e5e7eb;",
        "warning": "background:#fff7ed; border:1px solid #fed7aa;",
        "danger": "background:#fef2f2; border:1px solid #fecaca;",
        "success": "background:#f0fdf4; border:1px solid #bbf7d0;",
        "info": "background:#eff6ff; border:1px solid #bfdbfe;",
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
feedback_log = load_json_data(str(FEEDBACK_LOG_PATH))

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
    <div style="margin-bottom:1.4rem;">
        <div style="font-size:2.4rem; font-weight:800; line-height:1.15; color:#111827; margin-bottom:0.45rem;">
            Panel dyspozytora relokacji rowerów
        </div>
        <div style="font-size:1rem; color:#6b7280; line-height:1.45;">
            Plan dnia, lista działań, mikrostrefy, mapa, karty kierowcy i feedback z terenu.
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

    selected_microzone = st.selectbox("Mikrostrefa", options=microzone_options, index=0)
    selected_priority = st.selectbox("Pilność", options=priority_options, index=0)
    selected_problem = st.selectbox("Typ problemu", options=problem_options, index=0)

    card_layout_options = {
        "Komputer — 3 kolumny": 3,
        "Tablet — 2 kolumny": 2,
        "Telefon — 1 kolumna": 1,
    }

    selected_card_layout = st.selectbox(
        "Widok ekranu",
        options=list(card_layout_options.keys()),
        index=0,
    )

    cards_per_row = card_layout_options[selected_card_layout]

    kpi_cards_per_row = 5 if cards_per_row == 3 else cards_per_row

    st.divider()
    st.caption("Widok operacyjny dla dyspozytora i kierowcy")


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

tab_plan, tab_actions, tab_microzones, tab_map, tab_driver, tab_station, tab_feedback, tab_technical = st.tabs(
    [
        "Plan dnia",
        "Lista działań",
        "Mikrostrefy",
        "Mapa",
        "Karta kierowcy",
        "Szczegóły stacji",
        "Feedback",
        "Model i dane",
    ]
)


with tab_plan:
    st.subheader("Plan dnia")

    daily_plan_metrics = build_daily_plan_metrics(daily_actions_df)

    urgent_count = daily_plan_metrics["urgent_count"]
    bike_shortage_count = daily_plan_metrics["bike_shortage_count"]
    check_count = daily_plan_metrics["check_count"]
    relocation_sum = daily_plan_metrics["relocation_sum"]
    expected_impact_sum = daily_plan_metrics["expected_impact_sum"]

    st.markdown(
        f"""
        <div style="padding: 1.1rem 1.3rem; border: 1px solid #e5e7eb; border-radius: 18px; background: #f9fafb; margin-bottom: 1.2rem;">
            <div style="font-size: 0.95rem; color: #6b7280; margin-bottom: 0.35rem;">Plan operacyjny na {selected_date}</div>
            <div style="font-size: 1.2rem; font-weight: 700; color: #111827; margin-bottom: 0.35rem;">
                                Widok obejmuje {daily_plan_metrics["total_station_count"]} stacji po aktualnych filtrach.
            </div>
            <div style="font-size: 1rem; color: #374151;">
                Główne ryzyko: <b>{daily_plan_metrics["main_risk_label"]}</b>. Szacowana relokacja: <b>{daily_plan_metrics["relocation_sum"]} rowerów</b>. Potencjał operacyjny: <b>{format_number(daily_plan_metrics["expected_impact_sum"])}</b>.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

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
            "help_text": "Liczba stacji w aktualnym widoku, dla których głównym problemem jest ryzyko braku rowerów.",
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

    for item_index in range(0, len(kpi_items), kpi_cards_per_row):
        kpi_columns = st.columns(kpi_cards_per_row)

        for kpi_column, kpi_item in zip(
            kpi_columns,
            kpi_items[item_index:item_index + kpi_cards_per_row],
        ):
            with kpi_column:
                render_kpi_card(**kpi_item)
        
    st.markdown("### Najważniejsze działania")

    top_cards_df = daily_actions_view_df.head(6).copy()

    if top_cards_df.empty:
        st.info("Brak działań dla wybranych filtrów.")
    else:
        for row_index in range(0, len(top_cards_df), cards_per_row):
            card_columns = st.columns(cards_per_row)

            for card_column, (_, row) in zip(
                card_columns,
                top_cards_df.iloc[row_index:row_index + cards_per_row].iterrows(),
            ):
                with card_column:
                    with st.container(border=True):
                        render_daily_action_card(row)

    st.markdown("### Lista priorytetowych stacji")

    priority_table_df = daily_actions_view_df.head(40).copy()

    st.dataframe(
        priority_table_df,
        width="stretch",
        hide_index=True,
        column_config={
            "Lp.": st.column_config.NumberColumn("Lp.", width=35),
            "Stacja": st.column_config.TextColumn("Stacja", width=145),
            "Mikrostrefa": st.column_config.TextColumn("Mikrostrefa", width="small"),
            "Pilność": st.column_config.TextColumn("Pilność", width="small"),
            "Co grozi": st.column_config.TextColumn("Co grozi", width="medium"),
            "Zalecane działanie": st.column_config.TextColumn("Zalecane działanie", width="medium"),
            "Szacowana relokacja": st.column_config.TextColumn("Szacowana relokacja", width="medium"),
            "Godzina ryzyka": st.column_config.TextColumn("Godzina ryzyka", width="small"),
            "Pewność": st.column_config.TextColumn("Pewność", width="small"),
            "Potencjał": st.column_config.NumberColumn("Potencjał", format="%.2f", width="small"),
        },
    )


with tab_actions:
    st.subheader("Lista działań")

    st.caption(
        f"Pełna lista działań dla aktualnych filtrów: {format_number(len(daily_actions_view_df))} stacji."
    )

    if cards_per_row == 1:
        action_list_columns = [
            "Lp.",
            "Stacja",
            "Szacowana relokacja",
            "Godzina ryzyka",
        ]

        action_list_df = daily_actions_view_df[action_list_columns].copy()

        action_list_df = action_list_df.rename(
            columns={
                "Szacowana relokacja": "Relokacja",
                "Godzina ryzyka": "Godzina",
            }
        )

        st.dataframe(
            action_list_df,
            width="stretch",
            hide_index=True,
            column_config={
                "Lp.": st.column_config.NumberColumn("Lp.", width=35),
                "Stacja": st.column_config.TextColumn("Stacja", width=145),
                "Relokacja": st.column_config.TextColumn("Relokacja", width=190),
                "Godzina": st.column_config.TextColumn("Godzina", width=90),
            },
        )
    else:
        action_list_columns = [
            "Lp.",
            "Stacja",
            "Pilność",
            "Szacowana relokacja",
            "Godzina ryzyka",
            "Potencjał",
        ]

        action_list_df = daily_actions_view_df[action_list_columns].copy()

        action_list_df = action_list_df.rename(
            columns={
                "Szacowana relokacja": "Relokacja",
                "Godzina ryzyka": "Godzina",
            }
        )

        st.dataframe(
            action_list_df,
            width="stretch",
            hide_index=True,
            column_config={
                "Lp.": st.column_config.NumberColumn("Lp.", width=35),
                "Stacja": st.column_config.TextColumn("Stacja", width=145),
                "Pilność": st.column_config.TextColumn("Pilność", width=115),
                "Relokacja": st.column_config.TextColumn("Relokacja", width=190),
                "Godzina": st.column_config.TextColumn("Godzina", width=90),
                "Potencjał": st.column_config.NumberColumn("Potencjał", format="%.2f", width=95),
            },
        )

with tab_microzones:
    st.subheader("Mikrostrefy")

    if "activity_date" in microzone_summary_df.columns:
        daily_microzones_df = (
            microzone_summary_df.loc[microzone_summary_df["activity_date"] == selected_date_ts]
            .copy()
            .reset_index(drop=True)
        )
    else:
        daily_microzones_df = microzone_summary_df.copy()

    if daily_microzones_df.empty:
        st.info("Brak danych mikrostref dla wybranej daty.")
    else:
        microzone_view_df = daily_microzones_df.copy()

        microzone_view_df["Stacje do obsługi"] = (
            microzone_view_df["stations_to_deliver"].fillna(0)
            + microzone_view_df["stations_to_remove"].fillna(0)
            + microzone_view_df["stations_to_check"].fillna(0)
        ).astype(int)

        microzone_direction_labels = {
            "net_delivery_need": "potrzeba dowozu",
            "net_removal_need": "potrzeba odbioru",
            "balanced": "zbilansowana",
        }

        microzone_view_df["Kierunek"] = (
            microzone_view_df["microzone_balance_direction"]
            .map(microzone_direction_labels)
            .fillna(microzone_view_df["microzone_balance_direction"])
        )

        microzone_view_df = microzone_view_df.rename(
            columns={
                "microzone_id": "Mikrostrefa",
                "station_count": "Liczba stacji",
                "estimated_deliver_units": "Dowieźć",
                "estimated_remove_units": "Zabrać",
                "microzone_balance": "Bilans",
                "microzone_expected_business_impact": "Potencjał",
                "top_daily_plan_rank": "Najwyższy priorytet",
            }
        )

        if cards_per_row == 1:
            microzone_view_columns = [
                "Mikrostrefa",
                "Dowieźć",
                "Zabrać",
                "Bilans",
                "Kierunek",
            ]

            microzone_column_config = {
                "Mikrostrefa": st.column_config.TextColumn("Mikrostrefa", width=105),
                "Dowieźć": st.column_config.NumberColumn("Dowieźć", width=75),
                "Zabrać": st.column_config.NumberColumn("Zabrać", width=75),
                "Bilans": st.column_config.NumberColumn("Bilans", width=75),
                "Kierunek": st.column_config.TextColumn("Kierunek", width=140),
            }
        else:
            microzone_view_columns = [
                "Mikrostrefa",
                "Liczba stacji",
                "Stacje do obsługi",
                "Dowieźć",
                "Zabrać",
                "Bilans",
                "Kierunek",
                "Potencjał",
                "Najwyższy priorytet",
            ]

            microzone_column_config = {
                "Mikrostrefa": st.column_config.TextColumn("Mikrostrefa", width=110),
                "Liczba stacji": st.column_config.NumberColumn("Liczba stacji", width=95),
                "Stacje do obsługi": st.column_config.NumberColumn("Stacje do obsługi", width=130),
                "Dowieźć": st.column_config.NumberColumn("Dowieźć", width=85),
                "Zabrać": st.column_config.NumberColumn("Zabrać", width=85),
                "Bilans": st.column_config.NumberColumn("Bilans", width=85),
                "Kierunek": st.column_config.TextColumn("Kierunek", width=150),
                "Potencjał": st.column_config.NumberColumn("Potencjał", format="%.2f", width=105),
                "Najwyższy priorytet": st.column_config.NumberColumn("Najwyższy priorytet", width=130),
            }

        microzone_view_df = (
            microzone_view_df[microzone_view_columns]
            .sort_values(
                ["Dowieźć", "Zabrać", "Bilans"],
                ascending=[False, False, True],
            )
            .head(100)
            .copy()
        )

        if "Potencjał" in microzone_view_df.columns:
            microzone_view_df["Potencjał"] = microzone_view_df["Potencjał"].round(2)

        st.caption(
            f"Ranking mikrostref dla aktualnej daty: {format_number(len(microzone_view_df))} mikrostref w widoku."
        )

        st.dataframe(
            microzone_view_df,
            width="stretch",
            hide_index=True,
            column_config=microzone_column_config,
        )

    st.markdown("### Pary kompensacyjne")

    if local_pairs_df.empty:
        st.info("Brak lokalnych par dawca–biorca w aktualnym przebiegu danych.")
    else:
        st.dataframe(
            local_pairs_df,
            width="stretch",
            hide_index=True,
        )

with tab_map:
    st.subheader("Mapa działań")

    st.caption(
        "Mapa pokazuje stacje z aktualnego widoku filtrów. Punkty są posortowane według priorytetu planu dnia."
    )

    st.markdown(
        "<div style='display:flex; gap:0.75rem; flex-wrap:wrap; align-items:center; margin:0.4rem 0 1rem 0;'>"
        "<span style='font-weight:700; color:#374151;'>Legenda pilności:</span>"
        "<span style='display:inline-flex; align-items:center; gap:0.35rem; padding:0.25rem 0.55rem; border-radius:999px; background:#fee2e2; color:#991b1b; border:1px solid #fecaca; font-weight:700;'>"
        "<span style='width:0.7rem; height:0.7rem; border-radius:999px; background:red; display:inline-block;'></span>"
        "bardzo wysoki"
        "</span>"
        "<span style='display:inline-flex; align-items:center; gap:0.35rem; padding:0.25rem 0.55rem; border-radius:999px; background:#ffedd5; color:#9a3412; border:1px solid #fed7aa; font-weight:700;'>"
        "<span style='width:0.7rem; height:0.7rem; border-radius:999px; background:orange; display:inline-block;'></span>"
        "wysoki"
        "</span>"
        "<span style='display:inline-flex; align-items:center; gap:0.35rem; padding:0.25rem 0.55rem; border-radius:999px; background:#dbeafe; color:#1d4ed8; border:1px solid #bfdbfe; font-weight:700;'>"
        "<span style='width:0.7rem; height:0.7rem; border-radius:999px; background:blue; display:inline-block;'></span>"
        "średni"
        "</span>"
        "<span style='display:inline-flex; align-items:center; gap:0.35rem; padding:0.25rem 0.55rem; border-radius:999px; background:#f3f4f6; color:#374151; border:1px solid #d1d5db; font-weight:700;'>"
        "<span style='width:0.7rem; height:0.7rem; border-radius:999px; background:gray; display:inline-block;'></span>"
        "niski"
        "</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    if daily_actions_df.empty:
        st.info("Brak stacji do pokazania na mapie dla aktualnych filtrów.")
    else:
        try:
            station_action_map = build_station_action_map(daily_actions_df)
            map_html = station_action_map.get_root().render()
            components.html(map_html, height=650, scrolling=True)
        except Exception as exc:
            st.warning("Nie udało się zbudować mapy działań dla aktualnego widoku.")
            st.error(str(exc))

    st.markdown("### Połączenia relokacyjne")

    if relocation_line_df.empty:
        st.info("Dla wybranego dnia operacyjnego nie wyznaczono par stacja dawca → stacja biorca.")
    else:
        st.dataframe(
            relocation_line_df,
            width="stretch",
            hide_index=True,
        )


with tab_driver:
    st.subheader("Karta kierowcy")

    if daily_actions_view_df.empty:
        st.info("Brak kart kierowcy dla wybranej daty.")
    else:
        driver_cards_per_row = 1 if cards_per_row == 1 else 2
        driver_cards_df = daily_actions_view_df.copy().reset_index(drop=True)

        st.caption(
            f"Lista zadań dla kierowcy: {format_number(len(driver_cards_df))} zadań po aktualnych filtrach."
        )

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
                        "<div style='min-height:270px;'>"
                        f"<div style='font-size:1.45rem; font-weight:800; color:#111827; margin-bottom:0.85rem;'>Zadanie {task_rank}</div>"
                        f"<div style='font-size:1.05rem; color:#111827; margin-bottom:0.55rem;'><b>Jedź do:</b> {station_name}</div>"
                        f"<div style='font-size:1rem; color:#6b7280; margin-bottom:0.55rem;'><b>Mikrostrefa:</b> {microzone_id}</div>"
                        f"<div style='font-size:1.05rem; color:#111827; margin-bottom:0.55rem;'><b>Działanie:</b> {action_label}</div>"
                        f"<div style='font-size:1.2rem; font-weight:800; color:#111827; margin-bottom:0.65rem;'>{relocation_label}</div>"
                        f"<div style='font-size:1rem; color:#374151; margin-bottom:0.4rem;'><b>Godzina ryzyka:</b> {risk_hour}</div>"
                        f"<div style='font-size:1rem; color:#374151; margin-bottom:0.4rem;'><b>Pilność:</b> {priority_label}</div>"
                        f"<div style='font-size:1rem; color:#374151;'><b>Pewność:</b> {confidence_label} | <b>Potencjał:</b> {impact_value}</div>"
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
                                f"<div style='margin:0.65rem 0 0.85rem 0; padding:0.55rem 0.75rem; "
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

with tab_station:
    st.subheader("Szczegóły stacji")

    if daily_actions_df.empty:
        st.info("Brak stacji dla aktualnych filtrów.")
    else:
        station_options = (
            daily_actions_df[["daily_plan_rank", "station_name"]]
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

        selected_station_option = st.selectbox(
            "Wybierz stację",
            options=station_options,
            index=0,
        )

        selected_station_rank = int(selected_station_option.split(".", 1)[0])

        station_details_df = daily_actions_df.loc[
            daily_actions_df["daily_plan_rank"] == selected_station_rank
        ].copy()

        station_view_df = build_operational_view(station_details_df)

        if station_view_df.empty:
            st.info("Brak szczegółów dla wybranej stacji.")
        else:
            station_row = station_view_df.iloc[0]
            raw_station_row = station_details_df.iloc[0]

            station_rank = station_row.get("Lp.", "")
            station_name = station_row.get("Stacja", "")
            microzone_id = station_row.get("Mikrostrefa", "")
            priority_label = station_row.get("Pilność", "")
            problem_label = station_row.get("Co grozi", "")
            action_label = station_row.get("Zalecane działanie", "")
            relocation_label = station_row.get("Szacowana relokacja", "")
            risk_hour = station_row.get("Godzina ryzyka", "")
            confidence_label = station_row.get("Pewność", "")
            impact_value = station_row.get("Potencjał", "")

            station_summary_html = (
                "<div style='padding:1.2rem 1.35rem; border:1px solid #e5e7eb; "
                "border-radius:18px; background:#f9fafb; margin-bottom:1rem;'>"
                f"<div style='font-size:1.65rem; font-weight:850; color:#111827; margin-bottom:0.55rem;'>"
                f"{station_rank}. {station_name}"
                "</div>"
                f"<div style='font-size:1rem; color:#6b7280; margin-bottom:0.9rem;'>"
                f"Mikrostrefa: <b>{microzone_id}</b>"
                "</div>"
                f"<div style='font-size:1.15rem; color:#111827; margin-bottom:0.45rem;'>"
                f"Co grozi: <b>{problem_label}</b>"
                "</div>"
                f"<div style='font-size:1.15rem; color:#111827; margin-bottom:0.45rem;'>"
                f"Zalecane działanie: <b>{action_label}</b>"
                "</div>"
                f"<div style='font-size:1.45rem; font-weight:850; color:#111827; margin:0.65rem 0;'>"
                f"{relocation_label}"
                "</div>"
                f"<div style='font-size:1rem; color:#374151;'>"
                f"Godzina ryzyka: <b>{risk_hour}</b> | "
                f"Pilność: <b>{priority_label}</b> | "
                f"Pewność: <b>{confidence_label}</b>"
                "</div>"
                "</div>"
            )

            st.markdown(station_summary_html, unsafe_allow_html=True)

            metric_col_1, metric_col_2, metric_col_3, metric_col_4 = st.columns(4)

            with metric_col_1:
                st.metric("Potencjał", impact_value)

            with metric_col_2:
                st.metric(
                    "Wyjazdy",
                    int(raw_station_row.get("total_departures", 0)),
                )

            with metric_col_3:
                st.metric(
                    "Zwroty",
                    int(raw_station_row.get("total_returns", 0)),
                )

            with metric_col_4:
                st.metric(
                    "Bilans dnia",
                    int(raw_station_row.get("daily_net_flow", 0)),
                )

            st.markdown("### Decyzja operacyjna")

            decision_df = pd.DataFrame(
                [
                    {
                        "Element": "Stacja",
                        "Wartość": station_name,
                    },
                    {
                        "Element": "Mikrostrefa",
                        "Wartość": microzone_id,
                    },
                    {
                        "Element": "Problem",
                        "Wartość": problem_label,
                    },
                    {
                        "Element": "Działanie",
                        "Wartość": action_label,
                    },
                    {
                        "Element": "Relokacja",
                        "Wartość": relocation_label,
                    },
                    {
                        "Element": "Godzina ryzyka",
                        "Wartość": risk_hour,
                    },
                    {
                        "Element": "Pilność",
                        "Wartość": priority_label,
                    },
                    {
                        "Element": "Pewność",
                        "Wartość": confidence_label,
                    },
                ]
            )

            st.dataframe(
                decision_df,
                width="stretch",
                hide_index=True,
                column_config={
                    "Element": st.column_config.TextColumn("Element", width=180),
                    "Wartość": st.column_config.TextColumn("Wartość", width=420),
                },
            )

            with st.expander("Diagnostyka techniczna stacji"):
                technical_df = pd.DataFrame(
                    [
                        {
                            "Pole": "activity_date",
                            "Wartość": str(raw_station_row.get("activity_date", "")),
                        },
                        {
                            "Pole": "representative_station_id",
                            "Wartość": str(raw_station_row.get("representative_station_id", "")),
                        },
                        {
                            "Pole": "priority_level",
                            "Wartość": str(raw_station_row.get("priority_level", "")),
                        },
                        {
                            "Pole": "problem_type",
                            "Wartość": str(raw_station_row.get("problem_type", "")),
                        },
                        {
                            "Pole": "recommended_action",
                            "Wartość": str(raw_station_row.get("recommended_action", "")),
                        },
                        {
                            "Pole": "recommendation_confidence_final",
                            "Wartość": str(raw_station_row.get("recommendation_confidence_final", "")),
                        },
                        {
                            "Pole": "confidence_score",
                            "Wartość": str(raw_station_row.get("confidence_score", "")),
                        },
                        {
                            "Pole": "confidence_reason",
                            "Wartość": str(raw_station_row.get("confidence_reason", "")),
                        },
                        {
                            "Pole": "estimated_relocation_units",
                            "Wartość": str(raw_station_row.get("estimated_relocation_units", "")),
                        },
                        {
                            "Pole": "estimated_relocation_min",
                            "Wartość": str(raw_station_row.get("estimated_relocation_min", "")),
                        },
                        {
                            "Pole": "estimated_relocation_max",
                            "Wartość": str(raw_station_row.get("estimated_relocation_max", "")),
                        },
                        {
                            "Pole": "station_latitude",
                            "Wartość": str(raw_station_row.get("station_latitude", "")),
                        },
                        {
                            "Pole": "station_longitude",
                            "Wartość": str(raw_station_row.get("station_longitude", "")),
                        },
                    ]
                )

                st.dataframe(
                    technical_df,
                    width="stretch",
                    hide_index=True,
                    column_config={
                        "Pole": st.column_config.TextColumn("Pole", width=260),
                        "Wartość": st.column_config.TextColumn("Wartość", width=520),
                    },
                )                       


with tab_feedback:
    st.subheader("Feedback")

    feedback_entries = feedback_log.get("entries", [])

    st.metric("Liczba zapisanych wpisów feedbacku", len(feedback_entries))

    if not feedback_entries:
        st.info("Brak zapisanych wpisów feedbacku.")
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

            feedback_time = (
                feedback_df["_sort_time"]
                .dt.tz_convert("Europe/Warsaw")
                .dt.strftime("%Y-%m-%d %H:%M")
            )
            feedback_time = feedback_time.fillna("")
        else:
            feedback_time = pd.Series(
                [""] * len(feedback_df),
                index=feedback_df.index,
            )

        def get_feedback_series(column_name: str, default_value: str = "") -> pd.Series:
            if column_name in feedback_df.columns:
                return feedback_df[column_name].fillna(default_value).astype(str)

            return pd.Series(
                [default_value] * len(feedback_df),
                index=feedback_df.index,
            )

        def format_feedback_task(value: object) -> str:
            try:
                return f"Zadanie {int(value)}"
            except (TypeError, ValueError):
                return "Zadanie"

        compact_feedback_df = pd.DataFrame(
            {
                "Czas": feedback_time,
                "Status": get_feedback_series("status"),
                "Zadanie": get_feedback_series("task_rank").apply(format_feedback_task),
                "Stacja": get_feedback_series("station_name"),
                "Relokacja": get_feedback_series("relocation"),
                "Godzina": get_feedback_series("risk_hour"),
                "Pewność": get_feedback_series("confidence"),
            }
        )

        st.markdown("### Ostatnie zgłoszenia z terenu")

        st.dataframe(
            compact_feedback_df.head(50),
            width="stretch",
            hide_index=True,
            column_config={
                "Czas": st.column_config.TextColumn("Czas", width=135),
                "Status": st.column_config.TextColumn("Status", width=120),
                "Zadanie": st.column_config.TextColumn("Zadanie", width=110),
                "Stacja": st.column_config.TextColumn("Stacja", width=170),
                "Relokacja": st.column_config.TextColumn("Relokacja", width=190),
                "Godzina": st.column_config.TextColumn("Godzina", width=90),
                "Pewność": st.column_config.TextColumn("Pewność", width=100),
            },
        )

        with st.expander("Szczegółowy zapis operacyjny"):
            operational_feedback_df = feedback_df.drop(
                columns=["_sort_time"],
                errors="ignore",
            ).copy()

            if "created_at_utc" in operational_feedback_df.columns:
                operational_feedback_df["Czas kliknięcia statusu"] = (
                    pd.to_datetime(
                        operational_feedback_df["created_at_utc"],
                        errors="coerce",
                        utc=True,
                    )
                    .dt.tz_convert("Europe/Warsaw")
                    .dt.strftime("%Y-%m-%d %H:%M")
                )

            if "activity_date" in operational_feedback_df.columns:
                operational_feedback_df["Dzień operacyjny z danych"] = pd.to_datetime(
                    operational_feedback_df["activity_date"],
                    errors="coerce",
                ).dt.strftime("%Y-%m-%d")

            column_rename_map = {
                "task_rank": "Zadanie",
                "station_name": "Stacja",
                "microzone_id": "Mikrostrefa",
                "priority": "Pilność",
                "problem": "Problem",
                "recommended_action": "Działanie",
                "relocation": "Relokacja",
                "risk_hour": "Godzina ryzyka",
                "confidence": "Pewność",
                "status": "Status",
            }

            operational_feedback_df = operational_feedback_df.rename(
                columns=column_rename_map
            )

            display_column_order = [
                "Czas kliknięcia statusu",
                "Dzień operacyjny z danych",
                "Zadanie",
                "Status",
                "Stacja",
                "Mikrostrefa",
                "Pilność",
                "Problem",
                "Działanie",
                "Relokacja",
                "Godzina ryzyka",
                "Pewność",
            ]

            existing_display_columns = [
                column
                for column in display_column_order
                if column in operational_feedback_df.columns
            ]

            operational_feedback_df = operational_feedback_df[existing_display_columns]

            st.dataframe(
                operational_feedback_df,
                width="stretch",
                hide_index=True,
                column_config={
                    "Czas kliknięcia statusu": st.column_config.TextColumn("Czas kliknięcia statusu", width=175),
                    "Dzień operacyjny z danych": st.column_config.TextColumn("Dzień operacyjny z danych", width=175),
                    "Zadanie": st.column_config.NumberColumn("Zadanie", width=85),
                    "Status": st.column_config.TextColumn("Status", width=120),
                    "Stacja": st.column_config.TextColumn("Stacja", width=170),
                    "Mikrostrefa": st.column_config.TextColumn("Mikrostrefa", width=115),
                    "Pilność": st.column_config.TextColumn("Pilność", width=130),
                    "Problem": st.column_config.TextColumn("Problem", width=190),
                    "Działanie": st.column_config.TextColumn("Działanie", width=150),
                    "Relokacja": st.column_config.TextColumn("Relokacja", width=180),
                    "Godzina ryzyka": st.column_config.TextColumn("Godzina ryzyka", width=120),
                    "Pewność": st.column_config.TextColumn("Pewność", width=100),
                },
            )


with tab_technical:
    st.subheader("Model i dane")

    st.markdown(
        """
        <div style="padding:1.1rem 1.25rem; border:1px solid #bfdbfe; border-radius:18px; background:#eff6ff; margin-bottom:1.2rem;">
            <div style="font-size:1.15rem; font-weight:800; color:#1e3a8a; margin-bottom:0.45rem;">
                Charakter aplikacji
            </div>
            <div style="font-size:1rem; color:#1f2937; line-height:1.55;">
                To jest demonstracyjny panel operacyjny oparty na historycznych danych z lat <b>2017–2020</b>.
                Wybrana data oznacza <b>dzień operacyjny z danych</b>, a nie aktualny dzień live.
                Feedback i statusy są zapisywane w momencie kliknięcia w aplikacji, dlatego czas kliknięcia może być dzisiejszy,
                mimo że analizowany dzień pochodzi z danych historycznych.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    summary_cards = [
        {
            "label": "Typ aplikacji",
            "value": "Symulator operacyjny",
            "caption": "Panel demonstracyjny, nie system live",
        },
        {
            "label": "Zakres danych",
            "value": "2017–2020",
            "caption": "Historyczne dane operacyjne",
        },
        {
            "label": "Tryb pracy",
            "value": "Replay historyczny",
            "caption": "Plan dnia dla wybranego dnia z datasetu",
        },
    ]

    summary_columns = st.columns(3)

    for summary_column, summary_card in zip(summary_columns, summary_cards):
        with summary_column:
            st.markdown(
                (
                    "<div style='padding:0.95rem 1rem; border:1px solid #e5e7eb; "
                    "border-radius:16px; background:#f9fafb; height:8.4rem;'>"
                    f"<div style='font-size:0.9rem; color:#6b7280; margin-bottom:0.35rem;'>{summary_card['label']}</div>"
                    f"<div style='font-size:1.25rem; font-weight:800; color:#111827; margin-bottom:0.35rem;'>{summary_card['value']}</div>"
                    f"<div style='font-size:0.82rem; color:#6b7280; line-height:1.35;'>{summary_card['caption']}</div>"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )

    st.markdown("### Jak czytać tę aplikację")

    explanation_df = pd.DataFrame(
        [
            {
                "Element": "Dzień operacyjny",
                "Znaczenie": "Historyczna data z datasetu, dla której budowany jest plan działań.",
            },
            {
                "Element": "Czas kliknięcia statusu",
                "Znaczenie": "Aktualny czas zapisania feedbacku przez użytkownika aplikacji.",
            },
            {
                "Element": "Plan dnia",
                "Znaczenie": "Ranking stacji wymagających obsługi w wybranym dniu operacyjnym.",
            },
            {
                "Element": "Karta kierowcy",
                "Znaczenie": "Prosty widok zadań: gdzie jechać, co zrobić i ile rowerów relokować.",
            },
            {
                "Element": "Feedback",
                "Znaczenie": "Historia kliknięć statusów zadań zapisanych podczas pracy z aplikacją.",
            },
        ]
    )

    st.dataframe(
        explanation_df,
        width="stretch",
        hide_index=True,
        column_config={
            "Element": st.column_config.TextColumn("Element", width=190),
            "Znaczenie": st.column_config.TextColumn("Znaczenie", width=650),
        },
    )

    st.markdown("### Wersja produkcyjna")

    production_items = [
        {
            "title": "Dane wejściowe",
            "text": "Aktualne dane o stacjach, pojemności, przejazdach, pogodzie, kalendarzu i statusach technicznych.",
        },
        {
            "title": "Pipeline",
            "text": "Automatyczny przepływ: raw data → walidacja → feature engineering → scoring → artefakty → aplikacja.",
        },
        {
            "title": "Monitoring",
            "text": "Kontrola jakości danych, kompletności artefaktów i zgodności kontraktu aplikacji.",
        },
        {
            "title": "Użycie operacyjne",
            "text": "Dyspozytor widzi priorytety, a kierowca proste zadania do wykonania.",
        },
    ]

    production_columns = st.columns(2)

    for item_index, production_item in enumerate(production_items):
        with production_columns[item_index % 2]:
            st.markdown(
                (
                    "<div style='padding:0.95rem 1rem; border:1px solid #e5e7eb; "
                    "border-radius:16px; background:#f9fafb; min-height:7.8rem; margin-bottom:0.85rem;'>"
                    f"<div style='font-size:1rem; font-weight:800; color:#111827; margin-bottom:0.45rem;'>{production_item['title']}</div>"
                    f"<div style='font-size:0.9rem; color:#4b5563; line-height:1.45;'>{production_item['text']}</div>"
                    "</div>"
                ),
                unsafe_allow_html=True,
            )


    artifact_summary_df = pd.DataFrame(
        [
            {
                "Artefakt": path.name,
                "Status": "OK" if path.exists() else "Brak",
                "Rozmiar bajty": path.stat().st_size if path.exists() else 0,
            }
            for path in required_paths
        ]
    )

    st.caption(
        "Techniczny opis zasad działania aplikacji, kontraktu danych i konfiguracji panelu."
    )
    with st.expander("Kontrakt aplikacji"):
        st.json(app_contract)

    st.caption(
        "Opis ról poszczególnych zakładek oraz głównych użytkowników aplikacji."
    )
    with st.expander("Zakładki aplikacji"):
        st.dataframe(
            tab_contract_df,
            width="stretch",
            hide_index=True,
        )

    st.caption(
        "Lista wymaganych plików wejściowych wykorzystywanych przez panel operacyjny."
    )
    with st.expander("Artefakty wejściowe"):
        st.dataframe(
            artifact_summary_df,
            width="stretch",
            hide_index=True,
            column_config={
                "Artefakt": st.column_config.TextColumn("Artefakt", width=420),
                "Status": st.column_config.TextColumn("Status", width=100),
                "Rozmiar bajty": st.column_config.NumberColumn("Rozmiar bajty", width=140),
            },
        )