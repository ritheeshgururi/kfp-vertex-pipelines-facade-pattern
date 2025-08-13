import joblib
import pandas as pd
from sklearn.linear_model import LogisticRegression

def main():
    X_train_data = [[1], [2], [3], [4], [5], [6], [7], [8]]
    y_train_data = [0, 0, 0, 0, 1, 1, 1, 1]

    training_df = pd.DataFrame(X_train_data, columns = ['feature_1'])
    # training_df['target'] = y_train_data

    training_df.to_csv('training_data.csv', index = False)
    
    model = LogisticRegression().fit(X_train_data, y_train_data)
    
    joblib.dump(
        value = model,
        filename = 'model.joblib'
    )

if __name__ == '__main__':
    main()