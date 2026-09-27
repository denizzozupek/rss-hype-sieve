"""RSS-Hype-Sieve: AI-Driven Feed De-Hype Engine - Streamlit User Interface.

Standalone Streamlit application providing interactive controls, pipeline execution,
telemetry metrics, 7-day rolling feed inspection, and historical database inspection for RSS feeds.
"""

from __future__ import annotations

import asyncio
import concurrent.futures
from contextlib import closing
import logging
import os
from pathlib import Path
import sqlite3
import sys
from typing import Any, Coroutine, Final, TypeVar

from dotenv import load_dotenv
import pandas as pd
import streamlit as st

# Configure logger
logger = logging.getLogger("rss_hype_sieve.gui")
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(handler)
logger.setLevel(logging.INFO)

# Load existing .env file if available
load_dotenv()

# Fallback defaults in case core.config cannot be loaded prior to API key configuration
FALLBACK_DEFAULT_SOURCES: Final[list[str]] = [
    "https://magazine.sebastianraschka.com/feed",
    "https://importai.substack.com/feed",
    "https://www.therundown.ai/feed",
    "https://openai.com/news/rss.xml",
    "https://lilianweng.github.io/index.xml",
    "https://huggingface.co/blog/feed.xml",
    "https://eugeneyan.com/rss/",
]
FALLBACK_DEFAULT_DB_PATH: Final[Path] = Path("db/hype_evaluations.db")

T = TypeVar("T")


