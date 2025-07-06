import importlib.metadata

from .core.pipeline_builder import PipelineBuilder, Task
from .core.runner import PipelineRunner
# from .serving.container_builder import ServingContainerBuilder
from .utils.enums import ComponentType

try:
    __version__ = importlib.metadata.version('vp_abstractor')
except:
    __version__ = 'dev'