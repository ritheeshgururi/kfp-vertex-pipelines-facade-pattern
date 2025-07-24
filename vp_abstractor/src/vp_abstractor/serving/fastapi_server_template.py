"""
--- User code contract ---
The framework expects the user's predictor class to have:
1. An __init__() method that can be called with no arguments.
2. A predict(instances: list) method that takes a list of instances and returns a list of predictions.
3. A load(artifacts_uri: str) method if model artifact is to be loaded from GCS.
"""
import os
from importlib import import_module
from fastapi import FastAPI, Request

USER_MODULE_NAME = os.environ.get('USER_MODULE')
USER_CLASS_NAME = os.environ.get('USER_CLASS')
HEALTH_ROUTE = os.environ.get('AIP_HEALTH_ROUTE', '/health')
PREDICT_ROUTE = os.environ.get('AIP_PREDICT_ROUTE', '/predict')
AIP_STORAGE_URI = os.environ.get('AIP_STORAGE_URI')

if not USER_MODULE_NAME or not USER_CLASS_NAME:
    raise ValueError('Required environment variables USER_MODULE and USER_CLASS are not set.')

app = FastAPI()

print(f'Loading predictor {USER_CLASS_NAME} from module - {USER_MODULE_NAME}')
try:
    module = import_module(USER_MODULE_NAME)
    PredictorClass = getattr(module, USER_CLASS_NAME)

    predictor = PredictorClass()
    
    if hasattr(predictor, 'load'):
        if not AIP_STORAGE_URI:
           raise RuntimeError('Predictor has a load method but AIP_STORAGE_URI is not set.')
        print(f'Predictor has a .load() method. Calling it with artifacts from {AIP_STORAGE_URI}')
        predictor.load(artifacts_uri = AIP_STORAGE_URI)
    
    print('Predictor loaded and configured successfully.')
except Exception as e:
    print(f'Error loading predictor: {e}')

@app.get(HEALTH_ROUTE, status_code = 200)
async def health():
    """Health check endpoint required by Vertex AI"""
    return {'status': 'ok'}

@app.post(PREDICT_ROUTE)
async def predict(request: Request):
    """Prediction endpoint required by Vertex AI."""
    try:
        body = await request.json()
        instances = body['instances']
        
        predictions = predictor.predict(instances = instances)
        
        return {'predictions': predictions}
    except Exception as e:
        print(f'Prediction failed with error: {e}')
        return {'error': str(e)}, 500