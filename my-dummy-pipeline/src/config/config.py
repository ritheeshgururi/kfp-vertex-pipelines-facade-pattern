class PipelineConfig:
    PROJECT_ID = 'gcp-vertexai-mlops-blueprint'
    LOCATION = "asia-south1"

    PIPELINE_ROOT = 'gs://vertex-pipeline-root-training'
    PIPELINE_NAME = 'my-dummy-pipeline'
    DESCRIPTION = 'My dummy pipeline.'
    enable_caching = False
    wait_for_completion = True

class TaskNames:
    task_one = 'task-1'
    task_two = 'task-2'
    task_three = 'task-3'
    task_four = 'task-4'

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
    task_one = 'python:3.11'
    task_two = 'python:3.11'
    task_three = 'python:3.11'
    task_four = 'python:3.11'