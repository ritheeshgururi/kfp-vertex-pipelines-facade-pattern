from typing import List, NamedTuple
from kfp import dsl

@dsl.component(
    base_image = 'python:3.13.5-slim-bookworm',
    packages_to_install = ['google-cloud-aiplatform>=1.16.0']
)
def batch_prediction_step(
    project: str,
    location: str,
    job_display_name: str,
    model_resource_name: str,
    gcs_source_uris: List[str],
    gcs_destination_prefix: str,
    instances_format: str,
    predictions_format: str = 'jsonl',
    machine_type: str = 'n1-standard-2',
    starting_replica_count: int = 1,
    max_replica_count: int = 1,
) -> NamedTuple('Outputs', [
    ('gcs_output_directory', str),
    ('batch_prediction_job_resource_name', str),#type: ignore
]):
    """
    Creates and waits for a Vertex AI Batch Prediction job.

    Returns:
        NamedTuple:
            gcs_output_directory (str): The GCS path to the directory containing predictions.
            batch_prediction_job_resource_name (str): The resource name of the job.
    """
    from google.cloud import aiplatform
    from collections import namedtuple

    print(f'Initializing Vertex AI for project {project} in {location}')
    aiplatform.init(
        project = project,
        location = location
    )

    print(f'Retrieving model from resource name: {model_resource_name}')

    model = aiplatform.Model(model_name = model_resource_name)

    print(f'Starting batch prediction job {job_display_name}')
    print(f'Source: {gcs_source_uris}')
    print(f'Destination: {gcs_destination_prefix}')

    batch_prediction_job = model.batch_predict(
        job_display_name = job_display_name,
        gcs_source = gcs_source_uris,
        gcs_destination_prefix = gcs_destination_prefix,
        instances_format = instances_format,
        machine_type = machine_type,
        starting_replica_count = starting_replica_count,
        max_replica_count = max_replica_count,
        sync = True,
        predictions_format = predictions_format
    )

    print('Batch prediction job finished.')
    print(f'Job state: {batch_prediction_job.state}')
    print(f'Output available at: {batch_prediction_job.output_info.gcs_output_directory}')#type: ignore

    output_values = namedtuple('Outputs', ['gcs_output_directory', 'batch_prediction_job_resource_name'])
    return output_values(
        gcs_output_directory = batch_prediction_job.output_info.gcs_output_directory,#type: ignore
        batch_prediction_job_resource_name = batch_prediction_job.resource_name
    )