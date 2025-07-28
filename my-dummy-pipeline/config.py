class PipelineConfig:
    PROJECT_ID = 'gcp-vertexai-mlops-blueprint'
    LOCATION = 'asia-south1'

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

class TaskNames:
    task_one = 'component-1'
    task_two = 'component-2'
    task_three = 'component-3'
    task_four_true = 'component-4-true'
    task_four_false = 'component-4-false'
    data_drift_dummy = 'dummy_data_drift'
    model_upload_task = 'model-upload'
    batch_predict_task = 'vertex-batch-prediction'
    
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

class ModelUpload:
    model_display_name = 'my-dummy-sklearn-model'
    gcs_model_artifact_uri = 'gs://test-bucket-development/models/model2'
    # serving_container_image_uri = 'asia-docker.pkg.dev/vertex-ai/prediction/sklearn-cpu.1-5:latest'

class VertexBatchPrediction:
    job_display_name = 'prediction-on-dummy-data'
    instances_format = 'jsonl'
    gcs_source_uris = ['gs://test-bucket-development/data/dummy_prediction_data2.jsonl']
    gcs_destination_output_uri_prefix = 'gs://test-bucket-development/inference-data/'

class BaseImageConfig:
    python_base_image = 'python:3.10-slim-bookworm'
    requirements_file = 'requirements.txt'
    src_dir = 'src'
    artifact_registry_repo = 'asia-south1-docker.pkg.dev/gcp-vertexai-mlops-blueprint/gcp-vertex-ai-mlops-blueprint'
    image_name = 'vp_abstractor-test-image'
    
class ServingImage:
    CONFIG_NAME = 'dummy-sklearn-server'
    SRC_DIR = 'server_predictor'
    ARTIFACT_REGISTRY_REPO = 'asia-south1-docker.pkg.dev/gcp-vertexai-mlops-blueprint/gcp-vertex-ai-mlops-blueprint'
    IMAGE_NAME = 'dummy-sklearn-server'
    PREDICTION_SCRIPT = 'predictor.py'
    PREDICTION_CLASS = 'MyPredictor'
    REQUIREMENTS_FILE = 'requirements.txt'