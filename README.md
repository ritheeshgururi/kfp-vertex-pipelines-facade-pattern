## Local ML Scripts to Vertex AI Pipelines using vp_abstractor: A User Guide

This guide is a walk through of the process of taking your existing local Python scripts for machine learning and transforming them into a robust, automated pipeline on GCP's Vertex AI.

### Understanding the Template

When you open the template project (`dummy-inference-pipeline`), you'll see a few key files and directories. Out of these:

1.  `src/tasks/`: This is where your ML logic lives. You will place your Python scripts for things like data fetching, preprocessing, and prediction here.
2.  `run_pipeline.py`: This is the main "orchestrator" script. Here, you will define the sequence of your tasks and how they connect to each other to form a pipeline.
3.  `config.py`: A configuration file for things like project IDs, file paths, and model names.

The core workflow is:

1.  **Adapt**  your Python functions in  `src/tasks/`  to be compatible with the pipeline.
2.  **Assemble**  these adapted functions into a pipeline in  `run_pipeline.py`.
3.  **Configure**  your settings in  `config.py`.
4.  **Run**  the pipeline from your terminal.

----------

### Step 1: Adapting Your Python Functions for the Pipeline

A pipeline runs each of your functions (we'll call them "steps") in its own isolated, containerized environment. To pass data from one step to the next (e.g., passing a preprocessed DataFrame to a prediction step), we can't just  `return`  a variable. Instead, we must save the data to a file that the pipeline orchestrator knows how to manage.

Let's say you have a local preprocessing function like this:

```python
# Your local script (e.g., local_preprocess.py)
import pandas as pd

def preprocess_data(input_csv_path, id_column):
    df = pd.read_csv(input_csv_path)
    
    ids_df = df[[id_column]].copy()
    
    df = df.fillna(0)
    
    return df, ids_df
```

To make this function work in the pipeline, you need to make two key changes:

1.  Add special  **type annotations**  to the function signature for inputs and outputs.
2.  Use the  **`.path`  attribute**  of these annotated outputs to save your data in a preferred file format of yours.

After making these changes, this is the version which is compatible with the pipeline template. You can see this exact pattern in  `src/tasks/preprocessing.py`  in the template.

```python
# The pipeline-ready version (e.g., src/tasks/preprocessing.py)
import pandas as pd
from kfp.dsl import Input, Output, Dataset # <-- Import the annotations

def preprocessing(
    raw_data: Input[Dataset],          # <-- Annotate input artifact
    id_column: str,                    # <-- Simple variables are fine
    processed_features: Output[Dataset], # <-- Annotate output artifact
    original_ids: Output[Dataset]      # <-- Annotate output artifact
):
    # Use .path to read from the input artifact
    df = pd.read_parquet(raw_data.path)
    
    ids_df = df[[id_column]].copy()

    df = df.fillna(0)
    
    # Use .path to write to the output artifacts
    df.to_parquet(processed_features.path, index=False)
    ids_df.to_parquet(original_ids.path, index=False)
```

#### Understanding the Type Annotations

These annotations from  `kfp.dsl`  are how you tell the pipeline what kind of data your function expects and produces.

-   `Input[...]`: Use this for any file-based input that is the result of a previous pipeline step.
-   `Output[...]`: Use this for any file-based output you want to create and pass to a future step.
-   `Dataset`,  `Model`,  `Artifact`: These are common types you place inside  `Input`  and  `Output`. Use  `Dataset`  for tabular data,  `Model`  for model files, and  `Artifact`  for anything else.
-   `OutputPath(str)`,  `OutputPath(int)`  etc: Use this special annotation for simple, non-file outputs like a status string or a count of rows. Instead of saving a DataFrame, you'd just write the string or number to the given path.
    -   **Example:**  In  `src/tasks/data_fetching.py`,  `destination_type: OutputPath(str)`  is used to output a string ('gcs' or 'bigquery') which is then used for conditional logic in the pipeline.

**The Golden Rule:**  If you are passing data  _between steps_, it must be an  `Input`/`Output`  artifact. Regular arguments like  `id_column: str`  are used for passing simple, static values (like configuration parameters) into a step.

### Step 2: Assembling the Pipeline in the Pipeline Orchestrator file:

Now that we have adapted our Python functions into pipeline-ready steps, we can define how they connect and in what order they should run. We will do this in the  `run_pipeline.py`  file.

This file has two main parts:

-   A  `build_pipeline()`  function where we  **define the blueprint**  of the pipeline.
-   A  `main()`  function where we  **configure the execution**  and run the pipeline.

#### Defining the Pipeline Blueprint (`build_pipeline`  function)

Here, we will use the  `PipelineBuilder`  to add our steps and define the flow of data between them.

Let's look at the core of the  `build_pipeline`  function from the template:

```python
# In run_pipeline.py

from vp_abstractor import PipelineBuilder, ComponentType
from src.tasks.data_fetching import data_fetching
from src.tasks.preprocessing import preprocessing
import config

def build_pipeline():
    builder = PipelineBuilder(
        pipeline_name="inference-dummy-model",
        pipeline_root=config.PipelineConfig.PIPELINE_ROOT,
        description='A pipeline to run inference.'
    )
    
    # --- Step 1: Data Fetching ---
    data_fetching_task = builder.add_step(
        name="data-fetching",
        step_type=ComponentType.CUSTOM,
        step_function=data_fetching,
        inputs={
            'project_id': config.PipelineConfig.PROJECT_ID,
            'source_type': config.LiteralInputs.SOURCE_TYPE,
            # ... other inputs
        }
    )
    
    # --- Step 2: Preprocessing ---
    preprocessing_task = builder.add_step(
        name="preprocessing",
        step_type=ComponentType.CUSTOM,
        step_function=preprocessing,
        inputs={
            'raw_data': data_fetching_task.outputs['df_output'], # <-- connection from previous step.
            'id_column': config.LiteralInputs.ID_COLUMN,
            # ... other inputs
        }
    )

    return builder
```

##### Adding a Step with  `builder.add_step()`

The  `builder.add_step()`  method is how we add each of our functions to the pipeline. It takes a few key arguments:

-   `name`: A unique, human-readable name for this step (e.g.,  `"data-fetching"`). This is what is seen in the Vertex AI pipeline graph.
-   `step_type`: Specifies what kind of step this is. For custom Python functions, we will almost always use  **`ComponentType.CUSTOM`**. We will cover other types later.
-   `step_function`: The actual Python function to be run. Simply import it from the  `src/tasks/`  directory and pass it here (e.g.,  `step_function = data_fetching`).
-   `inputs`: A dictionary defining all the arguments for the  `step_function`. This is how we pass data into our step.

> Note: the `.add_step()` method takes all of [kfp.dsl's component decorator](https://www.kubeflow.org/docs/components/pipelines/user-guides/components/lightweight-python-components/) arguments as key word arguments inherently. In case you want to use any additional functionality of kfp.dsl's component decorator, refer to [KFP's official SDK reference](https://kubeflow-pipelines.readthedocs.io/en/stable/source/dsl.html#:~:text=kfp.dsl.component(,%3A%20bool%20%3D%20False)).

##### Connecting Steps: Using  `task.outputs`

This is how we create the pipeline graph. When we call  `builder.add_step()`, it returns a  `Task`  object (e.g.,  `data_fetching_task`). This object acts as a reference to our step and, holds its outputs.

Notice this line in the  `preprocessing`  step's inputs:  
`'raw_data': data_fetching_task.outputs['df_output']`

Let's break it down:

-   `data_fetching_task`: The reference to our first step.
-   `.outputs`: Accesses the collection of outputs from that task.
-   `['df_output']`: The name of the specific output artifact we want, which matches the argument name in our  `data_fetching`  function signature (`df_output: Output[Dataset]`).

This line basically tells the pipeline: "Take the  `df_output`  artifact produced by the  `data-fetching`  step and feed it into the  `raw_data`  input of the  `preprocessing`  step." This is the primary way we will chain our steps together.

#### Configuring the Execution (`main`  function)

The  `main`  function's job is to prepare the  `PipelineRunner` that will compile and execute the pipeline - and then run it.

```python
# In run_pipeline.py
def main():
    builder = build_pipeline() # Gets the blueprint we just defined
    
    runner = PipelineRunner(
        project_id = config.PipelineConfig.PROJECT_ID,
        location = config.PipelineConfig.LOCATION,
        # ... other configurations
        custom_base_image_config=CustomImageConfig(...) # More on this later
    )
    
    runner.run(
        pipeline_builder = builder,
        wait = True
    )
```

1.  **Instantiate  `PipelineRunner`**: We create a  `PipelineRunner`  object, providing our GCP project details and other high-level configurations from  `config.py`.
2.  **Call  `runner.run()`**: This is the final command that kicks off the entire process. It takes our  `builder`  blueprint and submits it to Vertex AI.

### Step 3: Advanced Pipeline Features

Now that we understand the basics of creating steps and linking them, let's explore some of the more advanced capabilities of the template. These features help us to manage dependencies, use powerful pre-built components, and control the flow of the pipeline.

#### Managing Python Dependencies

Any Python script will require external libraries like  `pandas`,  `scikit-learn`, or  `gcsfs`. The pipeline needs to know which packages to install in the container for each step. We have two primary ways to manage this.

##### Option 1: Quick and Easy (`packages_to_install`)

For steps that have only a few, unique dependencies, you can list them directly in the  `builder.add_step()`  call.

This is the simplest method and is great for quick additions or prototyping.

```python
# In run_pipeline.py
from src.tasks.postprocessing_gcs import postprocessing_gcs

# ... inside build_pipeline() ...

postprocessing_gcs_task = builder.add_step(
    name="postprocessing-gcs",
    step_type=ComponentType.CUSTOM,
    step_function=postprocessing_gcs,
    inputs={...},
    packages_to_install=[
        "pandas==1.5.3", 
        "gcsfs"
    ]
)
```

**When to use this:**

-   When a single step needs a specific package that other steps don't.
-   When we are quickly testing a new step or library.

##### Option 2: Robust and Recommended (Common Base Image)

Imagine you have ten different steps in your pipeline, and all of them use  `pandas`,  `numpy`, and  `scikit-learn`. Using  `packages_to_install`  for each one would be repetitive and inefficient, as the pipeline would have to re-install those same packages ten times at run time.

The better solution is to build a  **single, common base Docker image**  that has all your shared dependencies pre-installed. The pipeline will then use this image as the starting point for all your steps, saving significant time.

The template makes this easy. You don't need to write a Dockerfile, build it or push it to remote repository. You just need to give some configuration in  `run_pipeline.py`  and list your dependencies in  `src/requirements.txt`, and the rest will be done automatically by vp_abstractor behind the scenes.

**How to do it:**

1.  **List your dependencies:**  Open the  `src/requirements.txt`  file and list all the common packages your tasks need.
    
    ```
    # In src/requirements.txt
    pandas
    scikit-learn
    google-cloud-bigquery
    gcsfs
    ```
    
2.  **Configure the  `CustomImageConfig`:**  In the  `main()`  function of  `run_pipeline.py`, you'll see a section for  `custom_base_image_config`.
    
    ```python
    # In run_pipeline.py -> main() function
    from vp_abstractor import PipelineRunner, CustomImageConfig
    import config
    
    runner = PipelineRunner(
        project_id = config.PipelineConfig.PROJECT_ID,
        location = config.PipelineConfig.LOCATION,
        # This part tells the runner to build a base image
        custom_base_image_config=CustomImageConfig(
            src_dir = "src", # Looks for code and requirements in the 'src' folder
            artifact_registry_repo = config.BaseImageConfig.artifact_registry_repo,
            image_name = config.BaseImageConfig.image_name,
            requirements_file = "requirements.txt" # Points to your requirements file
        )
    )
    ```    

**When to use this:**

-   This is the  **recommended approach for most pipelines**.
-   When multiple steps share the same set of dependencies.
-   When your tasks depend on local utility files or modules within your  `src`  directory, as this method packages your entire  `src`  folder into the image.

**What about precedence?**  The framework is smart. If you configure a  `custom_base_image_config`  AND provide a  `packages_to_install`  list for a specific step, the pipeline will start with the common base image and then install the  _additional_  packages for that one step. This gives you the best of both worlds.

-----------

Beyond running our own custom Python functions, the  `vp_abstractor`  framework provides pre-built components for common MLOps tasks. Using them is as simple as adding a custom step, but we don't need to provide a  `step_function`. The framework handles the logic for us.

#### Model Inference: [Vertex AI Batch Prediction](https://cloud.google.com/vertex-ai/docs/predictions/get-batch-predictions#aiplatform_batch_predict_custom_trained-python_vertex_ai_sdk)

This is relavent if one choses to use [Vertex AI's Batch Prediction managed service](https://cloud.google.com/vertex-ai/docs/predictions/get-batch-predictions#aiplatform_batch_predict_custom_trained-python_vertex_ai_sdk) instead of running predictions inside a pipeline component.

This workflow involves two main parts:

1.  **Registering our model**  with the [Vertex AI Model Registry](https://cloud.google.com/vertex-ai/docs/model-registry/introduction).
2.  **Calling the Batch Prediction**  service using that registered model.

The template provides pre-built components for both of these, so we don't have to write the code ourselves.

##### Using the  `MODEL_UPLOAD`  Component

Before we can use a model for batch prediction, it needs to be in the [Vertex AI Model Registry](https://cloud.google.com/vertex-ai/docs/model-registry/introduction). This step usually involves packaging your model artifacts (like a  `model.pkl`  and a  `preprocessor.pkl`) with a serving container that knows how to load and use them.

We will see a separate  `model_upload_pipeline.py`  in the template. Its sole purpose is to handle this process. The key step in that file looks like this:

```python
# In model_upload_pipeline.py
from vp_abstractor import ComponentType, ModelUploadConfig

# ... inside build_pipeline() ...
model_upload_task = builder.add_step(
    name='upload-dummy-model',
    step_type=ComponentType.MODEL_UPLOAD, # <-- Use the pre-built component type
    inputs=ModelUploadConfig(
        display_name=config.DummyModelUpload.model_display_name,
        artifact_uri=config.DummyModelUpload.gcs_model_artifact_uri,
        serving_container_image_uri=builder.images[...], # <-- URI of the serving image
    )
)
```

-   `step_type=ComponentType.MODEL_UPLOAD`: This tells the builder to use the pre-built model uploading component.
-   `inputs=ModelUploadConfig(...)`: We pass the configuration for the model upload using the  `ModelUploadConfig`  dataclass. This includes the model's display name and the GCS path to its artifacts. We'll discuss the  `serving_container_image_uri`  in the next section on model serving.

> Note: Using the Model Upload pre-built component is usually a one-time process for inference-only pipelines. Therefore, the Model Upload prebuilt component can be used in a separate one-time Model Upload pipeline along with the serving image builder, or can be made a part of a training pipeline, if that is in the picture.

##### Using the  `BATCH_PREDICT`  Component

Once our model is in the registry, we can use it in the main inference pipeline (`run_pipeline.py`).

```python
# In run_pipeline.py
from vp_abstractor import ComponentType, BatchPredictionConfig

# ... inside build_pipeline() ...
batch_predict_task = builder.add_step(
    name="batch-predict-dummy-model",
    step_type=ComponentType.BATCH_PREDICT, # <-- Use the pre-built component type
    inputs=BatchPredictionConfig(
        job_display_name="dummy-inference",
        model_resource_name=config.DummyBatchPrediction.model_resource_name,
        gcs_source_uris=["gs://path/to/your/prediction_data.jsonl"],
        gcs_destination_prefix="gs://path/for/your/results/",
        # ... other batch prediction settings
    ),
    after=[preprocessing_task] # Enforce execution order
)
```

-   `step_type=ComponentType.BATCH_PREDICT`: Tells the builder to use the pre-built batch prediction component.
-   `inputs=BatchPredictionConfig(...)`: We configure the job using the  `BatchPredictionConfig`  dataclass. We provide the  `model_resource_name`  (which we get after running the model upload pipeline), a `gcs_source_uris` list, and a GCS path for the output (`gcs_destination_prefix`).
-   `after=[preprocessing_task]`: The batch prediction job reads a file from GCS that our preprocessing step creates. Because there is no  _direct_  artifact being passed between them, the pipeline doesn't automatically know the order.  `after`  lets us explicitly tell the pipeline to start this  `batch_predict_task` after the  `preprocessing_task`  has successfully finished."

> Note: It is the responsibility of the user to save their prediction data as JSONL files to a GCS bucket in upstream steps, in order to use the Batch Prediction prebuilt component by passing the saved JSONL file paths to the `gcs_source_uris` parameter in `BatchPredictionConfig`.
 
----------------

In the last section, we saw how to use the  `MODEL_UPLOAD`  component. A key part of that process is providing a  `serving_container_image_uri`. This container is a Docker image that holds your model and the code needed to serve predictions.

This might sound complex, but the template is designed to build this container for us automatically. All we need to do is provide a Python class that follows a specific contract.

#### Creating a [Custom Serving Container](https://cloud.google.com/vertex-ai/docs/predictions/use-custom-container) with a  `Predictor`  Class

The framework will automatically wrap your model logic in a production-ready web server (FastAPI). To enable this, you must create a special  `Predictor`  class.

In the template, navigate to the  `src/model_server/`  directory. You will find:

-   `predictor.py`: This is where we will write our  `Predictor`  class.
-   `requirements.txt`: The specific Python dependencies needed for our model to run (e.g.,  `scikit-learn`,  `xgboost`).

Let's look at  `src/model_server/predictor.py`:

```python
# In src/model_server/predictor.py
import pickle
import pandas as pd
from vp_abstractor.utils import prediction_utils # <-- helper module

class MyPredictor(object):
    def __init__(self):
        """Called when the server starts. Initialize variables here."""
        self._model = None
        self._model_file = "model.pkl"

    def load(self, artifacts_uri: str):
        """Called by the framework to load your model files."""
        # 1. Download all files from the GCS path to the local container
        prediction_utils.download_model_artifacts(artifacts_uri)
        
        # 2. Load the model file(s) into memory
        with open(self._model_file, "rb") as f:
            self._model = pickle.load(f)

    def predict(self, instances: list):
        """The core prediction logic. Receives a list of instances."""
        df = pd.DataFrame(instances)
        probabilities = self._model.predict_proba(df)
        # The return value must be a list
        return probabilities[:, 1].tolist()
```

##### The Predictor Contract

Your class  **must**  follow this structure:

1.  **An  `__init__(self)`  method:**
    
    -   This is called when the prediction server first starts up.
    -   It should take no arguments other than  `self`.
    -   Use it to initialize any variables, like the placeholder for your model object (`self._model = None`).
2.  **A  `load(self, artifacts_uri: str)`  method:**
    
    -   The framework calls this method after  `__init__`  and passes in the GCS path where your model artifacts are stored (`artifact_uri`). This is the same path you specify in  `ModelUploadConfig`.
    -   Your job is to load your model files from that location.
    -   **Best Practice:**  The template provides the  `prediction_utils.download_model_artifacts()`  helper function. Simply call this first. It handles all the logic of downloading the files from GCS to the container's local disk. Then, you can open the files locally as you normally would (e.g.,  `with open("model.pkl", "rb")`).
3.  **A  `predict(self, instances: list)`  method:**
    
    -   This is where your inference logic lives.
    -   The framework calls this for every prediction request. It will pass a list of instances (e.g., a list of dictionaries:  `[{'feature_A': 10, 'feature_B': 25}, ...]`).
    -   Your method must return a list of predictions.

That's it. We write this simple class, and the framework handles the rest of the web server complexity.

#### Configuring the Serving Image Build

The final step is to tell the  `PipelineRunner`  to build this serving container. We do this in our  `model_upload_pipeline.py`  file.

```python
# In model_upload_pipeline.py -> main() function
from vp_abstractor import PipelineRunner, ServingImageConfig
import config

runner = PipelineRunner(
    project_id=config.PipelineConfig.PROJECT_ID,
    location=config.PipelineConfig.LOCATION,
    serving_image_configs=[
        ServingImageConfig(
            config_name="dummy-model-server", # A unique name for this config
            src_dir="src/model_server", # Directory containing your predictor and requirements
            prediction_script="predictor.py", # The file with your Predictor class
            prediction_class="MyPredictor",   # The name of your Predictor class
            requirements_file="requirements.txt",
            # ... other config like artifact_registry_repo and image_name
        )
    ]
)
```

The  `ServingImageConfig`  dataclass tells the  `PipelineRunner`  everything it needs to know to build your serving container automatically. When you run this pipeline, the first thing it will do is build and push this image to your Artifact Registry. Then, it will pass the final image URI to the  `MODEL_UPLOAD`  step - based on the `config_name` given, completing the process.

#### Conditional Execution: Creating Dynamic Paths

The  `PipelineBuilder`  has a  `condition`  context manager that lets us create a conditional "if block" in our pipeline graph.

In the template,  `data_fetching.py`  outputs a string indicating where the data came from. We can use this output to control the pipeline's path in  `run_pipeline.py`.

```python
# In run_pipeline.py -> build_pipeline()

# ... after the batch_predict_task is defined ...

# This is an 'if' block for the pipeline graph
with builder.condition(
    data_fetching_task.outputs['destination_type'], '==', 'gcs', 
    name='Write-to-GCS'
):
    # This step will ONLY run if the condition is true
    postprocessing_gcs_task = builder.add_step(
        name=config.TaskNames.postprocessing_gcs,
        step_type=ComponentType.CUSTOM,
        step_function=postprocessing_gcs,
        inputs={...}
    )

# This is a separate 'if' block
with builder.condition(
    data_fetching_task.outputs['destination_type'], '==', 'bigquery', 
    name='Write-to-BQ'
):
    # This step will ONLY run if this other condition is true
    postprocessing_bq_task = builder.add_step(
        name=config.TaskNames.postprocessing_bq,
        step_type=ComponentType.CUSTOM,
        step_function=postprocessing_bq,
        inputs={...}
    )
```

**How it works:**

-   `builder.condition(...)`  takes three main arguments:
    1.  The  **left-hand side**  of the comparison (e.g.,  `data_fetching_task.outputs['destination_type']`). This will be an output from a previous task.
    2.  The  **operator**  as a string (e.g.,  `'=='`,  `'!='`,  `'>'`,  `'<'`).
    3.  The  **right-hand side**  of the comparison (e.g.,  `'gcs'`). This will be a static value.
-   Any  `builder.add_step()`  calls made  _inside_  the  `with`  block will only be executed if the condition evaluates to  `True`  during the pipeline run.

#### Customizing Compute Resources

By default, each pipeline step runs on a standard, general-purpose machine. For steps that are memory-intensive or require more CPU power, you can easily assign a more powerful machine.

When you add a step, you can pass an optional  `vertex_custom_job_spec`  argument. This converts your step into a Vertex AI Custom Job, giving you access to more options.

```python
# In a run_pipeline.py file
heavy_computation_task = builder.add_step(
    name="heavy-computation-step",
    step_type=ComponentType.CUSTOM,
    step_function=my_heavy_function,
    vertex_custom_job_spec={
        'machine_type': 'n1-highmem-8', # e.g., an 8-core, high-memory machine
        'service_account': config.PipelineConfig.SERVICE_ACCOUNT
    }
)
```

-   `machine_type`: Specify any valid  [Vertex AI machine type](https://www.google.com/url?sa=E&q=https%3A%2F%2Fcloud.google.com%2Fvertex-ai%2Fdocs%2Ftraining%2Fconfigure-compute). This is the most common reason to use this feature.
-   You can also specify other parameters like a specific  `service_account`  for the step to use.
-   The  `display_name`  of the custom job will default to the step's  `name`, but you can override it here if needed.

#### Logging Custom Metrics

A crucial part of MLOps is monitoring. You may want to calculate metrics in a step (e.g., data drift score, feature fill rates) and log them to Google Cloud Monitoring for tracking over time.

The template provides a special component for this:  `ComponentType.CUSTOM_METRIC_MONITORER`.

**How it works:**

1.  **Write a function that outputs a dictionary:**  Create a normal custom step function, but ensure it returns a  `dict`  where keys are metric names and values are metric numbers.
    
    ```python
    # In a task file, e.g., src/tasks/data_drift_dummy.py
    
    def data_drift_dummy() -> dict:
        # Your logic to calculate metrics
        psi_score = 0.05
        feature_fill_rate = 0.98
    
        # Output a dictionary of metrics
        metrics_dict = {}
        metrics_dict['psi_score'] = psi_score
        metrics_dict['feature_fill_rate'] = feature_fill_rate

        return metrics_dict
    ```
      
2.  **Add the step with the special type:**  In your  `build_pipeline`  function, add the step and set the  `step_type`  to  `CUSTOM_METRIC_MONITORER`. You must also provide  `metric_metadata`  for labeling your metrics in Cloud Monitoring.
    
    ```python
    # In run_pipeline.py -> build_pipeline()
    monitoring_task = builder.add_step(
        name="data-drift-monitoring",
        step_type=ComponentType.CUSTOM_METRIC_MONITORER,
        step_function=data_drift_dummy,
        metric_metadata={
            "model_name": "dummy-model",
            "pipeline_version": "v1.2"
        }
    )
    ```
    

This will automatically add a second, hidden step to your pipeline that takes the dictionary from your function and logs each key-value pair to Google Cloud Monitoring, tagged with the metadata you provided.

### Step 4: Summary & Quick Reference

This section provides a high-level summary of the key components you will interact with when building pipelines using the template.

#### Core Workflow Recap

1.  **Write Logic:**  Create standard Python functions for each task in your workflow. Place them in  `src/tasks/`.
2.  **Adapt Functions:**  Add  `kfp.dsl`  type annotations (`Input`,  `Output`,  `Dataset`,  `OutputPath`) to the function signatures. Use the  `.path`  attribute to read and write artifacts.
3.  **Build Pipeline:**  In  `run_pipeline.py`, use  `PipelineBuilder`  to define your pipeline.
    -   Call  `builder.add_step()`  for each task.
    -   Link steps by passing  `task.outputs['...']`  from one step to the  `inputs`  of another.
4.  **Configure Runner:**  In  `run_pipeline.py`, instantiate the  `PipelineRunner`  with your GCP settings and any image build configurations (`CustomImageConfig`  or  `ServingImageConfig`).
5.  **Run:**  Call  `runner.run()`  or  `runner.schedule()`  to execute your pipeline.

#### Key Class:  `PipelineBuilder`

This is the main object for defining your pipeline's structure in  `run_pipeline.py`.

| Method/Property | Purpose |
|---|---| 
| `__init__(...)` | Initializes the builder. You provide the `pipeline_name` and `pipeline_root` (GCS path for artifacts).|
| `add_step(...)` | The most important method. Adds a new task to the pipeline. See its key arguments below. |
| `condition(...)` | A context manager (with `builder.condition(...)`) for adding if-then logic to your pipeline graph. |
| `add_email_notification(...)` | Adds a final step that sends an email notification on pipeline completion (success or failure). |
| `images['...']` | A placeholder for referencing a serving container image URI that will be built by the `PipelineRunner`. Used in `ModelUploadConfig`. |

#### Key Method:  `builder.add_step()`
| Argument | Purpose |
|---|---|
| `name` | **Required**. A unique string name for the step. |
| `step_type` | **Required**. Specifies the step type. Use `ComponentType.CUSTOM` for your own functions, or pre-built ones like `ComponentType.BATCH_PREDICT`. |
| `step_function` | **Required** for `CUSTOM` steps. The Python function to execute. |
| `inputs` | A dictionary of arguments to pass to your `step_function` or pre-built component. |
| `after` | A list of Task objects (e.g., `[preprocessing_task]`) to enforce execution order when there's no direct data dependency. |
| `packages_to_install` | A list of Python packages to install for this specific step (e.g., `["pandas", "scikit-learn"]`). |
| `vertex_custom_job_spec` | A dictionary to specify compute resources like `{'machine_type': 'n1-highmem-8'}`. Converts the step to a Vertex Custom Job. |
| `metric_metadata` | **Required** for `CUSTOM_METRIC_MONITORER` steps. A dictionary of labels to attach to your metrics in Cloud Monitoring. |
| `base_image` | Specify a custom Docker image URL for this step. This overrides any image set by `CustomImageConfig`. |
| `**kwargs` | `add_step` also accepts any other valid keyword argument for KFP's `@dsl.component` decorator, such as `extra_pip_index_urls`, giving you full access to underlying KFP features if needed. |

#### Key Dataclasses for Configuration

These are imported from  `vp_abstractor`  and used to configure the  `PipelineRunner`  and pre-built steps. Always populate them with values from your  `config.py`  file.


| Dataclass | Where It's Used | Purpose |
|---|---|---|
| `CustomImageConfig` | Passed to `PipelineRunner(custom_base_image_config=...)` | Configures the automatic build of a common base image for all your custom steps from `src/requirements.txt`. |
| `ServingImageConfig` | Passed to `PipelineRunner(serving_image_configs=...)` | Configures the automatic build of a custom serving container based on your Predictor class in `src/model_server/`. |
| `ModelUploadConfig` | Passed to the inputs of a `ComponentType.MODEL_UPLOAD` step. | Provides all the parameters needed to upload a model to the Vertex AI Model Registry. |
| `BatchPredictionConfig` | Passed to the inputs of a `ComponentType.BATCH_PREDICT` step. | Provides all the parameters needed to run a Vertex AI Batch Prediction job. |