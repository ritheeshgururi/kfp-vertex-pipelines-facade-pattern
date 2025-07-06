from kfp import dsl

class CustomComponent:
    def __init__(self, kfp_component_func):
        self._kfp_component_func = kfp_component_func

    def execute(self, **kwargs):
        return self._kfp_component_func(**kwargs)


class ComponentFactory:
    @staticmethod
    def create_from_function(
        user_func,
        base_image = 'python:3.10-slim-bookworm',
        packages_to_install = None,
    ) -> CustomComponent:
        kfp_component = dsl.component(
            func = user_func,
            base_image = base_image,
            packages_to_install = packages_to_install or [],
        )

        return CustomComponent(kfp_component_func = kfp_component)