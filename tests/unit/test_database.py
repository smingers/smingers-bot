"""
Tests for SQLite database operations.

Tests cover:
- Schema creation and migrations
- Insert operations (forecasts, agent predictions, research sources)
- Query operations
- Update operations
- Analytics queries
"""

import pytest

from src.storage.database import (
    AgentPredictionRecord,
    ForecastDatabase,
    ForecastRecord,
    ResearchSourceRecord,
)

# ============================================================================
# ForecastRecord Dataclass Tests
# ============================================================================


class TestForecastRecord:
    """Tests for ForecastRecord dataclass."""

    def test_creates_with_required_fields(self):
        """Creates record with all required fields."""
        record = ForecastRecord(
            id="12345_20260101_120000",
            question_id=12345,
            timestamp="20260101_120000",
            question_type="binary",
            question_title="Test Question",
            base_rate=0.5,
            final_prediction=0.65,
        )

        assert record.id == "12345_20260101_120000"
        assert record.question_id == 12345
        assert record.question_type == "binary"
        assert record.final_prediction == 0.65

    def test_optional_fields_default(self):
        """Optional fields have correct defaults."""
        record = ForecastRecord(
            id="12345_20260101_120000",
            question_id=12345,
            timestamp="20260101_120000",
            question_type="binary",
            question_title="Test",
            base_rate=None,
            final_prediction=0.5,
        )

        assert record.actual_outcome is None
        assert record.brier_score is None
        assert record.total_cost == 0.0
        assert record.config_hash == ""
        assert record.tournament_id is None
        assert record.mode == "unknown"
        assert record.prediction_data == ""


class TestAgentPredictionRecord:
    """Tests for AgentPredictionRecord dataclass."""

    def test_creates_with_all_fields(self):
        """Creates record with all fields."""
        record = AgentPredictionRecord(
            forecast_id="12345_20260101_120000",
            agent_id="forecaster_1",
            model="test-model",
            weight=1.0,
            prediction=0.65,
            reasoning_length=500,
        )

        assert record.forecast_id == "12345_20260101_120000"
        assert record.agent_id == "forecaster_1"
        assert record.model == "test-model"
        assert record.weight == 1.0
        assert record.prediction == 0.65
        assert record.reasoning_length == 500


class TestResearchSourceRecord:
    """Tests for ResearchSourceRecord dataclass."""

    def test_creates_with_all_fields(self):
        """Creates record with all fields."""
        record = ResearchSourceRecord(
            forecast_id="12345_20260101_120000",
            source_type="google",
            query="test query",
            num_results=10,
        )

        assert record.forecast_id == "12345_20260101_120000"
        assert record.source_type == "google"
        assert record.query == "test query"
        assert record.num_results == 10


# ============================================================================
# Database Initialization Tests
# ============================================================================


class TestDatabaseInitialization:
    """Tests for database initialization."""

    @pytest.mark.asyncio
    async def test_creates_database_file(self, tmp_path):
        """Database file created on initialize."""
        db_path = tmp_path / "test.db"
        db = ForecastDatabase(db_path)

        await db.initialize()
        await db.migrate_schema()

        assert db_path.exists()

    @pytest.mark.asyncio
    async def test_creates_parent_directories(self, tmp_path):
        """Parent directories created if they don't exist."""
        db_path = tmp_path / "subdir" / "nested" / "test.db"
        db = ForecastDatabase(db_path)

        await db.initialize()
        await db.migrate_schema()

        assert db_path.exists()

    @pytest.mark.asyncio
    async def test_creates_all_tables(self, tmp_path):
        """All required tables are created."""
        import aiosqlite

        db_path = tmp_path / "test.db"
        db = ForecastDatabase(db_path)
        await db.initialize()
        await db.migrate_schema()

        async with aiosqlite.connect(db_path) as conn:
            cursor = await conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in await cursor.fetchall()}

        assert "forecasts" in tables
        assert "agent_predictions" in tables
        assert "research_sources" in tables

    @pytest.mark.asyncio
    async def test_initialize_idempotent(self, tmp_path):
        """Multiple initialize calls don't error."""
        db_path = tmp_path / "test.db"
        db = ForecastDatabase(db_path)

        await db.initialize()
        await db.migrate_schema()
        await db.initialize()  # Should not raise

        assert db_path.exists()


