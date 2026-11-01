"""Shared, cached dataset so every test uses the same (small, fast) generated data."""
import copy
from functools import lru_cache
from generator.build import generate_all
from generator.config import Config


@lru_cache(maxsize=None)
def dataset(employees=300, seed=20261022):
    return generate_all(Config(employees=employees, seed=seed))


def clone_tables(R):
    return {k: v.copy() for k, v in R["tables"].items()}
