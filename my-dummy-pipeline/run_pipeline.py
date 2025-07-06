from vp_abstractor import PipelineBuilder, PipelineRunner, ComponentType

from src.task1 import task1
from src.task2 import task2
from src.task3 import task3
from src.task4 import task4

GCP_PROJECT_ID = 'gcp-vertexai-mlops-blueprint'
GCP_PROJECT_LOCATION = "asia-south1"
PIPELINE_ROOT = 'gs://vertex-pipeline-root-training'

builder = PipelineBuilder(
    pipeline_name = 'my-dummy-pipeline',
    pipeline_root = PIPELINE_ROOT,
    description = 'My dummy pipeline.'
)

taskone = builder.add_step(
    name = 'task-1',
    step_type = ComponentType.CUSTOM,
    step_function = task1,
    packages_to_install = ['kfp']
)

tasktwo = builder.add_step(
    name = 'task-2',
    step_type = ComponentType.CUSTOM,
    step_function = task2,
    inputs = {
        'input_1': taskone.outputs['task1_outputs']
    },
    packages_to_install = ['kfp']
)

taskthree = builder.add_step(
    name = 'task-3',
    step_type = ComponentType.CUSTOM,
    step_function = task3,
    inputs = {
        'input_1': tasktwo.outputs['output_string'],
        'input_2': tasktwo.outputs['output_number']
    },
    base_image = 'python:3.11',
    packages_to_install = ['kfp'],
)

taskfour = builder.add_step(
    name = 'task-4',
    step_type = ComponentType.CUSTOM,
    step_function = task4,
    packages_to_install = ['kfp'],
    after = [taskthree]
)

if __name__ == '__main__':

    runner = PipelineRunner(
        project_id = GCP_PROJECT_ID,
        location = GCP_PROJECT_LOCATION,
        enable_caching = False
    )

    runner.run(
        pipeline_builder = builder,
        wait = True
    )