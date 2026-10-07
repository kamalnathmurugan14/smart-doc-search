"""Score fusion. min-max normalise each list, then blend."""

import numpy as np


def min_max(x: np.ndarray) -> np.ndarray:
    """Scale to [0,1]. If all values are equal the signal carries no ranking info -> zeros."""
    if x.size == 0:
        return x
    lo, hi = float(x.min()), float(x.max())
    if hi - lo < 1e-12:
        return np.zeros_like(x, dtype=float)
    return (x - lo) / (hi - lo)


def blend(keyword: np.ndarray, semantic: np.ndarray, alpha: float) -> np.ndarray:
    return alpha * min_max(semantic) + (1 - alpha) * min_max(keyword)
