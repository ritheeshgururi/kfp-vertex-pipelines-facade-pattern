import docker
import hashlib
import logging
import os
import tempfile
from typing import Optional, Any
from abc import ABC, abstractmethod

from docker import errors as dockererrors

from google.auth import default as get_google_credentials
from google.auth.transport.requests import Request as GoogleAuthRequest

import importlib.resources
import shutil

from ..utils.dataclasses import CustomImageConfig, ServingImageConfig

logger = logging.getLogger(__name__)

class _BaseImageBuilder(ABC):
    """
    [Internal] Abstract base class for building and pushing Docker images. Contains methods for hashing, checking Artifact Registry, and pushing.
    """
    PURPOSE: str
    def __init__(self, config: Any):
        """Initializes the base builder with a configuration object.
        """
        self.config = config
        try:
            self.docker_client = docker.from_env()
        except dockererrors.DockerException:
            logger.error('Docker is not running or not installed. Please start the Docker daemon.')
            raise

    def _calculate_content_hash(self) -> str:
        """Generates a SHA256 hash based on src_dir and requirements file contents.
        """
        hasher = hashlib.sha256()
        
        if getattr(self.config, 'requirements_file', None):
            req_path = os.path.join(self.config.src_dir, self.config.requirements_file)
            if not os.path.exists(req_path):
                raise FileNotFoundError(f'Requirements file not found at: {req_path}')
            with open(req_path, 'rb') as f:
                hasher.update(f.read())
        
        for root, _, files in sorted(os.walk(self.config.src_dir)):
            for name in sorted(files):
                relative_path = os.path.relpath(os.path.join(root, name), self.config.src_dir)
                hasher.update(relative_path.encode())
                with open(os.path.join(root, name), 'rb') as f:
                    hasher.update(f.read())
        return hasher.hexdigest()
    
    @abstractmethod
    def _prepare_temp_build_context(self) -> str:
        """Child class must implement this method to prepare a temporary build context that will be deleted.
        """
        pass

    @abstractmethod
    def _generate_dockerfile_content(self) -> str:
        """Child class must implement this method to generate the Dockerfile content.
        """
        pass

    def _image_exists_in_registry(
        self,
        image_uri: str,
    ) -> bool:
        """
        Checks if the Docker image URI exists in Artifact Registry.
        """
        try:
            credentials, _ = get_google_credentials()
            credentials.refresh(GoogleAuthRequest())
            registry = self.config.artifact_registry_repo.split('/')[0]
            self.docker_client.login(username = 'oauth2accesstoken', password = credentials.token, registry = registry)
            
            logger.info(f'Checking for existing {self.PURPOSE} image: {image_uri}')
            self.docker_client.images.get_registry_data(image_uri)
            logger.info(f'Found existing {self.PURPOSE} image with same hash tag in Artifact Registry.')
            return True
        except dockererrors.NotFound:
            logger.info(f'{self.PURPOSE} image with identical hash tag not found in Artifact Registry. A new {self.PURPOSE} image will be built.')
            return False
        except Exception as e:
            logger.warning(f'Could not check for existing {self.PURPOSE} image due to some error. Will build a new {self.PURPOSE} image anyway. Error: {e}')
            return False
        
    def build_and_push(
        self,
        force_rebuild: Optional[bool] = False
    ) -> str:
        """Orchestrates the build and push, using a temporary build context. Overrides the base method.
        """
        content_hash = self._calculate_content_hash()
        image_tag = f'{content_hash[:32]}'
        image_uri = f'{self.config.artifact_registry_repo}/{self.config.image_name}:{image_tag}'

        if force_rebuild:
            logger.info(f'Force rebuild requested. Skipping check for existing {self.PURPOSE} images in Artifact Registry.')
        elif self._image_exists_in_registry(image_uri):
            return image_uri

        logger.info(f'Building new {self.PURPOSE} image with tag: {image_tag}')

        temp_build_context_dir = self._prepare_temp_build_context()
        dockerfile_content = self._generate_dockerfile_content()
        
        dockerfile_path = os.path.join(temp_build_context_dir, f'Dockerfile.{image_tag}')

        with open(dockerfile_path, 'w') as f:
            f.write(dockerfile_content)

        try:
            logger.info(f'Starting Docker build for {self.PURPOSE} image')
            image, _ = self.docker_client.images.build(
                path = temp_build_context_dir,
                dockerfile = os.path.basename(dockerfile_path),
                tag = image_uri,
                rm = True
            )
            logger.info(f'Successfully built {self.PURPOSE} image: {image.tags}')

            logger.info(f'Pushing {self.PURPOSE} image to Artifact Registry')
            push_log = self.docker_client.images.push(image_uri, stream = True, decode = True)
            for line in push_log:
                if 'status' in line:
                    logger.info(line['status'])
            logger.info(f'Successfully pushed {self.PURPOSE} image.')

        except dockererrors.BuildError as e:
            logger.error(f'{self.PURPOSE} image Docker build failed.')
            for line in e.build_log:
                if 'stream' in line:
                    print(line['stream'].strip())
            raise
        finally:
            shutil.rmtree(temp_build_context_dir)
        
        return image_uri


