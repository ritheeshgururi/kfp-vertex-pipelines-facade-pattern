import re
import shutil
from pathlib import Path
from google.cloud import storage

GCS_URI_PREFIX = 'gs://'

def download_model_artifacts(artifact_uri: str) -> None:
    """Prepares model artifacts in the current working directory.

    If artifact_uri is a GCS uri, the model artifacts will be downloaded to the current working directory.
    If artifact_uri is a local directory, the model artifacts will be copied to the current working directory.
    This utility is inspired by Vertex AI Custom Prediction Routines.

    Args:
        artifact_uri (str):
            Required. The artifact uri that includes model artifacts.
    """
    print(f'Downloading model artifacts from: {artifact_uri}')
    current_dir = '.'
    
    if artifact_uri.startswith(GCS_URI_PREFIX):
        matches = re.match(f'{GCS_URI_PREFIX}(.*?)/(.*)', artifact_uri)
        if not matches:
            raise ValueError(f'Invalid GCS URI: {artifact_uri}')
        
        bucket_name, prefix = matches.groups()

        gcs_client = storage.Client()
        blobs = gcs_client.list_blobs(bucket_or_name = bucket_name, prefix = prefix)
        
        for blob in blobs:
            relative_path = blob.name[len(prefix) :].lstrip('/')
            
            if not relative_path:
                continue

            local_path = Path(current_dir, relative_path)
            local_path.parent.mkdir(parents = True, exist_ok = True)

            if not relative_path.endswith('/'):
                print(f'Downloading {blob.name} to {local_path}')
                blob.download_to_filename(str(local_path))
    else:
        print(f'Copying local artifacts from {artifact_uri} to {current_dir}')
        shutil.copytree(artifact_uri, current_dir, dirs_exist_ok = True)
    
    print('Model artifacts successfully downloaded.')