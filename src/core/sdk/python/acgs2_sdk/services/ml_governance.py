"""
ACGS-2 ML Governance Service
Adaptive ML models with feedback loops and drift detection
Constitutional Hash: cdd01ef066bc6cf2
"""

from typing import TYPE_CHECKING, Any

try:
    from src.core.shared.types import JSONDict, JSONValue
except ImportError:
    JSONValue = str | int | float | bool | None | dict[str, Any] | list[Any]  # type: ignore[misc]
    JSONDict = dict[str, JSONValue]  # type: ignore[misc]

from acgs2_sdk.constants import CONSTITUTIONAL_HASH, ML_GOVERNANCE_ENDPOINT
from acgs2_sdk.models import (
    ABNTest,
    CreateABNTestRequest,
    CreateMLModelRequest,
    DriftDetection,
    FeedbackSubmission,
    MakePredictionRequest,
    MLModel,
    ModelPrediction,
    PaginatedResponse,
    SubmitFeedbackRequest,
    UpdateMLModelRequest,
)

if TYPE_CHECKING:
    from acgs2_sdk.client import ACGS2Client


class MLGovernanceService:
    """Service for ML model governance and adaptive learning."""

    def __init__(self, client: "ACGS2Client") -> None:
        self._client = client
        self._base_path = ML_GOVERNANCE_ENDPOINT

    async def create_model(
        self,
        request: CreateMLModelRequest,
    ) -> MLModel:
        """Create/register a new ML model."""
        data = await self._client.post(
            f"{self._base_path}/models",
            json={
                **request.model_dump(by_alias=True, exclude_none=True),
                "constitutionalHash": CONSTITUTIONAL_HASH,
            },
        )
        return MLModel.model_validate(data.get("data", data))

    async def get_model(self, model_id: str) -> MLModel:
        """Get an ML model by ID."""
        data = await self._client.get(f"{self._base_path}/models/{model_id}")
        return MLModel.model_validate(data.get("data", data))

    async def list_models(
        self,
        page: int = 1,
        page_size: int = 50,
        model_type: str | None = None,
        framework: str | None = None,
    ) -> PaginatedResponse[MLModel]:
        """List ML models."""
        params: JSONDict = {"page": page, "pageSize": page_size}
        if model_type:
            params["modelType"] = model_type
        if framework:
            params["framework"] = framework

        data = await self._client.get(f"{self._base_path}/models", params=params)
        response_data = data.get("data", data)
        return PaginatedResponse[MLModel](
            data=[MLModel.model_validate(m) for m in response_data.get("data", [])],
            total=response_data.get("total", 0),
            page=response_data.get("page", page),
            page_size=response_data.get("pageSize", page_size),
            total_pages=response_data.get("totalPages", 0),
        )

    async def update_model(
        self,
        model_id: str,
        request: UpdateMLModelRequest,
    ) -> MLModel:
        """Update an ML model."""
        data = await self._client.put(
            f"{self._base_path}/models/{model_id}",
            json={
                **request.model_dump(by_alias=True, exclude_none=True),
                "constitutionalHash": CONSTITUTIONAL_HASH,
            },
        )
        return MLModel.model_validate(data.get("data", data))

    async def delete_model(self, model_id: str) -> None:
        """Delete an ML model."""
        await self._client.delete(f"{self._base_path}/models/{model_id}")

    async def make_prediction(
        self,
        request: MakePredictionRequest,
    ) -> ModelPrediction:
        """Make a prediction with an ML model."""
        data = await self._client.post(
            f"{self._base_path}/predictions",
            json={
                **request.model_dump(by_alias=True, exclude_none=True),
                "constitutionalHash": CONSTITUTIONAL_HASH,
            },
        )
        return ModelPrediction.model_validate(data.get("data", data))

    async def get_prediction(self, prediction_id: str) -> ModelPrediction:
        """Get a prediction by ID."""
        data = await self._client.get(f"{self._base_path}/predictions/{prediction_id}")
        return ModelPrediction.model_validate(data.get("data", data))

    async def list_predictions(
        self,
        model_id: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedResponse[ModelPrediction]:
        """List model predictions."""
        params: JSONDict = {"page": page, "pageSize": page_size}
        if model_id:
            params["modelId"] = model_id

        data = await self._client.get(f"{self._base_path}/predictions", params=params)
        response_data = data.get("data", data)
        return PaginatedResponse[ModelPrediction](
            data=[ModelPrediction.model_validate(p) for p in response_data.get("data", [])],
            total=response_data.get("total", 0),
            page=response_data.get("page", page),
            page_size=response_data.get("pageSize", page_size),
            total_pages=response_data.get("totalPages", 0),
        )

    async def submit_feedback(
        self,
        request: SubmitFeedbackRequest,
    ) -> FeedbackSubmission:
        """Submit feedback for model training."""
        data = await self._client.post(
            f"{self._base_path}/feedback",
            json={
                **request.model_dump(by_alias=True, exclude_none=True),
                "constitutionalHash": CONSTITUTIONAL_HASH,
            },
        )
        return FeedbackSubmission.model_validate(data.get("data", data))

    async def get_feedback(
        self,
        feedback_id: str,
    ) -> FeedbackSubmission:
        """Get feedback by ID."""
        data = await self._client.get(f"{self._base_path}/feedback/{feedback_id}")
        return FeedbackSubmission.model_validate(data.get("data", data))

    async def list_feedback(
        self,
        model_id: str | None = None,
        feedback_type: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedResponse[FeedbackSubmission]:
        """List feedback submissions."""
        params: JSONDict = {"page": page, "pageSize": page_size}
        if model_id:
            params["modelId"] = model_id
        if feedback_type:
            params["feedbackType"] = feedback_type

        data = await self._client.get(f"{self._base_path}/feedback", params=params)
        response_data = data.get("data", data)
        return PaginatedResponse[FeedbackSubmission](
            data=[FeedbackSubmission.model_validate(f) for f in response_data.get("data", [])],
            total=response_data.get("total", 0),
            page=response_data.get("page", page),
            page_size=response_data.get("pageSize", page_size),
            total_pages=response_data.get("totalPages", 0),
        )

    async def check_drift(self, model_id: str) -> DriftDetection:
        """Check for model drift."""
        data = await self._client.get(f"{self._base_path}/models/{model_id}/drift")
        return DriftDetection.model_validate(data.get("data", data))

    async def retrain_model(
        self,
        model_id: str,
        feedback_threshold: int | None = None,
    ) -> JSONDict:
        """Trigger model retraining."""
        json_data: JSONDict = {"constitutionalHash": CONSTITUTIONAL_HASH}
        if feedback_threshold:
            json_data["feedbackThreshold"] = feedback_threshold

        data = await self._client.post(
            f"{self._base_path}/models/{model_id}/retrain",
            json=json_data,
        )
        return data.get("data", data)

    async def create_ab_test(
        self,
        request: CreateABNTestRequest,
    ) -> ABNTest:
        """Create an A/B test."""
        data = await self._client.post(
            f"{self._base_path}/ab-tests",
            json={
                **request.model_dump(by_alias=True, exclude_none=True),
                "constitutionalHash": CONSTITUTIONAL_HASH,
            },
        )
        return ABNTest.model_validate(data.get("data", data))

    async def get_ab_test(self, test_id: str) -> ABNTest:
        """Get an A/B test by ID."""
        data = await self._client.get(f"{self._base_path}/ab-tests/{test_id}")
        return ABNTest.model_validate(data.get("data", data))

    async def list_ab_tests(
        self,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedResponse[ABNTest]:
        """List A/B tests."""
        params = {"page": page, "pageSize": page_size}
        data = await self._client.get(f"{self._base_path}/ab-tests", params=params)
        response_data = data.get("data", data)
        return PaginatedResponse[ABNTest](
            data=[ABNTest.model_validate(t) for t in response_data.get("data", [])],
            total=response_data.get("total", 0),
            page=response_data.get("page", page),
            page_size=response_data.get("pageSize", page_size),
            total_pages=response_data.get("totalPages", 0),
        )

    async def stop_ab_test(self, test_id: str) -> ABNTest:
        """Stop an A/B test."""
        data = await self._client.post(f"{self._base_path}/ab-tests/{test_id}/stop")
        return ABNTest.model_validate(data.get("data", data))

    async def get_ab_test_results(self, test_id: str) -> JSONDict:
        """Get A/B test results."""
        data = await self._client.get(f"{self._base_path}/ab-tests/{test_id}/results")
        return data.get("data", data)

    async def get_model_metrics(
        self,
        model_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> JSONDict:
        """Get model performance metrics."""
        params: JSONDict = {}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date

        data = await self._client.get(f"{self._base_path}/models/{model_id}/metrics", params=params)
        return data.get("data", data)

    async def get_dashboard_data(self) -> JSONDict:
        """Get ML governance dashboard data."""
        data = await self._client.get(f"{self._base_path}/dashboard")
        return data.get("data", data)
