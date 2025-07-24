"""
This module contains the PipelineRunner class - a tool for compiling
and executing pipelines. It is the bridge between the abstract pipeline
definition created by the PipelineBuilder and the Vertex Pipeline service.
"""
import logging
import tempfile

from google.cloud import aiplatform
from kfp.compiler import Compiler

from .image_builders import CustomImageConfig, ComponentImageBuilder, ServingImageBuilder
from . import pipeline_builder
from typing import Dict, Any, Optional, List

from ..utils.dataclasses import ServingImageConfig

logging.basicConfig(
    level = logging.INFO,
    format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PipelineRunner:
    """
    Compiles and executes a pipeline remotely on Vertex Pipelines.
    """
    def __init__(
        self,
        project_id: str,
        location: str,
        enable_caching: bool = False,
        custom_base_image_config: Optional[CustomImageConfig] = None,
        serving_image_configs: Optional[List[ServingImageConfig]] = None,
    ):
        """
        Initializes the PipelineRunner and the Vertex AI client.

        Args:
            project_id: GCP Project ID where the pipeline will run.
            location: The GCP region for Vertex AI.
            enable_caching: If True, enables execution caching for pipeline steps that have not changed. Set to False to force a full rerun.
            custom_base_image_config: Optional. Configuration to automatically build and use a custom base image for the pipeline components. This is useful when:
                1. Your step files use external file dependencies like utils or config files.
                2. Your pipeline steps have many common package dependencies that you would rather bake once into a common component base image at build time, than go for redundant installations at runtime.
                Note: Pipeline step base images in the vp_abstractor framework follow a three level precedence hierarchy. A `base_image` **kwargs argument passed to the `PipelineBuilder.add_step()` method is given first priority. The base image generated using the `CustomImageConfig` configuration passed to the PipelineRunner comes next. This custom base image will be overriden for a particular step, if the `base_image` argument is passed to its `add_step()` method. If neither of these two are specified, the default KFP base image (currently python:3.9) will be used.
        """
        if not project_id or not location:
            raise ValueError('Project ID and Location must be provided.')
        self.project_id = project_id
        self.location = location
        self.enable_caching = enable_caching
        self.custom_base_image_config = custom_base_image_config
        self.serving_image_configs = serving_image_configs

        aiplatform.init(
            project = self.project_id,
            location = self.location
        )
        logger.info(f'Vertex AI initialized for project {self.project_id} and location {self.location}.')

    def run(
        self,
        pipeline_builder: pipeline_builder.PipelineBuilder,
        pipeline_parameters: Optional[Dict[str, Any]] = None,
        service_account: Optional[str] = None,
        wait: Optional[bool] = True,
        force_image_rebuild: Optional[bool] = False
    ) -> aiplatform.PipelineJob:
        """
        Compiles the pipeline, submits it to Vertex AI.

        Args:
            pipeline_builder: The PipelineBuilder instance containing the full pipeline definition.
            pipeline_parameters: Optional. A dictionary of runtime parameters for the pipeline. These parameters will be passed to `builder.parameters` placeholders.
            service_accounnt: Optional. Service account to be used for authenticating the PipelineJob submission.
            wait: Optional. If True, the method will block and stream logs to the console until the pipeline job finishes. If False, it submits the job and returns immediately.
            force_image_rebuild: Optional. Relavent only if the `custom_base_image_config` argument is passed to the `PipelineRunner`. If set to True, existing images in the Artifact Registry repository with the same hash tag will be ignored, and the component base image will be rebuilt, even if the code in `src_dir` hasn't changed.

        Returns:
            An `aiplatform.PipelineJob` object representing the running or completed job.
        """        
        pipeline_params = pipeline_parameters or {}
        display_name = pipeline_builder.pipeline_name
        pipeline_root = pipeline_builder.pipeline_root

        built_serving_images: Dict[str, str] = {}
        if self.serving_image_configs:
            logger.info(f'{len(self.serving_image_configs)} serving image configuration provided. Starting serving image builder.') if len(self.serving_image_configs) == 1 else logger.info(f'{len(self.serving_image_configs)} serving image configurations provided. Starting serving image builders.')
            for config in self.serving_image_configs:
                if not isinstance(config, ServingImageConfig):
                    raise TypeError(f'Items in serving_image_configs must be of type ServingImageConfig. Instead recieved {type(config)}')
                
                serving_builder = ServingImageBuilder(config)
                image_uri = serving_builder.build_and_push(force_rebuild = force_image_rebuild)
                built_serving_images[config.config_name] = image_uri
                logger.info(f"Built serving image '{config.config_name}': {image_uri}")

        common_base_image = None
        if self.custom_base_image_config:
            logger.info('Custom common base image configuration provided. Starting component base image builder')
            image_builder = ComponentImageBuilder(self.custom_base_image_config)
            common_base_image = image_builder.build_and_push(force_rebuild = force_image_rebuild)
            logger.info(f'Using custom base image for pipeline: {common_base_image}')

        logger.info('Building KFP pipeline function from the builder definition')
        kfp_pipeline_function = pipeline_builder._build_kfp_pipeline(
            runtime_parameters = pipeline_params,
            common_base_image = common_base_image,
            built_serving_images = built_serving_images
        )

        with tempfile.NamedTemporaryFile(mode = 'w', suffix = '.yaml', delete = True) as temp_file:
            compiler = Compiler()
            logger.info(f'Compiling pipeline {display_name} to YAML')
            compiler.compile(
                pipeline_func = kfp_pipeline_function,#type: ignore
                package_path = temp_file.name
            )
            logger.info(f'Pipeline compiled successfully.')

            job = aiplatform.PipelineJob(
                display_name = display_name,
                template_path = temp_file.name,
                pipeline_root = pipeline_root,
                parameter_values = {
                    'project_id': self.project_id,
                    'location': self.location,
                    **pipeline_params
                },
                enable_caching = self.enable_caching,
            )

            logger.info(f'Submitting Vertex AI PipelineJob to Vertex Pipelines')
            job.submit(
                service_account = service_account
            )

        logger.info(f'Vertex AI PipelineJob submitted successfully')

        if wait:
            try:
                job.wait()
                logger.info(f'Pipeline job {display_name} finished')
            except Exception as e:
                logger.info(f'Pipeline job failed with an exception: {e}')
                raise
        
        return job