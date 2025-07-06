from enum import Enum, auto

class ComponentType(Enum):
    CUSTOM = auto()
    MODEL_UPLOAD = auto()
    BATCH_PREDICT = auto()
