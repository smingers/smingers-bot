"""
SQLite Database for Forecast Analytics

Enables queries like:
- "Which agent is most accurate on binary questions?"
- "Does more research correlate with better scores?"
- "What's my Brier score by question category?"
"""

import aiosqlite
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Any
from dataclasses import dataclass


@dataclass
class ForecastRecord:
    """A single forecast record for the database."""
    id: str  # {question_id}_{timestamp}
    question_id: int
    timestamp: str
    question_type: str  # binary, numeric, multiple_choice
    question_title: str
    base_rate: Optional[float]
    final_prediction: float
    actual_outcome: Optional[float] = None  # Filled after resolution
    brier_score: Optional[float] = None  # Calculated after resolution
    total_cost: float = 0.0
    config_hash: str = ""
    tournament_id: Optional[int] = None  # Legacy: use collection_id for new code
    source: str = "metaculus"  # Question source identifier

    @property
    def collection_id(self) -> Optional[str]:
        """Generic collection ID (alias for tournament_id)."""
        return str(self.tournament_id) if self.tournament_id else None


@dataclass
class AgentPredictionRecord:
    """A single agent's prediction within a forecast."""
    forecast_id: str
    agent_name: str
    model: str
    weight: float
    prediction: float
    reasoning_length: int  # Character count of reasoning


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
                    source TEXT DEFAULT 'metaculus',
                    created_at TEXT NOT NULL
                );

                -- Agent predictions within each forecast
                CREATE TABLE IF NOT EXISTS agent_predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    forecast_id TEXT NOT NULL,
                    agent_name TEXT NOT NULL,
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

            # Migration: Add source column if it doesn't exist (for existing databases)
            cursor = await db.execute("PRAGMA table_info(forecasts)")
            columns = [row[1] for row in await cursor.fetchall()]
            if "source" not in columns:
                await db.execute("ALTER TABLE forecasts ADD COLUMN source TEXT DEFAULT 'metaculus'")
                await db.commit()

    # =========================================================================
    # Insert Operations
    # =========================================================================

    async def insert_forecast(self, record: ForecastRecord) -> None:
        """Insert a new forecast record."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO forecasts
                (id, question_id, timestamp, question_type, question_title,
                 base_rate, final_prediction, actual_outcome, brier_score,
                 total_cost, config_hash, tournament_id, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
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
                record.source,
                datetime.now(timezone.utc).isoformat(),
            ))
            await db.commit()

    async def insert_agent_prediction(self, record: AgentPredictionRecord) -> None:
        """Insert an agent's prediction."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO agent_predictions
                (forecast_id, agent_name, model, weight, prediction, reasoning_length)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                record.forecast_id,
                record.agent_name,
                record.model,
                record.weight,
                record.prediction,
                record.reasoning_length,
            ))
            await db.commit()

    async def insert_research_source(self, record: ResearchSourceRecord) -> None:
        """Insert a research source record."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO research_sources
                (forecast_id, source_type, query, num_results)
                VALUES (?, ?, ?, ?)
            """, (
                record.forecast_id,
                record.source_type,
                record.query,
                record.num_results,
            ))
            await db.commit()

    # =========================================================================
    # Update Operations
    # =========================================================================

    async def update_outcome(
        self,
        question_id: int,
        actual_outcome: float,
        brier_score: Optional[float] = None
    ) -> int:
        """
        Update the actual outcome for all forecasts on a question.
        Returns number of rows updated.
        """
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                UPDATE forecasts
                SET actual_outcome = ?, brier_score = ?
                WHERE question_id = ?
            """, (actual_outcome, brier_score, question_id))
            await db.commit()
            return cursor.rowcount

    # =========================================================================
    # Query Operations
    # =========================================================================

    async def get_forecast(self, forecast_id: str) -> Optional[dict]:
        """Get a single forecast by ID."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM forecasts WHERE id = ?",
                (forecast_id,)
            )
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_forecasts_by_question(self, question_id: int) -> list[dict]:
        """Get all forecasts for a question."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM forecasts WHERE question_id = ? ORDER BY timestamp DESC",
                (question_id,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_agent_predictions(self, forecast_id: str) -> list[dict]:
        """Get all agent predictions for a forecast."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM agent_predictions WHERE forecast_id = ?",
                (forecast_id,)
            )
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # =========================================================================
    # Analytics Queries
    # =========================================================================

    async def get_agent_accuracy(self, question_type: Optional[str] = None) -> list[dict]:
        """
        Get accuracy stats by agent/model.
        Only includes forecasts with resolved outcomes.
        """
        type_filter = "AND f.question_type = ?" if question_type else ""
        params = (question_type,) if question_type else ()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(f"""
                SELECT
                    ap.agent_name,
                    ap.model,
                    COUNT(*) as num_forecasts,
                    AVG(ap.weight) as avg_weight,
                    AVG((ap.prediction - f.actual_outcome) * (ap.prediction - f.actual_outcome)) as agent_brier,
                    AVG(f.brier_score) as ensemble_brier
                FROM agent_predictions ap
                JOIN forecasts f ON ap.forecast_id = f.id
                WHERE f.actual_outcome IS NOT NULL {type_filter}
                GROUP BY ap.agent_name, ap.model
                ORDER BY agent_brier ASC
            """, params)
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

    async def get_brier_by_category(self, tournament_id: Optional[int] = None) -> list[dict]:
        """Get Brier scores grouped by question type."""
        tournament_filter = "AND tournament_id = ?" if tournament_id else ""
        params = (tournament_id,) if tournament_id else ()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(f"""
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
            """, params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_cost_summary(self, tournament_id: Optional[int] = None) -> dict:
        """Get cost statistics."""
        tournament_filter = "WHERE tournament_id = ?" if tournament_id else ""
        params = (tournament_id,) if tournament_id else ()

        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(f"""
                SELECT
                    COUNT(*) as num_forecasts,
                    SUM(total_cost) as total_cost,
                    AVG(total_cost) as avg_cost_per_forecast,
                    MIN(total_cost) as min_cost,
                    MAX(total_cost) as max_cost
                FROM forecasts
                {tournament_filter}
            """, params)
            row = await cursor.fetchone()
            return dict(row) if row else {}

    async def get_recent_forecasts(self, limit: int = 20) -> list[dict]:
        """Get the most recent forecasts."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT * FROM forecasts
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]
