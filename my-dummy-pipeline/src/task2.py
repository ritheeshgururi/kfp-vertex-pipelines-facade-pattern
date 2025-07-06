from kfp.dsl import Input, Output, Artifact

def task2(
    input_1: Input[Artifact],#check -> conflicting artifact type in task1.
    output_string: Output[Artifact],
    output_number: Output[Artifact]
):
    import pickle

    with open(input_1.path, "rb") as f:
        input1 = pickle.load(f)
    
    name_output_string = f"The name of task1's output is: {input1['task1_output1']}"
    output_num = input1['task1_output2'] * 2

    with open(output_string.path, "w") as f:
        f.write(name_output_string)
        
    with open(output_number.path, "w") as f:
        f.write(str(output_num))