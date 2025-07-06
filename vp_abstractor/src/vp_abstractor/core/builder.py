import re
from kfp import dsl

from .component_factory import ComponentFactory
from ..components import model_upload_step, batch_prediction_step

from ..utils.enums import ComponentType


class _Placeholder:
    def __init__(self, pattern):
        self.pattern = pattern

    def __str__(self):
        return self.pattern


class _TaskOutputs:
    def __init__(self, task_name):
        self._task_name = task_name

    def __getitem__(self, key):
        return _Placeholder(f"{{{{tasks.{self._task_name}.outputs.{key}}}}}")


class Task:
    def __init__(self, name):
        self.name = name
        self.outputs = _TaskOutputs(task_name = name)


class _PipelineParameters:
    def __getitem__(self, key):
        return _Placeholder(f"{{{{params.{key}}}}}")


class PipelineBuilder:
    def __init__(
        self,
        pipeline_name,
        pipeline_root,
        description = None
    ):
        self.pipeline_name = pipeline_name
        self.pipeline_root = pipeline_root
        self.description = description
        self.parameters = _PipelineParameters()
        self._steps = []
        self._step_objects = {}

    def add_step(
        self,
        name,
        step_type,
        step_function = None,
        inputs = None,
        after = None,
        **kwargs,
    ):
        step_definition = {
            "name": name,
            "step_type": step_type,
            "user_function": step_function,
            "inputs": inputs or {},
            "after": after or [],
            "kwargs": kwargs,
        }
        self._steps.append(step_definition)

        return Task(name = name)

    def _get_step_object(self, step_def):
        name = step_def["name"]
        if name in self._step_objects:
            return self._step_objects[name]

        step_type = step_def["step_type"]
        kwargs = step_def["kwargs"]
        step_obj = None

        if step_type == ComponentType.CUSTOM:
            step_obj = ComponentFactory.create_from_function(
                user_func = step_def["user_function"],
                **kwargs
            )
        # elif step_type == ComponentType.MODEL_UPLOAD:
        #     step_obj = model_upload_step.ModelUploadStep(**kwargs)
        # elif step_type == ComponentType.BATCH_PREDICT:
        #     step_obj = batch_prediction_step.BatchPredictionStep(**kwargs)

        self._step_objects[name] = step_obj
        return step_obj

    def _resolve_placeholders(
        self,
        value,
        kfp_tasks,
        pipeline_params
    ):
        if not isinstance(value, (str, _Placeholder)):
            return value

        placeholder_str = str(value)

        task_match = re.match(r"^{{tasks\.([\w-]+)\.outputs\.([\w-]+)}}$", placeholder_str)
        if task_match:
            task_name, output_key = task_match.groups()
            return kfp_tasks[task_name].outputs[output_key]

        param_match = re.match(r"^{{params\.([\w-]+)}}$", placeholder_str)
        if param_match:
            param_key = param_match.group(1)
            return pipeline_params[param_key]

        return value
    
    def _build_kfp_pipeline(self, runtime_parameters):
        @dsl.pipeline(name = self.pipeline_name, description = self.description)
        def generated_pipeline_func(
            project_id: str,
            location: str
        ):
            kfp_tasks = {}

            for step_def in self._steps:
                step_name = step_def["name"]
                step_obj = self._get_step_object(step_def)

                resolved_inputs = {
                    key: self._resolve_placeholders(val, kfp_tasks, runtime_parameters)
                    for key, val in step_def["inputs"].items()
                }

                # if step_def["step_type"] != ComponentType.CUSTOM:
                #     resolved_inputs["project"] = project_id
                #     resolved_inputs["location"] = location
                
                kfp_task = step_obj.execute(**resolved_inputs)
                
                kfp_task.set_display_name(step_name)

                kfp_tasks[step_name] = kfp_task

                for dep_task in step_def["after"]:
                    kfp_task.after(kfp_tasks[dep_task.name])

        return generated_pipeline_func