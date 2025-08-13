import joblib
from sklearn.linear_model import LogisticRegression
# from vp_abstractor.utils import prediction_utils
import prediction_utils

class MyPredictor:
    def __init__(self):
        self.model = None

    def load(self, artifacts_uri):
        prediction_utils.download_model_artifacts(artifacts_uri)

        self.model = joblib.load('model (2).joblib')

    def predict(self, instances):
        print(f'Received {len(instances)} instances for prediction.')

        try:
            processed_instances = [[instance['feature_1']] for instance in instances]
        except Exception as e:
            raise e
        
        print(f'Processed instances: {processed_instances}')
        predictions = self.model.predict(processed_instances)#type: ignore

        return predictions.tolist()