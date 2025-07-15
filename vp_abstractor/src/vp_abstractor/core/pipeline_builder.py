"""
This module contains the primary user-facing API for constructing pipelines:
- Task: A reference to a step within the pipeline.
- PipelineBuilder: The main class for defining a pipeline with its steps.
  It is a high-level interface for users to build a pipeline graph without writing any KFP DSL code.
"""
import operator

from typing import Any, Callable, Dict, List, Optional

from contextlib import contextmanager
import re
from kfp import dsl
from google_cloud_pipeline_components.v1.vertex_notification_email import VertexNotificationEmailOp
from google_cloud_pipeline_components.v1.custom_job import create_custom_training_job_from_component

from .component_builder import ComponentCreator, CustomComponent
from ..components import model_upload_step, batch_prediction_step
from ..components.custom_metric_monitorer_step import custom_metric_monitorer_step

from ..utils.enums import ComponentType


class _Placeholder:
    """[Internal] Represents a placeholder for task outputs and pipeline parameters that will be resolved later."""
    def __init__(self, pattern: str):
        self.pattern = pattern

    def __str__(self) -> str:
        return self.pattern


class _TaskOutputs:
    """
    [Internal] A dictionary-like object that generates placeholders for a Task's outputs. This enables the user to write `step1_task.outputs['output_name']`.
    """    
    def __init__(self, task_name: str):
        self._task_name = task_name

    def __getitem__(self, output_name: str) -> _Placeholder:
        """Returns a placeholder for a specific output of a task."""
        return _Placeholder(f'{{{{tasks.{self._task_name}.outputs.{output_name}}}}}')


class Task:
    """
    The user facing reference to a step added to the PipelineBuilder. This object is recieved from `PipelineBuilder.add_step()` 
    """    
    def __init__(self, name: str):
        self.name = name
        self.outputs = _TaskOutputs(self.name)
    
    def __repr__(self) -> str:
        return f"Task(name='{self.name}')"

class _PipelineParameters:
    """
    [Internal] A dictionary-like object that generates placeholders for runtime parameters. This enables users to write `builder.parameters['pipeline_parameter']`.
    """
    def __getitem__(self, key: str) -> _Placeholder:
        return _Placeholder(f'{{{{params.{key}}}}}')
    
class _ConditionGroup:
    """[Internal] Represents an if block in the pipeline graph."""
    def __init__(
        self,
        lhs_operand: Any,
        operation: str,
        rhs_operand: Any,
        name: Optional[str] = None
    ):
        if operation not in ['==', '!=', '>', '<', '>=', '<=']:
            raise ValueError(f"Unsupported operator '{operation}'. Use one of '==', '!=', '>', '<', '>=', '<='.")
        self.lhs_operand = lhs_operand
        self.operation = operation
        self.rhs_operand = rhs_operand
        self.name = name
        self.steps: List[Dict[str, Any]] = []