# ============================================================================
# Insert Operations Tests
# ============================================================================


class TestInsertOperations:
    """Tests for database insert operations."""

    @pytest.mark.asyncio
    async def test_insert_forecast(self, tmp_path):
        """Inserts forecast record successfully."""
        db = ForecastDatabase(tmp_path / "test.db")
        await db.initialize()
        await db.migrate_schema()
        await db.migrate_schema()

        record = ForecastRecord(
            id="12345_20260101_120000",
            question_id=12345,
            timestamp="20260101_120000",
            question_type="binary",
            question_title="Test Question",
            base_rate=0.5,
            final_prediction=0.65,
            total_cost=0.05,
            mode="test",
        )

        await db.insert_forecast(record)

        # Verify by retrieving
        result = await db.get_forecast("12345_20260101_120000")
        assert result is not None
        assert result["question_id"] == 12345
        assert result["final_prediction"] == 0.65
        assert result["mode"] == "test"

    @pytest.mark.asyncio
    async def test_insert_forecast_replaces_existing(self, tmp_path):
        """INSERT OR REPLACE updates existing record."""
        db = ForecastDatabase(tmp_path / "test.db")
        await db.initialize()
        await db.migrate_schema()
        await db.migrate_schema()

        record1 = ForecastRecord(
            id="12345_20260101_120000",
            question_id=12345,
            timestamp="20260101_120000",
            question_type="binary",
            question_title="Test Question",
            base_rate=0.5,
            final_prediction=0.65,
        )
        record2 = ForecastRecord(
            id="12345_20260101_120000",  # Same ID
            question_id=12345,
            timestamp="20260101_120000",
            question_type="binary",
            question_title="Updated Title",
            base_rate=0.5,
            final_prediction=0.75,  # Different prediction
        )

        await db.insert_forecast(record1)
        await db.insert_forecast(record2)

        result = await db.get_forecast("12345_20260101_120000")
        assert result["final_prediction"] == 0.75
        assert result["question_title"] == "Updated Title"

    @pytest.mark.asyncio
    async def test_insert_agent_prediction(self, tmp_path):
        """Inserts agent prediction record."""
        db = ForecastDatabase(tmp_path / "test.db")
        await db.initialize()
        await db.migrate_schema()

        # First insert a forecast
        forecast = ForecastRecord(
            id="12345_20260101_120000",
            question_id=12345,
            timestamp="20260101_120000",
            question_type="binary",
            question_title="Test",
            base_rate=0.5,
            final_prediction=0.65,
        )
        await db.insert_forecast(forecast)

        # Insert agent prediction
        agent_record = AgentPredictionRecord(
            forecast_id="12345_20260101_120000",
            agent_id="forecaster_1",
            model="claude-3-haiku",
            weight=1.0,
            prediction=0.60,
            reasoning_length=500,
        )
        await db.insert_agent_prediction(agent_record)

        # Verify
        predictions = await db.get_agent_predictions("12345_20260101_120000")
        assert len(predictions) == 1
        assert predictions[0]["agent_id"] == "forecaster_1"
        assert predictions[0]["prediction"] == 0.60

    @pytest.mark.asyncio
    async def test_insert_research_source(self, tmp_path):
        """Inserts research source record."""
        import aiosqlite

        db = ForecastDatabase(tmp_path / "test.db")
        await db.initialize()
        await db.migrate_schema()

        # First insert a forecast
        forecast = ForecastRecord(
            id="12345_20260101_120000",
            question_id=12345,
            timestamp="20260101_120000",
            question_type="binary",
            question_title="Test",
            base_rate=0.5,
            final_prediction=0.65,
        )
        await db.insert_forecast(forecast)

        # Insert research source
        source = ResearchSourceRecord(
            forecast_id="12345_20260101_120000",
            source_type="google",
            query="test query",
            num_results=10,
        )
        await db.insert_research_source(source)

        # Verify via direct query
        async with aiosqlite.connect(db.db_path) as conn:
            cursor = await conn.execute(
                "SELECT * FROM research_sources WHERE forecast_id = ?", ("12345_20260101_120000",)
            )
            rows = await cursor.fetchall()

        assert len(rows) == 1


