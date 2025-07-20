
# Unlocking the Full Power of the vp_abstractor Framework - A User Guide

## Setting the Context

Moving a machine learning model from a development environment of python scripts and ipynb notebooks to a production ready workflow is a complex task. As a data scientist/ML engineer, you've done all the hard work of iterating and experimentation for developing your models, and now you want to operationalize them. This involves building reliable, automated containerized pipelines that contain various tasks like data preprocessing, training, inference and monitoring, etc.

Evidently, there are a host of open source and GCP tools and services like Vertex Pipelines, KFP, etc that are designed exactly to address these requirements. But all of these tools, with their own learning curves, can be overwhelming and time consuming, taking weeks to fully get accustomed to, and operationalize, especially for a data scientist with no prior MLOps experience.

This is where the `vp_abstractor` framework comes into the picture. It is a powerful abstraction package that hides all of these MLOps complexities. Instead of getting into the nitty gritties of KFP or Vertex Pipelines code, using `vp_abstractor`, you can define your entire workflow using a simple central orchestration file in python, using a predefined template. The package does all the hard work under the hood, and currently offers the following features:

- Containerizing your ML tasks.

- Defining and running Vertex Al Pipelines using KFP under the hood.

- A custom base image builder for your pipeline components.

- A Vertex Al Custom Job wrapper for your pipeline components.

- A prebuilt component for model management and versioning using Vertex Al Model Registry.

- A prebuilt serving container builder.

- A prebuilt component for setting up Vertex Al Batch Prediction.

- A prebuilt component for setting up model monitoring and dashboarding using GCP's Cloud Monitoring.

- Automating your ML workload.

> Note: Some of the terms in the above feature list might not be privy to you if you are new to MLOps on GCP and Vertex Al, but this user guide gives you clear steps on what features are relavent to you, based on your goals and requirements.

This allows a data scientist or ML engineer, to focus on developing their core ML logic, while the framework handles all the repetitive plumbing work.

This document acts as a cookbook, guiding the user along each step, based on their goals and requirements.

## The ML Codebase

As a data scientist/ML engineer, you might have a complex ML code base with a directory structure in place holding multiple utility and configuration files. Lets walkthrough this using a dummy codebase with five steps, including a custom metric for monitoring. The following is the directory structure of the user's ML codebase:

> Note: Your ML codebase might be structured differently or have extra or less parts than the following dummy codebase. The `vp_abstractor` framework is well equipped to handle these variations, as long as one follows the guardrails mentioned in this document. However, the following dummy codebase has been designed keeping standard practice in mind.

```
								.
								├── config
								│ └── config.py
								├── requirements.txt
								├── tasks
								│ ├── data_drift_dummy.py
								│ ├── task1.py
								│ ├── task2.py
								│ ├── task3.py
								│ └── task4.py
								└── utils
									└── utils.py
```

The first step for the user would be to define the I/O for each of the step functions, by annotating and serializing all of the input and output artifacts of all their step files with predefined type generics, like so:

```python

#task1.py
def  task1(
	#we annotate all of the components' input and output artifacts using appropriate type generics.
	task1_outputs: Output[Dataset]
):
	#since these task functions will be containerized as self contained containers, all package and module imports have to be made inside the functions.
	import pickle
	from utils.utils import utils_function
	
	#dummy output dictionary
	outputs = {
		'task1_output1': 'task_1_dummy_output',
		'task1_output2': 2
	}
	
	#dummy util function call
	utils_function('Hello from task1')

	#we serialize all of our components' output artifacts, and save them to a predefined GCS path inside the pipeline root using the .path attribute of an Output artifact.
	with open(task1_outputs.path, 'wb') as f:
		pickle.dump(outputs, f)

```

```python
#task2.py
def task2(
	#we annotate all of the components' input and output artifacts using appropriate type generics.
	input_1: Input[Artifact],
	output_string: Output[Artifact],
	output_number: Output[Artifact],
	flag_output: OutputPath(str)
):
	import pickle
	
	#we deserialize each of our components' input artifacts using the same .path attribute
	with open(input_1.path, 'rb') as f:
		input1 = pickle.load(f)

	name_output_string = f"The name of task1's output is: {input1['task1_output1']}"
	output_num = input1['task1_output2'] * 2

	#saving our output artifacts using the .path attribute
	with open(output_string.path, 'w') as f:
		f.write(name_output_string)

	with open(output_number.path, 'w') as f:
		f.write(str(output_num))

	with open(flag_output, 'w') as f:
		f.write('True')
```

```python
#task3.py
def task3(
	#We use the Dataset, Artifact, and Model properties to help classify our I/O artifacts and better represent them in the Vertex Pipelines GUI pipeline graph
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
```

  

```python
#task4.py
def task4():
	from utils.utils import utils_function
	
	#this is one dummy task with no I/O artifacts, but with an external util function call. Such external utils and config module dependencies can only be used with custom base images. More about this below
	input_string = 'Hello from task4'
	utils_function(input_string)
```

