from kfp.dsl import component, Input

def create_model_monitoring_job(
    project_id: str,
    location: str,
    bucket_uri: str,
    model_resource_name: str,
    batch_prediction_job_resource_name: str,
    training_data_gcs_uri: str,
    user_emails: list,
    monitoring_display_name: str,
):
    from google.cloud import aiplatform
    from vertexai.resources.preview import ml_monitoring
    import warnings
    
    warnings.filterwarnings('ignore')
    
    aiplatform.init(project = project_id, location = location, staging_bucket = bucket_uri)

    model = aiplatform.Model(model_name = model_resource_name)
    batch_prediction_job = aiplatform.BatchPredictionJob(
        batch_prediction_job_name = batch_prediction_job_resource_name
    )

    print(f'Setting up monitoring for Model: {model.resource_name}')
    print(f'Using Batch Prediction Job for target data: {batch_prediction_job.resource_name}')
    print(f'Using Training Data for baseline: {training_data_gcs_uri}')

    model_monitoring_schema = ml_monitoring.spec.ModelMonitoringSchema(
        feature_fields = [
            ml_monitoring.spec.FieldSchema(name = 'feature_1', data_type = 'float'),
        ]
    )

    baseline_dataset = ml_monitoring.spec.MonitoringInput(
        gcs_uri = training_data_gcs_uri,
        data_format = 'csv'
    )

    target_dataset = ml_monitoring.spec.MonitoringInput(
        batch_prediction_job = batch_prediction_job.resource_name
    )

    drift_spec = ml_monitoring.spec.DataDriftSpec(
        default_numeric_alert_threshold = 0.3
    )

    notification_spec = ml_monitoring.spec.NotificationSpec(user_emails = user_emails)
    output_spec = ml_monitoring.spec.OutputSpec(gcs_base_dir = f'{bucket_uri}/monitoring-output')

    monitor = None
    existing_monitors = ml_monitoring.ModelMonitor.list(project = project_id, location = location)
    for existing_monitor in existing_monitors:
        model_target = existing_monitor._gca_resource.model_monitoring_target.vertex_model
        if model_target and model_target.model == model.resource_name:
            print(f'Found and deleting existing monitor: {existing_monitor.resource_name}')
            existing_monitor.delete(force = True)
            break

    monitor = ml_monitoring.ModelMonitor.create(
        project = project_id,
        location = location,
        display_name = monitoring_display_name,
        model_name = model.resource_name,
        model_version_id = model.version_id,
        model_monitoring_schema = model_monitoring_schema
    )
    print(f'Created ModelMonitor resource: {monitor.resource_name}')

    monitoring_job = monitor.run(
        display_name = f'{monitoring_display_name}-job',
        baseline_dataset = baseline_dataset,
        target_dataset = target_dataset,
        tabular_objective_spec = ml_monitoring.spec.TabularObjective(
            feature_drift_spec = drift_spec
        ),
        notification_spec = notification_spec,
        output_spec = output_spec,
    )
    
    print('Monitoring job completed')