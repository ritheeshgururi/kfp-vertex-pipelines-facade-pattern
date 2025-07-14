from kfp.dsl import Input, Output, Artifact, Model

def task3(
    input_1: Input[Artifact],
    input_2: Input[Artifact],
    final_output_artifact: Output[Model]
):
    with open(input_1.path, 'r') as f:
        input_string = f.read()
        
    with open(input_2.path, 'r') as f:
        input_number_str = f.read()

    final_output = f'{input_string} + {input_number_str}'
    
    print(f"Final combined output: '{final_output}'")

    with open(final_output_artifact.path, 'w') as f:
        f.write(final_output)