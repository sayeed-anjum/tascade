from __future__ import annotations

import math
import statistics
from typing import Iterable, Optional


def clamp(value: float, lower: float = 0.0, upper: float = 1.0) -> float:
    return max(lower, min(upper, value))


def ratio_or_none(numerator: float, denominator: float) -> Optional[float]:
    if denominator == 0:
        return None
    return numerator / denominator


def mean(values: Iterable[float]) -> Optional[float]:
    values_list = list(values)
    if not values_list:
        return None
    return statistics.fmean(values_list)


def stddev(values: Iterable[float]) -> Optional[float]:
    values_list = list(values)
    if not values_list:
        return None
    if len(values_list) == 1:
        return 0.0
    return statistics.pstdev(values_list)


def percentile_cont(values: Iterable[float], percentile: float) -> Optional[float]:
    values_list = sorted(values)
    count = len(values_list)
    if count == 0:
        return None

    if percentile <= 0:
        return values_list[0]
    if percentile >= 1:
        return values_list[-1]

    position = 1 + (count - 1) * percentile
    lower_index = int(math.floor(position)) - 1
    upper_index = int(math.ceil(position)) - 1

    if lower_index == upper_index:
        return values_list[lower_index]

    lower_value = values_list[lower_index]
    upper_value = values_list[upper_index]
    fraction = position - math.floor(position)
    return lower_value + fraction * (upper_value - lower_value)