class PipelineBuilder:
    """
    User facig API for programmatically defining a Vertex Pipeline graph.
    """    
    def __init__(
        self,
        pipeline_name: str,
        pipeline_root: str,
        description: Optional[str] = None
    ):
        """
        Initializes the PipelineBuilder.

        Args:
            pipeline_name: Vertex AI pipeline name.
            pipeline_root: The GCS path to be used as KFP pipeline root to store pipeline artifacts.
            description: Optional description for the pipeline.
        """
        self.pipeline_name = re.sub(r'[^a-z0-9-]', '-', pipeline_name.lower())
        self.pipeline_root = pipeline_root
        self.description = description
        self.parameters = _PipelineParameters()
        self._pipeline_graph: List[Any] = [] 
        self._active_condition_group: Optional[_ConditionGroup] = None
        self._exit_notification_recipients: Optional[List[str]] = None

    def add_email_notification(
        self,
        recipients: List[str]
    ):
        """
        Sends an email notification to a list of recipients when the pipeline finishes if called on the PipelineBuilder.

        Args:
            recipients: A list of email address strings.
        """
        if self._exit_notification_recipients:
            raise ValueError('Email notification exit handler has already been added for this pipeline.')
        if not recipients:
            raise ValueError('The list of email recipients cannot be empty.')
            
        self._exit_notification_recipients = recipients

    @contextmanager
    def condition(
        self,
        lhs_operand: Any,
        operation: str,
        rhs_operand: Any,
        name: Optional[str] = None
    ):
        """
        A context manager to define a conditional block of steps.

        Args:
            lhs_operand: The LHS of the comparison. Typically a placeholder from a previous task's output.
            operation: The comparison operator ('==', '!=', etc).
            rhs_operand: The RHS of the comparison. Typically a static value (str, int, bool).
            name: The name of the group. Used as display name in UI.
        """
        if self._active_condition_group:
            raise NotImplementedError('Nested conditional blocks are not supported.')

        condition_group = _ConditionGroup(lhs_operand, operation, rhs_operand, name = name)
        self._pipeline_graph.append(condition_group)
        self._active_condition_group = condition_group
        
        try:
            yield
        finally:
            self._active_condition_group = None

    def add_step(
        self,
        name: str,
        step_type: ComponentType,
        step_function: Optional[Callable[..., Any]] = None,
        inputs: Optional[Dict[str, Any]] = None,
        after: Optional[List[Task]] = None,
        vertex_custom_job_spec: Optional[Dict[str, Any]] = None,
        metric_metadata: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> Task:
        """
        Adds a new step to the pipeline definition.

        Args:
            name: A unique name for the step.
            step_type: The type of step to add, from the ComponentType enum.
            inputs: A dictionary of inputs for the step. Values can be literals or placeholders from `builder.parameters` or other `Task.outputs`.
            after: A list of Task objects to force an execution order for steps that do not have a direct data dependency.
            vertex_custom_job_spec: A **kwargs like dictionary unpacker, with arguments to be passed to the `create_custom_training_job_from_component` wrapper method from Google Cloud Pipeline Component's CustomJob API. Only use if you want to convert your KFP components into Vertex AI Custom Training Jobs, to access parameters like `machine_type` and `service_account`. The `'display_name'` key will be mapped to the `name` argument by default. If specified otherwise, `name` will be overriden for the Custom Training Job. To see all valid keys, see their official SDK reference - [Google Cloud Pipeline Components - CustomJob](https://google-cloud-pipeline-components.readthedocs.io/en/google-cloud-pipeline-components-2.20.0/api/v1/custom_job.html#v1.custom_job.create_custom_training_job_from_component)
            metric_metadata: Required only for `ComponentType.CUSTOM_METRIC_MONITORER`. A dictionary of key-value pairs for filtering and visualization in Cloud Monitoring. The metric names in the returned dictionary are automatically added as a labels.
            **kwargs: Additional arguments specific to the component type. KFP component arguments can be passed here for ComponentType.CUSTOM steps. To see all valid additional arguments, see KFP's official SDK reference documentation - [kfp.dsl.component()](https://kubeflow-pipelines.readthedocs.io/en/sdk-2.13.0/source/dsl.html#kfp.dsl.component).
            Note: Pipeline step base images in the vp_abstractor framework follow a three level precedence hierarchy. A `base_image` **kwargs argument passed to the `PipelineBuilder.add_step()` method is given first priority. The base image generated using the `CustomImageConfig` configuration passed to the PipelineRunner comes next. This custom base image will be overriden for a particular step, if the `base_image` argument is passed to its `add_step()` method. If neither of these two are specified, the default KFP base image (currently python:3.9) will be used.

        Returns:
            A Task object representing this step, which can be used to define dependencies for subsequent steps.
        """        
        all_step_names = [s['name'] for s in self._pipeline_graph if isinstance(s, dict)] + [s['name'] for g in self._pipeline_graph if isinstance(g, _ConditionGroup) for s in g.steps]
        if name in all_step_names:
            raise ValueError(f"The step name '{name}' has been used multiple times.")
        
        if step_type == ComponentType.CUSTOM_METRIC_MONITORER:
            if not metric_metadata:
                raise ValueError('`metric_metadata` must be provided for METRIC_LOGGER steps.')
            
        step_definition = {
            'name': name,
            'step_type': step_type,
            'step_function': step_function,
            'inputs': inputs or {},
            'after': after or [],
            'vertex_custom_job_spec': vertex_custom_job_spec,
            'metric_metadata': metric_metadata,
            'kwargs': kwargs
        }
        if self._active_condition_group:
            self._active_condition_group.steps.append(step_definition)
        else:
            self._pipeline_graph.append(step_definition)

        return Task(name)
    
    def _get_step_object(
        self,
        step_definition: Dict[str, Any],
        common_base_image: Optional[str] = None
    ):
        """Creates KFP component objects using the component builder. Wraps them into Vertex AI Custom Jobs if `vertex_custom_job_spec` is specified."""
        step_type = step_definition['step_type']
        kwargs = step_definition['kwargs']

        if step_type in [ComponentType.CUSTOM, ComponentType.CUSTOM_METRIC_MONITORER]:
            if not step_definition['step_function']:
                raise ValueError(f'step_function must be provided for {step_type.value} steps.')
            
            if 'base_image' not in kwargs and common_base_image:
                kwargs['base_image'] = common_base_image
            
            kfp_component_object = ComponentCreator.create_from_function(
                step_function = step_definition['step_function'],
                **kwargs
            )
            vertex_custom_job_spec = step_definition.get('vertex_custom_job_spec')
            if vertex_custom_job_spec:
                vertex_custom_job_kwargs = {
                    'display_name': step_definition['name'],
                    **vertex_custom_job_spec 
                }

                vertex_custom_job_wrapper = create_custom_training_job_from_component(
                    component_spec = kfp_component_object.kfp_component_function,
                    **vertex_custom_job_kwargs
                )
                
                return CustomComponent(kfp_component_function = vertex_custom_job_wrapper)

            else:
                return kfp_component_object
        # elif step_type == ComponentType.MODEL_UPLOAD:
        #     step_object = model_upload_step.ModelUploadStep(**kwargs)
        # elif step_type == ComponentType.BATCH_PREDICT:
        #     step_object = batch_prediction_step.BatchPredictionStep(**kwargs)
        else:
            raise NotImplementedError(f'Invalid step type {step_type} received.')

    def _resolve_placeholders(
        self,
        value: Any,
        pipeline_tasks: Dict[str, dsl.PipelineTask],
        pipeline_params: Dict[str, Any]
    ) -> Any:
        """[Internal] Resolves placeholder objects/strings into KFP artifacts or pipeline parameters."""
        if not isinstance(value, (str, _Placeholder)):
            return value

        placeholder_str = str(value)

        task_match = re.match(r'^{{tasks\.([\w-]+)\.outputs\.([\w-]+)}}$', placeholder_str)
        if task_match:
            task_name, output_key = task_match.groups()
            if task_name not in pipeline_tasks:
                raise ValueError(f'Step {task_name} not found.')
            return pipeline_tasks[task_name].outputs[output_key]

        param_match = re.match(r'^{{params\.([\w-]+)}}$', placeholder_str)
        if param_match:
            param_key = param_match.group(1)
            if param_key not in pipeline_params:
                raise ValueError(f"Runtime parameter '{param_key}' not provided.")            
            return pipeline_params[param_key]

        return value

    def _build_kfp_pipeline(
        self,
        runtime_parameters: Dict[str, Any],
        common_base_image: Optional[str] = None
    ):
        """
        [Internal] Translates the user pipeline definition into a callable KFP pipeline function.
        Called by the PipelineRunner.
        """
        @dsl.pipeline(name = self.pipeline_name, description = self.description)
        def generated_pipeline_function(
            project_id: str,
            location: str
        ):
            def define_main_pipeline():
                pipeline_tasks: Dict[str, dsl.PipelineTask] = {}

                operator_map = {'==': operator.eq, '!=': operator.ne, '>': operator.gt, '<': operator.lt, '>=': operator.ge, '<=': operator.le}

                def _process_graph_level(
                    graph_level: List[Any],
                    global_base_image: Optional[str] = None
                ):
                    for task_group in graph_level:
                        if isinstance(task_group, dict):
                            step_definition = task_group
                            step_name = step_definition['name']
                            step_obj = self._get_step_object(step_definition, common_base_image)

                            resolved_inputs = {}
                            for key, value in step_definition['inputs'].items():
                                resolved_value = self._resolve_placeholders(value, pipeline_tasks, runtime_parameters)
                                resolved_inputs[key] = resolved_value
                            
                            # if step_definition['step_type'] not in [ComponentType.CUSTOM, ComponentType.CUSTOM_METRIC_MONITORER]:
                            #     resolved_inputs['project'] = project_id
                            #     resolved_inputs['location'] = location
                            
                            pipeline_task = step_obj.execute(**resolved_inputs)
                            pipeline_task.set_display_name(step_name)
                            pipeline_tasks[step_name] = pipeline_task

                            if step_definition['step_type'] == ComponentType.CUSTOM_METRIC_MONITORER:
                                print(f'Pairing custom metric monitorer with step: {step_name}')
                                
                                metric_dict_output = pipeline_task.output

                                metric_type_name = f'custom.googleapis.com/{self.pipeline_name}/custom_metrics'
                                print(f'Logging to pipeline-specific metric type: {metric_type_name}')

                                custom_metric_monitorer_task = custom_metric_monitorer_step(
                                    project_id = project_id,
                                    metrics = metric_dict_output, #type: ignore
                                    metadata = step_definition['metric_metadata'],
                                    metric_type_name = metric_type_name
                                )
                                custom_metric_monitorer_task.set_display_name(f'{step_name}-monitorer') #type: ignore

                            for dep_task in step_definition['after']:
                                pipeline_task.after(pipeline_tasks[dep_task.name])
                        
                        elif isinstance(task_group, _ConditionGroup):
                            condition_group = task_group
                            
                            resolved_lhs_operand = self._resolve_placeholders(
                                condition_group.lhs_operand, pipeline_tasks, runtime_parameters
                            )

                            op_function = operator_map[condition_group.operation]

                            kfp_condition = op_function(resolved_lhs_operand, condition_group.rhs_operand)

                            with dsl.If(kfp_condition, name = condition_group.name):
                                _process_graph_level(condition_group.steps, global_base_image)

                _process_graph_level(self._pipeline_graph, common_base_image)

            if self._exit_notification_recipients:
                with dsl.ExitHandler(
                    exit_task = VertexNotificationEmailOp(
                        recipients = self._exit_notification_recipients
                    ), 
                    name = 'Email Notification'
                ):
                    define_main_pipeline()
            else:
                define_main_pipeline()

        return generated_pipeline_function