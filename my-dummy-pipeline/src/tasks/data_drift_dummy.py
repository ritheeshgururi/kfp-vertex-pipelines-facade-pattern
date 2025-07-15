def data_drift_dummy() -> dict:
    import numpy as np
    import pandas as pd
        
    base_line = {
        'feature_1': np.random.normal(loc=100, scale=15, size=2000),
        'feature_2': np.random.normal(loc=50, scale=5, size=2000)
    }
    base_line_df = pd.DataFrame(base_line)

    latest = {
        'feature_1': np.random.normal(loc=105, scale=18, size=1800),
        'feature_2': np.random.normal(loc=49.5, scale=5.2, size=1800)
    }
    latest_df = pd.DataFrame(latest)

    custom_drift_metrics = {}
    features = ['feature_1', 'feature_2']
    for feature in features:
        base_mean = base_line_df[feature].mean()
        latest_mean = latest_df[feature].mean()
        mean_difference = abs(latest_mean - base_mean)
        
        base_standard_deviation = base_line_df[feature].std()
        current_standard_deviation = latest_df[feature].std()
        standard_deviation_difference = abs(current_standard_deviation - base_standard_deviation)
        
        custom_drift_metrics[f'mean_difference_{feature}'] = mean_difference
        custom_drift_metrics[f'standard_deviation_difference_{feature}'] = standard_deviation_difference

    return custom_drift_metrics