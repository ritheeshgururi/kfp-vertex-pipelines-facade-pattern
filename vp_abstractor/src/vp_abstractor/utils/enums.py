"""
This module provides the user-facing enumerations for the differnt types of pipeline steps a user can define.
"""
from enum import Enum, auto

class ComponentType(Enum):
    """
    Defines the type of a step in a pipeline.
    """
    CUSTOM = auto()
    MODEL_UPLOAD = auto()
    BATCH_PREDICT = auto()