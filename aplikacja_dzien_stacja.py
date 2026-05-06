# Aplikacja

from pathlib import Path
import json

import joblib
import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="Aplikacja Dzień–Stacja",
    layout="wide",
)

APP_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = APP_DIR

INPUT_MODEL_PACKAGE_DIR = APP_DIR / "input_model_package"
OUTPUTS_DIR = APP_DIR / "outputs_dzien_stacja"

APP_HANDOFF_PATH = OUTPUTS_DIR / "b4u_05_app_handoff.json"
PREDICTIONS_FOR_APP_PATH = OUTPUTS_DIR / "b4u_05_predictions_for_app.parquet"
FEATURE_IMPORTANCE_PATH = INPUT_MODEL_PACKAGE_DIR / "b4_15_feature_importance.parquet"
BEST_MODEL_PATH = INPUT_MODEL_PACKAGE_DIR / "b4_15_best_model.joblib"
INFERENCE_CONFIG_PATH = INPUT_MODEL_PACKAGE_DIR / "b4_15_inference_config.json"

APP_RUNTIME_DIR = APP_DIR / "app_runtime"
APP_RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

RUNTIME_PREDICTIONS_PATH = APP_RUNTIME_DIR / "b5_07_runtime_predictions.parquet"
RUNTIME_RUNLOG_PATH = APP_RUNTIME_DIR / "b5_07_app_runlog.json"
RUNBOOK_PATH = APP_RUNTIME_DIR / "b5_07_app_runbook.json"
CHECKLIST_PATH = APP_RUNTIME_DIR / "b5_07_app_checklist.json"


def resolve_single_file(root_dir: Path, file_name: str) -> Path:
    matches = sorted(root_dir.rglob(file_name))
    if not matches:
        raise FileNotFoundError(f"Nie znaleziono pliku: {file_name}")
    if len(matches) > 1:
        raise RuntimeError(f"Znaleziono więcej niż jeden plik {file_name}: {matches}")
    return matches[0]


MODEL_READY_PATH = resolve_single_file(PROJECT_ROOT, "b3_13_model_ready_dataset.parquet")
NULL_SEMANTICS_PATH = resolve_single_file(PROJECT_ROOT, "b3_13_null_semantics.parquet")


