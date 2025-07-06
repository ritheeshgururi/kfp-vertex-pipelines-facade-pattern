import tempfile

from google.cloud import aiplatform
from kfp.compiler import Compiler

class PipelineRunner:
    def __init__(
        self,
        project_id,
        location,
        enable_caching = False,
    ):
        self.project_id = project_id
        self.location = location
        self.enable_caching = enable_caching

        aiplatform.init(project = self.project_id, location = self.location)
        print(f'Vertex AI initialized for project {self.project_id} and location {self.location}.')

    def run(
        self,
        pipeline_builder,
        pipeline_parameters = None,
        wait = True,
    ):
        pipeline_params = pipeline_parameters or {}
        display_name = pipeline_builder.pipeline_name
        pipeline_root = pipeline_builder.pipeline_root

        print("Building KFP pipeline function from the builder definition")
        pipeline_func = pipeline_builder._build_kfp_pipeline(pipeline_params)

        with tempfile.NamedTemporaryFile(mode = 'w', suffix = '.yaml', delete = True) as temp_file:
            compiler = Compiler()
            print(f'Compiling pipeline {display_name} to YAML')
            compiler.compile(pipeline_func = pipeline_func, package_path = temp_file.name)
            print(f"Pipeline compiled successfully.")

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

            print(f"Submitting Vertex AI PipelineJob to Vertex Pipelines")
            job.submit()

        print(f"Vertex AI PipelineJob submitted successfully")

        if wait:
            try:
                job.wait()
                print(f'Pipeline job {display_name} finished')
            except Exception as e:
                print(f"Pipeline job failed with an exception: {e}")
                raise
        
        return job