from kfp.dsl import Output, Artifact, Dataset

def task1(
    task1_outputs: Output[Dataset]
):
    import pickle
    outputs = {
        'task1_output1': 'task_1_dummy_output',
        'task1_output2': 2
    }
    
    with open(task1_outputs.path, "wb") as f:
        pickle.dump(outputs, f)