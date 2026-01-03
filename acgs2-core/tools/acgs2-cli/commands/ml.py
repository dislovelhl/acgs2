"""
ACGS-2 CLI - ML Governance Commands
Constitutional Hash: cdd01ef066bc6cf2
"""

import asyncio
import json
import sys
from typing import Any

import click
from acgs2_sdk import MLGovernanceService, create_client


@click.group()
@click.pass_context
def ml(ctx):
    """ML Governance management commands"""
    pass


@ml.group()
@click.pass_context
def models(ctx):
    """ML model management"""
    pass


@models.command("create")
@click.option("--name", required=True, help="Model name")
@click.option(
    "--framework", required=True, help="ML framework (scikit-learn, tensorflow, pytorch, etc.)"
)
@click.option("--model-type", required=True, help="Model type (classification, regression, etc.)")
@click.option("--description", help="Model description")
@click.option("--accuracy", type=float, help="Initial accuracy score")
@click.pass_context
def create_model(
    ctx,
    name: str,
    framework: str,
    model_type: str,
    description: str | None,
    accuracy: float | None,
):
    """Create/register a new ML model"""

    async def create():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                ml_service = MLGovernanceService(client)

                model_data = {
                    "name": name,
                    "framework": framework,
                    "model_type": model_type,
                }
                if description:
                    model_data["description"] = description
                if accuracy is not None:
                    model_data["initial_accuracy_score"] = accuracy

                model = await ml_service.create_model(model_data)

                click.secho("🤖 ML Model created successfully!", fg="green")
                click.echo(f"ID: {model.id}")
                click.echo(f"Name: {model.name}")
                click.echo(f"Framework: {model.framework}")
                click.echo(f"Type: {model.model_type}")
                click.echo(f"Status: {model.training_status}")
                if model.accuracy_score:
                    click.echo(".2f")

        except Exception as e:
            click.secho(f"❌ Failed to create model: {e}", fg="red")
            sys.exit(1)

    asyncio.run(create())


@models.command("list")
@click.option("--framework", help="Filter by framework")
@click.option("--type", "model_type", help="Filter by model type")
@click.option("--limit", type=int, default=20, help="Number of results to show")
@click.pass_context
def list_models(ctx, framework: str | None, model_type: str | None, limit: int):
    """List ML models"""

    async def list():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                ml_service = MLGovernanceService(client)

                models = await ml_service.list_models(
                    framework=framework, model_type=model_type, page_size=limit
                )

                click.secho(f"🤖 ML Models ({models.total})", fg="blue", bold=True)

                if not models.data:
                    click.echo("No models found.")
                    return

                for model in models.data:
                    status_color = {
                        "training": "yellow",
                        "completed": "green",
                        "failed": "red",
                        "stopped": "grey",
                    }.get(model.training_status, "white")

                    click.secho(f"• {model.id}", fg=status_color, nl=False)
                    click.echo(f" | {model.name} | {model.framework} | {model.model_type}")
                    if model.accuracy_score:
                        click.echo(".2f")

        except Exception as e:
            click.secho(f"❌ Failed to list models: {e}", fg="red")
            sys.exit(1)

    asyncio.run(list())


@models.command("show")
@click.argument("model_id")
@click.pass_context
def show_model(ctx, model_id: str):
    """Show ML model details"""

    async def show():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                ml_service = MLGovernanceService(client)

                model = await ml_service.get_model(model_id)

                click.secho(f"🤖 ML Model: {model.name}", fg="blue", bold=True)
                click.echo(f"ID: {model.id}")
                click.echo(f"Framework: {model.framework}")
                click.echo(f"Type: {model.model_type}")
                click.echo(f"Status: {model.training_status}")
                if model.description:
                    click.echo(f"Description: {model.description}")
                if model.accuracy_score:
                    click.echo(".2f")
                if model.last_trained_at:
                    click.echo(f"Last Trained: {model.last_trained_at}")
                click.echo(f"Created: {model.created_at}")
                click.echo(f"Updated: {model.updated_at}")

        except Exception as e:
            click.secho(f"❌ Failed to get model: {e}", fg="red")
            sys.exit(1)

    asyncio.run(show())


@models.command("update")
@click.argument("model_id")
@click.option("--name", help="New model name")
@click.option("--description", help="New description")
@click.option("--accuracy", type=float, help="New accuracy score")
@click.pass_context
def update_model(
    ctx, model_id: str, name: str | None, description: str | None, accuracy: float | None
):
    """Update ML model"""

    async def update():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                ml_service = MLGovernanceService(client)

                update_data: dict[str, Any] = {}
                if name:
                    update_data["name"] = name
                if description:
                    update_data["description"] = description
                if accuracy is not None:
                    update_data["accuracy_score"] = accuracy

                if not update_data:
                    click.secho("❌ No update parameters provided", fg="red")
                    return

                model = await ml_service.update_model(model_id, update_data)

                click.secho("✅ ML Model updated successfully!", fg="green")
                click.echo(f"Name: {model.name}")
                if model.accuracy_score:
                    click.echo(".2f")

        except Exception as e:
            click.secho(f"❌ Failed to update model: {e}", fg="red")
            sys.exit(1)

    asyncio.run(update())


