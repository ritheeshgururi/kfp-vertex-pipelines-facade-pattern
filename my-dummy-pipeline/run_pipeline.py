from vp_abstractor import PipelineBuilder, PipelineRunner, ComponentType, CustomImageConfig

from src.tasks.task1 import task1
from src.tasks.task2 import task2
from src.tasks.task3 import task3
from src.tasks.task4 import task4

from src.config import config

def build_pipeline():
    builder = PipelineBuilder(
        pipeline_name = config.PipelineConfig.PIPELINE_NAME,
        pipeline_root = config.PipelineConfig.PIPELINE_ROOT,
        description = config.PipelineConfig.DESCRIPTION
    )

    builder.add_email_notification_on_exit(
        recipients = config.PipelineConfig.EMAIL_NOTIFICATION_RECIPIENTS
    )

    taskone = builder.add_step(
        name = config.TaskNames.task_one,
        step_type = ComponentType.CUSTOM,
        step_function = task1,
        packages_to_install = config.Dependencies.task_one,
        custom_job_spec = {
            'display_name': config.TaskNames.task_one,
            'service_account': config.PipelineConfig.SERVICE_ACCOUNT
        }
    )

    tasktwo = builder.add_step(
        name = config.TaskNames.task_two,
        step_type = ComponentType.CUSTOM,
        step_function = task2,
        inputs = {
            'input_1': taskone.outputs['task1_outputs']
        },
        packages_to_install = config.Dependencies.task_two,
    )

    with builder.condition(
        tasktwo.outputs['flag_output'], '==', 'True',
        name = config.ConditionNames.condition1
    ):
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

        taskfour_true = builder.add_step(
            name = config.TaskNames.task_four_true,
            step_type = ComponentType.CUSTOM,
            step_function = task4,
            after = [taskthree],
            custom_job_spec = {
                'machine_type': config.ComputeResources.task_four,
                'service_account': config.PipelineConfig.SERVICE_ACCOUNT
            }
        )

    with builder.condition(
        tasktwo.outputs['flag_output'], '==', 'True',
        name = config.ConditionNames.condition2
    ):
        taskfour_false = builder.add_step(
            name = config.TaskNames.task_four_false,
            step_type = ComponentType.CUSTOM,
            step_function = task4
        )

    return builder

def main():
    runner = PipelineRunner(
        project_id = config.PipelineConfig.PROJECT_ID,
        location = config.PipelineConfig.LOCATION,
        enable_caching = config.PipelineConfig.enable_caching,
        custom_image_config = CustomImageConfig(
            src_dir = config.BaseImageConfig.src_dir,
            python_base_image = config.BaseImageConfig.python_base_image,
            artifact_registry_repo = config.BaseImageConfig.artifact_registry_repo,
            image_name = config.BaseImageConfig.image_name,
            requirements_file = config.BaseImageConfig.requirements_file
        )
    )

    builder = build_pipeline()

    runner.run(
        pipeline_builder = builder,
        wait = config.PipelineConfig.wait_for_completion,
        service_account = config.PipelineConfig.SERVICE_ACCOUNT,
        force_image_rebuild = config.PipelineConfig.force_image_rebuild
    )

if __name__ == '__main__':
    main()