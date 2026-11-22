# Author: Juan-Louw Greyling <juanlouw.greyling@gmail.com>
"""Nearest-neighbour recommender (from services/autonomous-ai RecommendationEngine)
implemented with numpy so it needs no scikit-learn/pandas."""
import numpy as np


class Recommender:
    def __init__(self) -> None:
        self.items = np.empty((0, 0))
        self.labels: list[str] = []

    def fit(self, rows: list[list[float]], labels: list[str] | None = None) -> None:
        self.items = np.asarray(rows, dtype=float)
        self.labels = labels or [str(i) for i in range(len(rows))]

    def recommend(self, query: list[float], k: int = 3) -> list[dict]:
        if not len(self.items):
            raise ValueError("fit() first")
        d = np.linalg.norm(self.items - np.asarray(query, dtype=float), axis=1)
        idx = np.argsort(d)[:k]
        return [{"item": self.labels[i], "index": int(i), "distance": float(d[i])} for i in idx]
