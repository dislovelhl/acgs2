"""
ACGS-2 Dynamic Constraint Updater
基于实时反馈动态调整CFG约束
"""

import logging
from typing import Dict, Any, List, Optional, TYPE_CHECKING
from datetime import datetime, timedelta, timezone
from collections import defaultdict
import json

if TYPE_CHECKING:
    from constraint_generator import GenerationRequest, GenerationResult

logger = logging.getLogger(__name__)


class DynamicConstraintUpdater:
    """
    动态约束更新器 - 基于反馈实时调整约束
    """

    def __init__(self,
                 feedback_window_hours: int = 24,
                 min_feedback_samples: int = 10,
                 update_threshold: float = 0.1):
        """
        初始化动态更新器

        Args:
            feedback_window_hours: 反馈时间窗口（小时）
            min_feedback_samples: 最少反馈样本数
            update_threshold: 更新阈值（性能变化百分比）
        """
        self.feedback_window = timedelta(hours=feedback_window_hours)
        self.min_samples = min_feedback_samples
        self.update_threshold = update_threshold

        # 存储反馈数据
        self.feedback_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

        # 动态约束调整
        self.dynamic_constraints: Dict[str, Dict[str, Any]] = defaultdict(dict)

        # 性能指标
        self.performance_metrics: Dict[str, Dict[str, float]] = defaultdict(dict)

        logger.info("DynamicConstraintUpdater initialized")

    async def update_constraints(self, request: "GenerationRequest", result: "GenerationResult"):
        """
        基于生成结果更新约束

        Args:
            request: 生成请求
            result: 生成结果
        """
        language = request.language.lower()
        timestamp = datetime.now(timezone.utc)

        # 记录反馈
        feedback_entry = {
            'timestamp': timestamp,
            'task': request.task_description,
            'syntax_valid': result.syntax_valid,
            'quality_score': result.quality_score,
            'generation_time': result.generation_time,
            'constraint_violations': result.constraint_violations,
            'feedback_data': result.feedback_data
        }

        self.feedback_history[language].append(feedback_entry)

        # 清理过期反馈
        self._cleanup_old_feedback(language)

        # 分析性能并更新约束
        if len(self.feedback_history[language]) >= self.min_samples:
            await self._analyze_and_update_constraints(language)

    def get_dynamic_constraints(self, language: str) -> Dict[str, Any]:
        """
        获取语言的动态约束

        Args:
            language: 编程语言

        Returns:
            动态约束字典
        """
        return self.dynamic_constraints.get(language.lower(), {})

    async def process_feedback(self, feedback: Dict[str, Any]):
        """
        处理外部反馈

        Args:
            feedback: 反馈数据
        """
        language = feedback.get('language', 'unknown').lower()
        timestamp = datetime.now(timezone.utc)

        feedback_entry = {
            'timestamp': timestamp,
            'external_feedback': True,
            **feedback
        }

        self.feedback_history[language].append(feedback_entry)
        self._cleanup_old_feedback(language)

        if len(self.feedback_history[language]) >= self.min_samples:
            await self._analyze_and_update_constraints(language)

    def _cleanup_old_feedback(self, language: str):
        """清理过期反馈"""
        cutoff_time = datetime.now(timezone.utc) - self.feedback_window
        self.feedback_history[language] = [
            entry for entry in self.feedback_history[language]
            if entry['timestamp'] > cutoff_time
        ]

    async def _analyze_and_update_constraints(self, language: str):
        """
        分析反馈并更新约束

        Args:
            language: 编程语言
        """
        feedback = self.feedback_history[language]

        # 计算性能指标
        metrics = self._calculate_performance_metrics(feedback)

        # 检查是否需要更新
        if self._should_update_constraints(language, metrics):
            # 生成新的约束调整
            constraint_updates = self._generate_constraint_updates(language, feedback, metrics)

            # 应用更新
            self.dynamic_constraints[language].update(constraint_updates)

            # 更新性能基准
            self.performance_metrics[language] = metrics

            logger.info(f"Updated dynamic constraints for {language}: {constraint_updates}")

    def _calculate_performance_metrics(self, feedback: List[Dict[str, Any]]) -> Dict[str, float]:
        """
        计算性能指标

        Args:
            feedback: 反馈列表

        Returns:
            性能指标字典
        """
        if not feedback:
            return {}

        total_samples = len(feedback)
        syntax_errors = sum(1 for f in feedback if not f.get('syntax_valid', True))
        quality_scores = [f.get('quality_score', 0) for f in feedback if f.get('quality_score') is not None]
        generation_times = [f.get('generation_time', 0) for f in feedback if f.get('generation_time', 0) > 0]

        metrics = {
            'syntax_error_rate': syntax_errors / total_samples,
            'avg_quality_score': sum(quality_scores) / len(quality_scores) if quality_scores else 0,
            'avg_generation_time': sum(generation_times) / len(generation_times) if generation_times else 0,
            'total_samples': total_samples
        }

        return metrics

    def _should_update_constraints(self, language: str, new_metrics: Dict[str, float]) -> bool:
        """
        判断是否应该更新约束

        Args:
            language: 编程语言
            new_metrics: 新性能指标

        Returns:
            是否需要更新
        """
        old_metrics = self.performance_metrics.get(language, {})

        if not old_metrics:
            return True  # 首次更新

        # 检查关键指标变化
        key_metrics = ['syntax_error_rate', 'avg_quality_score']

        for metric in key_metrics:
            if metric in new_metrics and metric in old_metrics:
                old_value = old_metrics[metric]
                new_value = new_metrics[metric]

                if old_value > 0:
                    change_ratio = abs(new_value - old_value) / old_value
                    if change_ratio > self.update_threshold:
                        return True

        return False

    def _generate_constraint_updates(self,
                                   language: str,
                                   feedback: List[Dict[str, Any]],
                                   metrics: Dict[str, float]) -> Dict[str, Any]:
        """
        生成约束更新

        Args:
            language: 编程语言
            feedback: 反馈列表
            metrics: 性能指标

        Returns:
            约束更新字典
        """
        updates = {}

        # 基于语法错误率调整
        syntax_error_rate = metrics.get('syntax_error_rate', 0)
        if syntax_error_rate > 0.1:  # 高于10%的错误率
            updates['strict_syntax_check'] = True
            updates['max_complexity'] = max(1, updates.get('max_complexity', 5) - 1)
        elif syntax_error_rate < 0.01:  # 低于1%的错误率
            updates['strict_syntax_check'] = False
            updates['max_complexity'] = min(10, updates.get('max_complexity', 5) + 1)

        # 基于质量分数调整
        avg_quality = metrics.get('avg_quality_score', 0)
        if avg_quality < 6.0:  # 质量较低
            updates['require_docstrings'] = True
            updates['require_type_hints'] = True
            updates['min_comment_ratio'] = 0.1
        elif avg_quality > 8.0:  # 质量较高
            updates['require_docstrings'] = False
            updates['require_type_hints'] = False
            updates['min_comment_ratio'] = 0.05

        # 基于生成时间调整
        avg_time = metrics.get('avg_generation_time', 0)
        if avg_time > 10.0:  # 生成太慢
            updates['max_tokens'] = max(1000, updates.get('max_tokens', 2000) - 500)
            updates['simplify_constraints'] = True
        elif avg_time < 2.0:  # 生成太快，可能质量不足
            updates['max_tokens'] = min(4000, updates.get('max_tokens', 2000) + 500)
            updates['add_quality_checks'] = True

        # 分析常见约束违反
        violations = []
        for f in feedback:
            violations.extend(f.get('constraint_violations', []))

        if violations:
            common_violations = self._find_common_violations(violations)
            updates['additional_forbidden_patterns'] = common_violations

        return updates

    def _find_common_violations(self, violations: List[str]) -> List[str]:
        """
        找出常见约束违反

        Args:
            violations: 违反列表

        Returns:
            常见违反模式
        """
        from collections import Counter

        # 统计违反频率
        violation_counts = Counter(violations)

        # 返回最常见的违反（出现率>20%）
        total_violations = len(violations)
        common_violations = [
            violation for violation, count in violation_counts.items()
            if count / total_violations > 0.2
        ]

        return common_violations[:5]  # 最多5个

    def get_constraint_suggestions(self, language: str) -> Dict[str, Any]:
        """
        获取约束建议

        Args:
            language: 编程语言

        Returns:
            建议的约束调整
        """
        feedback = self.feedback_history.get(language.lower(), [])
        if len(feedback) < self.min_samples:
            return {'status': 'insufficient_data', 'samples_needed': self.min_samples - len(feedback)}

        metrics = self._calculate_performance_metrics(feedback)

        suggestions = {
            'status': 'ready',
            'current_metrics': metrics,
            'suggested_updates': self._generate_constraint_updates(language, feedback, metrics),
            'confidence': min(1.0, len(feedback) / (self.min_samples * 2))
        }

        return suggestions

    def export_feedback_data(self, language: str) -> str:
        """
        导出反馈数据为JSON

        Args:
            language: 编程语言

        Returns:
            JSON字符串
        """
        feedback = self.feedback_history.get(language.lower(), [])
        data = {
            'language': language,
            'export_time': datetime.now(timezone.utc).isoformat(),
            'feedback_count': len(feedback),
            'feedback': feedback,
            'dynamic_constraints': self.dynamic_constraints.get(language.lower(), {}),
            'performance_metrics': self.performance_metrics.get(language.lower(), {})
        }

        return json.dumps(data, indent=2, default=str)

    def import_feedback_data(self, json_data: str):
        """
        导入反馈数据

        Args:
            json_data: JSON字符串
        """
        try:
            data = json.loads(json_data)
            language = data.get('language', 'unknown').lower()

            # 合并反馈历史
            existing_feedback = self.feedback_history[language]
            imported_feedback = data.get('feedback', [])

            # 避免重复
            existing_timestamps = {f['timestamp'] for f in existing_feedback}
            new_feedback = [
                f for f in imported_feedback
                if f['timestamp'] not in existing_timestamps
            ]

            self.feedback_history[language].extend(new_feedback)

            # 导入约束和指标
            if 'dynamic_constraints' in data:
                self.dynamic_constraints[language].update(data['dynamic_constraints'])

            if 'performance_metrics' in data:
                self.performance_metrics[language].update(data['performance_metrics'])

            logger.info(f"Imported {len(new_feedback)} feedback entries for {language}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to import feedback data: {e}")

    def reset_language_data(self, language: str):
        """
        重置语言数据

        Args:
            language: 编程语言
        """
        language = language.lower()
        self.feedback_history[language].clear()
        self.dynamic_constraints[language].clear()
        self.performance_metrics[language].clear()

        logger.info(f"Reset all data for language: {language}")