@models.command("delete")
@click.argument("model_id")
@click.option("--force", is_flag=True, help="Force deletion without confirmation")
@click.pass_context
def delete_model(ctx, model_id: str, force: bool):
    """Delete ML model"""

    if not force and not click.confirm(f"Are you sure you want to delete model {model_id}?"):
        return

    async def delete():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                ml_service = MLGovernanceService(client)

                await ml_service.delete_model(model_id)

                click.secho("🗑️  ML Model deleted successfully!", fg="red")

        except Exception as e:
            click.secho(f"❌ Failed to delete model: {e}", fg="red")
            sys.exit(1)

    asyncio.run(delete())


@models.command("drift")
@click.argument("model_id")
@click.pass_context
def check_drift(ctx, model_id: str):
    """Check model drift"""

    async def check():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                ml_service = MLGovernanceService(client)

                drift = await ml_service.check_drift(model_id)

                click.secho("📈 Model Drift Analysis", fg="blue", bold=True)
                click.echo(".3f")
                click.echo(f"Direction: {drift.drift_direction}")
                click.echo(".2f")
                click.echo(".2f")
                click.echo(f"Detected: {drift.detected_at}")
                if drift.recommendations:
                    click.echo("\n💡 Recommendations:")
                    for rec in drift.recommendations:
                        click.echo(f"  • {rec}")

        except Exception as e:
            click.secho(f"❌ Failed to check drift: {e}", fg="red")
            sys.exit(1)

    asyncio.run(check())


@models.command("retrain")
@click.argument("model_id")
@click.option("--threshold", type=int, help="Feedback threshold for retraining")
@click.pass_context
def retrain_model(ctx, model_id: str, threshold: int | None):
    """Trigger model retraining"""

    async def retrain():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                ml_service = MLGovernanceService(client)

                result = await ml_service.retrain_model(model_id, threshold)

                click.secho("🔄 Model retraining initiated!", fg="green")
                for key, value in result.items():
                    click.echo(f"{key}: {value}")

        except Exception as e:
            click.secho(f"❌ Failed to retrain model: {e}", fg="red")
            sys.exit(1)

    asyncio.run(retrain())


@ml.command("predict")
@click.argument("model_id")
@click.option("--features", required=True, help="JSON features for prediction")
@click.option("--confidence", is_flag=True, help="Include confidence score")
@click.pass_context
def predict(ctx, model_id: str, features: str, confidence: bool):
    """Make a prediction with an ML model"""

    async def make_prediction():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                ml_service = MLGovernanceService(client)

                features_data = json.loads(features)

                prediction = await ml_service.make_prediction(
                    {
                        "model_id": model_id,
                        "features": features_data,
                        "include_confidence": confidence,
                    }
                )

                click.secho("🎯 Prediction Result", fg="green", bold=True)
                click.echo(f"Prediction: {prediction.prediction}")
                click.echo(f"Model: {prediction.model_id} v{prediction.model_version}")
                if prediction.confidence_score:
                    click.echo(".2f")
                click.echo(f"Timestamp: {prediction.timestamp}")

        except Exception as e:
            click.secho(f"❌ Failed to make prediction: {e}", fg="red")
            sys.exit(1)

    asyncio.run(make_prediction())


@ml.command("feedback")
@click.argument("model_id")
@click.option("--prediction-id", help="Prediction ID to correct")
@click.option(
    "--type", "feedback_type", required=True, help="Feedback type (correction, rating, explanation)"
)
@click.option("--value", required=True, help="Feedback value")
@click.option("--user", help="User ID providing feedback")
@click.pass_context
def submit_feedback(
    ctx,
    model_id: str,
    prediction_id: str | None,
    feedback_type: str,
    value: str,
    user: str | None,
):
    """Submit feedback for model improvement"""

    async def submit():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                ml_service = MLGovernanceService(client)

                # Parse feedback value (could be string, number, or JSON)
                try:
                    feedback_value = json.loads(value)
                except json.JSONDecodeError:
                    feedback_value = value

                feedback_data = {
                    "model_id": model_id,
                    "feedback_type": feedback_type,
                    "feedback_value": feedback_value,
                }
                if prediction_id:
                    feedback_data["prediction_id"] = prediction_id
                if user:
                    feedback_data["user_id"] = user

                feedback = await ml_service.submit_feedback(feedback_data)

                click.secho("💬 Feedback submitted successfully!", fg="green")
                click.echo(f"ID: {feedback.id}")
                click.echo(f"Type: {feedback.feedback_type}")
                click.echo(f"Submitted: {feedback.submitted_at}")

        except Exception as e:
            click.secho(f"❌ Failed to submit feedback: {e}", fg="red")
            sys.exit(1)

    asyncio.run(submit())


