"""
vp_abstractor: A user friendly framework for building and running KFP pipelines on Vertex Pipelines with prebuilt components and additional functionalities.
"""
import importlib.metadata

from .core.pipeline_builder import PipelineBuilder, Task
from .core.runner import PipelineRunner
from .utils.dataclasses import ModelUploadConfig, BatchPredictionConfig, ServingImageConfig, CustomImageConfig
from .utils.enums import ComponentType

try:
    __version__ = importlib.metadata.version('vp-abstractor')
except:
    __version__ = 'dev'

__all__ = [
    'PipelineBuilder',
    'Task',
    'PipelineRunner',
    'ServingImageConfig',
    'ComponentType',
    'CustomImageConfig',
    'ModelUploadConfig',
    'BatchPredictionConfig',
    '__version__',
]