from kfp import dsl

class CustomComponent:
    def __init__(
        self,
        kfp_component_function
    ):
        self._kfp_component_function = kfp_component_function

    def execute(self, **kwargs):
        return self._kfp_component_function(**kwargs)


class ComponentCreator:
    @staticmethod
    def create_from_function(
        step_function,
        base_image = 'python:3.10-slim-bookworm',
        packages_to_install = None
    ) -> CustomComponent:
        kfp_component = dsl.component(
            func = step_function,
            base_image = base_image,
            packages_to_install = packages_to_install,
        )

        return CustomComponent(kfp_component_function = kfp_component)