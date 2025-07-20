from src.tasks.task1 import task1
from src.tasks.task2 import task2
from src.tasks.task3 import task3
from src.tasks.task4 import task4
from src.tasks.data_drift_dummy import data_drift_dummy

import config as config

from vp_abstractor import PipelineBuilder, PipelineRunner, ComponentType, CustomImageConfig, ModelUploadConfig, BatchPredictionConfig

def build_pipeline():
    builder = PipelineBuilder(
        pipeline_name = config.PipelineConfig.PIPELINE_NAME,
        pipeline_root = config.PipelineConfig.PIPELINE_ROOT,
        description = config.PipelineConfig.DESCRIPTION
    )

    builder.add_email_notification(
        recipients = config.PipelineConfig.EMAIL_NOTIFICATION_RECIPIENTS
    )

    stepone = builder.add_step(
        name = config.TaskNames.task_one,
        step_type = ComponentType.CUSTOM,
        step_function = task1,
        packages_to_install = config.Dependencies.task_one,
        vertex_custom_job_spec = {
            'display_name': config.TaskNames.task_one,
            'service_account': config.PipelineConfig.SERVICE_ACCOUNT
        }
    )

    steptwo = builder.add_step(
        name = config.TaskNames.task_two,
        step_type = ComponentType.CUSTOM,
        step_function = task2,
        inputs = {
            'input_1': stepone.outputs['task1_outputs']
        },
        packages_to_install = config.Dependencies.task_two,
    )

    with builder.condition(
        steptwo.outputs['flag_output'], '==', 'True',
        name = config.ConditionNames.condition1
    ):
        stepthree = builder.add_step(
            name = config.TaskNames.task_three,
            step_type = ComponentType.CUSTOM,
            step_function = task3,
            inputs = {
                'input_1': steptwo.outputs['output_string'],
                'input_2': steptwo.outputs['output_number']
            },
            base_image = config.BaseImages.task_three,
            packages_to_install = config.Dependencies.task_three,
        )

        stepfour_true = builder.add_step(
            name = config.TaskNames.task_four_true,
            step_type = ComponentType.CUSTOM,
            step_function = task4,
            after = [stepthree],
            vertex_custom_job_spec = {
                'machine_type': config.ComputeResources.task_four,
                'service_account': config.PipelineConfig.SERVICE_ACCOUNT
            }
        )

    with builder.condition(
        steptwo.outputs['flag_output'], '==', 'False',
        name = config.ConditionNames.condition2
    ):
        stepfour_false = builder.add_step(
            name = config.TaskNames.task_four_false,
            step_type = ComponentType.CUSTOM,
            step_function = task4
        )

    builder.add_step(
        name = config.TaskNames.data_drift_dummy,
        step_type = ComponentType.CUSTOM_METRIC_MONITORER,
        step_function = data_drift_dummy, 
        metric_metadata = config.LiteralInputs.metric_metadata,
    )

    upload_task = builder.add_step(
        name = 'upload-dummy-model',
        step_type = ComponentType.MODEL_UPLOAD,
        inputs = ModelUploadConfig(
            model_display_name = 'my-dummy-sklearn-model',
            gcs_model_artifact_uri = 'gs://test-bucket-development/models/dummy_sklearn_model',
            serving_container_image_uri = 'asia-docker.pkg.dev/vertex-ai/prediction/sklearn-cpu.1-5:latest',
        ),
        vertex_custom_job_spec = {
            'machine_type': config.ComputeResources.task_four,
            'service_account': config.PipelineConfig.SERVICE_ACCOUNT
        }
    )

    predict_task = builder.add_step(
        name = 'run-batch-prediction',
        step_type = ComponentType.BATCH_PREDICT,
        inputs = BatchPredictionConfig(
            job_display_name = 'prediction-on-dummy-data',
            model_resource_name = upload_task.outputs['model_resource_name'],
            instances_format = 'jsonl',
            gcs_source_uris = ['gs://test-bucket-development/data/dummy_prediction_data.jsonl'],
            gcs_destination_output_uri_prefix = 'gs://test-bucket-development/inference-data/'
        )
    )

    return builder

def main():
    runner = PipelineRunner(
        project_id = config.PipelineConfig.PROJECT_ID,
        location = config.PipelineConfig.LOCATION,
        enable_caching = config.PipelineConfig.enable_caching,
        custom_base_image_config = CustomImageConfig(
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