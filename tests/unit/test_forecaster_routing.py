"""
Tests for Forecaster question routing and orchestration.

Tests cover:
- Correct handler selection based on question type
- Error handling for unknown question types
- Question fetching by ID and URL
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.bot.exceptions import QuestionTypeError
from src.bot.forecaster import Forecaster, ScopedArtifactStore
from src.utils.metaculus_api import MetaculusQuestion

# ============================================================================
# Helper Fixtures
# ============================================================================


@pytest.fixture
def mock_question_binary():
    """Mock binary MetaculusQuestion."""
    q = MagicMock(spec=MetaculusQuestion)
    q.id = 12345
    q.question_id = 67890
    q.title = "Will X happen?"
    q.question_type = "binary"
    q.description = "Background"
    q.background_info = "More background"
    q.resolution_criteria = "Criteria"
    q.raw = {"fine_print": "Fine print"}
    q.open_time = "2025-01-01"
    q.scheduled_close_time = "2026-12-31"
    q.scheduled_resolve_time = "2027-01-15"
    q.status = "open"
    q.community_prediction = 0.5
    q.num_forecasters = 10
    return q


@pytest.fixture
def mock_question_numeric():
    """Mock numeric MetaculusQuestion."""
    q = MagicMock(spec=MetaculusQuestion)
    q.id = 12346
    q.question_id = 67891
    q.title = "How many X?"
    q.question_type = "numeric"
    q.description = "Background"
    q.background_info = "More background"
    q.resolution_criteria = "Criteria"
    q.raw = {"fine_print": "Fine print", "scaling": {"range_min": 0, "range_max": 100}}
    q.open_time = "2025-01-01"
    q.scheduled_close_time = "2026-12-31"
    q.scheduled_resolve_time = "2027-01-15"
    q.status = "open"
    q.unit_of_measure = "units"
    q.lower_bound = 0
    q.upper_bound = 100
    q.open_lower_bound = True
    q.open_upper_bound = True
    q.zero_point = None
    q.nominal_lower_bound = None
    q.nominal_upper_bound = None
    q.cdf_size = 201
    return q


@pytest.fixture
def mock_question_discrete():
    """Mock discrete MetaculusQuestion."""
    q = MagicMock(spec=MetaculusQuestion)
    q.id = 12347
    q.question_id = 67892
    q.title = "How many discrete X?"
    q.question_type = "discrete"
    q.description = "Background"
    q.background_info = "More background"
    q.resolution_criteria = "Criteria"
    q.raw = {"fine_print": "Fine print", "scaling": {"range_min": 0, "range_max": 10}}
    q.open_time = "2025-01-01"
    q.scheduled_close_time = "2026-12-31"
    q.scheduled_resolve_time = "2027-01-15"
    q.status = "open"
    q.unit_of_measure = None
    q.lower_bound = 0
    q.upper_bound = 10
    q.open_lower_bound = False
    q.open_upper_bound = False
    q.zero_point = None
    q.nominal_lower_bound = None
    q.nominal_upper_bound = None
    q.cdf_size = 102
    return q


@pytest.fixture
def mock_question_date():
    """Mock date MetaculusQuestion."""
    q = MagicMock(spec=MetaculusQuestion)
    q.id = 12348
    q.question_id = 67893
    q.title = "When will X happen?"
    q.question_type = "date"
    q.description = "Background"
    q.background_info = "More background"
    q.resolution_criteria = "Criteria"
    q.raw = {
        "fine_print": "Fine print",
        "scaling": {"range_min": 1767225600, "range_max": 1798761600},
    }
    q.open_time = "2025-01-01"
    q.scheduled_close_time = "2026-12-31"
    q.scheduled_resolve_time = "2027-01-15"
    q.status = "open"
    q.unit_of_measure = None
    q.lower_bound = 1767225600
    q.upper_bound = 1798761600
    q.lower_bound_date_str = "2026-01-01"
    q.upper_bound_date_str = "2027-01-01"
    q.open_lower_bound = False
    q.open_upper_bound = True
    q.zero_point = None
    q.nominal_lower_bound = None
    q.nominal_upper_bound = None
    q.cdf_size = 201
    return q


@pytest.fixture
def mock_question_multiple_choice():
    """Mock multiple choice MetaculusQuestion."""
    q = MagicMock(spec=MetaculusQuestion)
    q.id = 12349
    q.question_id = 67894
    q.title = "Which option?"
    q.question_type = "multiple_choice"
    q.description = "Background"
    q.background_info = "More background"
    q.resolution_criteria = "Criteria"
    q.raw = {"fine_print": "Fine print", "question": {"options": []}}
    q.open_time = "2025-01-01"
    q.scheduled_close_time = "2026-12-31"
    q.scheduled_resolve_time = "2027-01-15"
    q.status = "open"
    q.options = [{"label": "A"}, {"label": "B"}, {"label": "C"}]
    return q


@pytest.fixture
def mock_question_unknown():
    """Mock question with unknown type."""
    q = MagicMock(spec=MetaculusQuestion)
    q.id = 12350
    q.question_id = 67895
    q.title = "Unknown question"
    q.question_type = "conditional"  # Not supported
    q.description = "Background"
    q.background_info = "More background"
    q.resolution_criteria = "Criteria"
    q.raw = {"fine_print": "Fine print"}
    q.open_time = "2025-01-01"
    q.scheduled_close_time = "2026-12-31"
    q.scheduled_resolve_time = "2027-01-15"
    q.status = "open"
    q.community_prediction = None
    q.num_forecasters = 0
    return q


@pytest.fixture
def mock_config():
    """Minimal config for Forecaster."""
    return {
        "mode": "test",
        "_active_agents": [
            {"name": "forecaster_1", "model": "test", "weight": 1.0},
        ],
        "_active_models": {},
        "storage": {
            "base_dir": "./data",
            "database_path": "./data/forecasts.db",
        },
    }


# ============================================================================
# Question Routing Tests
# ============================================================================


class TestForecasterRouting:
    """Tests for question type routing."""

    @pytest.mark.asyncio
    async def test_routes_binary_question(self, mock_question_binary, mock_config):
        """Binary questions use _forecast_binary."""
        with patch.multiple(
            "src.bot.forecaster",
            MetaculusClient=MagicMock,
            LLMClient=MagicMock,
            ArtifactStore=MagicMock,
            ForecastDatabase=MagicMock,
        ):
            forecaster = Forecaster(mock_config)
            forecaster.metaculus.get_question = AsyncMock(return_value=mock_question_binary)
            forecaster.artifact_store.create_forecast_artifacts = MagicMock()
            forecaster.artifact_store.save_question = MagicMock()
            forecaster.artifact_store.save_metadata = MagicMock()
            forecaster.artifact_store.save_prediction = MagicMock()
            forecaster.database.initialize = AsyncMock()
            forecaster.database.insert_forecast = AsyncMock()
            forecaster.database.insert_agent_prediction = AsyncMock()

            # Mock the handler
            mock_result = MagicMock()
            mock_result.final_probability = 0.65
            mock_result.agent_results = []
            mock_result.historical_context = ""
            mock_result.current_context = ""

            with patch.object(
                forecaster,
                "_forecast_binary",
                AsyncMock(
                    return_value={
                        "final_prediction": 0.65,
                        "agent_results": [],
                        "historical_context": "",
                        "current_context": "",
                    }
                ),
            ) as mock_handler:
                result = await forecaster.forecast_question(question=mock_question_binary)

                mock_handler.assert_called_once()
                assert result["prediction"] == 0.65

    @pytest.mark.asyncio
    async def test_routes_numeric_question(self, mock_question_numeric, mock_config):
        """Numeric questions use _forecast_numeric."""
        with patch.multiple(
            "src.bot.forecaster",
            MetaculusClient=MagicMock,
            LLMClient=MagicMock,
            ArtifactStore=MagicMock,
            ForecastDatabase=MagicMock,
        ):
            forecaster = Forecaster(mock_config)
            forecaster.metaculus.get_question = AsyncMock(return_value=mock_question_numeric)
            forecaster.artifact_store.create_forecast_artifacts = MagicMock()
            forecaster.artifact_store.save_question = MagicMock()
            forecaster.artifact_store.save_metadata = MagicMock()
            forecaster.artifact_store.save_prediction = MagicMock()
            forecaster.database.initialize = AsyncMock()
            forecaster.database.insert_forecast = AsyncMock()
            forecaster.database.insert_agent_prediction = AsyncMock()

            with patch.object(
                forecaster,
                "_forecast_numeric",
                AsyncMock(
                    return_value={
                        "final_percentiles": {"50": 50},
                        "final_cdf": [0.5] * 201,
                        "agent_results": [],
                        "historical_context": "",
                        "current_context": "",
                    }
                ),
            ) as mock_handler:
                result = await forecaster.forecast_question(question=mock_question_numeric)

                mock_handler.assert_called_once()
                assert "cdf" in result

    @pytest.mark.asyncio
    async def test_routes_discrete_question(self, mock_question_discrete, mock_config):
        """Discrete questions use _forecast_numeric (same as numeric)."""
        with patch.multiple(
            "src.bot.forecaster",
            MetaculusClient=MagicMock,
            LLMClient=MagicMock,
            ArtifactStore=MagicMock,
            ForecastDatabase=MagicMock,
        ):
            forecaster = Forecaster(mock_config)
            forecaster.metaculus.get_question = AsyncMock(return_value=mock_question_discrete)
            forecaster.artifact_store.create_forecast_artifacts = MagicMock()
            forecaster.artifact_store.save_question = MagicMock()
            forecaster.artifact_store.save_metadata = MagicMock()
            forecaster.artifact_store.save_prediction = MagicMock()
            forecaster.database.initialize = AsyncMock()
            forecaster.database.insert_forecast = AsyncMock()
            forecaster.database.insert_agent_prediction = AsyncMock()

            with patch.object(
                forecaster,
                "_forecast_numeric",
                AsyncMock(
                    return_value={
                        "final_percentiles": {"50": 5},
                        "final_cdf": [0.5] * 102,
                        "agent_results": [],
                        "historical_context": "",
                        "current_context": "",
                    }
                ),
            ) as mock_handler:
                await forecaster.forecast_question(question=mock_question_discrete)

                mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_routes_date_question(self, mock_question_date, mock_config):
        """Date questions use _forecast_numeric with date flag."""
        with patch.multiple(
            "src.bot.forecaster",
            MetaculusClient=MagicMock,
            LLMClient=MagicMock,
            ArtifactStore=MagicMock,
            ForecastDatabase=MagicMock,
        ):
            forecaster = Forecaster(mock_config)
            forecaster.metaculus.get_question = AsyncMock(return_value=mock_question_date)
            forecaster.artifact_store.create_forecast_artifacts = MagicMock()
            forecaster.artifact_store.save_question = MagicMock()
            forecaster.artifact_store.save_metadata = MagicMock()
            forecaster.artifact_store.save_prediction = MagicMock()
            forecaster.database.initialize = AsyncMock()
            forecaster.database.insert_forecast = AsyncMock()
            forecaster.database.insert_agent_prediction = AsyncMock()

            with patch.object(
                forecaster,
                "_forecast_numeric",
                AsyncMock(
                    return_value={
                        "final_percentiles": {"50": 1777000000},
                        "final_cdf": [0.5] * 201,
                        "agent_results": [],
                        "historical_context": "",
                        "current_context": "",
                    }
                ),
            ) as mock_handler:
                await forecaster.forecast_question(question=mock_question_date)

                mock_handler.assert_called_once()

    @pytest.mark.asyncio
    async def test_routes_multiple_choice_question(
        self, mock_question_multiple_choice, mock_config
    ):
        """Multiple choice questions use _forecast_multiple_choice."""
        with patch.multiple(
            "src.bot.forecaster",
            MetaculusClient=MagicMock,
            LLMClient=MagicMock,
            ArtifactStore=MagicMock,
            ForecastDatabase=MagicMock,
        ):
            forecaster = Forecaster(mock_config)
            forecaster.metaculus.get_question = AsyncMock(
                return_value=mock_question_multiple_choice
            )
            forecaster.artifact_store.create_forecast_artifacts = MagicMock()
            forecaster.artifact_store.save_question = MagicMock()
            forecaster.artifact_store.save_metadata = MagicMock()
            forecaster.artifact_store.save_prediction = MagicMock()
            forecaster.database.initialize = AsyncMock()
            forecaster.database.insert_forecast = AsyncMock()
            forecaster.database.insert_agent_prediction = AsyncMock()

            with patch.object(
                forecaster,
                "_forecast_multiple_choice",
                AsyncMock(
                    return_value={
                        "final_probabilities": {"A": 0.5, "B": 0.3, "C": 0.2},
                        "agent_results": [],
                        "historical_context": "",
                        "current_context": "",
                        "options": ["A", "B", "C"],
                    }
                ),
            ) as mock_handler:
                result = await forecaster.forecast_question(question=mock_question_multiple_choice)

                mock_handler.assert_called_once()
                assert "prediction" in result

    @pytest.mark.asyncio
    async def test_raises_for_unknown_type(self, mock_question_unknown, mock_config):
        """Unknown question types raise QuestionTypeError."""
        with patch.multiple(
            "src.bot.forecaster",
            MetaculusClient=MagicMock,
            LLMClient=MagicMock,
            ArtifactStore=MagicMock,
            ForecastDatabase=MagicMock,
        ):
            forecaster = Forecaster(mock_config)
            forecaster.metaculus.get_question = AsyncMock(return_value=mock_question_unknown)
            forecaster.artifact_store.create_forecast_artifacts = MagicMock()
            forecaster.artifact_store.save_question = MagicMock()
            forecaster.artifact_store.save_metadata = MagicMock()
            forecaster.database.initialize = AsyncMock()

            with pytest.raises(QuestionTypeError) as exc_info:
                await forecaster.forecast_question(question=mock_question_unknown)

            assert "conditional" in str(exc_info.value)


# ============================================================================
# Question Fetching Tests
# ============================================================================


class TestForecasterQuestionFetching:
    """Tests for question fetching by ID and URL."""

    @pytest.mark.asyncio
    async def test_fetches_by_question_id(self, mock_question_binary, mock_config):
        """Fetches question by ID when question_id provided."""
        with patch.multiple(
            "src.bot.forecaster",
            MetaculusClient=MagicMock,
            LLMClient=MagicMock,
            ArtifactStore=MagicMock,
            ForecastDatabase=MagicMock,
        ):
            forecaster = Forecaster(mock_config)
            forecaster.metaculus.get_question = AsyncMock(return_value=mock_question_binary)
            forecaster.artifact_store.create_forecast_artifacts = MagicMock()
            forecaster.artifact_store.save_question = MagicMock()
            forecaster.artifact_store.save_metadata = MagicMock()
            forecaster.artifact_store.save_prediction = MagicMock()
            forecaster.database.initialize = AsyncMock()
            forecaster.database.insert_forecast = AsyncMock()
            forecaster.database.insert_agent_prediction = AsyncMock()

            with patch.object(
                forecaster,
                "_forecast_binary",
                AsyncMock(
                    return_value={
                        "final_prediction": 0.5,
                        "agent_results": [],
                        "historical_context": "",
                        "current_context": "",
                    }
                ),
            ):
                await forecaster.forecast_question(question_id=12345)

                forecaster.metaculus.get_question.assert_called_once_with(12345)

    @pytest.mark.asyncio
    async def test_fetches_by_url(self, mock_question_binary, mock_config):
        """Fetches question by URL when question_url provided."""
        with patch.multiple(
            "src.bot.forecaster",
            MetaculusClient=MagicMock,
            LLMClient=MagicMock,
            ArtifactStore=MagicMock,
            ForecastDatabase=MagicMock,
        ):
            forecaster = Forecaster(mock_config)
            forecaster.metaculus.get_question_by_url = AsyncMock(return_value=mock_question_binary)
            forecaster.artifact_store.create_forecast_artifacts = MagicMock()
            forecaster.artifact_store.save_question = MagicMock()
            forecaster.artifact_store.save_metadata = MagicMock()
            forecaster.artifact_store.save_prediction = MagicMock()
            forecaster.database.initialize = AsyncMock()
            forecaster.database.insert_forecast = AsyncMock()
            forecaster.database.insert_agent_prediction = AsyncMock()

            with patch.object(
                forecaster,
                "_forecast_binary",
                AsyncMock(
                    return_value={
                        "final_prediction": 0.5,
                        "agent_results": [],
                        "historical_context": "",
                        "current_context": "",
                    }
                ),
            ):
                await forecaster.forecast_question(
                    question_url="https://metaculus.com/questions/12345/"
                )

                forecaster.metaculus.get_question_by_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_raises_without_question_source(self, mock_config):
        """Raises ValueError when no question source provided."""
        with patch.multiple(
            "src.bot.forecaster",
            MetaculusClient=MagicMock,
            LLMClient=MagicMock,
            ArtifactStore=MagicMock,
            ForecastDatabase=MagicMock,
        ):
            forecaster = Forecaster(mock_config)

            with pytest.raises(ValueError, match="Must provide"):
                await forecaster.forecast_question()


# ============================================================================
# ScopedArtifactStore Tests
# ============================================================================


class TestScopedArtifactStore:
    """Tests for ScopedArtifactStore wrapper."""

    def test_delegates_save_query_generation(self):
        """Delegates to underlying store with artifacts."""
        mock_store = MagicMock()
        mock_artifacts = MagicMock()

        scoped = ScopedArtifactStore(mock_store, mock_artifacts)
        scoped.save_query_generation("historical", "prompt", "response")

        mock_store.save_query_generation.assert_called_once_with(
            mock_artifacts, "historical", "prompt", "response"
        )

    def test_delegates_save_search_results(self):
        """Delegates save_search_results to underlying store."""
        mock_store = MagicMock()
        mock_artifacts = MagicMock()

        scoped = ScopedArtifactStore(mock_store, mock_artifacts)
        scoped.save_search_results("current", {"results": []})

        mock_store.save_search_results.assert_called_once_with(
            mock_artifacts, "current", {"results": []}
        )

    def test_delegates_save_agent_step1(self):
        """Delegates save_agent_step1 to underlying store."""
        mock_store = MagicMock()
        mock_artifacts = MagicMock()

        scoped = ScopedArtifactStore(mock_store, mock_artifacts)
        scoped.save_agent_step1(1, "response")

        mock_store.save_agent_step1.assert_called_once_with(mock_artifacts, 1, "response")

    def test_delegates_save_aggregation(self):
        """Delegates save_aggregation to underlying store."""
        mock_store = MagicMock()
        mock_artifacts = MagicMock()

        scoped = ScopedArtifactStore(mock_store, mock_artifacts)
        scoped.save_aggregation({"final": 0.5})

        mock_store.save_aggregation.assert_called_once_with(mock_artifacts, {"final": 0.5})