class ComponentImageBuilder(_BaseImageBuilder):
    """Builds and pushes a custom Docker image to be used as a KFP component base image."""

    PURPOSE = 'component base'
    def __init__(self, config: CustomImageConfig):
        """Initializes the component builder."""
        super().__init__(config)

    def _prepare_temp_build_context(self) -> str:
        """Returns the source directory as the build context
        """
        temp_build_context_path = tempfile.mkdtemp()
        shutil.copytree(self.config.src_dir, temp_build_context_path, dirs_exist_ok = True)

        return temp_build_context_path

    def _generate_dockerfile_content(self) -> str:
        """
        Generates Dockerfile content for a KFP component.
        """
        dockerfile_lines = [f'FROM {self.config.python_base_image}']
        dockerfile_lines.append('WORKDIR /app')

        if not self.config.dependencies_preinstalled:
            if self.config.requirements_file:
                dockerfile_lines.append(f'COPY {self.config.requirements_file} ./requirements.txt')
                dockerfile_lines.append('RUN pip install --no-cache-dir -r requirements.txt')

        dockerfile_lines.append('COPY . ./')

        return '\n'.join(dockerfile_lines)
    

class ServingImageBuilder(_BaseImageBuilder):
    """Builds and pushes a custom Docker image for model serving on Vertex AI."""

    PURPOSE = 'serving'
    def __init__(self, config: ServingImageConfig):
        """Initializes the serving image builder.
        """
        super().__init__(config)

    def _prepare_temp_build_context(self) -> str:
        """
        Copies user's code and server template into the same context for docker build.

        Returns:
            The path to the temporary build context directory.
        """
        temp_build_context_path = tempfile.mkdtemp()
        shutil.copytree(self.config.src_dir, temp_build_context_path, dirs_exist_ok = True)

        with importlib.resources.path('vp_abstractor.serving', 'fastapi_server_template.py') as p:
            fastapi_server_template_path = p
        shutil.copy(fastapi_server_template_path, os.path.join(temp_build_context_path, 'main.py'))

        return temp_build_context_path
    
    def _generate_dockerfile_content(self) -> str:
        """
        Generates Dockerfile content the serving container.
        """
        dockerfile_lines = [f'FROM {self.config.python_base_image}']
        dockerfile_lines.append('WORKDIR /app')

        if not self.config.dependencies_preinstalled:
            dockerfile_lines.append('RUN pip install --no-cache-dir "fastapi" "uvicorn[standard]" "google-cloud-storage"')

            dockerfile_lines.append(f'COPY {self.config.requirements_file} ./requirements.txt')
            dockerfile_lines.append('RUN pip install --no-cache-dir -r requirements.txt')

        dockerfile_lines.append("COPY . .")

        user_module = os.path.splitext(self.config.prediction_script)[0]
        dockerfile_lines.append(f'ENV USER_MODULE={user_module}')
        dockerfile_lines.append(f'ENV USER_CLASS={self.config.prediction_class}')

        dockerfile_lines.append('EXPOSE 8080')

        dockerfile_lines.append('CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]')
        
        return '\n'.join(dockerfile_lines)