# ============================================================================
# Query Operations Tests
# ============================================================================


class TestQueryOperations:
    """Tests for database query operations."""

    @pytest.mark.asyncio
    async def test_get_forecast_returns_none_for_missing(self, tmp_path):
        """Returns None for non-existent forecast."""
        db = ForecastDatabase(tmp_path / "test.db")
        await db.initialize()
        await db.migrate_schema()

        result = await db.get_forecast("nonexistent_id")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_forecast_returns_dict(self, tmp_path):
        """Returns forecast as dictionary."""
        db = ForecastDatabase(tmp_path / "test.db")
        await db.initialize()
        await db.migrate_schema()

        forecast = ForecastRecord(
            id="12345_20260100_120000",
            question_id=12345,
            timestamp="20260100_120000",
            question_type="binary",
            question_title="Test Question 0",
            base_rate=0.5,
            final_prediction=0.5,
            mode="test",
        )
        await db.insert_forecast(forecast)

        result = await db.get_forecast("12345_20260100_120000")

        assert isinstance(result, dict)
        assert result["question_id"] == 12345
        assert result["question_title"] == "Test Question 0"

    @pytest.mark.asyncio
    async def test_get_forecasts_by_question(self, tmp_path):
        """Returns all forecasts for a question."""
        db = ForecastDatabase(tmp_path / "test.db")
        await db.initialize()
        await db.migrate_schema()

        # Insert multiple forecasts for same question
        for i in range(3):
            forecast = ForecastRecord(
                id=f"12345_2026010{i}_120000",
                question_id=12345,
                timestamp=f"2026010{i}_120000",
                question_type="binary",
                question_title=f"Test Question {i}",
                base_rate=0.5,
                final_prediction=0.5 + i * 0.1,
            )
            await db.insert_forecast(forecast)

        results = await db.get_forecasts_by_question(12345)

        assert len(results) == 3
        # Should be ordered by timestamp descending
        assert results[0]["timestamp"] > results[1]["timestamp"]

    @pytest.mark.asyncio
    async def test_get_forecasts_by_question_empty(self, tmp_path):
        """Returns empty list for question with no forecasts."""
        db = ForecastDatabase(tmp_path / "test.db")
        await db.initialize()
        await db.migrate_schema()

        results = await db.get_forecasts_by_question(99999)
        assert results == []

    @pytest.mark.asyncio
    async def test_get_recent_forecasts(self, tmp_path):
        """Returns most recent forecasts with limit."""
        db = ForecastDatabase(tmp_path / "test.db")
        await db.initialize()
        await db.migrate_schema()

        for i in range(5):
            forecast = ForecastRecord(
                id=f"1234{i}_20260101_120000",
                question_id=12340 + i,
                timestamp="20260101_120000",
                question_type="binary",
                question_title=f"Question {i}",
                base_rate=0.5,
                final_prediction=0.5,
            )
            await db.insert_forecast(forecast)

        results = await db.get_recent_forecasts(limit=2)

        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_get_agent_predictions_empty(self, tmp_path):
        """Returns empty list when no agent predictions exist."""
        db = ForecastDatabase(tmp_path / "test.db")
        await db.initialize()
        await db.migrate_schema()

        forecast = ForecastRecord(
            id="12345_20260100_120000",
            question_id=12345,
            timestamp="20260100_120000",
            question_type="binary",
            question_title="Test",
            base_rate=0.5,
            final_prediction=0.5,
        )
        await db.insert_forecast(forecast)

        results = await db.get_agent_predictions("12345_20260100_120000")
        assert results == []


# ============================================================================
# Update Operations Tests
# ============================================================================