def run_async(coro: Coroutine[Any, Any, T]) -> T:
    """Execute an asynchronous coroutine safely across different Streamlit execution environments."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    else:
        return asyncio.run(coro)


def get_default_sources() -> list[str]:
    """Retrieve default sources defensively from core.config or fallback list."""
    try:
        from core.config import DEFAULT_SOURCES

        return list(DEFAULT_SOURCES)
    except Exception:
        return list(FALLBACK_DEFAULT_SOURCES)


def get_db_path() -> Path:
    """Retrieve database path defensively from core.config or fallback path."""
    try:
        from core.config import DEFAULT_DB_PATH

        return Path(DEFAULT_DB_PATH)
    except Exception:
        return FALLBACK_DEFAULT_DB_PATH


def load_historical_articles(db_path: Path | str) -> pd.DataFrame:
    """Query persisted evaluation records from the SQLite database."""
    target_path = Path(db_path)
    if not target_path.exists():
        return pd.DataFrame()

    try:
        with closing(sqlite3.connect(target_path, timeout=10.0)) as conn:
            query = """
                SELECT 
                    id, 
                    title, 
                    source, 
                    is_passed, 
                    hype_score, 
                    violated_rule, 
                    hype_reason, 
                    summary, 
                    url, 
                    created_at
                FROM hype_evaluations
                ORDER BY id DESC
            """
            df = pd.read_sql_query(query, conn)
            return df
    except Exception as exc:
        logger.error("Failed to query historical articles: %s", exc)
        return pd.DataFrame()


async def execute_pipeline_coro(
    sources: list[str], db_path: Path | str
) -> dict[str, Any]:
    """Execute the core LangGraph pipeline using imported repository modules."""
    from services.db import db_init
    from graph.pipeline import create_pipeline_graph
    from core.state import PipelineGraphState

    # Ensure database schema is ready
    await asyncio.to_thread(db_init, db_path)

    # Initialize graph
    pipeline_graph = create_pipeline_graph()
    initial_state: PipelineGraphState = {
        "sources": sources,
    }

    # Execute workflow
    final_state = await pipeline_graph.ainvoke(initial_state)
    return dict(final_state)


def inject_custom_css() -> None:
    """Inject clean, modern technical dashboard styles compatible with light/dark themes."""
    st.markdown(
        """
        <style>
        /* Global Typography & Spacing */
        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1200px;
        }

        /* Metric Cards */
        div[data-testid="stMetric"] {
            background-color: rgba(128, 128, 128, 0.04);
            border: 1px solid rgba(128, 128, 128, 0.15);
            border-radius: 8px;
            padding: 14px 18px;
            transition: border-color 0.2s ease;
        }
        div[data-testid="stMetric"]:hover {
            border-color: rgba(128, 128, 128, 0.35);
        }
        div[data-testid="stMetricLabel"] {
            font-size: 0.8rem !important;
            font-weight: 600 !important;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: rgba(128, 128, 128, 0.9);
        }
        div[data-testid="stMetricValue"] {
            font-size: 1.55rem !important;
            font-weight: 600 !important;
        }

        /* Bordered Container (Article Cards) */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 8px !important;
            border-color: rgba(128, 128, 128, 0.18) !important;
            background-color: rgba(128, 128, 128, 0.02) !important;
            margin-bottom: 1rem !important;
            padding: 16px !important;
            transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }
        div[data-testid="stVerticalBlockBorderWrapper"]:hover {
            border-color: rgba(128, 128, 128, 0.38) !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
        }

        /* Article Link & Title */
        .stMarkdown h4 {
            margin-top: 0.15rem !important;
            margin-bottom: 0.45rem !important;
        }
        .stMarkdown h4 a,
        div[data-testid="stVerticalBlockBorderWrapper"] h4 a,
        div[data-testid="stVerticalBlockBorderWrapper"] a {
            color: #E2E8F0 !important;
            text-decoration: none !important;
            font-weight: 600 !important;
            transition: color 0.15s ease, text-decoration 0.15s ease;
        }
        .stMarkdown h4 a:hover,
        div[data-testid="stVerticalBlockBorderWrapper"] h4 a:hover,
        div[data-testid="stVerticalBlockBorderWrapper"] a:hover {
            color: #63B3ED !important;
            text-decoration: underline !important;
        }

        /* Sidebar Multiselect Tags (Baseweb) */
        span[data-baseweb="tag"] {
            background-color: #2D3748 !important;
            color: #E2E8F0 !important;
            border: 1px solid #4A5568 !important;
            border-radius: 4px !important;
        }
        span[data-baseweb="tag"] span {
            color: #E2E8F0 !important;
        }
        span[data-baseweb="tag"] svg {
            fill: #CBD5E0 !important;
        }
        span[data-baseweb="tag"]:hover {
            background-color: #3A475C !important;
            border-color: #718096 !important;
        }

        /* Technical Badges / Status Pills */
        .badge {
            display: inline-block;
            padding: 2px 9px;
            font-size: 0.75rem;
            font-weight: 600;
            line-height: 1.4;
            border-radius: 6px;
            letter-spacing: 0.2px;
            white-space: nowrap;
        }
        .badge-success {
            background-color: rgba(46, 160, 67, 0.12);
            color: #2da44e;
            border: 1px solid rgba(46, 160, 67, 0.25);
        }
        .badge-danger {
            background-color: rgba(209, 36, 47, 0.12);
            color: #cf222e;
            border: 1px solid rgba(209, 36, 47, 0.25);
        }
        .badge-warning {
            background-color: rgba(191, 135, 0, 0.12);
            color: #b07d00;
            border: 1px solid rgba(191, 135, 0, 0.25);
        }
        .badge-neutral {
            background-color: rgba(128, 128, 128, 0.1);
            color: inherit;
            border: 1px solid rgba(128, 128, 128, 0.2);
        }

        /* Subtle metadata text */
        .meta-text {
            font-size: 0.82rem;
            color: rgba(128, 128, 128, 0.85);
        }

        /* Streamlit Expanders */
        div[data-testid="stExpander"] {
            border-radius: 8px !important;
            border: 1px solid rgba(128, 128, 128, 0.18) !important;
            background-color: #1A202C !important;
        }
        div[data-testid="stExpander"] details {
            border-radius: 8px !important;
            background-color: #1A202C !important;
        }
        div[data-testid="stExpander"] summary {
            font-size: 0.85rem !important;
            color: #CBD5E0 !important;
            background-color: transparent !important;
        }
        div[data-testid="stExpander"] summary:hover {
            color: #63B3ED !important;
        }
        div[data-testid="stExpander"] div[data-testid="stExpanderDetails"] {
            background-color: #1A202C !important;
            border-top: 1px solid rgba(128, 128, 128, 0.15) !important;
            padding: 12px 14px !important;
            color: #E2E8F0 !important;
        }

        /* Header Subtitle Accent */
        .app-subheading {
            font-size: 0.95rem;
            color: rgba(128, 128, 128, 0.85);
            margin-top: -0.5rem;
            margin-bottom: 1.5rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="RSS-Hype-Sieve",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Inject Clean Minimal Technical CSS
    inject_custom_css()

    # Page Header
    st.title("RSS-Hype-Sieve: AI-Driven Feed De-Hype Engine")
    st.markdown(
        "<p class='app-subheading'>Automated signal filtration for AI and tech feeds. Ingests raw articles, "
        "evaluates technical substance against promotional hype via LLM validation, and surfaces high-density developments.</p>",
        unsafe_allow_html=True,
    )

    # Environment & API Key Check
    env_api_key = os.getenv("OPENAI_API_KEY", "").strip()

    # Sidebar: Configuration
    st.sidebar.header("Configuration")

    # API Key Management
    st.sidebar.subheader("OpenAI API Key")
    user_api_key = st.sidebar.text_input(
        "API Key",
        value=env_api_key,
        type="password",
        help="Required for LLM hype evaluation (gpt-4o-mini).",
        placeholder="sk-...",
    ).strip()

    if user_api_key:
        os.environ["OPENAI_API_KEY"] = user_api_key
        st.sidebar.success("API Key configured")
    else:
        st.sidebar.warning("API Key not set")
        st.warning(
            "**OPENAI_API_KEY is missing.** Please provide your OpenAI API key in the sidebar "
            "or configure a `.env` file to enable live pipeline execution. "
            "You can still inspect the **Historical Archive** below."
        )

    # Database Path status
    db_path = get_db_path()
    st.sidebar.caption(f"Database Path: `{db_path}`")

    # Feed Source Management
    st.sidebar.subheader("Feed Sources")
    default_sources = get_default_sources()

    if "custom_sources" not in st.session_state:
        st.session_state["custom_sources"] = default_sources

    new_feed = st.sidebar.text_input("Add Custom Feed URL", placeholder="https://...")
    if st.sidebar.button("Add Feed") and new_feed:
        if new_feed not in st.session_state["custom_sources"]:
            st.session_state["custom_sources"].append(new_feed)
            st.sidebar.success("Feed added")
            st.rerun()

    selected_sources = st.sidebar.multiselect(
        "Active Feeds for Ingestion",
        options=st.session_state["custom_sources"],
        default=st.session_state["custom_sources"],
        help="Choose which RSS feeds to ingest during the next pipeline run.",
    )

    # Filter Options in Sidebar
    st.sidebar.subheader("Filter & Display Settings")
    max_display_items = st.sidebar.slider(
        "Max Articles to Display per Tab", min_value=5, max_value=100, value=25, step=5
    )

    # Run Pipeline Action Button
    st.sidebar.markdown("---")
    can_run = bool(os.getenv("OPENAI_API_KEY")) and bool(selected_sources)
    run_btn = st.sidebar.button(
        "Run Pipeline",
        type="primary",
        disabled=not can_run,
        width="stretch",
        help="Execute RSS ingestion, deduplication, LLM evaluation, and database persistence.",
    )

    if not can_run and not os.getenv("OPENAI_API_KEY"):
        st.sidebar.info("Provide an API Key above to unlock pipeline execution.")
    elif not can_run and not selected_sources:
        st.sidebar.info("Select at least one feed source to run the pipeline.")

    # Pipeline Execution Handler
    if run_btn:
        with st.spinner(
            "Executing de-hype pipeline (Fetching RSS feeds ➔ Preprocessing text ➔ LLM evaluation ➔ Saving to DB)..."
        ):
            try:
                final_state = run_async(
                    execute_pipeline_coro(selected_sources, db_path)
                )
                st.session_state["latest_pipeline_state"] = final_state
                st.success("Pipeline executed successfully.")
            except Exception as exc:
                logger.error("Pipeline run failed: %s", exc, exc_info=True)
                st.error(f"Pipeline execution encountered an error: {exc}")

    # Fetch database records early so both tabs and historical archive share persistent data
    df_history = load_historical_articles(db_path)

    # 7-Day Rolling Digest Filter
    if not df_history.empty and "created_at" in df_history.columns:
        created_dt = pd.to_datetime(df_history["created_at"], errors="coerce")
        if created_dt.dt.tz is None:
            created_dt = created_dt.dt.tz_localize("UTC")
        else:
            created_dt = created_dt.dt.tz_convert("UTC")
        df_history["created_at_dt"] = created_dt
        cutoff = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=7)
        df_weekly = df_history[df_history["created_at_dt"] >= cutoff].copy()
    else:
        df_weekly = pd.DataFrame()

    # Main Area: Metrics & Telemetry
    pipeline_state = st.session_state.get("latest_pipeline_state")

    st.markdown("### Operational Metrics")
    if pipeline_state:
        evaluated_articles: list[dict[str, Any]] = pipeline_state.get(
            "evaluated_articles", []
        )
        failed_articles: list[dict[str, Any]] = pipeline_state.get(
            "failed_articles", []
        )

        curated_run = [a for a in evaluated_articles if a.get("is_passed")]
        filtered_run = [a for a in evaluated_articles if not a.get("is_passed")]

        total_ingested = len(evaluated_articles) + len(failed_articles)
        curated_count = len(curated_run)
        filtered_count = len(filtered_run)
        pass_rate = (
            (curated_count / total_ingested * 100) if total_ingested > 0 else 0.0
        )

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Run Ingested", total_ingested)
        col2.metric("Filtered (Hype)", filtered_count)
        col3.metric("Curated (Signal)", curated_count)
        col4.metric("Run Pass Rate", f"{pass_rate:.1f}%")

        if pipeline_state.get("db_error"):
            st.error(f"Database error during run: {pipeline_state['db_error']}")
    elif not df_history.empty:
        total_persisted = len(df_history)
        curated_total = int((df_history["is_passed"] == 1).sum())
        filtered_total = int((df_history["is_passed"] == 0).sum())
        pass_rate_total = (
            (curated_total / total_persisted * 100) if total_persisted > 0 else 0.0
        )

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Persisted Ingested", total_persisted)
        col2.metric("Filtered (Hype)", filtered_total)
        col3.metric("Curated (Signal)", curated_total)
        col4.metric("Historical Pass Rate", f"{pass_rate_total:.1f}%")
    else:
        st.info(
            "No articles found in database. Click **'Run Pipeline'** in the sidebar to execute "
            "live ingestion and evaluation."
        )

    # Interactive Feed Inspection Tabs (7-Day Rolling Digest View)
    st.markdown("---")
    st.markdown("### Feed Inspection (Last 7 Days)")
    tab_curated, tab_filtered, tab_report = st.tabs(
        [
            "Curated Articles",
            "Filtered (Hype)",
            "Briefing Report",
        ]
    )

    with tab_curated:
        if not df_weekly.empty:
            curated_df = df_weekly[df_weekly["is_passed"] == 1]
            if not curated_df.empty:
                display_count = min(len(curated_df), max_display_items)
                st.caption(
                    f"Showing curated technical articles from the last 7 days ({display_count} of {len(curated_df)}):"
                )
                for idx, (_, article) in enumerate(
                    curated_df.head(max_display_items).iterrows(), start=1
                ):
                    title = article.get("title", "Untitled")
                    url = article.get("url", "#")
                    score = article.get("hype_score", "N/A")
                    reason = article.get(
                        "hype_reason", "No evaluation rationale provided."
                    )
                    summary = str(article.get("summary") or "").strip()
                    source = article.get("source", "Unknown Source")
                    date = article.get("created_at", "")

                    with st.container(border=True):
                        st.markdown(f"#### {idx}. [{title}]({url})")
                        col_meta, col_score = st.columns([3, 1])
                        date_str = f" · {date}" if date else ""
                        col_meta.markdown(
                            f"<span class='meta-text'>{source}{date_str}</span>",
                            unsafe_allow_html=True,
                        )
                        col_score.markdown(
                            f"<div style='text-align: right;'><span class='badge badge-success'>Hype Score: {score}/10</span></div>",
                            unsafe_allow_html=True,
                        )
                        if reason:
                            st.info(f"**Signal Evaluation:** {reason}")
                        if summary:
                            with st.expander("Extracted Summary"):
                                st.write(summary)
            else:
                st.info(
                    "No curated technical articles found in the last 7 days. Inspect older records in the Historical Archive below."
                )
        else:
            st.info(
                "No articles evaluated in the last 7 days. Inspect older records in the Historical Archive below."
            )

    with tab_filtered:
        if not df_weekly.empty:
            filtered_df = df_weekly[df_weekly["is_passed"] == 0]
            if not filtered_df.empty:
                display_count = min(len(filtered_df), max_display_items)
                st.caption(
                    f"Showing hype-filtered articles from the last 7 days ({display_count} of {len(filtered_df)}):"
                )
                for idx, (_, article) in enumerate(
                    filtered_df.head(max_display_items).iterrows(), start=1
                ):
                    title = article.get("title", "Untitled")
                    url = article.get("url", "#")
                    score = article.get("hype_score", "N/A")
                    rule = article.get("violated_rule") or "UNKNOWN"
                    reason = article.get(
                        "hype_reason", "No violation reason provided."
                    )
                    summary = str(article.get("summary") or "").strip()
                    source = article.get("source", "Unknown Source")

                    with st.container(border=True):
                        st.markdown(f"#### {idx}. [{title}]({url})")
                        col_meta, col_score = st.columns([3, 1])
                        col_meta.markdown(
                            f"<span class='meta-text'>{source}</span> &nbsp;"
                            f"<span class='badge badge-warning'>{rule}</span>",
                            unsafe_allow_html=True,
                        )
                        col_score.markdown(
                            f"<div style='text-align: right;'><span class='badge badge-danger'>Hype Score: {score}/10</span></div>",
                            unsafe_allow_html=True,
                        )
                        if reason:
                            st.warning(f"**Rejection Rationale:** {reason}")
                        if summary:
                            with st.expander("Raw Summary"):
                                st.write(summary)
            else:
                st.info("No articles were filtered out in the last 7 days.")
        else:
            st.info(
                "No articles evaluated in the last 7 days. Inspect older records in the Historical Archive below."
            )

    with tab_report:
        if pipeline_state and pipeline_state.get("final_report"):
            st.markdown(pipeline_state["final_report"])
        else:
            st.info("Run the pipeline to generate a fresh briefing report.")

    # Historical Archive Section (Global, unconstrained view)
    st.markdown("---")
    st.markdown("### Historical Archive")
    st.caption("Inspect and search all persisted articles stored in the local SQLite database.")

    if df_history.empty:
        st.info("No records found in database or database has not been initialized.")
    else:
        # Search & Filter Controls
        col_search, col_filter, col_source = st.columns([2, 1, 1])

        search_query = col_search.text_input(
            "Search Archive (Title or Summary)", placeholder="e.g., LLM, PyTorch, agent"
        ).strip()
        status_filter = col_filter.selectbox(
            "Filter by Status", ["All", "Curated Only", "Filtered (Hype)"]
        )

        all_sources = ["All Sources"] + sorted(
            [str(s) for s in df_history["source"].dropna().unique()]
        )
        selected_source_filter = col_source.selectbox(
            "Filter by Source", options=all_sources
        )

        # Apply Filters
        filtered_archive_df = df_history.copy()

        if search_query:
            mask = filtered_archive_df["title"].str.contains(
                search_query, case=False, na=False
            ) | filtered_archive_df["summary"].str.contains(
                search_query, case=False, na=False
            )
            filtered_archive_df = filtered_archive_df[mask]

        if status_filter == "Curated Only":
            filtered_archive_df = filtered_archive_df[
                filtered_archive_df["is_passed"] == 1
            ]
        elif status_filter == "Filtered (Hype)":
            filtered_archive_df = filtered_archive_df[
                filtered_archive_df["is_passed"] == 0
            ]

        if selected_source_filter != "All Sources":
            filtered_archive_df = filtered_archive_df[
                filtered_archive_df["source"] == selected_source_filter
            ]

        # Display Mode Toggle
        col_count, col_view = st.columns([3, 1])
        col_count.caption(
            f"Displaying **{len(filtered_archive_df)}** of **{len(df_history)}** persisted records"
        )
        view_mode = col_view.radio(
            "View Format",
            ["Table", "Cards"],
            horizontal=True,
            label_visibility="collapsed",
        )

        if view_mode == "Table":
            display_columns = [
                "id",
                "title",
                "source",
                "is_passed",
                "hype_score",
                "violated_rule",
                "hype_reason",
                "created_at",
                "url",
            ]
            st.dataframe(
                filtered_archive_df[display_columns],
                width="stretch",
                column_config={
                    "url": st.column_config.LinkColumn("Article URL"),
                    "is_passed": st.column_config.CheckboxColumn("Curated?"),
                    "hype_score": st.column_config.NumberColumn(
                        "Hype Score", format="%d/10"
                    ),
                },
                hide_index=True,
            )
        else:
            for _, row in filtered_archive_df.iterrows():
                pass_label = "CURATED" if row["is_passed"] else "FILTERED"
                rule_info = (
                    f" · {row['violated_rule']}"
                    if row["violated_rule"] and row["violated_rule"] != "NONE"
                    else ""
                )
                score_str = (
                    f"[{row['hype_score']}/10]"
                    if pd.notna(row["hype_score"])
                    else "[N/A]"
                )
                header_text = f"[{pass_label}] {score_str} {row['title']} ({row['source']}){rule_info}"

                with st.expander(header_text):
                    st.markdown(f"**URL:** [{row['url']}]({row['url']})")
                    st.markdown(
                        f"**Recorded Date:** `{row['created_at']}` | **Hype Score:** `{row['hype_score']}/10`"
                    )
                    if row["violated_rule"] and row["violated_rule"] != "NONE":
                        st.markdown(
                            f"**Violated Rule:** `{row['violated_rule']}`"
                        )
                    if row["hype_reason"]:
                        if row["is_passed"]:
                            st.info(f"**Evaluation:** {row['hype_reason']}")
                        else:
                            st.warning(f"**Evaluation:** {row['hype_reason']}")
                    if row["summary"]:
                        st.markdown(f"**Summary:** {row['summary']}")


if __name__ == "__main__":
    main()
