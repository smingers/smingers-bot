"""
SQLite Database for Forecast Analytics

Enables queries like:
- "Which agent is most accurate on binary questions?"
- "Does more research correlate with better scores?"
- "What's my Brier score by question category?"
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import aiosqlite


@dataclass
class ForecastRecord:
    """A single forecast record for the database."""

    id: str  # {question_id}_{timestamp}
    question_id: int
    timestamp: str
    question_type: str  # binary, numeric, multiple_choice
    question_title: str
    base_rate: float | None
    final_prediction: float
    actual_outcome: float | None = None  # Filled after resolution
    brier_score: float | None = None  # Calculated after resolution
    total_cost: float = 0.0
    config_hash: str = ""
    tournament_id: int | None = None
    mode: str = "unknown"  # test, preview, live
    prediction_data: str = (
        ""  # JSON: full prediction (percentiles for numeric, probabilities for MC)
    )


@dataclass
class AgentPredictionRecord:
    """
    A single agent's prediction within a forecast.

    Attributes:
        forecast_id: Links to the parent forecast record (format: {question_id}_{timestamp})
        agent_id: Identifies which ensemble agent made this prediction (e.g., "forecaster_1")
        model: The LLM model used (e.g., "openrouter/anthropic/claude-sonnet-4")
        weight: Agent's weight in the ensemble average (typically 1.0 for equal weighting)
        prediction: The agent's probability prediction (0-1 for binary)
        reasoning_length: Character count of the agent's reasoning output
        prediction_data: JSON string with full prediction details (percentiles for numeric, etc.)
    """

    forecast_id: str
    agent_id: str
    model: str
    weight: float
    prediction: float
    reasoning_length: int
    prediction_data: str = ""


@dataclass
class ResearchSourceRecord:
    """Research source used in a forecast."""

    forecast_id: str
    source_type: str  # google, google_news, agent, asknews, etc.
    query: str
    num_results: int


class ForecastDatabase:
    """
    Async SQLite database for tracking forecast performance.
    """

    def __init__(self, db_path: str | Path = "./data/forecasts.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    async def initialize(self) -> None:
        """Create tables if they don't exist."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript("""
                -- Main forecasts table
                CREATE TABLE IF NOT EXISTS forecasts (
                    id TEXT PRIMARY KEY,
                    question_id INTEGER NOT NULL,
                    timestamp TEXT NOT NULL,
                    question_type TEXT NOT NULL,
                    question_title TEXT,
                    base_rate REAL,
                    final_prediction REAL NOT NULL,
                    actual_outcome REAL,
                    brier_score REAL,
                    total_cost REAL DEFAULT 0.0,
                    config_hash TEXT,
                    tournament_id INTEGER,
                    created_at TEXT NOT NULL,
                    mode TEXT
                );

                -- Agent predictions within each forecast
                CREATE TABLE IF NOT EXISTS agent_predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    forecast_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    model TEXT NOT NULL,
                    weight REAL NOT NULL,
                    prediction REAL NOT NULL,
                    reasoning_length INTEGER,
                    FOREIGN KEY (forecast_id) REFERENCES forecasts(id)
                );

                -- Research sources used
                CREATE TABLE IF NOT EXISTS research_sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    forecast_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    query TEXT,
                    num_results INTEGER,
                    FOREIGN KEY (forecast_id) REFERENCES forecasts(id)
                );

                -- Indices for common queries
                CREATE INDEX IF NOT EXISTS idx_forecasts_question_id ON forecasts(question_id);
                CREATE INDEX IF NOT EXISTS idx_forecasts_question_type ON forecasts(question_type);
                CREATE INDEX IF NOT EXISTS idx_forecasts_tournament ON forecasts(tournament_id);
                CREATE INDEX IF NOT EXISTS idx_agent_predictions_forecast ON agent_predictions(forecast_id);
                CREATE INDEX IF NOT EXISTS idx_agent_predictions_model ON agent_predictions(model);
                CREATE INDEX IF NOT EXISTS idx_research_sources_forecast ON research_sources(forecast_id);
            """)
            await db.commit()

    async def migrate_schema(self) -> None:
        """Run schema migrations to add/rename columns."""
        async with aiosqlite.connect(self.db_path) as db:
            # Check forecasts table columns
            cursor = await db.execute("PRAGMA table_info(forecasts)")
            forecast_columns = {row[1] for row in await cursor.fetchall()}

            if "mode" not in forecast_columns:
                await db.execute("ALTER TABLE forecasts ADD COLUMN mode TEXT")

            if "prediction_data" not in forecast_columns:
                await db.execute("ALTER TABLE forecasts ADD COLUMN prediction_data TEXT")

            # Check agent_predictions table columns
            cursor = await db.execute("PRAGMA table_info(agent_predictions)")
            agent_columns = {row[1] for row in await cursor.fetchall()}

            if "prediction_data" not in agent_columns:
                await db.execute("ALTER TABLE agent_predictions ADD COLUMN prediction_data TEXT")

            await db.commit()

    # =========================================================================
    # Insert Operations
    # =========================================================================

    async def insert_forecast(self, record: ForecastRecord) -> None:
        """Insert a new forecast record."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO forecasts
                (id, question_id, timestamp, question_type, question_title,
                 base_rate, final_prediction, actual_outcome, brier_score,
                 total_cost, config_hash, tournament_id, created_at, mode, prediction_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    record.id,
                    record.question_id,
                    record.timestamp,
                    record.question_type,
                    record.question_title,
                    record.base_rate,
                    record.final_prediction,
                    record.actual_outcome,
                    record.brier_score,
                    record.total_cost,
                    record.config_hash,
                    record.tournament_id,
                    datetime.now(UTC).isoformat(),
                    record.mode,
                    record.prediction_data,
                ),
            )
            await db.commit()

    async def insert_agent_prediction(self, record: AgentPredictionRecord) -> None:
        """Insert an agent's prediction."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO agent_predictions
                (forecast_id, agent_id, model, weight, prediction, reasoning_length, prediction_data)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    record.forecast_id,
                    record.agent_id,
                    record.model,
                    record.weight,
                    record.prediction,
                    record.reasoning_length,
                    record.prediction_data,
                ),
            )
            await db.commit()

    async def insert_research_source(self, record: ResearchSourceRecord) -> None:
        """Insert a research source record."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                INSERT INTO research_sources
                (forecast_id, source_type, query, num_results)
                VALUES (?, ?, ?, ?)
            """,
                (
                    record.forecast_id,
                    record.source_type,
                    record.query,
                    record.num_results,
                ),
            )
            await db.commit()

    # =========================================================================
    # Update Operations
    # =========================================================================

    async def update_question_resolution(
        self, question_id: int, actual_outcome: float, brier_score: float | None = None
    ) -> int:
        """
        Update resolution data (outcome and Brier score) for all forecasts on a question.
        Returns number of rows updated.
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                """
                UPDATE forecasts
                SET actual_outcome = ?, brier_score = ?
                WHERE question_id = ?
            """,
                (actual_outcome, brier_score, question_id),
            )
            await db.commit()
            return cursor.rowcount

    # =========================================================================
    # Query Operations
    # =========================================================================

    async def get_forecast(self, forecast_id: str) -> dict | None:
        """Get a single forecast by ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM forecasts WHERE id = ?", (forecast_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_forecasts_by_question(self, question_id: int) -> list[dict]:
        """Get all forecasts for a question."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM forecasts WHERE question_id = ? ORDER BY timestamp DESC",
                (question_id,),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_agent_predictions(self, forecast_id: str) -> list[dict]:
        """Get all agent predictions for a forecast."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM agent_predictions WHERE forecast_id = ?", (forecast_id,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # =========================================================================
    # Analytics Queries
    # =========================================================================

    async def get_agent_accuracy(self, question_type: str | None = None) -> list[dict]:
        """
        Get accuracy stats by agent/model.
        Only includes forecasts with resolved outcomes.
        """
        type_filter = "AND f.question_type = ?" if question_type else ""
        params = (question_type,) if question_type else ()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                f"""
                SELECT
                    ap.agent_id,
                    ap.model,
                    COUNT(*) as num_forecasts,
                    AVG(ap.weight) as avg_weight,
                    AVG((ap.prediction - f.actual_outcome) * (ap.prediction - f.actual_outcome)) as agent_brier,
                    AVG(f.brier_score) as ensemble_brier
                FROM agent_predictions ap
                JOIN forecasts f ON ap.forecast_id = f.id
                WHERE f.actual_outcome IS NOT NULL {type_filter}
                GROUP BY ap.agent_id, ap.model
                ORDER BY agent_brier ASC
            """,
                params,
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_research_correlation(self) -> list[dict]:
        """
        Analyze if more research correlates with better scores.
        Groups forecasts by number of research sources used.
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT
                    rs.num_sources,
                    COUNT(*) as num_forecasts,
                    AVG(f.brier_score) as avg_brier_score,
                    AVG(f.total_cost) as avg_cost
                FROM (
                    SELECT forecast_id, COUNT(*) as num_sources
                    FROM research_sources
                    GROUP BY forecast_id
                ) rs
                JOIN forecasts f ON rs.forecast_id = f.id
                WHERE f.brier_score IS NOT NULL
                GROUP BY rs.num_sources
                ORDER BY rs.num_sources
            """)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_brier_by_category(self, tournament_id: int | None = None) -> list[dict]:
        """Get Brier scores grouped by question type."""
        tournament_filter = "AND tournament_id = ?" if tournament_id else ""
        params = (tournament_id,) if tournament_id else ()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                f"""
                SELECT
                    question_type,
                    COUNT(*) as num_forecasts,
                    AVG(brier_score) as avg_brier_score,
                    MIN(brier_score) as best_brier,
                    MAX(brier_score) as worst_brier
                FROM forecasts
                WHERE brier_score IS NOT NULL {tournament_filter}
                GROUP BY question_type
                ORDER BY avg_brier_score ASC
            """,
                params,
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_cost_summary(self, tournament_id: int | None = None) -> dict:
        """Get cost statistics."""
        tournament_filter = "WHERE tournament_id = ?" if tournament_id else ""
        params = (tournament_id,) if tournament_id else ()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                f"""
                SELECT
                    COUNT(*) as num_forecasts,
                    SUM(total_cost) as total_cost,
                    AVG(total_cost) as avg_cost_per_forecast,
                    MIN(total_cost) as min_cost,
                    MAX(total_cost) as max_cost
                FROM forecasts
                {tournament_filter}
            """,
                params,
            )
            row = await cursor.fetchone()
            return dict(row) if row else {}

    async def get_recent_forecasts(self, limit: int = 20) -> list[dict]:
        """Get the most recent forecasts."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM forecasts
                ORDER BY created_at DESC
                LIMIT ?
            """,
                (limit,),
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_forecasts_with_agents(
        self, mode: str | None = None, question_type: str | None = None, limit: int = 100
    ) -> list[dict]:
        """
        Get forecasts with agent predictions for dashboard display.
        Returns forecasts with agent predictions pivoted into columns.
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            # Build WHERE clause
            conditions = []
            params: list[Any] = []
            if mode:
                conditions.append("f.mode = ?")
                params.append(mode)
            if question_type:
                conditions.append("f.question_type = ?")
                params.append(question_type)

            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            params.append(limit)

            cursor = await db.execute(
                f"""
                SELECT
                    f.id,
                    f.question_id,
                    f.timestamp,
                    f.mode,
                    f.question_type,
                    f.question_title,
                    f.final_prediction,
                    f.prediction_data,
                    f.total_cost,
                    f.created_at,
                    MAX(CASE WHEN ap.agent_id = 'forecaster_1' THEN ap.prediction END) as agent_1,
                    MAX(CASE WHEN ap.agent_id = 'forecaster_2' THEN ap.prediction END) as agent_2,
                    MAX(CASE WHEN ap.agent_id = 'forecaster_3' THEN ap.prediction END) as agent_3,
                    MAX(CASE WHEN ap.agent_id = 'forecaster_4' THEN ap.prediction END) as agent_4,
                    MAX(CASE WHEN ap.agent_id = 'forecaster_5' THEN ap.prediction END) as agent_5,
                    MAX(CASE WHEN ap.agent_id = 'forecaster_1' THEN ap.prediction_data END) as agent_1_data,
                    MAX(CASE WHEN ap.agent_id = 'forecaster_2' THEN ap.prediction_data END) as agent_2_data,
                    MAX(CASE WHEN ap.agent_id = 'forecaster_3' THEN ap.prediction_data END) as agent_3_data,
                    MAX(CASE WHEN ap.agent_id = 'forecaster_4' THEN ap.prediction_data END) as agent_4_data,
                    MAX(CASE WHEN ap.agent_id = 'forecaster_5' THEN ap.prediction_data END) as agent_5_data
                FROM forecasts f
                LEFT JOIN agent_predictions ap ON f.id = ap.forecast_id
                {where_clause}
                GROUP BY f.id
                ORDER BY f.timestamp DESC
                LIMIT ?
            """,
                params,
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def update_forecast_mode(self, forecast_id: str, mode: str) -> None:
        """Update the mode for a specific forecast."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("UPDATE forecasts SET mode = ? WHERE id = ?", (mode, forecast_id))
            await db.commit()

    async def update_forecast_prediction_data(self, forecast_id: str, prediction_data: str) -> None:
        """Update the prediction_data JSON for a specific forecast."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE forecasts SET prediction_data = ? WHERE id = ?",
                (prediction_data, forecast_id),
            )
            await db.commit()

    async def update_agent_prediction_data(
        self, forecast_id: str, agent_id: str, prediction_data: str
    ) -> None:
        """Update the prediction_data JSON for a specific agent prediction."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE agent_predictions SET prediction_data = ? WHERE forecast_id = ? AND agent_id = ?",
                (prediction_data, forecast_id, agent_id),
            )
            await db.commit()