class TestUpdateOperations:
    """Tests for database update operations."""

    @pytest.mark.asyncio
    async def test_update_outcome(self, tmp_path):
        """Updates outcome and brier score."""
        db = ForecastDatabase(tmp_path / "test.db")
        await db.initialize()
        await db.migrate_schema()

        forecast = ForecastRecord(
            id="12345_20260101_120000",
            question_id=12345,
            timestamp="20260101_120000",
            question_type="binary",
            question_title="Test",
            base_rate=0.5,
            final_prediction=0.65,
            mode="test",
        )
        await db.insert_forecast(forecast)

        rows_updated = await db.update_outcome(
            question_id=12345,
            actual_outcome=1.0,
            brier_score=0.1225,  # (0.65 - 1.0)^2
        )

        assert rows_updated == 1

        result = await db.get_forecast("12345_20260101_120000")
        assert result["actual_outcome"] == 1.0
        assert result["brier_score"] == 0.1225

    @pytest.mark.asyncio
    async def test_update_outcome_no_match(self, tmp_path):
        """Returns 0 when no forecasts match."""
        db = ForecastDatabase(tmp_path / "test.db")
        await db.initialize()
        await db.migrate_schema()

        rows_updated = await db.update_outcome(
            question_id=99999,
            actual_outcome=1.0,
        )

        assert rows_updated == 0

    @pytest.mark.asyncio
    async def test_update_forecast_mode(self, tmp_path):
        """Updates forecast mode."""
        db = ForecastDatabase(tmp_path / "test.db")
        await db.initialize()
        await db.migrate_schema()

        forecast = ForecastRecord(
            id="12345_20260101_120000",
            question_id=12345,
            timestamp="20260101_120000",
            question_type="binary",
            question_title="Test",
            base_rate=0.5,
            final_prediction=0.65,
            mode="test",
        )
        await db.insert_forecast(forecast)

        await db.update_forecast_mode(
            forecast_id="12345_20260101_120000",
            mode="live",
        )

        result = await db.get_forecast("12345_20260101_120000")
        assert result["mode"] == "live"


# ============================================================================
# Analytics Queries Tests
# ============================================================================


