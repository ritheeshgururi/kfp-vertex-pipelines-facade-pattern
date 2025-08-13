from src.tasks.task1 import task1
from src.tasks.task2 import task2
from src.tasks.task3 import task3
from src.tasks.task4 import task4
from src.tasks.data_drift_dummy import data_drift_dummy
from src.tasks.vertex_monitoring import create_model_monitoring_job

import config as config

from vp_abstractor import PipelineBuilder, PipelineRunner, ComponentType, CustomImageConfig, ModelUploadConfig, BatchPredictionConfig, ServingImageConfig

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
        packages_to_install = config.Dependencies.task_two
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
            packages_to_install = config.Dependencies.task_three
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

    monitoring_task = builder.add_step(
        name = config.TaskNames.data_drift_dummy,
        step_type = ComponentType.CUSTOM_METRIC_MONITORER,
        step_function = data_drift_dummy, 
        metric_metadata = config.LiteralInputs.metric_metadata
    )

    model_upload_task = builder.add_step(
        name = config.TaskNames.model_upload_task,
        step_type = ComponentType.MODEL_UPLOAD,
        inputs = ModelUploadConfig(#type: ignore
            display_name = config.ModelUpload.model_display_name,
            artifact_uri = config.ModelUpload.gcs_model_artifact_uri,
            serving_container_image_uri = builder.images[config.ServingImage.CONFIG_NAME],#type: ignore
        ),
        vertex_custom_job_spec = {
            'machine_type': config.ComputeResources.task_four,
            'service_account': config.PipelineConfig.SERVICE_ACCOUNT
        }
    )

    batch_predict_task = builder.add_step(
        name = config.TaskNames.batch_predict_task,
        step_type = ComponentType.BATCH_PREDICT,
        inputs = BatchPredictionConfig(#type: ignore
            job_display_name = config.VertexBatchPrediction.job_display_name,
            model_resource_name = model_upload_task.outputs['model_resource_name'],
            instances_format = config.VertexBatchPrediction.instances_format,
            gcs_source_uris = config.VertexBatchPrediction.gcs_source_uris,
            gcs_destination_prefix = config.VertexBatchPrediction.gcs_destination_output_uri_prefix,
            batch_size = 8
        )
    )

    vertex_model_monitoring_task = builder.add_step(
        name = 'dummy-vertex-monitoring',
        step_type = ComponentType.CUSTOM,
        step_function = create_model_monitoring_job,
        inputs = {
            'project_id': config.PipelineConfig.PROJECT_ID,
            'location': config.PipelineConfig.LOCATION,
            'bucket_uri': '',
            'model_resource_name': model_upload_task.outputs['model_resource_name'],
            'batch_prediction_job_resource_name': batch_predict_task.outputs['batch_prediction_job_resource_name'],
            'training_data_gcs_uri': '',
            'user_emails': config.PipelineConfig.EMAIL_NOTIFICATION_RECIPIENTS,
            'monitoring_display_name': 'dummy-vertex-monitoring'
        },
        packages_to_install =  ['vertexai', 'pandas', 'google-cloud-aiplatform'],
        vertex_custom_job_spec = {
            'machine_type': 'e2-standard-8',
            'service_account': config.PipelineConfig.SERVICE_ACCOUNT
        }
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
        ),
        serving_image_configs = [ServingImageConfig(
            config_name = config.ServingImage.CONFIG_NAME,
            src_dir = config.ServingImage.SRC_DIR,
            artifact_registry_repo = config.ServingImage.ARTIFACT_REGISTRY_REPO,
            image_name = config.ServingImage.IMAGE_NAME,
            prediction_script = config.ServingImage.PREDICTION_SCRIPT,
            prediction_class = config.ServingImage.PREDICTION_CLASS,
            requirements_file = config.ServingImage.REQUIREMENTS_FILE
        )]
    )

    builder = build_pipeline()

    runner.run(
        pipeline_builder = builder,
        wait = config.PipelineConfig.wait_for_completion,
        service_account = config.PipelineConfig.SERVICE_ACCOUNT,
        force_image_rebuild = config.PipelineConfig.force_image_rebuild
    )

    # runner.schedule(
    #     pipeline_builder = builder,
    #     schedule_display_name = f'{config.PipelineConfig.PIPELINE_NAME}-hourly-schedule',
    #     cron = '0 * * * *',
    #     service_account = config.PipelineConfig.SERVICE_ACCOUNT,
    #     force_image_rebuild = config.PipelineConfig.force_image_rebuild
    # )

if __name__ == '__main__':
    main()