## Basic model info

Model name: runwayml/gen4-image
Model description: Runway's Gen-4 Image model with references. Use up to 3 reference images to create the exact image you need. Capture every angle.


## Model inputs

- prompt (required): Text prompt for image generation (string)
- seed (optional): Random seed. Set for reproducible generation (integer)
- aspect_ratio (optional): Image aspect ratio (string)
- resolution (optional): Image resolution (string)
- reference_images (optional): Up to 3 reference images. Images must be between 0.5 and 2 aspect ratio. (array)
- reference_tags (optional): An optional tag for each of your reference images. Tags must be alphanumeric and start with a letter. You can reference them in your prompt using @tag_name. Tags must be between 3 and 15 characters. (array)


## Model output schema

{
  "type": "string",
  "title": "Output",
  "format": "uri"
}

If the input or output schema includes a format of URI, it is referring to a file.


## Example inputs and outputs

Use these example outputs to better understand the types of inputs the model accepts, and the types of outputs the model returns:

### Example (https://replicate.com/p/mywmh37rrnrme0cqpbzs5wq2wm)

#### Input

```json
{
  "prompt": "a close up portrait of @woman, she is standing on stage in the middle of giving a tech talk at a large conference",
  "resolution": "1080p",
  "aspect_ratio": "4:3",
  "reference_tags": [
    "woman"
  ],
  "reference_images": [
    "https://replicate.delivery/pbxt/NGEXyNlRyT6OFrrscxAae4lLm6PJTOKjjvYTrfJljtUuQdVL/0_1%20copy.jpg"
  ]
}
```

#### Output

```json
"https://replicate.delivery/xezq/oQpTo6WK0IJnPxXHJGmf6ctgzNhifKKVDXwvQgZfvuQlfqsTB/tmpoz5pix9w.png"
```


## Model readme

