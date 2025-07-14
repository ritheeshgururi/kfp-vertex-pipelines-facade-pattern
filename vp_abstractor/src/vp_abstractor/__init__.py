"""
vp_abstractor: A user friendly framework for building and running KFP pipelines on Vertex Pipelines with prebuilt components and additional functionalities.
"""
import importlib.metadata

from .core.pipeline_builder import PipelineBuilder, Task
from .core.runner import PipelineRunner
from .core.image_builder import CustomImageConfig
# from .serving.container_builder import ServingContainerBuilder
from .utils.enums import ComponentType

try:
    __version__ = importlib.metadata.version('vp_abstractor')
except:
    __version__ = 'dev'

__all__ = [
    'PipelineBuilder',
    'Task',
    'PipelineRunner',
    # 'ServingContainerBuilder',
    'ComponentType',
    'CustomImageConfig',
    '__version__',
]