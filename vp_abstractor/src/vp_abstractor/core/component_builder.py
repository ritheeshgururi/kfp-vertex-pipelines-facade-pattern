"""
This module dynamically creates KFP components from user-provided python scripts.
"""
from typing import List, Any, Callable, Optional

from kfp import dsl
from kfp.dsl import PipelineTask

class CustomComponent:
    """
    A wrapper around a dynamically generated KFP component.

    This class holds the KFP component function created from a user's script
    and provides a consistent `execute` method for the PipelineBuilder to call.
    """
    def __init__(
        self,
        kfp_component_function: Callable[..., PipelineTask]
    ):
        """
        Initializes the component wrapper.

        Args:
            kfp_component_function: The actual callable KFP component function.
        """
        self._kfp_component_function = kfp_component_function

    def execute(
        self,
        **kwargs: Any
    ) -> PipelineTask:
        """
        Executes the underlying KFP component function, creating
        a step (PipelineTask) in the pipeline graph.
        """
        return self._kfp_component_function(**kwargs)


class ComponentCreator:
    """
    Creates CustomComponent objects from KFP-aware functions.
    """
    @staticmethod
    def create_from_function(
        step_function: Callable[..., Any],
        base_image: str = 'python:3.10-slim-bookworm',
        packages_to_install: Optional[List[str]] = None
    ) -> CustomComponent:
        """
        Takes a user-provided function with KFP type annotations and applies the @dsl.component decorator to it.

        Args:
            step_function: KFP-aware Python function written by the user.
            base_image: The base Docker image to run the component in.
            packages_to_install: A list of Python packages to pip install in the container.

        Returns:
            A CustomComponent instance containing the compiled KFP component.
        """        
        if not callable(step_function):
            raise TypeError("The `step_function` must be a callable python function.")
        
        kfp_component = dsl.component(
            func = step_function,
            base_image = base_image,
            packages_to_install = packages_to_install,
        )

        return CustomComponent(kfp_component_function = kfp_component)