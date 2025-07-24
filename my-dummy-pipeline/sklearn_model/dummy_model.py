import joblib
from sklearn.linear_model import LogisticRegression

def main():
    X_train = [[1], [2], [3], [4], [5], [6], [7], [8]]
    y_train = [0, 0, 0, 0, 1, 1, 1, 1]
    
    model = LogisticRegression().fit(X_train, y_train)
    
    joblib.dump(
        value = model,
        filename = 'model.joblib'
    )

if __name__ == '__main__':
    main()