@ml.group()
@click.pass_context
def abtests(ctx):
    """A/B test management"""
    pass


@abtests.command("create")
@click.option("--name", required=True, help="A/B test name")
@click.option("--model-a", required=True, help="Model A ID")
@click.option("--model-b", required=True, help="Model B ID")
@click.option("--duration", type=int, required=True, help="Test duration in days")
@click.option(
    "--split", type=float, default=50.0, help="Traffic split percentage for A (default: 50)"
)
@click.option("--metric", required=True, help="Success metric")
@click.option("--description", help="Test description")
@click.pass_context
def create_ab_test(
    ctx,
    name: str,
    model_a: str,
    model_b: str,
    duration: int,
    split: float,
    metric: str,
    description: str | None,
):
    """Create an A/B test"""

    async def create():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                ml_service = MLGovernanceService(client)

                test_data = {
                    "name": name,
                    "model_a_id": model_a,
                    "model_b_id": model_b,
                    "test_duration_days": duration,
                    "traffic_split_percentage": split,
                    "success_metric": metric,
                }
                if description:
                    test_data["description"] = description

                ab_test = await ml_service.create_ab_test(test_data)

                click.secho("🆚 A/B Test created successfully!", fg="green")
                click.echo(f"ID: {ab_test.id}")
                click.echo(f"Name: {ab_test.name}")
                click.echo(f"Models: {ab_test.model_a_id} vs {ab_test.model_b_id}")
                click.echo(f"Duration: {ab_test.test_duration_days} days")
                click.echo(f"Traffic Split: {ab_test.traffic_split_percentage}%")
                click.echo(f"Status: {ab_test.status}")

        except Exception as e:
            click.secho(f"❌ Failed to create A/B test: {e}", fg="red")
            sys.exit(1)

    asyncio.run(create())


@abtests.command("list")
@click.option("--limit", type=int, default=20, help="Number of results to show")
@click.pass_context
def list_ab_tests(ctx, limit: int):
    """List A/B tests"""

    async def list():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                ml_service = MLGovernanceService(client)

                tests = await ml_service.list_ab_tests(page_size=limit)

                click.secho(f"🆚 A/B Tests ({tests.total})", fg="blue", bold=True)

                if not tests.data:
                    click.echo("No A/B tests found.")
                    return

                for test in tests.data:
                    status_color = {
                        "active": "green",
                        "completed": "blue",
                        "paused": "yellow",
                        "cancelled": "red",
                    }.get(test.status, "white")

                    click.secho(f"• {test.id}", fg=status_color, nl=False)
                    click.echo(
                        f" | {test.name} | {test.model_a_id} vs {test.model_b_id} | {test.status}"
                    )

        except Exception as e:
            click.secho(f"❌ Failed to list A/B tests: {e}", fg="red")
            sys.exit(1)

    asyncio.run(list())


@abtests.command("results")
@click.argument("test_id")
@click.pass_context
def get_ab_test_results(ctx, test_id: str):
    """Get A/B test results"""

    async def get_results():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                ml_service = MLGovernanceService(client)

                results = await ml_service.get_ab_test_results(test_id)

                click.secho(f"📊 A/B Test Results: {test_id}", fg="blue", bold=True)
                for key, value in results.items():
                    if isinstance(value, (int, float)):
                        click.echo(f"{key}: {value}")
                    else:
                        click.echo(f"{key}: {json.dumps(value, indent=2)}")

        except Exception as e:
            click.secho(f"❌ Failed to get test results: {e}", fg="red")
            sys.exit(1)

    asyncio.run(get_results())


@abtests.command("stop")
@click.argument("test_id")
@click.pass_context
def stop_ab_test(ctx, test_id: str):
    """Stop an A/B test"""

    async def stop():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                ml_service = MLGovernanceService(client)

                test = await ml_service.stop_ab_test(test_id)

                click.secho("⏹️  A/B Test stopped successfully!", fg="yellow")
                click.echo(f"ID: {test.id}")
                click.echo(f"Status: {test.status}")

        except Exception as e:
            click.secho(f"❌ Failed to stop A/B test: {e}", fg="red")
            sys.exit(1)

    asyncio.run(stop())


@ml.command("dashboard")
@click.pass_context
def dashboard(ctx):
    """Show ML governance dashboard"""

    async def show_dashboard():
        try:
            sdk_config = ctx.obj["sdk_config"]
            async with create_client(sdk_config) as client:
                ml_service = MLGovernanceService(client)

                dashboard_data = await ml_service.get_dashboard_data()

                click.secho("📊 ML Governance Dashboard", fg="blue", bold=True)
                for section, data in dashboard_data.items():
                    click.echo(f"\n{section.upper()}:")
                    if isinstance(data, dict):
                        for key, value in data.items():
                            click.echo(f"  {key}: {value}")
                    else:
                        click.echo(f"  {data}")

        except Exception as e:
            click.secho(f"❌ Failed to get dashboard data: {e}", fg="red")
            sys.exit(1)

    asyncio.run(show_dashboard())
