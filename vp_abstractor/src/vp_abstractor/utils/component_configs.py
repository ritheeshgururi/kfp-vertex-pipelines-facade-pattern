from dataclasses import dataclass
from typing import Optional, Any, List

@dataclass
class ModelUploadConfig:
    """Configuration for the pre-built model upload step.
    """
    model_display_name: str
    gcs_model_artifact_uri: Any
    serving_container_image_uri: str
    parent_model_resource_name: Optional[Any] = None
    
@dataclass
class BatchPredictionConfig:
    """Configuration for the pre-built batch prediction step.
    """
    job_display_name: str
    model_resource_name: Any
    instances_format: str
    gcs_source_uris: List[Any]
    gcs_destination_output_uri_prefix: str
    machine_type: str = 'n1-standard-2'
    starting_replica_count: int = 1
    max_replica_count: int = 1