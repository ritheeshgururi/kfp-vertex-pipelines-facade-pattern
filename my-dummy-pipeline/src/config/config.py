class PipelineConfig:
    PROJECT_ID = 'gcp-vertexai-mlops-blueprint'
    LOCATION = "asia-south1"

    PIPELINE_ROOT = 'gs://vertex-pipeline-root-training'
    PIPELINE_NAME = 'my-dummy-pipeline'
    DESCRIPTION = '.'
    enable_caching = False
    wait_for_completion = True

class TaskNames:
    task_one = 'component-1'
    task_two = 'component-2'
    task_three = 'component-3'
    task_four_true = 'component-4-true'
    task_four_false = 'component-4-false'


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