class TestAnalyticsQueries:
    """Tests for analytics query operations."""

    @pytest.mark.asyncio
    async def test_get_cost_summary(self, tmp_path):
        """Returns cost statistics."""
        db = ForecastDatabase(tmp_path / "test.db")
        await db.initialize()
        await db.migrate_schema()

        # Insert forecasts with costs
        for i in range(5):
            forecast = ForecastRecord(
                id=f"1234{i}_20260101_120000",
                question_id=12340 + i,
                timestamp="20260101_120000",
                question_type="binary",
                question_title=f"Question {i}",
                base_rate=0.5,
                final_prediction=0.5,
                total_cost=0.05 + i * 0.01,
                tournament_id=100,
            )
            await db.insert_forecast(forecast)

        result = await db.get_cost_summary()

        assert result["num_forecasts"] == 5
        assert result["total_cost"] > 0
        assert result["avg_cost_per_forecast"] > 0

    @pytest.mark.asyncio
    async def test_get_cost_summary_with_tournament(self, tmp_path):
        """Filters cost summary by tournament."""
        db = ForecastDatabase(tmp_path / "test.db")
        await db.initialize()
        await db.migrate_schema()

        for i in range(3):
            forecast = ForecastRecord(
                id=f"1234{i}_20260101_120000",
                question_id=12340 + i,
                timestamp="20260101_120000",
                question_type="binary",
                question_title=f"Question {i}",
                base_rate=0.5,
                final_prediction=0.5,
                total_cost=0.05,
                tournament_id=100,
            )
            await db.insert_forecast(forecast)

        result = await db.get_cost_summary(tournament_id=100)

        assert result["num_forecasts"] == 3

    @pytest.mark.asyncio
    async def test_get_cost_summary_empty_tournament(self, tmp_path):
        """Returns zeros for non-existent tournament."""
        db = ForecastDatabase(tmp_path / "test.db")
        await db.initialize()
        await db.migrate_schema()

        result = await db.get_cost_summary(tournament_id=999)

        assert result["num_forecasts"] == 0

    @pytest.mark.asyncio
    async def test_get_brier_by_category(self, tmp_path):
        """Returns Brier scores grouped by question type."""
        db = ForecastDatabase(tmp_path / "test.db")
        await db.initialize()
        await db.migrate_schema()

        # Insert forecasts with Brier scores
        for i in range(5):
            forecast = ForecastRecord(
                id=f"1234{i}_20260101_120000",
                question_id=12340 + i,
                timestamp="20260101_120000",
                question_type="binary" if i < 3 else "numeric",
                question_title=f"Question {i}",
                base_rate=0.5,
                final_prediction=0.5,
                actual_outcome=1.0,
                brier_score=0.1 + i * 0.02,
            )
            await db.insert_forecast(forecast)

        results = await db.get_brier_by_category()

        # Should have binary and numeric categories
        types = {r["question_type"] for r in results}
        assert "binary" in types
        assert "numeric" in types

    @pytest.mark.asyncio
    async def test_get_agent_accuracy(self, tmp_path):
        """Returns accuracy stats by agent."""
        db = ForecastDatabase(tmp_path / "test.db")
        await db.initialize()
        await db.migrate_schema()

        # Insert forecast with outcome
        forecast = ForecastRecord(
            id="12345_20260101_120000",
            question_id=12345,
            timestamp="20260101_120000",
            question_type="binary",
            question_title="Question",
            base_rate=0.5,
            final_prediction=0.6,
            actual_outcome=1.0,
            brier_score=0.16,
        )
        await db.insert_forecast(forecast)

        # Add agent prediction
        agent = AgentPredictionRecord(
            forecast_id="12345_20260101_120000",
            agent_id="forecaster_1",
            model="test-model",
            weight=1.0,
            prediction=0.6,
            reasoning_length=500,
        )
        await db.insert_agent_prediction(agent)

        results = await db.get_agent_accuracy()

        assert len(results) > 0
        assert results[0]["agent_id"] == "forecaster_1"

    @pytest.mark.asyncio
    async def test_get_forecasts_with_agents(self, tmp_path):
        """Returns forecasts with pivoted agent predictions."""
        db = ForecastDatabase(tmp_path / "test.db")
        await db.initialize()
        await db.migrate_schema()

        # Insert forecast
        forecast = ForecastRecord(
            id="12345_20260101_120000",
            question_id=12345,
            timestamp="20260101_120000",
            question_type="binary",
            question_title="Question",
            base_rate=0.5,
            final_prediction=0.6,
            mode="live",
        )
        await db.insert_forecast(forecast)

        # Add agent predictions
        for i in range(3):
            agent = AgentPredictionRecord(
                forecast_id="12345_20260101_120000",
                agent_id=f"forecaster_{i + 1}",
                model="test-model",
                weight=1.0,
                prediction=0.5 + i * 0.1,
                reasoning_length=500,
            )
            await db.insert_agent_prediction(agent)

        results = await db.get_forecasts_with_agents(limit=10)

        assert len(results) > 0
        # Should have agent columns
        assert "agent_1" in results[0]


# ============================================================================
# Schema Migration Tests
# ============================================================================


class TestSchemaMigration:
    """Tests for schema migration."""

    @pytest.mark.asyncio
    async def test_migrate_schema_adds_missing_columns(self, tmp_path):
        """Migration adds columns that don't exist."""
        import aiosqlite

        db_path = tmp_path / "test.db"
        db = ForecastDatabase(db_path)

        # First initialize
        await db.initialize()
        await db.migrate_schema()

        # Run migration (should be idempotent)
        await db.migrate_schema()

        # Check columns exist
        async with aiosqlite.connect(db_path) as conn:
            cursor = await conn.execute("PRAGMA table_info(forecasts)")
            columns = {row[1] for row in await cursor.fetchall()}

        assert "mode" in columns
        assert "prediction_data" in columns

    @pytest.mark.asyncio
    async def test_migrate_schema_idempotent(self, tmp_path):
        """Multiple migration calls don't error."""
        db_path = tmp_path / "test.db"
        db = ForecastDatabase(db_path)

        await db.initialize()
        await db.migrate_schema()
        await db.migrate_schema()
        await db.migrate_schema()  # Should not raise
