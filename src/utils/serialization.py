"""
Serialization utilities for converting NumPy types to native Python types.
"""

import numpy as np
import pandas as pd
from typing import Any, Dict, List, Union

def convert_to_serializable(obj: Any) -> Any:
    """
    Recursively convert NumPy/Pandas types to Python native types.
    
    Args:
        obj: Any object that might contain NumPy types
    
    Returns:
        Object with all NumPy types converted to Python native types
    """
    if isinstance(obj, dict):
        return {key: convert_to_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(convert_to_serializable(item) for item in obj)
    elif isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64, np.float32, np.float16)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, (np.bool_, bool)):
        return bool(obj)
    elif isinstance(obj, (pd.Series, pd.DataFrame)):
        return obj.to_dict()
    elif isinstance(obj, (pd.Timestamp, np.datetime64)):
        return str(obj)
    elif isinstance(obj, (set, frozenset)):
        return list(obj)
    elif obj is None:
        return None
    else:
        return obj

def clean_state_for_serialization(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Clean an entire state dictionary for serialization.
    
    Args:
        state: The InvestmentState dictionary
    
    Returns:
        Cleaned state with all NumPy types converted
    """
    return convert_to_serializable(state)