from kfp import dsl
from typing import Dict

@dsl.component(
    base_image = 'python:3.13.5-slim-bookworm',
    packages_to_install = [
        'google-cloud-monitoring == 2.20.0',
        'google-api-python-client == 2.136.0'
    ]
)
def custom_metric_monitorer_step(
    project_id: str,
    metrics: Dict[str, float],
    metadata: Dict[str, str],
    metric_type_name: str
):
    """
    A prebuilt component that logs a metrics passed in a dictionary to Cloud Monitoring.

    Args:
        project_id: GCP Project ID.
        metrics: A dictionary of metric name numeric value key value pairs.
        metadata: A dictionary of key-value pairs to be used as labels for filtering in Cloud Monitoring.
        metric_type_name: The name of the custom metric to log to.
    """
    import datetime
    from google.cloud import monitoring_v3
    from google.protobuf.timestamp_pb2 import Timestamp

    if not metrics:
        print('Metrics dictionary is empty. Atleast one key value pair is required.')
        return #type: ignore

    time = datetime.datetime.now(datetime.timezone.utc)
    timestamp = Timestamp()
    timestamp.FromDatetime(time)

    combined_metrics_timeseries = []

    print(f'Starting logging of {len(metrics)} metrics with metadata: {metadata}')

    for metric_name, metric_value in metrics.items():
        time_series = monitoring_v3.TimeSeries()

        time_series.metric.type = metric_type_name
        time_series.metric.labels.update(metadata)
        time_series.metric.labels['metric_name'] = metric_name

        data_point = monitoring_v3.Point()
        data_point.value.double_value = float(metric_value)
        data_point.interval.end_time = timestamp
        time_series.points = [data_point]

        combined_metrics_timeseries.append(time_series)
        print(f'Timeseries metric {metric_name} created with value: {metric_value}')

    try:
        monitoring_v3.MetricServiceClient().create_time_series(
            name = f'projects/{project_id}',
            time_series = combined_metrics_timeseries
        )
        print('All metrics logged to Cloud Monitoring successfully.')

        metrics_explorer_link = f'https://console.cloud.google.com/monitoring/metrics-explorer?project={project_id}'

        print('\n--- Logging Summary ---')
        print(f'Project ID:      {project_id}')
        print(f'Metric Type:     {metric_type_name}')
        print(f'Common Labels:   {metadata}')
        print('Metrics Sent:')
        
        for name, value in metrics.items():
            print(f'  - {name}: {value}')
        print(f'\nView in Metrics Explorer: {metrics_explorer_link}')
        print('-----------------------\n')
    except Exception as e:
        print(f'Logging metrics to Cloud Monitoring failed with error: {e}')
        raise e