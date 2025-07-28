from dataclasses import dataclass
from typing import Optional, Any, List

@dataclass
class ModelUploadConfig:
    """Configuration for the pre-built model upload step.
    """
    display_name: str
    artifact_uri: Any
    serving_container_image_uri: str
    parent_model: Optional[Any] = None
    
@dataclass
class BatchPredictionConfig:
    """Configuration for the pre-built batch prediction step.
    """
    job_display_name: str
    model_resource_name: Any
    instances_format: str
    gcs_source_uris: List[Any]
    gcs_destination_prefix: str
    machine_type: str = 'n1-standard-2'
    starting_replica_count: int = 1
    max_replica_count: int = 1
    predictions_format:str = 'jsonl'

@dataclass
class CustomImageConfig:
    """
    Configuration to automatically build and use a custom base image for the pipeline components. This is useful when:
        1. Your step files use external file dependencies like utils or config files.
        2. Your pipeline steps have many common package dependencies that you would rather bake once into a common component base image at build time, than go for redundant installations at runtime.
        Note: Pipeline step base images in the vp_abstractor framework follow a three level precedence hierarchy. A `base_image` **kwargs argument passed to the `PipelineBuilder.add_step()` method is given first priority. The base image generated using the `CustomImageConfig` configuration passed to the PipelineRunner comes next. This custom base image will be overriden for a particular step, if the `base_image` argument is passed to its `add_step()` method. If neither of these two are specified, the default KFP base image (currently python:3.9) will be used.

    Args:
        src_dir: Path to a root directory containing all the pipeline step files and other file dependencies.
        python_base_image: A Python base image to be used as the base image for building the component base image docker container. Goes into the FROM command in the Dockerfile.
        artifact_registry_repo: The URI of a pre-created Artifact Registry repository to push the component base image to.
        image_name: The image name to be used in the Artifact Registry repository for the component base image.
        requirements_file: Optional. The path to a requirements.txt file relative to the path passed to `src_dir`. Use this to install any package dependencies common to most of the pipeline components at build time.
    """
    src_dir: str
    python_base_image: str
    artifact_registry_repo: str
    image_name: str
    requirements_file: Optional[str] = None
    dependencies_preinstalled: bool = False

@dataclass
class ServingImageConfig:
    """Configuration for building a custom serving container for Vertex Batch Prediction.
    """
    config_name: str
    src_dir: str
    artifact_registry_repo: str
    image_name: str
    prediction_script: str
    prediction_class: str
    requirements_file: str
    python_base_image: str = 'python:3.10-slim-bookworm'
    dependencies_preinstalled: bool = False