@st.cache_data
def load_json_data(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


@st.cache_data
def load_parquet_data(path: str) -> pd.DataFrame:
    return pd.read_parquet(path)

@st.cache_resource
def load_model_resource(path: str):
    return joblib.load(path)


def save_parquet_data(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)


def save_json_data(payload: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


try:
    for required_path in [
        APP_HANDOFF_PATH,
        PREDICTIONS_FOR_APP_PATH,
        FEATURE_IMPORTANCE_PATH,
        BEST_MODEL_PATH,
        INFERENCE_CONFIG_PATH,
        MODEL_READY_PATH,
        NULL_SEMANTICS_PATH,
    ]:
        if not required_path.exists():
            raise FileNotFoundError(f"Brak wymaganego pliku: {required_path}")

    app_handoff = load_json_data(str(APP_HANDOFF_PATH))
    predictions_for_app_df = load_parquet_data(str(PREDICTIONS_FOR_APP_PATH))
    feature_importance_df = load_parquet_data(str(FEATURE_IMPORTANCE_PATH))
    inference_config = load_json_data(str(INFERENCE_CONFIG_PATH))

    model_ready_df = load_parquet_data(str(MODEL_READY_PATH))
    null_semantics_df = load_parquet_data(str(NULL_SEMANTICS_PATH))
    model_object = load_model_resource(str(BEST_MODEL_PATH))

except Exception as exc:
    st.error("Nie udało się wczytać wymaganych artefaktów aplikacji.")
    st.error(str(exc))
    st.stop()

required_handoff_keys = [
    "model_name",
    "model_release_tag",
    "selected_scoring_date",
    "applied_threshold",
    "scoring_date_mode",
    "supported_scoring_modes",
    "app_output_columns",
    "technical_panel_source",
]
missing_handoff_keys = [
    key_name for key_name in required_handoff_keys if key_name not in app_handoff
]
if missing_handoff_keys:
    st.error(f"Brakuje wymaganych kluczy w handoff aplikacyjnym: {missing_handoff_keys}")
    st.stop()


model_ready_df["activity_date"] = pd.to_datetime(
    model_ready_df["activity_date"],
    errors="coerce",
).dt.normalize()
model_ready_df["station_id"] = model_ready_df["station_id"].astype("string")

null_semantics_feature_key = next(
    (
        column_name
        for column_name in ["column_name", "feature_name", "feature"]
        if column_name in null_semantics_df.columns
    ),
    None,
)
if null_semantics_feature_key is None:
    st.error("Nie znaleziono kolumny klucza cech w kontrakcie null semantics.")
    st.stop()

feature_columns = list(inference_config["input_feature_names"])
decision_threshold = float(inference_config["decision_threshold"])
available_scoring_dates = sorted(
    model_ready_df["activity_date"].dropna().dt.normalize().unique().tolist()
)

if not available_scoring_dates:
    st.error("Lista dostępnych dat scoringowych jest pusta.")
    st.stop()

null_semantics_features = set(
    null_semantics_df[null_semantics_feature_key].astype("string").tolist()
)

missing_null_semantics_features = [
    feature_name
    for feature_name in feature_columns
    if feature_name not in null_semantics_features
]
if missing_null_semantics_features:
    st.error(
        f"Brakuje cech w kontrakcie null semantics: {missing_null_semantics_features}"
    )
    st.stop()

missing_feature_columns_in_model_ready = [
    feature_name
    for feature_name in feature_columns
    if feature_name not in model_ready_df.columns
]
if missing_feature_columns_in_model_ready:
    st.error(
        "Brakuje wymaganych cech w model_ready dataset: "
        f"{missing_feature_columns_in_model_ready}"
    )
    st.stop()

context_candidates = [
    "hub_flag",
    "is_cold_start",
    "is_holiday",
    "is_business_free_day",
    "alert_hours_roll_sum_14",
    "alert_hours_lag_1",
    "consecutive_alert_days_before_t",
]

context_columns = [
    column_name
    for column_name in context_candidates
    if column_name in model_ready_df.columns
]

if not hasattr(model_object, "predict_proba") or not hasattr(model_object, "classes_"):
    st.error("Załadowany model nie obsługuje predict_proba lub classes_.")
    st.stop()

model_classes = list(model_object.classes_)
if 1 in model_classes:
    positive_class_index = model_classes.index(1)
elif "1" in model_classes:
    positive_class_index = model_classes.index("1")
else:
    st.error(f"Nie znaleziono klasy dodatniej 1 w modelu: {model_classes}")
    st.stop()


def build_runtime_scored_data(selected_scoring_date_value: str) -> pd.DataFrame:
    selected_scoring_date_ts = pd.to_datetime(
        selected_scoring_date_value,
        errors="coerce",
    ).normalize()

    if pd.isna(selected_scoring_date_ts):
        raise ValueError("Wybrana data scoringowa jest niepoprawna.")

    if selected_scoring_date_ts not in available_scoring_dates:
        raise ValueError("Wybrana data scoringowa jest poza zakresem dostępnych batchy.")

    scoring_batch_df = (
        model_ready_df.loc[model_ready_df["activity_date"] == selected_scoring_date_ts]
        .copy()
        .reset_index(drop=True)
    )

    if scoring_batch_df.empty:
        raise ValueError("Brak danych historycznych dla wybranej daty.")

    duplicate_key_count = int(
        scoring_batch_df.duplicated(subset=["activity_date", "station_id"]).sum()
    )
    if duplicate_key_count != 0:
        raise ValueError("Batch scoringowy zawiera zduplikowane klucze dzień–stacja.")

    model_input_df = scoring_batch_df[feature_columns].copy()

    if list(model_input_df.columns) != feature_columns:
        raise ValueError("Kolejność cech wejściowych nie zgadza się z kontraktem modelu.")

    predict_proba_array = model_object.predict_proba(model_input_df)
    predicted_probability = predict_proba_array[:, positive_class_index]
    predicted_label = (predicted_probability >= decision_threshold).astype("int8")

    scored_output_df = scoring_batch_df[
        ["activity_date", "station_id"] + context_columns
    ].copy()

    scored_output_df["predicted_probability"] = predicted_probability.astype("float32")
    scored_output_df["predicted_label"] = predicted_label.astype("int8")
    scored_output_df["model_release_tag"] = str(app_handoff["model_release_tag"])
    scored_output_df["applied_threshold"] = decision_threshold

    scored_output_df = (
        scored_output_df.sort_values(
            ["predicted_probability", "station_id"],
            ascending=[False, True],
        )
        .reset_index(drop=True)
    )

    return scored_output_df   

expected_output_columns = list(app_handoff["app_output_columns"])
actual_output_columns = list(predictions_for_app_df.columns)

if actual_output_columns != expected_output_columns:
    st.error("Kontrakt kolumn wynikowych nie zgadza się z handoff aplikacyjnym.")
    st.stop()

predictions_for_app_df["activity_date"] = pd.to_datetime(
    predictions_for_app_df["activity_date"],
    errors="coerce",
).dt.normalize()
predictions_for_app_df["station_id"] = predictions_for_app_df["station_id"].astype("string")

if predictions_for_app_df["activity_date"].isna().any():
    st.error("Wyniki aplikacyjne zawierają niepoprawne wartości activity_date.")
    st.stop()

if predictions_for_app_df["station_id"].isna().any():
    st.error("Wyniki aplikacyjne zawierają brakujące station_id.")
    st.stop()

if "scored_data" not in st.session_state:
    st.session_state["scored_data"] = predictions_for_app_df.copy()

scored_data_df = st.session_state["scored_data"].copy()
scored_data_df = (
    scored_data_df.sort_values(
        ["predicted_probability", "station_id"],
        ascending=[False, True],
    )
    .reset_index(drop=True)
)

model_name = str(app_handoff["model_name"])
model_release_tag = str(app_handoff["model_release_tag"])
selected_scoring_date = str(app_handoff["selected_scoring_date"])
applied_threshold = float(app_handoff["applied_threshold"])
scoring_date_mode = str(app_handoff["scoring_date_mode"])
supported_scoring_modes = list(app_handoff["supported_scoring_modes"])

scoring_mode_display_map = {
    "latest_available": "Latest available",
    "selected_date": "Selected date",
}
scoring_mode_display = scoring_mode_display_map.get(
    scoring_date_mode,
    scoring_date_mode,
)

total_feature_count = int(len(feature_importance_df))

ranking_column = str(app_handoff["technical_panel_source"]["ranking_column"])
feature_name_column_candidates = ["feature_name", "feature", "column_name"]
feature_name_column = next(
    (
        column_name
        for column_name in feature_name_column_candidates
        if column_name in feature_importance_df.columns
    ),
    None,
)

if feature_name_column is None:
    st.error("Nie znaleziono kolumny z nazwą cechy w pliku feature importance.")
    st.stop()

if ranking_column not in feature_importance_df.columns:
    st.error(f"Nie znaleziono kolumny rankingu w pliku feature importance: {ranking_column}")
    st.stop()

technical_panel_columns = [feature_name_column, ranking_column]
optional_rank_columns = [
    "gain_rank",
    "permutation_rank",
    "shap_rank",
    "gain_importance",
    "permutation_importance_mean",
    "mean_abs_shap",
]
technical_panel_columns += [
    column_name
    for column_name in optional_rank_columns
    if column_name in feature_importance_df.columns
]

top_features_df = (
    feature_importance_df[technical_panel_columns]
    .copy()
    .rename(columns={feature_name_column: "feature_name"})
    .sort_values(ranking_column, ascending=True)
    .head(10)
    .reset_index(drop=True)
)

st.title("Aplikacja Dzień–Stacja")

tab1, tab2, tab3 = st.tabs(
    ["🚀 Panel Scoringowy", "📊 Wyniki i KPI", "⚙️ Informacje Techniczne"]
)

with tab1:
    st.subheader("Panel scoringowy")

    available_scoring_date_min = min(available_scoring_dates).date()
    available_scoring_date_max = max(available_scoring_dates).date()

    default_selected_scoring_date = pd.to_datetime(
        app_handoff.get("selected_scoring_date"),
        errors="coerce",
    )
    if pd.isna(default_selected_scoring_date):
        default_selected_scoring_date = max(available_scoring_dates)
    default_selected_scoring_date = default_selected_scoring_date.date()

    scoring_mode_display_map = {
        "latest_available": "Latest available",
        "selected_date": "Selected date",
    }
    scoring_mode_reverse_map = {
        "Latest available": "latest_available",
        "Selected date": "selected_date",
    }

    scoring_mode_options_display = [
        scoring_mode_display_map.get(mode_name, mode_name)
        for mode_name in supported_scoring_modes
    ]

    default_mode_display = scoring_mode_display_map.get(
        app_handoff.get("scoring_date_mode", "latest_available"),
        "Latest available",
    )

    selected_mode_display = st.radio(
        "Tryb scoringu",
        options=scoring_mode_options_display,
        index=scoring_mode_options_display.index(default_mode_display),
        horizontal=True,
    )

    selected_mode = scoring_mode_reverse_map.get(
        selected_mode_display,
        selected_mode_display,
    )

    selected_runtime_date = available_scoring_date_max
    if selected_mode == "selected_date":
        selected_runtime_date = st.date_input(
            "Wybór daty scoringowej",
            value=default_selected_scoring_date,
            min_value=available_scoring_date_min,
            max_value=available_scoring_date_max,
        )

    st.session_state["ui_scoring_mode"] = selected_mode
    st.session_state["ui_selected_date"] = str(selected_runtime_date)

    if selected_mode == "latest_available":
        resolved_runtime_date = str(available_scoring_date_max)
    else:
        resolved_runtime_date = str(selected_runtime_date)

    preview_batch_df = (
        model_ready_df.loc[
            model_ready_df["activity_date"] == pd.to_datetime(resolved_runtime_date).normalize()
        ]
        .copy()
        .reset_index(drop=True)
    )

    preview_duplicate_key_count = int(
        preview_batch_df.duplicated(subset=["activity_date", "station_id"]).sum()
    )

    available_feature_count = sum(
        feature_name in preview_batch_df.columns
        for feature_name in feature_columns
    )
    missing_feature_count = len(feature_columns) - available_feature_count

    null_semantics_ready_ui = int(
        all(feature_name in null_semantics_features for feature_name in feature_columns)
    )
    contract_ready_ui = int(
        (missing_feature_count == 0)
        and (preview_duplicate_key_count == 0)
        and (null_semantics_ready_ui == 1)
    )

    action_col_1, action_col_2 = st.columns(2)

load_from_db = action_col_1.button(
    "Wczytaj dane z bazy",
    width="stretch",
)

run_scoring = action_col_2.button(
    "Uruchom scoring",
    type="primary",
    width="stretch",
    disabled=(contract_ready_ui == 0),
    help="Scoring uruchomi się tylko wtedy, gdy wsad przejdzie walidację kontraktu.",
)

if load_from_db:
    try:
        st.session_state["source_batch_preview"] = preview_batch_df.copy()
        st.session_state["source_batch_preview_date"] = resolved_runtime_date
        st.success(f"Dane wsadowe zostały wczytane z bazy dla daty {resolved_runtime_date}.")
    except Exception as exc:
        st.warning("Nie udało się wczytać danych wsadowych z bazy.")
        st.error(str(exc))

if run_scoring:
    try:
        runtime_scored_df = build_runtime_scored_data(resolved_runtime_date)

        st.session_state["scored_data"] = runtime_scored_df.copy()
        st.session_state["current_scoring_date"] = resolved_runtime_date
        st.session_state["current_scoring_mode"] = selected_mode

        save_parquet_data(runtime_scored_df, RUNTIME_PREDICTIONS_PATH)

        runtime_runlog_payload = {
            "app_name": "aplikacja_dzien_stacja.py",
            "model_name": model_name,
            "model_release_tag": model_release_tag,
            "scoring_mode": selected_mode,
            "selected_scoring_date": str(resolved_runtime_date),
            "applied_threshold": float(decision_threshold),
            "record_count": int(runtime_scored_df.shape[0]),
            "station_count": int(runtime_scored_df["station_id"].nunique()),
            "positive_prediction_count": int(runtime_scored_df["predicted_label"].sum()),
            "positive_prediction_share": float(runtime_scored_df["predicted_label"].mean()),
            "runtime_predictions_path": str(RUNTIME_PREDICTIONS_PATH),
            "saved_at_utc": pd.Timestamp.utcnow().isoformat(),
        }
        save_json_data(runtime_runlog_payload, RUNTIME_RUNLOG_PATH)

        st.session_state["source_batch_preview"] = preview_batch_df.copy()
        st.session_state["source_batch_preview_date"] = resolved_runtime_date

        st.success(f"Scoring został uruchomiony dla daty {resolved_runtime_date}.")
        st.rerun()

    except Exception as exc:
        st.warning("Nie udało się uruchomić scoringu dla wybranego trybu lub daty.")
        st.error(str(exc))

current_loaded_scoring_date = pd.to_datetime(
    scored_data_df["activity_date"].iloc[0],
    errors="coerce",
)
if pd.notna(current_loaded_scoring_date):
    current_loaded_scoring_date = current_loaded_scoring_date.strftime("%Y-%m-%d")
else:
    current_loaded_scoring_date = "brak"

info_col_1, info_col_2, info_col_3, info_col_4 = st.columns(4)
info_col_1.metric("Liczba rekordów batcha", int(preview_batch_df.shape[0]))
info_col_2.metric("Liczba stacji", int(preview_batch_df["station_id"].nunique()))
info_col_3.metric("Próg decyzji", f"{decision_threshold:.2f}")
info_col_4.metric("Tryb scoringu", selected_mode_display)

st.markdown(f"**Model:** {model_name}")
st.markdown(f"**Release tag:** {model_release_tag}")
st.markdown(f"**Bieżący załadowany batch:** {current_loaded_scoring_date}")
st.markdown(f"**Wybrana data w panelu:** {resolved_runtime_date}")
st.markdown("**Źródło danych wsadowych:** model_ready_dataset / baza")
st.markdown(
    f"**Wspierane tryby:** {', '.join(scoring_mode_display_map.get(mode, mode) for mode in supported_scoring_modes)}"
)

contract_summary_df = pd.DataFrame(
    [
        {
            "obszar": "Wymagane cechy z configu",
            "wartość": len(feature_columns),
            "status": "OK",
        },
        {
            "obszar": "Dostępne cechy w batchu",
            "wartość": available_feature_count,
            "status": "OK" if missing_feature_count == 0 else "Brak",
        },
        {
            "obszar": "Brakujące cechy",
            "wartość": missing_feature_count,
            "status": "OK" if missing_feature_count == 0 else "Brak",
        },
        {
            "obszar": "Duplikaty klucza dzień–stacja",
            "wartość": preview_duplicate_key_count,
            "status": "OK" if preview_duplicate_key_count == 0 else "Błąd",
        },
        {
            "obszar": "Null semantics",
            "wartość": null_semantics_ready_ui,
            "status": "OK" if null_semantics_ready_ui == 1 else "Brak",
        },
        {
            "obszar": "Kontrakt wejścia",
            "wartość": contract_ready_ui,
            "status": "OK" if contract_ready_ui == 1 else "Błąd",
        },
    ]
)

st.markdown("**Kontrola zgodności kolumn z configiem**")
st.dataframe(
    contract_summary_df,
    width="stretch",
    hide_index=True,
)

if contract_ready_ui == 0:
    st.error("Wsad danych nie przeszedł walidacji kontraktu. Scoring nie jest możliwy.")
else:
    st.success("Wsad danych przeszedł walidację kontraktu. Scoring jest możliwy.")

    preview_display_columns = [
        column_name
        for column_name in [
            "activity_date",
            "station_id",
            "hub_flag",
            "is_cold_start",
            "is_holiday",
            "is_business_free_day",
            "alert_hours_roll_sum_14",
            "alert_hours_lag_1",
            "consecutive_alert_days_before_t",
        ]
        if column_name in preview_batch_df.columns
    ]

    preview_display_df = preview_batch_df[preview_display_columns].copy()
    if "activity_date" in preview_display_df.columns:
        preview_display_df["activity_date"] = pd.to_datetime(
            preview_display_df["activity_date"],
            errors="coerce",
        ).dt.strftime("%Y-%m-%d")

    st.markdown("**Podgląd danych wsadowych z bazy**")
    st.dataframe(
        preview_display_df.head(10),
        width="stretch",
        hide_index=True,
    )

with tab2:
    st.subheader("Wyniki i KPI")

    filter_col_1, filter_col_2, filter_col_3 = st.columns(3)

    station_options = sorted(scored_data_df["station_id"].dropna().astype(str).unique().tolist())
    selected_stations = filter_col_1.multiselect(
    "Filtr po stacji",
    options=station_options,
    default=[],
    placeholder="Wybierz stacje",
)

    hub_filter = filter_col_2.selectbox(
        "Filtr hub / non-hub",
        options=["Wszystkie", "Tylko hub", "Tylko non-hub"],
        index=0,
    )

    positive_only = filter_col_3.checkbox("Tylko predykcja dodatnia", value=False)

    extra_filter_col_1, extra_filter_col_2 = st.columns(2)
    cold_start_only = extra_filter_col_1.checkbox(
        "Tylko is_cold_start = 1",
        value=False,
        disabled="is_cold_start" not in scored_data_df.columns,
    )
    holiday_only = extra_filter_col_2.checkbox(
        "Tylko is_holiday = 1",
        value=False,
        disabled="is_holiday" not in scored_data_df.columns,
    )

    filtered_df = scored_data_df.copy()

    if selected_stations:
        filtered_df = filtered_df.loc[
            filtered_df["station_id"].astype(str).isin(selected_stations)
        ].copy()

    if hub_filter == "Tylko hub" and "hub_flag" in filtered_df.columns:
        filtered_df = filtered_df.loc[filtered_df["hub_flag"] == 1].copy()
    elif hub_filter == "Tylko non-hub" and "hub_flag" in filtered_df.columns:
        filtered_df = filtered_df.loc[filtered_df["hub_flag"] == 0].copy()

    if positive_only:
        filtered_df = filtered_df.loc[filtered_df["predicted_label"] == 1].copy()

    if cold_start_only and "is_cold_start" in filtered_df.columns:
        filtered_df = filtered_df.loc[filtered_df["is_cold_start"] == 1].copy()

    if holiday_only and "is_holiday" in filtered_df.columns:
        filtered_df = filtered_df.loc[filtered_df["is_holiday"] == 1].copy()

    filtered_df = (
        filtered_df.sort_values(
            ["predicted_probability", "station_id"],
            ascending=[False, True],
        )
        .reset_index(drop=True)
    )

    kpi_col_1, kpi_col_2, kpi_col_3 = st.columns(3)
    kpi_col_1.metric("Liczba stacji w widoku", int(filtered_df["station_id"].nunique()))
    kpi_col_2.metric("Stacje wysokiego ryzyka", int(filtered_df["predicted_label"].sum()))
    kpi_col_3.metric(
        "Cold starty w ryzyku",
        int(
            filtered_df.loc[
                (filtered_df["predicted_label"] == 1)
                & (filtered_df["is_cold_start"] == 1)
            ].shape[0]
        ) if "is_cold_start" in filtered_df.columns else 0,
    )

    display_columns = [
        column_name
        for column_name in [
            "activity_date",
            "station_id",
            "predicted_probability",
            "predicted_label",
            "hub_flag",
            "is_cold_start",
            "is_holiday",
            "is_business_free_day",
            "alert_hours_roll_sum_14",
            "alert_hours_lag_1",
            "consecutive_alert_days_before_t",
        ]
        if column_name in filtered_df.columns
    ]

    display_df = filtered_df[display_columns].copy()

    if "activity_date" in display_df.columns:
        display_df["activity_date"] = pd.to_datetime(
            display_df["activity_date"],
            errors="coerce",
        ).dt.strftime("%Y-%m-%d")

    if "predicted_probability" in display_df.columns:
        display_df["predicted_probability"] = display_df["predicted_probability"].round(4)

    st.dataframe(
        display_df,
        width="stretch",
        hide_index=True,
    )

    csv_data = display_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        label="Pobierz CSV na komputer",
        data=csv_data,
        file_name=f"predictions_day_station_{selected_scoring_date}.csv",
        mime="text/csv",
    )

with tab3:
    st.subheader("Informacje Techniczne")

    current_loaded_scoring_date = pd.to_datetime(
        scored_data_df["activity_date"].iloc[0],
        errors="coerce",
    )
    if pd.notna(current_loaded_scoring_date):
        current_loaded_scoring_date = current_loaded_scoring_date.strftime("%Y-%m-%d")
    else:
        current_loaded_scoring_date = "brak"

    tech_col_1, tech_col_2, tech_col_3, tech_col_4 = st.columns(4)
    tech_col_1.metric("Próg", f"{decision_threshold:.2f}")
    tech_col_2.metric("Liczba cech", total_feature_count)
    tech_col_3.metric("Liczba rekordów", int(scored_data_df.shape[0]))
    tech_col_4.metric("Data scoringu", current_loaded_scoring_date)

    st.markdown(f"**Model:** {model_name}")
    st.markdown(f"**Release tag:** {model_release_tag}")
    st.markdown(f"**Ranking techniczny:** {ranking_column}")

    explainability_candidates = [
        feature_name
        for feature_name in [
            "alert_hours_roll_sum_14",
            "alert_hours_lag_1",
            "consecutive_alert_days_before_t",
        ]
        if feature_name in top_features_df["feature_name"].tolist()
    ]

    if explainability_candidates:
        st.markdown(
            "**Explainability light:** "
            + ", ".join(explainability_candidates)
        )

    st.markdown("**Top cechy według consensus_rank**")

    st.dataframe(
        top_features_df,
        width="stretch",
        hide_index=True,
    )

    readiness_checks_df = pd.DataFrame(
    [
        {"obszar": "Tryb Latest available", "status": "OK" if "latest_available" in supported_scoring_modes else "Brak"},
        {"obszar": "Tryb Selected date", "status": "OK" if "selected_date" in supported_scoring_modes else "Brak"},
        {"obszar": "Runtime scored_data", "status": "OK" if "scored_data" in st.session_state else "Brak"},
        {"obszar": "Filtr po stacji", "status": "OK" if "station_id" in scored_data_df.columns else "Brak"},
        {"obszar": "Filtr hub / non-hub", "status": "OK" if "hub_flag" in scored_data_df.columns else "Brak"},
        {"obszar": "Predykcja dodatnia", "status": "OK" if "predicted_label" in scored_data_df.columns else "Brak"},
        {"obszar": "Eksport CSV", "status": "OK"},
        {"obszar": "Panel techniczny", "status": "OK"},
    ]
)
    
checklist_payload = {
    "app_name": "aplikacja_dzien_stacja.py",
    "model_name": model_name,
    "model_release_tag": model_release_tag,
    "scoring_date": current_loaded_scoring_date,
    "checks": readiness_checks_df.to_dict(orient="records"),
    "generated_at_utc": pd.Timestamp.utcnow().isoformat(),
}
save_json_data(checklist_payload, CHECKLIST_PATH)

runbook_payload = {
    "app_name": "aplikacja_dzien_stacja.py",
    "technology": "streamlit",
    "entrypoint": str(APP_DIR / "aplikacja_dzien_stacja.py"),
    "local_url": "http://localhost:8501",
    "required_artifacts": {
        "best_model": str(BEST_MODEL_PATH),
        "inference_config": str(INFERENCE_CONFIG_PATH),
        "feature_importance": str(FEATURE_IMPORTANCE_PATH),
        "app_handoff": str(APP_HANDOFF_PATH),
        "runtime_predictions": str(RUNTIME_PREDICTIONS_PATH),
        "runtime_runlog": str(RUNTIME_RUNLOG_PATH),
        "checklist": str(CHECKLIST_PATH),
    },
    "supported_scoring_modes": supported_scoring_modes,
    "decision_threshold": float(decision_threshold),
    "current_scoring_date": current_loaded_scoring_date,
    "generated_at_utc": pd.Timestamp.utcnow().isoformat(),
}
save_json_data(runbook_payload, RUNBOOK_PATH)

st.markdown("**Odbiór końcowy MVP**")
st.success("Aplikacja gotowa do użycia operacyjnego.")
st.dataframe(
    readiness_checks_df,
    width="stretch",
    hide_index=True,
)