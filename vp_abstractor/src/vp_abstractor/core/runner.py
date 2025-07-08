"""
This module contains the PipelineRunner class - a tool for compiling
and executing pipelines. It is the bridge between the abstract pipeline
definition created by the PipelineBuilder and the Vertex Pipeline service.
"""
import logging
import tempfile

from google.cloud import aiplatform
from kfp.compiler import Compiler

#Importing only for type annotations
from . import pipeline_builder
from typing import Dict, Any

logging.basicConfig(
    level = logging.INFO,
    format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("vp_abstractor.runner")

class PipelineRunner:
    """
    Compiles and executes a pipeline remotely on Vertex Pipelines.
    """
    def __init__(
        self,
        project_id: str,
        location: str,
        enable_caching: bool = False,
    ):
        """
        Initializes the PipelineRunner and the Vertex AI client.

        Args:
            project_id: GCP Project ID where the pipeline will run.
            location: The GCP region for Vertex AI.
            enable_caching: If True, enables execution caching for pipeline steps
                           that have not changed. Set to False to force a full rerun.
        """
        if not project_id or not location:
            raise ValueError("Project ID and Location must be provided.")
        self.project_id = project_id
        self.location = location
        self.enable_caching = enable_caching

        aiplatform.init(
            project = self.project_id,
            location = self.location
        )
        logger.info(f'Vertex AI initialized for project {self.project_id} and location {self.location}.')

    def run(
        self,
        pipeline_builder: pipeline_builder.PipelineBuilder,
        pipeline_parameters: Dict[str, Any] = None,
        service_account: str = None,
        wait: bool = True
    ) -> aiplatform.PipelineJob:
        """
        Compiles the pipeline, submits it to Vertex AI.

        Args:
            pipeline_builder: The PipelineBuilder instance containing the full pipeline definition.
            pipeline_parameters: A dictionary of runtime parameters for the pipeline. These parameters will be passed to `builder.parameters` placeholders.
            service_accounnt: Service account to be used for authenticating the PipelineJob submission.
            wait: If True, the method will block and stream logs to the console until the
                  pipeline job finishes. If False, it submits the job and returns immediately.

        Returns:
            An `aiplatform.PipelineJob` object representing the running or completed job.
        """        
        pipeline_params = pipeline_parameters or {}
        display_name = pipeline_builder.pipeline_name
        pipeline_root = pipeline_builder.pipeline_root

        logger.info("Building KFP pipeline function from the builder definition")
        kfp_pipeline_function = pipeline_builder._build_kfp_pipeline(pipeline_params)

        with tempfile.NamedTemporaryFile(mode = 'w', suffix = '.yaml', delete = True) as temp_file:
            compiler = Compiler()
            logger.info(f'Compiling pipeline {display_name} to YAML')
            compiler.compile(
                pipeline_func = kfp_pipeline_function,
                package_path = temp_file.name
            )
            logger.info(f"Pipeline compiled successfully.")

            job = aiplatform.PipelineJob(
                display_name = display_name,
                template_path = temp_file.name,
                pipeline_root = pipeline_root,
                parameter_values = {
                    "project_id": self.project_id,
                    "location": self.location,
                    **pipeline_params
                },
                enable_caching = self.enable_caching,
            )

            logger.info(f"Submitting Vertex AI PipelineJob to Vertex Pipelines")
            job.submit(
                service_account = service_account
            )

        logger.info(f"Vertex AI PipelineJob submitted successfully")

        if wait:
            try:
                job.wait()
                logger.info(f'Pipeline job {display_name} finished')
            except Exception as e:
                logger.info(f"Pipeline job failed with an exception: {e}")
                raise
        
        return job