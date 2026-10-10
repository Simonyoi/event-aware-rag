"""指标/事实抽取 + 时间标注。"""
from .metric_extractor import extract
from .time_annotator import guess_period, period_options

__all__ = ["extract", "guess_period", "period_options"]