```python
#data_drift_dummy.py

#a synthetic drift metric calculating dummy task that we will use to demonstrate the vp_abstractor framework's inbuilt monitoring capabilities
def data_drift_dummy() -> dict:
	import numpy as np
	import pandas as pd
	
	#generating dummy baseline data
	base_line = {
		'feature_1': np.random.normal(loc=100, scale=15, size=2000),
		'feature_2': np.random.normal(loc=50, scale=5, size=2000)
	}
	base_line_df = pd.DataFrame(base_line)

	#generating dummy current data
	latest = {
		'feature_1': np.random.normal(loc=105, scale=18, size=1800),
		'feature_2': np.random.normal(loc=49.5, scale=5.2, size=1800)
	}
	latest_df = pd.DataFrame(latest)

	#initializing an empty dictionary to store our custom metric names and metric data as key value pairs
	custom_drift_metrics = {}
	features = ['feature_1', 'feature_2']
	#calculating dummy drift and appending the corresponding metric key value pairs to the custom_drift_metrics dictionary
	for feature in features:
		base_mean = base_line_df[feature].mean()
		latest_mean = latest_df[feature].mean()
		mean_difference =  abs(latest_mean - base_mean)
		
		base_standard_deviation = base_line_df[feature].std()
		current_standard_deviation = latest_df[feature].std()
		standard_deviation_difference =  abs(current_standard_deviation - base_standard_deviation)

		custom_drift_metrics[f'mean_difference_{feature}'] = mean_difference
		custom_drift_metrics[f'standard_deviation_difference_{feature}'] = standard_deviation_difference
	
	#the custom monitoring task has to return a dictionary with all the metric names and metric data listed as key value pairs. This is the user's end of the contract. The logging and dashboarding of these metric values as time series objects will be done by the vp_abstractor framework behind the scenes
	return custom_drift_metrics

```

```python

#utils.py
def utils_function(input_string):
	#a dummy utils function
	print('Hello from utils function')
	print(f'Input string: {input_string}')

```

Once this is done, the user places their entire codebase into a root directory, making it accessible to a central orchestration file, like so:

```
							.
							├── run_pipeline.py
							└── src
							├── config
							│ └── config.py
							├── requirements.txt
							├── tasks
							│ ├── data_drift_dummy.py
							│ ├── task1.py
							│ ├── task2.py
							│ ├── task3.py
							│ └── task4.py
							└── utils
								└── utils.py

```

## The Orchestration File

The orchestration file in our case is `run_pipeline.py`, through which we will define and control our entire ML. pipeline. Lets start defining our `run_pipeline.py` file.

1. The first step would be to import all of our task functions from our task files as modules, like so:

```python

from src.tasks.task1 import task1
from src.tasks.task2 import task2
from src.tasks.task3 import task3
from src.tasks.task4 import task4
from src.tasks.data_drift_dummy import data_drift_dummy
```

2. Then, we Import all the required modules from the `vp_abstractor` package:
```python
from vp_abstractor import PipelineBuilder, PipelineRunner, ComponentType, CustomImageConfig
```

3. The first step towards building our pipeline is initializing a `PipelineBuilder` object, like so:
```python
		builder = PipelineBuilder(
			pipeline_name = 'your-pipeline-name',
			pipeline_root = 'gs://path/to/a/directory/in/a/GCS/bucket',
			description = 'Optional description of the pipeline'
		)
```

As you can see, there are two required arguments that the `PipelineBuilder` object takes. `pipeline_name` will be used as the Vertex Pipeline display name, and the GCS URI passed to the `pipeline_root` parameter will be used to store the I/O artifacts of the pipeline components in.

4. Next, if you would like to be notified about the pipeline execution status by mail, we use the `add_email_notification` method on our bullder object with a list of email recipients passed as strings like so:

```python
		builder.add_email_notification(
			recipients = ['recipient1@email.com', 'recipient2@email.com']
		)
```
> Note: This method can be called only once anywhere in the builder definition, and this is optional.

5. Now, we add start adding components to our pipeline based on their task functions, by calling the generic`.add_step()` method on our `builder` object, like so:
```python
		stepone = builder.add_step(
			name = config.TaskNames.task_one,
			step_type = ComponentType.CUSTOM,
			step_function = task1,
			packages_to_install = config.Dependencies.task_one,
			vertex_custom_job_spec = {
				'display_name': config.TaskNames.task_one,
				'service_account': config.PipelineConfig.SERVICE_ACCOUNT
			}
		) 

		steptwo = builder.add_step(
			name = config.TaskNames.task_two,
			step_type = ComponentType.CUSTOM,
			step_function = task2,
			inputs = {
				'input_1': stepone.outputs['task1_outputs']
			},
			packages_to_install = config.Dependencies.task_two,
		)
```
`.add_step()` is a very powerful generic method, that can be used to add custom and prebuilt components to our pipeline. It expects three required arguments - 
- `name` - to be used as the display name of the pipeline component
- `step_type` - an enum from the ComponentType class. This specifies what type of component we are trying to add, and also determines the arguments to be passed downstream in this component. Currently, there is one `CUSTOM` enum for custom components, ,and three pre built component enums available - `MODEL_UPLOAD`, `BATCH_PREDICT`, and `CUSTOM_METRIC_MONITORER`.
- `step_function` - The task function to be used to build the pipeline component