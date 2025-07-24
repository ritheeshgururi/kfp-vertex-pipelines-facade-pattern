import joblib
from sklearn.linear_model import LogisticRegression
# from vp_abstractor.utils import prediction_utils
import prediction_utils

class MyPredictor:
    def __init__(self):
        return
            
    def load(self, artifacts_uri):
        prediction_utils.download_model_artifacts(artifacts_uri)

        self.model = joblib.load('model.joblib')

    def predict(self, instances):
        print(f'Received {len(instances)} instances for prediction.')
        predictions = self.model.predict(instances)
        return predictions.tolist()