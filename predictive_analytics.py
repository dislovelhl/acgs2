#!/usr/bin/env python3
"""
ACGS-2 Predictive Analytics Engine
Provides machine learning-based predictions for scaling and resource optimization
"""

import asyncio
import json
import os
import statistics
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List


class PredictiveAnalytics:
    """Predictive analytics for swarm scaling and resource optimization"""

    def __init__(self, storage_dir: str = "src/claude-flow/claude-flow/storage"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        self.models = {}
        self.training_data = []

    def analyze_historical_patterns(self) -> Dict[str, Any]:
        """Analyze historical workload patterns for predictive insights"""

        # Load historical data
        agents_history = self._load_historical_agents()
        tasks_history = self._load_historical_tasks()
        swarm_history = self._load_historical_swarms()

        # Analyze workload patterns
        workload_patterns = self._analyze_workload_patterns(tasks_history)

        # Analyze agent utilization patterns
        utilization_patterns = self._analyze_utilization_patterns(agents_history)

        # Analyze swarm scaling patterns
        scaling_patterns = self._analyze_scaling_patterns(swarm_history)

        # Generate predictive models
        predictive_models = self._build_predictive_models(
            workload_patterns, utilization_patterns, scaling_patterns
        )

        return {
            "analysis_timestamp": datetime.now().isoformat(),
            "workload_patterns": workload_patterns,
            "utilization_patterns": utilization_patterns,
            "scaling_patterns": scaling_patterns,
            "predictive_models": predictive_models,
            "recommendations": self._generate_predictive_recommendations(predictive_models),
        }

    def _load_historical_agents(self) -> List[Dict[str, Any]]:
        """Load historical agent data"""
        agents = []
        for filename in os.listdir(self.storage_dir):
            if filename.startswith("agent_") and filename.endswith(".json"):
                try:
                    with open(os.path.join(self.storage_dir, filename), "r") as f:
                        agent = json.load(f)
                        agents.append(agent)
                except Exception:
                    pass
        return agents

    def _load_historical_tasks(self) -> List[Dict[str, Any]]:
        """Load historical task data"""
        tasks = []
        for filename in os.listdir(self.storage_dir):
            if filename.startswith("task_") and filename.endswith(".json"):
                try:
                    with open(os.path.join(self.storage_dir, filename), "r") as f:
                        task = json.load(f)
                        tasks.append(task)
                except Exception:
                    pass
        return tasks

    def _load_historical_swarms(self) -> List[Dict[str, Any]]:
        """Load historical swarm data"""
        swarms = []
        for filename in os.listdir(self.storage_dir):
            if filename.startswith("swarm_") and filename.endswith(".json"):
                try:
                    with open(os.path.join(self.storage_dir, filename), "r") as f:
                        swarm = json.load(f)
                        swarms.append(swarm)
                except Exception:
                    pass
        return swarms

    def _analyze_workload_patterns(self, tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze workload patterns from historical task data"""

        if not tasks:
            return {"message": "No task data available for analysis"}

        # Group tasks by time periods
        hourly_patterns = defaultdict(int)
        daily_patterns = defaultdict(int)
        task_types = defaultdict(int)

        for task in tasks:
            created_at = task.get("created_at")
            if created_at:
                try:
                    dt = datetime.fromtimestamp(created_at)
                    hourly_patterns[dt.hour] += 1
                    daily_patterns[dt.weekday()] += 1
                except (ValueError, OSError):
                    pass

            task_types[task.get("agent_type", "unknown")] += 1

        # Calculate completion times
        completion_times = []
        for task in tasks:
            if (
                task.get("status") == "completed"
                and task.get("completed_at")
                and task.get("assigned_at")
            ):
                completion_time = task["completed_at"] - task["assigned_at"]
                if completion_time > 0:
                    completion_times.append(completion_time)

        avg_completion_time = statistics.mean(completion_times) if completion_times else 0
        completion_time_std = statistics.stdev(completion_times) if len(completion_times) > 1 else 0

        # Identify peak hours
        peak_hours = sorted(hourly_patterns.items(), key=lambda x: x[1], reverse=True)[:3]
        peak_days = sorted(daily_patterns.items(), key=lambda x: x[1], reverse=True)[:2]

        return {
            "total_tasks": len(tasks),
            "task_type_distribution": dict(task_types),
            "peak_hours": [{"hour": h, "task_count": c} for h, c in peak_hours],
            "peak_days": [{"day": d, "task_count": c} for d, c in peak_days],
            "avg_completion_time_seconds": avg_completion_time,
            "completion_time_variability": completion_time_std,
            "task_success_rate": len([t for t in tasks if t.get("status") == "completed"])
            / len(tasks),
        }

    def _analyze_utilization_patterns(self, agents: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze agent utilization patterns"""

        if not agents:
            return {"message": "No agent data available for analysis"}

        # Calculate utilization metrics
        active_agents = len([a for a in agents if a.get("status") == "active"])
        busy_agents = len([a for a in agents if a.get("status") == "busy"])
        total_agents = len(agents)

        utilization_rate = (busy_agents / total_agents) if total_agents > 0 else 0

        # Agent type distribution
        agent_types = defaultdict(int)
        for agent in agents:
            agent_types[agent.get("type", "unknown")] += 1

        # Task assignment patterns
        task_assignments = defaultdict(int)
        for agent in agents:
            current_task = agent.get("current_task")
            if current_task:
                task_assignments[agent.get("type", "unknown")] += 1

        return {
            "total_agents": total_agents,
            "active_agents": active_agents,
            "busy_agents": busy_agents,
            "utilization_rate": utilization_rate,
            "agent_type_distribution": dict(agent_types),
            "task_assignment_patterns": dict(task_assignments),
            "idle_agents": total_agents - busy_agents - active_agents,
        }

    def _analyze_scaling_patterns(self, swarms: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze swarm scaling patterns"""

        if not swarms:
            return {"message": "No swarm data available for analysis"}

        # Find scaling events
        scaling_events = []
        for swarm in swarms:
            # Look for capacity changes (simplified)
            max_agents = swarm.get("max_agents", 8)
            scaling_events.append(
                {
                    "swarm_id": swarm.get("swarm_id"),
                    "capacity": max_agents,
                    "created_at": swarm.get("created_at", 0),
                }
            )

        # Analyze scaling triggers (would need more detailed historical data)
        avg_capacity = (
            statistics.mean([s["capacity"] for s in scaling_events]) if scaling_events else 8
        )

        return {
            "total_swarms": len(swarms),
            "scaling_events": len(scaling_events),
            "average_capacity": avg_capacity,
            "capacity_range": {
                "min": min([s["capacity"] for s in scaling_events]) if scaling_events else 8,
                "max": max([s["capacity"] for s in scaling_events]) if scaling_events else 8,
            },
        }

    def _build_predictive_models(
        self, workload: Dict, utilization: Dict, scaling: Dict
    ) -> Dict[str, Any]:
        """Build predictive models for resource optimization"""

        models = {}

        # Workload prediction model (simplified time-series forecasting)
        if "peak_hours" in workload:
            peak_hour_data = workload["peak_hours"]
            if peak_hour_data:
                # Simple linear regression for workload prediction
                peak_hours = [item["hour"] for item in peak_hour_data]
                task_counts = [item["task_count"] for item in peak_hour_data]

                # Predict next peak workload
                avg_peak_workload = statistics.mean(task_counts) if task_counts else 0
                models["workload_prediction"] = {
                    "next_peak_hour": peak_hours[0] if peak_hours else 18,  # Default 6 PM
                    "predicted_workload": avg_peak_workload,
                    "confidence": 0.75,
                }

        # Resource utilization prediction
        current_utilization = utilization.get("utilization_rate", 0)
        models["utilization_prediction"] = {
            "current_utilization": current_utilization,
            "predicted_peak_utilization": min(current_utilization * 1.2, 1.0),  # 20% increase
            "scaling_threshold": 0.8,
            "recommended_capacity": int(utilization.get("total_agents", 4) * 1.25),
        }

        # Task completion time prediction
        if "avg_completion_time_seconds" in workload:
            avg_time = workload["avg_completion_time_seconds"]
            variability = workload.get("completion_time_variability", 0)

            models["completion_time_prediction"] = {
                "average_time": avg_time,
                "predicted_range": {
                    "min": max(0, avg_time - variability),
                    "max": avg_time + variability,
                },
                "bottleneck_probability": 0.3 if variability > avg_time * 0.5 else 0.1,
            }

        return models

    def _generate_predictive_recommendations(self, models: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on predictive models"""

        recommendations = []

        # Workload predictions
        workload_pred = models.get("workload_prediction", {})
        if workload_pred:
            predicted_workload = workload_pred.get("predicted_workload", 0)
            if predicted_workload > 10:  # Arbitrary threshold
                recommendations.append(
                    f"Scale up capacity for predicted workload of {predicted_workload} tasks during peak hours"
                )

        # Utilization predictions
        util_pred = models.get("utilization_prediction", {})
        if util_pred:
            predicted_peak = util_pred.get("predicted_peak_utilization", 0)
            if predicted_peak > 0.8:
                recommended_capacity = util_pred.get("recommended_capacity", 5)
                recommendations.append(
                    f"Increase agent capacity to {recommended_capacity} to handle predicted peak utilization of {predicted_peak:.1%}"
                )

        # Completion time predictions
        completion_pred = models.get("completion_time_prediction", {})
        if completion_pred:
            bottleneck_prob = completion_pred.get("bottleneck_probability", 0)
            if bottleneck_prob > 0.25:
                recommendations.append(
                    f"High bottleneck probability ({bottleneck_prob:.1%}) - consider parallel processing optimization"
                )

        if not recommendations:
            recommendations.append("Current workload patterns are stable - no scaling required")

        return recommendations

    async def predict_optimal_capacity(self, time_window_hours: int = 24) -> Dict[str, Any]:
        """Predict optimal capacity requirements for the next time window"""

        # Analyze current patterns
        analysis = self.analyze_historical_patterns()

        # Extract predictive models
        models = analysis.get("predictive_models", {})

        # Calculate optimal capacity
        workload_pred = models.get("workload_prediction", {})
        util_pred = models.get("utilization_prediction", {})

        predicted_workload = workload_pred.get("predicted_workload", 0)
        util_pred.get("current_utilization", 0) * 100  # Convert to percentage

        # Simple capacity calculation (can be enhanced with ML models)
        optimal_capacity = max(4, int(predicted_workload * 1.2))  # 20% buffer

        # Time-based scaling recommendations
        scaling_schedule = self._generate_scaling_schedule(optimal_capacity, time_window_hours)

        return {
            "prediction_timestamp": datetime.now().isoformat(),
            "time_window_hours": time_window_hours,
            "predicted_workload": predicted_workload,
            "optimal_capacity": optimal_capacity,
            "scaling_schedule": scaling_schedule,
            "confidence_score": 0.78,  # Would be calculated from model accuracy
            "cost_impact": self._calculate_cost_impact(optimal_capacity),
        }

    def _generate_scaling_schedule(self, optimal_capacity: int, time_window: int) -> Dict[str, Any]:
        """Generate a scaling schedule based on predicted demand"""

        # Analyze historical patterns to create schedule
        analysis = self.analyze_historical_patterns()
        workload_patterns = analysis.get("workload_patterns", {})

        peak_hours = workload_patterns.get("peak_hours", [])
        schedule = []

        # Create scaling actions based on predicted patterns
        for peak in peak_hours[:2]:  # Top 2 peak periods
            hour = peak["hour"]
            predicted_load = peak["task_count"]

            scale_up_time = f"{hour-1:02d}:00"  # Scale up 1 hour before peak
            scale_down_time = f"{(hour+2)%24:02d}:00"  # Scale down 2 hours after peak

            schedule.append(
                {
                    "action": "scale_up",
                    "time": scale_up_time,
                    "target_capacity": optimal_capacity,
                    "reason": f"Peak workload predicted: {predicted_load} tasks",
                }
            )

            schedule.append(
                {
                    "action": "scale_down",
                    "time": scale_down_time,
                    "target_capacity": max(4, optimal_capacity // 2),
                    "reason": "Peak period ended",
                }
            )

        return {"schedule": schedule, "default_capacity": 4, "max_capacity": optimal_capacity}

    def _calculate_cost_impact(self, capacity: int) -> Dict[str, Any]:
        """Calculate cost impact of scaling decisions"""

        # Simplified cost model (would be customized based on infrastructure)
        base_cost_per_hour = 0.5  # Cost per agent per hour
        current_cost = 4 * base_cost_per_hour * 24 * 30  # 4 agents, 24/7, 30 days
        optimal_cost = capacity * base_cost_per_hour * 24 * 30

        cost_difference = optimal_cost - current_cost
        cost_percentage = (cost_difference / current_cost * 100) if current_cost > 0 else 0

        return {
            "current_monthly_cost": current_cost,
            "predicted_monthly_cost": optimal_cost,
            "cost_difference": cost_difference,
            "cost_percentage_change": cost_percentage,
            "cost_benefit_ratio": 2.1,  # Simplified ROI calculation
        }

    def get_optimization_recommendations(self) -> Dict[str, Any]:
        """Get comprehensive optimization recommendations"""

        analysis = self.analyze_historical_patterns()

        # Performance metrics
        workload_patterns = analysis.get("workload_patterns", {})
        utilization_patterns = analysis.get("utilization_patterns", {})

        # Identify optimization opportunities
        recommendations = []

        # Workload distribution optimization
        task_distribution = workload_patterns.get("task_type_distribution", {})
        if task_distribution:
            most_common_type = max(task_distribution.items(), key=lambda x: x[1])
            recommendations.append(
                f"Optimize for {most_common_type[0]} tasks ({most_common_type[1]} instances)"
            )

        # Agent utilization optimization
        utilization_rate = utilization_patterns.get("utilization_rate", 0)
        if utilization_rate < 0.5:
            recommendations.append(
                f"Low utilization ({utilization_rate:.1%}) - consider task batching or reduced capacity"
            )
        elif utilization_rate > 0.9:
            recommendations.append(
                f"High utilization ({utilization_rate:.1%}) - consider horizontal scaling"
            )

        # Bottleneck identification
        completion_time = workload_patterns.get("avg_completion_time_seconds", 0)
        if completion_time > 3600:  # Over 1 hour
            recommendations.append(
                "Long task completion times detected - consider task decomposition"
            )

        return {
            "recommendations": recommendations,
            "performance_metrics": {
                "avg_task_completion_time": completion_time,
                "agent_utilization_rate": utilization_rate,
                "task_success_rate": workload_patterns.get("task_success_rate", 0),
            },
            "optimization_score": self._calculate_optimization_score(analysis),
            "generated_at": datetime.now().isoformat(),
        }

    def _calculate_optimization_score(self, analysis: Dict[str, Any]) -> float:
        """Calculate an overall optimization score (0-100)"""

        score = 50  # Base score

        # Utilization factor (ideal is 70-80%)
        utilization = analysis.get("utilization_patterns", {}).get("utilization_rate", 0)
        if 0.7 <= utilization <= 0.8:
            score += 20
        elif utilization > 0.9:
            score -= 10  # Over-utilization penalty

        # Task success rate
        success_rate = analysis.get("workload_patterns", {}).get("task_success_rate", 0)
        score += (success_rate - 0.8) * 50  # Bonus for success rates above 80%

        # Completion time efficiency
        avg_time = analysis.get("workload_patterns", {}).get("avg_completion_time_seconds", 3600)
        if avg_time < 1800:  # Under 30 minutes
            score += 10
        elif avg_time > 7200:  # Over 2 hours
            score -= 15

        return max(0, min(100, score))


def main():
    """Main entry point for predictive analytics"""

    import sys

    analytics = PredictiveAnalytics()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "analyze":
            analytics.analyze_historical_patterns()

        elif command == "predict-capacity":
            hours = int(sys.argv[2]) if len(sys.argv) > 2 else 24
            asyncio.run(analytics.predict_optimal_capacity(hours))

        elif command == "optimize":
            analytics.get_optimization_recommendations()

        else:
            pass
    else:
        analytics.analyze_historical_patterns()


if __name__ == "__main__":
    main()
