"""
ACGS-2 Feedback Loop
处理反馈并改进生成模型
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone
import json
import statistics

from .constraint_generator import GenerationResult

logger = logging.getLogger(__name__)


class FeedbackLoop:
    """
    反馈循环 - 收集反馈并改进生成模型
    """

    def __init__(self,
                 feedback_window_hours: int = 168,  # 一周
                 min_samples_for_training: int = 100,
                 improvement_threshold: float = 0.05):
        """
        初始化反馈循环

        Args:
            feedback_window_hours: 反馈收集时间窗口
            min_samples_for_training: 最少训练样本数
            improvement_threshold: 改进阈值
        """
        self.feedback_window = timedelta(hours=feedback_window_hours)
        self.min_samples = min_samples_for_training
        self.improvement_threshold = improvement_threshold

        # 反馈存储
        self.feedback_data: List[Dict[str, Any]] = []

        # 性能跟踪
        self.performance_history: List[Dict[str, Any]] = []

        # 改进建议
        self.improvement_suggestions: List[Dict[str, Any]] = []

        logger.info("FeedbackLoop initialized")

    async def process_feedback(self, request: Dict[str, Any], result: GenerationResult) -> Optional[Dict[str, Any]]:
        """
        处理生成结果的反馈

        Args:
            request: 生成请求
            result: 生成结果

        Returns:
            反馈数据
        """
        feedback_entry = {
            'timestamp': datetime.now(timezone.utc),
            'request': request,
            'result': {
                'syntax_valid': result.syntax_valid,
                'quality_score': result.quality_score,
                'generation_time': result.generation_time,
                'constraint_violations': result.constraint_violations
            },
            'feedback_type': 'automatic'
        }

        self.feedback_data.append(feedback_entry)

        # 清理过期反馈
        self._cleanup_old_feedback()

        # 分析反馈并生成改进建议
        if len(self.feedback_data) >= self.min_samples:
            suggestions = await self._analyze_feedback_and_suggest_improvements()
            if suggestions:
                self.improvement_suggestions.extend(suggestions)
                return {'suggestions': suggestions, 'feedback_count': len(self.feedback_data)}

        return None

    def add_manual_feedback(self, feedback: Dict[str, Any]):
        """
        添加手动反馈

        Args:
            feedback: 手动反馈数据
        """
        feedback_entry = {
            'timestamp': datetime.now(timezone.utc),
            'feedback_type': 'manual',
            **feedback
        }

        self.feedback_data.append(feedback_entry)
        self._cleanup_old_feedback()

        logger.info("Manual feedback added")

    def _cleanup_old_feedback(self):
        """清理过期反馈"""
        cutoff_time = datetime.now(timezone.utc) - self.feedback_window
        self.feedback_data = [
            entry for entry in self.feedback_data
            if entry['timestamp'] > cutoff_time
        ]

    async def _analyze_feedback_and_suggest_improvements(self) -> List[Dict[str, Any]]:
        """
        分析反馈并生成改进建议

        Returns:
            改进建议列表
        """
        suggestions = []

        # 分析语法错误率
        syntax_analysis = self._analyze_syntax_errors()
        if syntax_analysis['needs_improvement']:
            suggestions.append({
                'type': 'syntax_improvement',
                'priority': 'high',
                'description': f"语法错误率过高 ({syntax_analysis['error_rate']:.2%})",
                'suggested_actions': syntax_analysis['actions'],
                'expected_impact': '减少80%的语法错误'
            })

        # 分析质量分数
        quality_analysis = self._analyze_quality_scores()
        if quality_analysis['needs_improvement']:
            suggestions.append({
                'type': 'quality_improvement',
                'priority': 'medium',
                'description': f"代码质量需要提升 (当前平均分: {quality_analysis['avg_score']:.2f})",
                'suggested_actions': quality_analysis['actions'],
                'expected_impact': '提高代码质量评分至8.0+'
            })

        # 分析生成时间
        timing_analysis = self._analyze_generation_timing()
        if timing_analysis['needs_improvement']:
            suggestions.append({
                'type': 'performance_improvement',
                'priority': 'low',
                'description': f"生成时间过长 (平均: {timing_analysis['avg_time']:.2f}s)",
                'suggested_actions': timing_analysis['actions'],
                'expected_impact': '减少30%的生成时间'
            })

        # 分析约束违反模式
        constraint_analysis = self._analyze_constraint_violations()
        if constraint_analysis['common_violations']:
            suggestions.append({
                'type': 'constraint_enhancement',
                'priority': 'medium',
                'description': f"发现常见约束违反模式",
                'suggested_actions': constraint_analysis['actions'],
                'expected_impact': '减少约束违反50%'
            })

        # 分析语言特定问题
        language_analysis = self._analyze_language_specific_issues()
        for lang_suggestion in language_analysis:
            suggestions.append(lang_suggestion)

        return suggestions

    def _analyze_syntax_errors(self) -> Dict[str, Any]:
        """分析语法错误"""
        total_samples = len(self.feedback_data)
        syntax_errors = sum(1 for f in self.feedback_data if not f['result']['syntax_valid'])

        error_rate = syntax_errors / total_samples if total_samples > 0 else 0

        needs_improvement = error_rate > 0.005  # 0.5%的错误率阈值

        actions = []
        if needs_improvement:
            actions.extend([
                "加强语法约束检查",
                "更新CFG语法规则",
                "增加语法验证步骤",
                "改进错误恢复机制"
            ])

        return {
            'error_rate': error_rate,
            'needs_improvement': needs_improvement,
            'actions': actions
        }

    def _analyze_quality_scores(self) -> Dict[str, Any]:
        """分析质量分数"""
        quality_scores = [
            f['result']['quality_score'] for f in self.feedback_data
            if f['result']['quality_score'] is not None
        ]

        if not quality_scores:
            return {'needs_improvement': False, 'avg_score': 0, 'actions': []}

        avg_score = statistics.mean(quality_scores)
        needs_improvement = avg_score < 7.0  # 质量阈值

        actions = []
        if needs_improvement:
            actions.extend([
                "启用SonarQube深度分析",
                "加强代码风格检查",
                "增加最佳实践验证",
                "改进文档生成"
            ])

        return {
            'avg_score': avg_score,
            'needs_improvement': needs_improvement,
            'actions': actions
        }

    def _analyze_generation_timing(self) -> Dict[str, Any]:
        """分析生成时间"""
        generation_times = [
            f['result']['generation_time'] for f in self.feedback_data
            if f['result']['generation_time'] > 0
        ]

        if not generation_times:
            return {'needs_improvement': False, 'avg_time': 0, 'actions': []}

        avg_time = statistics.mean(generation_times)
        needs_improvement = avg_time > 5.0  # 5秒阈值

        actions = []
        if needs_improvement:
            actions.extend([
                "优化约束检查算法",
                "减少不必要的验证步骤",
                "改进缓存机制",
                "使用更快的语法分析器"
            ])

        return {
            'avg_time': avg_time,
            'needs_improvement': needs_improvement,
            'actions': actions
        }

    def _analyze_constraint_violations(self) -> Dict[str, Any]:
        """分析约束违反"""
        all_violations = []
        for f in self.feedback_data:
            all_violations.extend(f['result']['constraint_violations'] or [])

        if not all_violations:
            return {'common_violations': [], 'actions': []}

        # 统计常见违反
        from collections import Counter
        violation_counts = Counter(all_violations)
        common_violations = [
            violation for violation, count in violation_counts.items()
            if count / len(all_violations) > 0.1  # 10%以上
        ]

        actions = []
        for violation in common_violations:
            actions.append(f"添加针对'{violation}'的约束规则")

        return {
            'common_violations': common_violations,
            'actions': actions
        }

    def _analyze_language_specific_issues(self) -> List[Dict[str, Any]]:
        """分析语言特定问题"""
        suggestions = []

        # 按语言分组反馈
        language_feedback = {}
        for f in self.feedback_data:
            language = f.get('request', {}).get('language', 'unknown')
            if language not in language_feedback:
                language_feedback[language] = []
            language_feedback[language].append(f)

        for language, feedbacks in language_feedback.items():
            if len(feedbacks) < 10:  # 最少10个样本
                continue

            # 计算语言特定的指标
            syntax_errors = sum(1 for f in feedbacks if not f['result']['syntax_valid'])
            error_rate = syntax_errors / len(feedbacks)

            if error_rate > 0.01:  # 1%的语言特定错误率
                suggestions.append({
                    'type': 'language_specific_improvement',
                    'priority': 'medium',
                    'description': f"{language}语言语法错误率较高 ({error_rate:.2%})",
                    'suggested_actions': [
                        f"改进{language}语法约束",
                        f"更新{language}CFG规则",
                        f"为{language}添加专门的验证器"
                    ],
                    'expected_impact': f"减少{language}语法错误80%"
                })

        return suggestions

    def get_feedback_summary(self) -> Dict[str, Any]:
        """
        获取反馈摘要

        Returns:
            反馈统计摘要
        """
        if not self.feedback_data:
            return {'status': 'no_data'}

        total_samples = len(self.feedback_data)
        syntax_valid = sum(1 for f in self.feedback_data if f['result']['syntax_valid'])
        quality_scores = [
            f['result']['quality_score'] for f in self.feedback_data
            if f['result']['quality_score'] is not None
        ]

        summary = {
            'total_samples': total_samples,
            'syntax_success_rate': syntax_valid / total_samples,
            'avg_quality_score': statistics.mean(quality_scores) if quality_scores else None,
            'avg_generation_time': statistics.mean([
                f['result']['generation_time'] for f in self.feedback_data
                if f['result']['generation_time'] > 0
            ]) if any(f['result']['generation_time'] > 0 for f in self.feedback_data) else None,
            'improvement_suggestions_count': len(self.improvement_suggestions),
            'feedback_window_hours': self.feedback_window.total_seconds() / 3600
        }

        return summary

    def export_feedback_for_training(self, language: Optional[str] = None) -> str:
        """
        导出反馈数据用于模型训练

        Args:
            language: 可选的语言过滤

        Returns:
            JSON格式的训练数据
        """
        training_data = []

        for feedback in self.feedback_data:
            if language and feedback.get('request', {}).get('language') != language:
                continue

            # 转换为训练格式
            training_entry = {
                'input': feedback.get('request', {}),
                'output': {
                    'code': 'generated_code_placeholder',  # 在实际使用中需要原始代码
                    'quality_score': feedback['result']['quality_score'],
                    'syntax_valid': feedback['result']['syntax_valid']
                },
                'feedback': {
                    'violations': feedback['result']['constraint_violations'],
                    'timestamp': feedback['timestamp'].isoformat()
                }
            }

            training_data.append(training_entry)

        return json.dumps(training_data, indent=2, default=str)

    def get_improvement_recommendations(self) -> List[Dict[str, Any]]:
        """
        获取改进建议

        Returns:
            改进建议列表
        """
        return self.improvement_suggestions.copy()

    def clear_old_suggestions(self, days: int = 7):
        """
        清理旧的改进建议

        Args:
            days: 保留天数
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(days=days)
        self.improvement_suggestions = [
            s for s in self.improvement_suggestions
            if s.get('timestamp', datetime.now(timezone.utc)) > cutoff_time
        ]

    def get_performance_trends(self) -> Dict[str, Any]:
        """
        获取性能趋势

        Returns:
            性能趋势分析
        """
        if len(self.performance_history) < 2:
            return {'status': 'insufficient_data'}

        # 计算趋势
        recent = self.performance_history[-10:]  # 最近10个数据点
        older = self.performance_history[-20:-10] if len(self.performance_history) >= 20 else []

        trends = {}

        if older:
            for metric in ['syntax_success_rate', 'avg_quality_score', 'avg_generation_time']:
                recent_avg = statistics.mean([p.get(metric, 0) for p in recent if p.get(metric) is not None])
                older_avg = statistics.mean([p.get(metric, 0) for p in older if p.get(metric) is not None])

                if older_avg > 0:
                    change = (recent_avg - older_avg) / older_avg
                    trends[metric] = {
                        'change_percent': change * 100,
                        'improving': change > 0 if metric != 'avg_generation_time' else change < 0
                    }

        return {
            'trends': trends,
            'data_points': len(self.performance_history)
        }