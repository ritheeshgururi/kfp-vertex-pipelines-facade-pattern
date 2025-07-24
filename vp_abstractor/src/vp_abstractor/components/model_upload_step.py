from kfp import dsl
from typing import NamedTuple

@dsl.component(
    base_image = 'python:3.13.5-slim-bookworm',
    packages_to_install = ['google-cloud-aiplatform>=1.16.0']
)
def model_upload_step(
    project: str,
    location: str,
    display_name: str,
    artifact_uri: str,
    serving_container_image_uri: str,
    parent_model: str = None,#type: ignore
) -> NamedTuple('Outputs', [('model_resource_name', str)]):#type: ignore
    """
    Uploads a model to the Vertex AI Model Registry and returns its resource name.

    Returns:
        str: The full resource name of the uploaded model version.
    """
    from google.cloud import aiplatform
    from collections import namedtuple

    print(f'Initializing Vertex AI for project {project} in {location}')
    aiplatform.init(project = project, location = location)

    print(f'Starting model upload for {display_name}')
    print(f'Artifacts URI: {display_name}')
    print(f'Serving Image: {serving_container_image_uri}')
    if parent_model:
        print(f'Uploading as new version of: {parent_model}')

    model = aiplatform.Model.upload(
        display_name = display_name,
        artifact_uri = artifact_uri,
        serving_container_image_uri = serving_container_image_uri,
        parent_model = parent_model,
        sync = True,
        serving_container_predict_route = '/predict',
        serving_container_health_route = '/health',    
    )

    print(f'Model uploaded successfully. Resource Name: {model.resource_name}')#type: ignore

    output = namedtuple('Outputs', ['model_resource_name'])
    return output(model_resource_name = model.resource_name)#type: ignore