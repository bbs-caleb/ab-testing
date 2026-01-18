"""
Deterministic hash-based A/B split.

Why hash instead of random?
- User always sees same variant (no flickering)
- No need to store assignments in DB
- Reproducible across services
- Different salt = independent experiments
"""

import hashlib
from typing import List, Optional
import pandas as pd
import numpy as np


class ABSplitter:
    """
    Deterministic user assignment using SHA-256.
    
    Usage:
        splitter = ABSplitter(salt="my_experiment_2024")
        group = splitter.get_group(user_id=12345)  # Always same result
    """
    
    def __init__(self, salt: str = ""):
        """
        Args:
            salt: Unique experiment identifier. Different salt = different assignment.
        """
        self.salt = salt
    
    def _hash_to_float(self, value) -> float:
        """Convert any value to float in [0, 1) using SHA-256."""
        combined = f"{self.salt}_{value}"
        hash_bytes = hashlib.sha256(combined.encode()).digest()
        return int.from_bytes(hash_bytes[:8], 'big') / (2**64)
    
    def get_group(
        self, 
        user_id, 
        groups: List[str] = None,
        weights: List[float] = None
    ) -> str:
        """
        Get group for single user.
        
        Args:
            user_id: Any hashable value
            groups: Group names. Default ['control', 'test']
            weights: Split ratios. Default equal split
        """
        if groups is None:
            groups = ['control', 'test']
        if weights is None:
            weights = [1/len(groups)] * len(groups)
            
        if not np.isclose(sum(weights), 1.0):
            raise ValueError(f"Weights must sum to 1, got {sum(weights)}")
        
        bucket = self._hash_to_float(user_id)
        
        cumulative = 0.0
        for group, weight in zip(groups, weights):
            cumulative += weight
            if bucket < cumulative:
                return group
        return groups[-1]
    
    def assign_groups(
        self,
        df: pd.DataFrame,
        user_col: str,
        groups: List[str] = None,
        weights: List[float] = None
    ) -> pd.DataFrame:
        """Add 'group' column to DataFrame."""
        df = df.copy()
        df['group'] = df[user_col].apply(
            lambda uid: self.get_group(uid, groups, weights)
        )
        return df
    
    def check_distribution(self, df: pd.DataFrame, group_col: str = 'group') -> pd.DataFrame:
        """Show actual vs expected distribution."""
        counts = df[group_col].value_counts()
        total = len(df)
        return pd.DataFrame({
            'count': counts,
            'actual_pct': (counts / total * 100).round(2),
        })


def quick_split(df: pd.DataFrame, user_col: str, salt: str, test_pct: float = 0.5) -> pd.DataFrame:
    """
    One-liner for simple 50/50 split.
    
    Example:
        df = quick_split(df, 'user_id', 'pricing_test')
    """
    splitter = ABSplitter(salt=salt)
    return splitter.assign_groups(
        df, user_col, 
        groups=['control', 'test'],
        weights=[1-test_pct, test_pct]
    )


# Demo
if __name__ == "__main__":
    # Test determinism
    splitter = ABSplitter(salt="demo_test")
    
    print("Testing determinism:")
    for _ in range(3):
        print(f"  user_12345 -> {splitter.get_group(12345)}")
    
    # Test distribution
    df = pd.DataFrame({'user_id': range(10000)})
    df = splitter.assign_groups(df, 'user_id')
    
    print("\nDistribution check:")
    print(splitter.check_distribution(df))