> # Gen-4 Image with references
> 
> A reference-based image generation model that maintains character and location consistency across generations.
> 
> When attributing to Runway, please use “Powered by Runway” and link to runwayml.com from the user interface.
> 
> - [Usage policy](https://help.runwayml.com/hc/en-us/articles/17944787368595-Runway-s-Usage-Policy)
> - [Terms of use](https://runwayml.com/terms-of-use)
> - [Privacy policy](https://runwayml.com/privacy-policy)
> 
> ## Overview
> 
> Gen-4 Image with references enables generation of consistent characters and locations using 1-3 reference images. The model preserves visual identity while allowing transformation of lighting, poses, settings, and styling through text prompts.
> 
> ## Core Features
> 
> - Character preservation: Maintain facial features and identity across different scenes
> - Location consistency: Generate multiple angles and shots of the same environment  
> - Multi-reference support: Use up to 3 reference images per generation
> - Conversational prompting: Natural language descriptions with iterative refinement
> 
> ## Optimal reference images
> 
> - Natural, even lighting (avoid harsh shadows)
> - Neutral expressions for maximum flexibility
> - Moderate to high quality
> - Clear subject visibility
> 
> ## Usage Patterns
> 
> ### Single Reference
> 
> Use text prompts to describe transformations while preserving character identity.
> 
> ```
> @character_name wearing a leather jacket in a cyberpunk city
> ```
> 
> ### Multi-Reference
> 
> Combine character and scene references for precise control.
> 
> ```
> @character sitting in @location with dramatic lighting
> ```
> 
> ### Scene Generation
> 
> Create consistent environments from different angles.
> 
> ```
> show the castle courtyard from above
> wide shot of the same location at sunset  
> ```
> 
> ## Advanced Workflows
> 
> - Iterative refinement: Use generated outputs as new references to build complex scenes step-by-step.
> - Separate pathways: Develop character and environment references independently, then combine.
> - Element isolation: Generate specific clothing, poses, or lighting setups as references for final compositions.
> 
> ![](https://runway-static-assets.s3.amazonaws.com/site/images/api-page/powered-by-runway-black.png)



## Set the REPLICATE_API_TOKEN environment variable

```export REPLICATE_API_TOKEN=r8_2no**********************************```

## Visibility

Learn more about authentication

## Install Replicate’s Python client library

```pip install replicate```

## Learn more about setup

Run runwayml/gen4-image using Replicate’s API. Check out the model's schema for an overview of inputs and outputs.

```python
import replicate

input = {
    "prompt": "a close up portrait of @woman and @man standing in @park, hands in pockets, looking cool. She is wearing her pink sweater and bangles.",
    "aspect_ratio": "4:3",
    "reference_tags": ["park","woman","man"],
    "reference_images": ["https://replicate.delivery/pbxt/NHVhGWPplgrmOE8EGTVhbeSqWuZBcZLHyMQrgrTH4Hpa1ljU/m4hjkmbk79rma0cqrnxt67cqnw.jpg","https://replicate.delivery/pbxt/NHVhFhdxAAmuXKUyT4r10KIalYrXf9vp5B40CmAeXlPieuOs/w99em95b01rmc0cqrny8chf49w.jpg","https://replicate.delivery/pbxt/NHVhGE5GSJlAfL9RkGFvUbx70KVl7l7KamUNLHOAUd1sQVuF/psjdbkzgm1rmc0cqrnysbg93cm.jpg"]
}

output = replicate.run(
    "runwayml/gen4-image",
    input=input
)
```

# To access the file URL:
print(output.url())
#=> "https://replicate.delivery/.../output.png"

# To write the file to disk:
with open("output.png", "wb") as file:
    file.write(output.read())
#=> output.png written to disk

# Learn more


Authentication
Whenever you make an API request, you need to authenticate using a token. A token is like a password that uniquely identifies your account and grants you access.

The following examples all expect your Replicate access token to be available from the command line. Because tokens are secrets, they should not be in your code. They should instead be stored in environment variables. Replicate clients look for the REPLICATE_API_TOKEN environment variable and use it if available.

To set this up you can use:

``` export REPLICATE_API_TOKEN=r8_2no**********************************```

# Visibility

Some application frameworks and tools also support a text file named .env which you can edit to include the same token:

```REPLICATE_API_TOKEN=r8_2no**********************************```

# Visibility

The Replicate API uses the Authorization HTTP header to authenticate requests. If you’re using a client library this is handled for you.

You can test that your access token is setup correctly by using our account.get endpoint:

# What is cURL?
```bash 
curl https://api.replicate.com/v1/account -H "Authorization: Bearer $REPLICATE_API_TOKEN"
# {"type":"user","username":"aron","name":"Aron Carroll","github_url":"https://github.com/aron"}
```
If it is working correctly you will see a JSON object returned containing some information about your account, otherwise ensure that your token is available:

```python
echo "$REPLICATE_API_TOKEN"
# "r8_xyz"
```

# Setup
First you’ll need to ensure you have a Python environment setup:

```python
 python -m venv .venv
source .venv/bin/activate 
```     
Then install the replicate Python library:

```pip install replicate```

 In a main.py file, import replicate:

``` import replicate```

 This will use the REPLICATE_API_TOKEN API token you’ve set up in your environment for authorization.

# Run the model
Use the replicate.run() method to run the model:
```python
input = {
    "prompt": "a close up portrait of @woman and @man standing in @park, hands in pockets, looking cool. She is wearing her pink sweater and bangles.",
    "aspect_ratio": "4:3",
    "reference_tags": ["park","woman","man"],
    "reference_images": ["https://replicate.delivery/pbxt/NHVhGWPplgrmOE8EGTVhbeSqWuZBcZLHyMQrgrTH4Hpa1ljU/m4hjkmbk79rma0cqrnxt67cqnw.jpg","https://replicate.delivery/pbxt/NHVhFhdxAAmuXKUyT4r10KIalYrXf9vp5B40CmAeXlPieuOs/w99em95b01rmc0cqrny8chf49w.jpg","https://replicate.delivery/pbxt/NHVhGE5GSJlAfL9RkGFvUbx70KVl7l7KamUNLHOAUd1sQVuF/psjdbkzgm1rmc0cqrnysbg93cm.jpg"]
}

output = replicate.run(
    "runwayml/gen4-image",
    input=input
)
```
# To access the file URL:
print(output.url())
#=> "https://replicate.delivery/.../output.png"

# To write the file to disk:
with open("output.png", "wb") as file:
    file.write(output.read())
#=> output.png written to disk

You can learn about pricing for this model on the model page.

The run() function returns the output directly, which you can then use or pass as the input to another model. If you want to access the full prediction object (not just the output), use the replicate.predictions.create() method instead. This will return a Prediction object that includes the prediction id, status, logs, etc.

# Prediction lifecycle
Running predictions and trainings can often take significant time to complete, beyond what is reasonable for an HTTP request/response.

When you run a model on Replicate, the prediction is created with a “starting” state, then instantly returned. This will then move to "processing" and eventual one of “successful”, "failed" or "canceled".

-Starting
-Running
-Succeeded
-Failed
-Canceled
You can explore the prediction lifecycle by using the prediction.reload() method update the prediction to it's latest state.

Show example
Webhooks
Webhooks provide real-time updates about your prediction. Specify an endpoint when you create a prediction, and Replicate will send HTTP POST requests to that URL when the prediction is created, updated, and finished.

It is possible to provide a URL to the predictions.create() function that will be requested by Replicate when the prediction status changes. This is an alternative to polling.

To receive webhooks you’ll need a web server. The following example uses AIOHTTP, a basic webserver built on top of Python’s asyncio library, but this pattern will apply to most frameworks.

Show example
Then create the prediction passing in the webhook URL and specify which events you want to receive out of "start" , "output" ”logs” and "completed".

input = {
    "prompt": "a close up portrait of @woman and @man standing in @park, hands in pockets, looking cool. She is wearing her pink sweater and bangles.",
    "aspect_ratio": "4:3",
    "reference_tags": ["park","woman","man"],
    "reference_images": ["https://replicate.delivery/pbxt/NHVhGWPplgrmOE8EGTVhbeSqWuZBcZLHyMQrgrTH4Hpa1ljU/m4hjkmbk79rma0cqrnxt67cqnw.jpg","https://replicate.delivery/pbxt/NHVhFhdxAAmuXKUyT4r10KIalYrXf9vp5B40CmAeXlPieuOs/w99em95b01rmc0cqrny8chf49w.jpg","https://replicate.delivery/pbxt/NHVhGE5GSJlAfL9RkGFvUbx70KVl7l7KamUNLHOAUd1sQVuF/psjdbkzgm1rmc0cqrnysbg93cm.jpg"]
}

callback_url = "https://my.app/webhooks/replicate"
replicate.predictions.create(
  model="runwayml/gen4-image",
  input=input,
  webhook=callback_url,
  webhook_events_filter=["completed"]
)

# The server will now handle the event and log:
#=> Prediction(id='z3wbih3bs64of7lmykbk7tsdf4', ...)
```

The replicate.run() method is not used here. Because we're using webhooks, and we don’t need to poll for updates.

From a security perspective it is also possible to verify that the webhook came from Replicate, check out our documentation on verifying webhooks for more information.

Access a prediction
You may wish to access the prediction object. In these cases it’s easier to use the replicate.predictions.create() function, which return the prediction object.

Though note that these functions will only return the created prediction, and it will not wait for that prediction to be completed before returning. Use replicate.predictions.get() to fetch the latest prediction.

```python
import replicate

input = {
    "prompt": "a close up portrait of @woman and @man standing in @park, hands in pockets, looking cool. She is wearing her pink sweater and bangles.",
    "aspect_ratio": "4:3",
    "reference_tags": ["park","woman","man"],
    "reference_images": ["https://replicate.delivery/pbxt/NHVhGWPplgrmOE8EGTVhbeSqWuZBcZLHyMQrgrTH4Hpa1ljU/m4hjkmbk79rma0cqrnxt67cqnw.jpg","https://replicate.delivery/pbxt/NHVhFhdxAAmuXKUyT4r10KIalYrXf9vp5B40CmAeXlPieuOs/w99em95b01rmc0cqrny8chf49w.jpg","https://replicate.delivery/pbxt/NHVhGE5GSJlAfL9RkGFvUbx70KVl7l7KamUNLHOAUd1sQVuF/psjdbkzgm1rmc0cqrnysbg93cm.jpg"]
}

prediction = replicate.predictions.create(
  model="runwayml/gen4-image",
  input=input
)
#=> Prediction(id='z3wbih3bs64of7lmykbk7tsdf4', ...)
```

# Cancel a prediction

You may need to cancel a prediction. Perhaps the user has navigated away from the browser or canceled your application. To prevent unnecessary work and reduce runtime costs you can use prediction.cancel() method to call the predictions.cancel endpoint.
```python

input = {
    "prompt": "a close up portrait of @woman and @man standing in @park, hands in pockets, looking cool. She is wearing her pink sweater and bangles.",
    "aspect_ratio": "4:3",
    "reference_tags": ["park","woman","man"],
    "reference_images": ["https://replicate.delivery/pbxt/NHVhGWPplgrmOE8EGTVhbeSqWuZBcZLHyMQrgrTH4Hpa1ljU/m4hjkmbk79rma0cqrnxt67cqnw.jpg","https://replicate.delivery/pbxt/NHVhFhdxAAmuXKUyT4r10KIalYrXf9vp5B40CmAeXlPieuOs/w99em95b01rmc0cqrny8chf49w.jpg","https://replicate.delivery/pbxt/NHVhGE5GSJlAfL9RkGFvUbx70KVl7l7KamUNLHOAUd1sQVuF/psjdbkzgm1rmc0cqrnysbg93cm.jpg"]
}

prediction = replicate.predictions.create(
  model="runwayml/gen4-image",
  input=input
)

prediction.cancel()
```

# Async Python methods

asyncio is a module built into Python's standard library for writing concurrent code using the async/await syntax.

Replicate's Python client has support for asyncio. Each of the methods has an async equivalent prefixed with async_<name>.

```python
input = {
    "prompt": "a close up portrait of @woman and @man standing in @park, hands in pockets, looking cool. She is wearing her pink sweater and bangles.",
    "aspect_ratio": "4:3",
    "reference_tags": ["park","woman","man"],
    "reference_images": ["https://replicate.delivery/pbxt/NHVhGWPplgrmOE8EGTVhbeSqWuZBcZLHyMQrgrTH4Hpa1ljU/m4hjkmbk79rma0cqrnxt67cqnw.jpg","https://replicate.delivery/pbxt/NHVhFhdxAAmuXKUyT4r10KIalYrXf9vp5B40CmAeXlPieuOs/w99em95b01rmc0cqrny8chf49w.jpg","https://replicate.delivery/pbxt/NHVhGE5GSJlAfL9RkGFvUbx70KVl7l7KamUNLHOAUd1sQVuF/psjdbkzgm1rmc0cqrnysbg93cm.jpg"]
}

prediction = replicate.predictions.create(
  model="runwayml/gen4-image",
  input=input
)

prediction = await replicate.predictions.async_create(
  model="runwayml/gen4-image",
  input=input
)
```

# Input schema
| Key | Type | Description | Default |
| --- | --- | --- | --- |
| seed | integer | Random seed. Set for reproducible generation |  |
| prompt | string | Text prompt for image generation |  |
| resolution | string | Image resolution | "1080p" |
| aspect_ratio | string | Image aspect ratio | "16:9" |
| reference_tags | array | An optional tag for each of your reference images. Tags must be alphanumeric and start with a letter. You can reference them in your prompt using @tag_name. Tags must be between 3 and 15 characters. |  |
| reference_images | array | Up to 3 reference images. Images must be between 0.5 and 2 aspect ratio. |  |

# Output schema
Type | uri