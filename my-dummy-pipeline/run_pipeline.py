from fastapi import dependencies
from vp_abstractor import PipelineBuilder, PipelineRunner, ComponentType

from src.task1 import task1
from src.task2 import task2
from src.task3 import task3
from src.task4 import task4

from src.config import config

builder = PipelineBuilder(
    pipeline_name = config.PipelineConfig.PIPELINE_NAME,
    pipeline_root = config.PipelineConfig.PIPELINE_ROOT,
    description = config.PipelineConfig.DESCRIPTION
)

taskone = builder.add_step(
    name = config.TaskNames.task_one,
    step_type = ComponentType.CUSTOM,
    step_function = task1,
    packages_to_install = config.Dependencies.task_one
)

tasktwo = builder.add_step(
    name = config.TaskNames.task_two,
    step_type = ComponentType.CUSTOM,
    step_function = task2,
    inputs = {
        'input_1': taskone.outputs['task1_outputs']
    },
    packages_to_install = config.Dependencies.task_two
)

taskthree = builder.add_step(
    name = config.TaskNames.task_three,
    step_type = ComponentType.CUSTOM,
    step_function = task3,
    inputs = {
        'input_1': tasktwo.outputs['output_string'],
        'input_2': tasktwo.outputs['output_number']
    },
    base_image = config.BaseImages.task_three,
    packages_to_install = config.Dependencies.task_three,
)

taskfour = builder.add_step(
    name = config.TaskNames.task_four,
    step_type = ComponentType.CUSTOM,
    step_function = task4,
    packages_to_install = config.Dependencies.task_four,
    after = [taskthree]
)

if __name__ == '__main__':

    runner = PipelineRunner(
        project_id = config.PipelineConfig.PROJECT_ID,
        location = config.PipelineConfig.LOCATION,
        enable_caching = config.PipelineConfig.enable_caching
    )

    runner.run(
        pipeline_builder = builder,
        wait = config.PipelineConfig.wait_for_completion
    )