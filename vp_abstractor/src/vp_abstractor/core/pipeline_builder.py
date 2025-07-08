"""
This module contains the primary user-facing API for constructing pipelines:
- Task: A lightweight reference to a step within the pipeline.
- PipelineBuilder: The main class for defining a pipeline and its steps. It
  acts as a high-level "canvas" for users to draw their pipeline graph
  without writing any KFP DSL code.
"""
from typing import Any, Callable, Dict, List, Optional

import re
from kfp import dsl

from .component_builder import ComponentCreator
from ..components import model_upload_step, batch_prediction_step

from ..utils.enums import ComponentType


class _Placeholder:
    """[Internal] Represents a placeholder for task outputs and pipeline parameters that will be resolved later."""
    def __init__(self, pattern: str):
        self.pattern = pattern

    def __str__(self) -> str:
        return self.pattern


class _TaskOutputs:
    """
    [Internal] A dictionary-like object that generates placeholders for a Task's outputs.
    This enables the user to write `step1_task.outputs["output_name"]`.
    """    
    def __init__(self, task_name: str):
        self._task_name = task_name

    def __getitem__(self, output_name: str) -> _Placeholder:
        """Returns a placeholder for a specific output of a task."""
        return _Placeholder(f'{{{{tasks.{self._task_name}.outputs.{output_name}}}}}')


class Task:
    """
    A public-facing reference to a step that has been added to the PipelineBuilder.
    Users receive this object from `PipelineBuilder.add_step()` 
    """    
    def __init__(self, name: str):
        self.name = name
        self.outputs = _TaskOutputs(self.name)
    
    def __repr__(self) -> str:
        return f"Task(name='{self.name}')"

class _PipelineParameters:
    """
    [Internal] A dictionary-like object that generates placeholders for runtime parameters.
    This enables the user to write `builder.parameters["pipeline_parameter"]`.
    """
    def __getitem__(self, key: str) -> _Placeholder:
        return _Placeholder(f'{{{{params.{key}}}}}')


class PipelineBuilder:
    """
    User facig API for programmatically defining a Vertex AI pipeline graph.
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
        self._step_definitions: List[Dict[str, Any]] = []

    def add_step(
        self,
        name: str,
        step_type: ComponentType,
        step_function: Optional[Callable[..., Any]] = None,
        inputs: Optional[Dict[str, Any]] = None,
        after: Optional[List[Task]] = None,
        **kwargs: Any
    ) -> Task:
        """
        Adds a new step to the pipeline definition.

        Args:
            name: A unique name for the step.
            step_type: The type of step to add, from the ComponentType enum.
            inputs: A dictionary of inputs for the step. Values can be static
                    or placeholders from `builder.parameters` or other `Task.outputs`.
            after: A list of Task objects to enforce execution order for steps
                   that do not have a direct data dependency.
            **kwargs: Additional arguments specific to the component type.
                      KFP component arguments can be passed here for ComponentType.CUSTOM steps.

        Returns:
            A Task object representing this step, which can be used to define
            dependencies for subsequent steps.
        """        
        if any(s['name'] == name for s in self._step_definitions):
            raise ValueError(f"The step name - '{name}' has been used multiple times.")
            
        step_definition = {
            'name': name,
            'step_type': step_type,
            'step_function': step_function,
            'inputs': inputs or {},
            'after': after or [],
            'kwargs': kwargs
        }
        self._step_definitions.append(step_definition)

        return Task(name)

    def _get_step_object(
        self,
        step_definition: Dict[str, Any]
    ):
        """Creates KFP component objects using the component builder."""
        step_type = step_definition['step_type']
        kwargs = step_definition["kwargs"]

        if step_type == ComponentType.CUSTOM:
            if not step_definition["step_function"]:
                raise ValueError("`step_function` must be provided for CUSTOM steps.")
            step_object = ComponentCreator.create_from_function(
                step_function = step_definition['step_function'],
                **kwargs
            )
        # elif step_type == ComponentType.MODEL_UPLOAD:
        #     step_object = model_upload_step.ModelUploadStep(**kwargs)
        # elif step_type == ComponentType.BATCH_PREDICT:
        #     step_object = batch_prediction_step.BatchPredictionStep(**kwargs)
        else:
            raise NotImplementedError(f"Invalid step type '{step_type}' received.")

        return step_object

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

        task_match = re.match(r"^{{tasks\.([\w-]+)\.outputs\.([\w-]+)}}$", placeholder_str)
        if task_match:
            task_name, output_key = task_match.groups()
            if task_name not in pipeline_tasks:
                raise ValueError(f"Step '{task_name}' not found.")
            return pipeline_tasks[task_name].outputs[output_key]

        param_match = re.match(r"^{{params\.([\w-]+)}}$", placeholder_str)
        if param_match:
            param_key = param_match.group(1)
            if param_key not in pipeline_params:
                raise ValueError(f"Runtime parameter '{param_key}' not provided.")            
            return pipeline_params[param_key]

        return value
    
    def _build_kfp_pipeline(
        self,
        runtime_parameters: Dict[str, Any]
    ):
        """
        [Internal] Translates the abstract pipeline definition into a concrete, callable KFP pipeline function.
        Called by the PipelineRunner.
        """        
        @dsl.pipeline(name = self.pipeline_name, description = self.description)
        def generated_pipeline_function(
            project_id: str,
            location: str
        ):
            pipeline_tasks: Dict[str, dsl.PipelineTask] = {}

            for step_definition in self._step_definitions:
                step_name = step_definition['name']
                step_obj = self._get_step_object(step_definition)

                resolved_inputs = {}
                for key, value in step_definition['inputs'].items():
                    resolved_value = self._resolve_placeholders(value, pipeline_tasks, runtime_parameters)
                    resolved_inputs[key] = resolved_value

                if step_definition["step_type"] != ComponentType.CUSTOM:
                    resolved_inputs["project"] = project_id
                    resolved_inputs["location"] = location
                
                pipeline_task = step_obj.execute(**resolved_inputs)
                
                pipeline_task.set_display_name(step_name)

                pipeline_tasks[step_name] = pipeline_task

                for dep_task in step_definition["after"]:
                    pipeline_task.after(pipeline_tasks[dep_task.name])

        return generated_pipeline_function