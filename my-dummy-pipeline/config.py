class PipelineConfig:
    PROJECT_ID = 'gcp-vertexai-mlops-blueprint'
    LOCATION = "asia-south1"

    PIPELINE_ROOT = 'gs://vertex-pipeline-root-training'
    PIPELINE_NAME = 'my-dummy-pipeline'
    DESCRIPTION = '.'
    enable_caching = False
    wait_for_completion = True
    force_image_rebuild = False
    EMAIL_NOTIFICATION_RECIPIENTS = [
        'ritheeshgururi187@gmail.com',
        'gurugulapudi2024@gmail.com'
    ]
    SERVICE_ACCOUNT = 'gcp-vertexai-mlops-blueprint@gcp-vertexai-mlops-blueprint.iam.gserviceaccount.com'

class BaseImageConfig:
    python_base_image = 'python:3.10-slim-bookworm'
    requirements_file = 'requirements.txt'
    src_dir = 'src'
    artifact_registry_repo = 'asia-south1-docker.pkg.dev/gcp-vertexai-mlops-blueprint/gcp-vertex-ai-mlops-blueprint'
    image_name = 'vp_abstractor-test-image'

class TaskNames:
    task_one = 'component-1'
    task_two = 'component-2'
    task_three = 'component-3'
    task_four_true = 'component-4-true'
    task_four_false = 'component-4-false'
    data_drift_dummy = 'dummy_data_drift'
    
class ConditionNames:
    condition1 = 'Flag condition True'
    condition2 = 'Flag condition False'


class Dependencies:
    task_one = [
        'kfp'
    ]
    task_two = [
        'kfp'
    ]
    task_three = [
        'kfp'
    ]
    task_four = [
        'kfp'
    ]

class BaseImages:
    task_one = 'python:3.10-slim-bookworm'
    task_two = 'python:3.10-slim-bookworm'
    task_three = 'python:3.10-slim-bookworm'
    task_four = 'python:3.10-slim-bookworm'

class ComputeResources:
    task_one = 'e2-standard-4'
    task_two = 'e2-standard-4'
    task_three = 'e2-standard-4'
    task_four = 'e2-standard-4'

class LiteralInputs:
    metric_metadata = {
        'model_name': 'dummy-model',
        'model_version': 'dummy',
        'run_type': 'test'
    }