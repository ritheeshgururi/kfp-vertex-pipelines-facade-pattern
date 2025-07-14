import docker
import hashlib
import logging
import os
import tempfile
from dataclasses import dataclass
from typing import Optional

from docker import errors as dockererrors

from google.auth import default as get_google_credentials
from google.auth.transport.requests import Request as GoogleAuthRequest

logger = logging.getLogger(__name__)

@dataclass
class CustomImageConfig:
    """
    Configuration to automatically build and use a custom base image for the pipeline components. This is useful when:
        1. Your step files use external file dependencies like utils or config files.
        2. Your pipeline steps have many common package dependencies that you would rather bake once into a common component base image at build time, than go for redundant installations at runtime.
        Note: Pipeline step base images in the vp_abstractor framework follow a three level precedence hierarchy. A `base_image` **kwargs argument passed to the `PipelineBuilder.add_step()` method is given first priority. The base image generated using the `CustomImageConfig` configuration passed to the PipelineRunner comes next. This custom base image will be overriden for a particular step, if the `base_image` argument is passed to its `add_step()` method. If neither of these two are specified, the default KFP base image (currently python:3.9) will be used.

    Args:
        src_dir: Path to a root directory containing all the pipeline step files and other file dependencies.
        python_base_image: A Python base image to be used as the base image for building the component base image docker container. Goes into the FROM command in the Dockerfile.
        artifact_registry_repo: The URI of a pre-created Artifact Registry repository to push the component base image to.
        image_name: The image name to be used in the Artifact Registry repository for the component base image.
        requirements_file: Optional. The path to a requirements.txt file relative to the path passed to `src_dir`. Use this to install any package dependencies common to most of the pipeline components at build time.
    """
    src_dir: str
    python_base_image: str
    artifact_registry_repo: str
    image_name: str
    requirements_file: Optional[str] = None


class ImageBuilder:
    """Builds and pushes a custom Docker image to Artifact Registry."""

    def __init__(self, config: CustomImageConfig):
        """Initializes the ImageBuilder with CustomImageConfig configuration."""
        self.config = config
        try:
            self.docker_client = docker.from_env()
        except dockererrors.DockerException:
            logger.error('Docker is not running or not installed. Please start the Docker daemon.')
            raise

    def _calculate_content_hash(self) -> str:
        """
        Generates a SHA256 hash based on the contents of specified directories and the requirements file. This hash will be used as the image tag.
        """
        hasher = hashlib.sha256()
        
        if self.config.requirements_file:
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

    def _generate_dockerfile_content(self) -> str:
        """Generates Dockerfile content as a string."""
        dockerfile_lines = [f'FROM {self.config.python_base_image}']

        dockerfile_lines.append('WORKDIR /app')

        if self.config.requirements_file:
            dockerfile_lines.append(f'COPY {self.config.requirements_file} ./requirements.txt')
            dockerfile_lines.append('RUN pip install --no-cache-dir -r requirements.txt')

        dockerfile_lines.append('COPY . ./')

        return '\n'.join(dockerfile_lines)

    def _image_exists_in_registry(self, image_uri: str) -> bool:
        """
        Checks if the Docker image URI with same hash tag exists in Artifact Registry. This uses the Docker client to try to pull the manifest.
        """
        try:
            credentials, _ = get_google_credentials()
            credentials.refresh(GoogleAuthRequest())
            registry = self.config.artifact_registry_repo.split('/')[0]
            self.docker_client.login(username = 'oauth2accesstoken', password = credentials.token, registry = registry)
            
            logger.info(f'Checking for existing image: {image_uri}')
            self.docker_client.images.get_registry_data(image_uri)
            logger.info('Found existing image with same hash tag in Artifact Registry.')
            return True
        except dockererrors.NotFound:
            logger.info('Image with identical hash tag not found in Artifact Registry. A new image will be built.')
            return False
        except Exception as e:
            logger.warning(f'Could not check for existing image due to some error. Will build a new image anyway. Error: {e}')
            return False

    def build_and_push(
        self,
        force_rebuild: Optional[bool] = False
    ) -> str:
        """
        Orchestrates image build, push, and caching.

        Args:
            force_rebuild: If set to True, bypasses the check for existing images in Artifact Registry and forces a new build.
        """
        content_hash = self._calculate_content_hash()
        image_tag = f'{content_hash[:32]}'
        image_uri = f'{self.config.artifact_registry_repo}/{self.config.image_name}:{image_tag}'

        if force_rebuild:
            logger.info('Force rebuild requested. Skipping check for existing images in Artifact Registry.')
        elif self._image_exists_in_registry(image_uri):
            return image_uri

        logger.info(f'Building new image with tag: {image_tag}')

        dockerfile_content = self._generate_dockerfile_content()

        temp_dockerfile = tempfile.NamedTemporaryFile(
            mode = 'w',
            suffix = 'Dockerfile.tmp',
            delete = False
        )
        try:
            temp_dockerfile.write(dockerfile_content)
            temp_dockerfile.flush()
            logger.info('Starting Docker build')
            image, _ = self.docker_client.images.build(
                path = self.config.src_dir,
                dockerfile = temp_dockerfile.name,
                tag = image_uri,
                rm = True
            )
            logger.info(f'Successfully built image: {image.tags}')

            logger.info('Pushing image to Artifact Registry')
            push_log = self.docker_client.images.push(image_uri, stream = True, decode = True)
            for line in push_log:
                if 'status' in line:
                    logger.info(line['status'])
            logger.info('Successfully pushed image.')
                
        except dockererrors.BuildError as e:
            logger.error('Docker build failed.')
            for line in e.build_log:
                if 'stream' in line:
                    print(line['stream'].strip())
            raise
        finally:
            os.remove(temp_dockerfile.name)

        return image_uri