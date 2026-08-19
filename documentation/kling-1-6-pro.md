## Basic model info

Model name: kwaivgi/kling-v1.6-pro
Model description: Generate 5s and 10s videos in 1080p resolution


## Model inputs

- prompt: Text prompt for video generation (string)
- negative_prompt: Things you do not want to see in the video (string)
- aspect_ratio: Aspect ratio of the video. Ignored if start_image is provided. (string)
- start_image: First frame of the video. A start or end image is required. (string)
- end_image: Last frame of the video. A start or end image is required. (string)
- reference_images: Reference images to use in video generation (up to 4 images). Also known as scene elements. (array)
- cfg_scale: Flexibility in video generation; The higher the value, the lower the model's degree of flexibility, and the stronger the relevance to the user's prompt. (number)
- duration: Duration of the video in seconds (integer)


## Model output schema

{
  "type": "string",
  "title": "Output",
  "format": "uri"
}

If the input or output schema includes a format of URI, it is referring to a file.


## Example inputs and outputs

Use these example outputs to better understand the types of inputs the model accepts, and the types of outputs the model returns:

### Example (https://replicate.com/p/h5c575vh29rge0cmk03abch7hg)

#### Input

```json
{
  "prompt": "Reflections in crystal mirrors, rainbow light, geometric world",
  "duration": 5,
  "cfg_scale": 0.5,
  "start_image": "https://replicate.delivery/pbxt/MNRLOqN0ASEzIG3YPuv9R1JSVGsSOQQzE3rgtVD9Qk230Lgt/image_fx_%20%285%29.jpg",
  "aspect_ratio": "16:9",
  "negative_prompt": ""
}
```

#### Output

```json
"https://replicate.delivery/czjl/dLWqDLYlXD6yMdlorUshiJxZstZNDmjBj49F5OjPJZLWpECF/tmpe6j5tmkr.mp4"
```


## Model readme

> # Kling v1.6
> 
> An AI text-to-video generation model developed by Kuaishou AI Team.
> 
> Data from this model is sent from Replicate to Kuaishou.
> 
> https://klingai.com/
> 
> ## Privacy policy
> 
> https://docs.qingque.cn/d/home/eZQCzFHiWVM1OFfpXZb3kGthx
> 
> ## API terms
> 
> https://docs.qingque.cn/d/home/eZQC4FkUthNLuEMk9AgXvH-et
> 
> ## Service level agreement
> 
> https://docs.qingque.cn/d/home/eZQAedFwivWXjj_2d_ITWyV2X


## Basic model info

Model name: kwaivgi/kling-v1.6-pro
Model description: Generate 5s and 10s videos in 1080p resolution


## Model inputs

- prompt: Text prompt for video generation (string)
- negative_prompt: Things you do not want to see in the video (string)
- aspect_ratio: Aspect ratio of the video. Ignored if start_image is provided. (string)
- start_image: First frame of the video. A start or end image is required. (string)
- end_image: Last frame of the video. A start or end image is required. (string)
- reference_images: Reference images to use in video generation (up to 4 images). Also known as scene elements. (array)
- cfg_scale: Flexibility in video generation; The higher the value, the lower the model's degree of flexibility, and the stronger the relevance to the user's prompt. (number)
- duration: Duration of the video in seconds (integer)


## Model output schema

{
  "type": "string",
  "title": "Output",
  "format": "uri"
}

If the input or output schema includes a format of URI, it is referring to a file.


## Example inputs and outputs

Use these example outputs to better understand the types of inputs the model accepts, and the types of outputs the model returns:

### Example (https://replicate.com/p/h5c575vh29rge0cmk03abch7hg)

#### Input

```json
{
  "prompt": "Reflections in crystal mirrors, rainbow light, geometric world",
  "duration": 5,
  "cfg_scale": 0.5,
  "start_image": "https://replicate.delivery/pbxt/MNRLOqN0ASEzIG3YPuv9R1JSVGsSOQQzE3rgtVD9Qk230Lgt/image_fx_%20%285%29.jpg",
  "aspect_ratio": "16:9",
  "negative_prompt": ""
}
```

#### Output

```json
"https://replicate.delivery/czjl/dLWqDLYlXD6yMdlorUshiJxZstZNDmjBj49F5OjPJZLWpECF/tmpe6j5tmkr.mp4"
```


## Model readme

> # Kling v1.6
> 
> An AI text-to-video generation model developed by Kuaishou AI Team.
> 
> Data from this model is sent from Replicate to Kuaishou.
> 
> https://klingai.com/
> 
> ## Privacy policy
> 
> https://docs.qingque.cn/d/home/eZQCzFHiWVM1OFfpXZb3kGthx
> 
> ## API terms
> 
> https://docs.qingque.cn/d/home/eZQC4FkUthNLuEMk9AgXvH-et
> 
> ## Service level agreement
> 
> https://docs.qingque.cn/d/home/eZQAedFwivWXjj_2d_ITWyV2X



Authentication
Whenever you make an API request, you need to authenticate using a token. A token is like a password that uniquely identifies your account and grants you access.

The following examples all expect your Replicate access token to be available from the command line. Because tokens are secrets, they should not be in your code. They should instead be stored in environment variables. Replicate clients look for the REPLICATE_API_TOKEN environment variable and use it if available.

To set this up you can use:

export REPLICATE_API_TOKEN=r8_2no**********************************

Visibility

Copy
Some application frameworks and tools also support a text file named .env which you can edit to include the same token:

REPLICATE_API_TOKEN=r8_2no**********************************

Visibility

Copy
The Replicate API uses the Authorization HTTP header to authenticate requests. If you’re using a client library this is handled for you.

You can test that your access token is setup correctly by using our account.get endpoint:

What is cURL?
curl https://api.replicate.com/v1/account -H "Authorization: Bearer $REPLICATE_API_TOKEN"
# {"type":"user","username":"aron","name":"Aron Carroll","github_url":"https://github.com/aron"}

Copy
If it is working correctly you will see a JSON object returned containing some information about your account, otherwise ensure that your token is available:

echo "$REPLICATE_API_TOKEN"
# "r8_xyz"

Copy
Setup
First you’ll need to ensure you have a Python environment setup:

python -m venv .venv
source .venv/bin/activate

Copy
Then install the replicate Python library:

pip install replicate

Copy
In a main.py file, import replicate:

import replicate

Copy
This will use the REPLICATE_API_TOKEN API token you’ve set up in your environment for authorization.

Run the model
Use the replicate.run() method to run the model:

input = {
    "prompt": "Reflections in crystal mirrors, rainbow light, geometric world",
    "start_image": "https://replicate.delivery/pbxt/MNRLOqN0ASEzIG3YPuv9R1JSVGsSOQQzE3rgtVD9Qk230Lgt/image_fx_%20%285%29.jpg"
}

output = replicate.run(
    "kwaivgi/kling-v1.6-pro",
    input=input
)
with open("output.mp4", "wb") as file:
    file.write(output.read())
#=> output.mp4 written to disk

Copy
You can learn about pricing for this model on the model page.

The run() function returns the output directly, which you can then use or pass as the input to another model. If you want to access the full prediction object (not just the output), use the replicate.predictions.create() method instead. This will return a Prediction object that includes the prediction id, status, logs, etc.

File inputs
This model accepts files as input, e.g. start_image. You can provide a file as input using a URL, a local file on your computer, or a base64 encoded object:

Option 1: Hosted file
Use a URL as in the earlier example:

start_image = "https://replicate.delivery/pbxt/MNRLOqN0ASEzIG3YPuv9R1JSVGsSOQQzE3rgtVD9Qk230Lgt/image_fx_%20%285%29.jpg";

Copy
This is useful if you already have a file hosted somewhere on the internet.

Option 2: Local file
You can provide Replicate with a file object and the library will handle the upload for you:

start_image = open("./path/to/my/start_image.jpg", "rb");

Copy
Option 3: Data URI
Lastly, you can create a data URI consisting of the base64 encoded data for your file, but this is only recommended if the file is < 1mb:

import base64

with open("./path/to/my/start_image.jpg", 'rb') as file:
  data = base64.b64encode(file.read()).decode('utf-8')
  start_image = f"data:application/octet-stream;base64,{data}"

Copy
Then pass the file as part of the input:

input = {
    "prompt": "Reflections in crystal mirrors, rainbow light, geometric world",
    "start_image": start_image
}

output = replicate.run(
    "kwaivgi/kling-v1.6-pro",
    input=input
)
with open("output.mp4", "wb") as file:
    file.write(output.read())
#=> output.mp4 written to disk

Copy
Prediction lifecycle
Running predictions and trainings can often take significant time to complete, beyond what is reasonable for an HTTP request/response.

When you run a model on Replicate, the prediction is created with a “starting” state, then instantly returned. This will then move to "processing" and eventual one of “successful”, "failed" or "canceled".

Starting
Running
Succeeded
Failed
Canceled
You can explore the prediction lifecycle by using the prediction.reload() method update the prediction to it's latest state.

Show example
Webhooks
Webhooks provide real-time updates about your prediction. Specify an endpoint when you create a prediction, and Replicate will send HTTP POST requests to that URL when the prediction is created, updated, and finished.

It is possible to provide a URL to the predictions.create() function that will be requested by Replicate when the prediction status changes. This is an alternative to polling.

To receive webhooks you’ll need a web server. The following example uses AIOHTTP, a basic webserver built on top of Python’s asyncio library, but this pattern will apply to most frameworks.

Show example
Then create the prediction passing in the webhook URL and specify which events you want to receive out of "start" , "output" ”logs” and "completed".

input = {
    "prompt": "Reflections in crystal mirrors, rainbow light, geometric world",
    "start_image": "https://replicate.delivery/pbxt/MNRLOqN0ASEzIG3YPuv9R1JSVGsSOQQzE3rgtVD9Qk230Lgt/image_fx_%20%285%29.jpg"
}

callback_url = "https://my.app/webhooks/replicate"
replicate.predictions.create(
  model="kwaivgi/kling-v1.6-pro", #use version='kwaivgi/kling-v1.6-pro' instead of model if you only have model name and donot have the model hash or available.
  input=input,
  webhook=callback_url,
  webhook_events_filter=["completed"]
)

# The server will now handle the event and log:
#=> Prediction(id='z3wbih3bs64of7lmykbk7tsdf4', ...)

Copy
The replicate.run() method is not used here. Because we're using webhooks, and we don’t need to poll for updates.

From a security perspective it is also possible to verify that the webhook came from Replicate, check out our documentation on verifying webhooks for more information.

Access a prediction
You may wish to access the prediction object. In these cases it’s easier to use the replicate.predictions.create() function, which return the prediction object.

Though note that these functions will only return the created prediction, and it will not wait for that prediction to be completed before returning. Use replicate.predictions.get() to fetch the latest prediction.

import replicate

input = {
    "prompt": "Reflections in crystal mirrors, rainbow light, geometric world",
    "start_image": "https://replicate.delivery/pbxt/MNRLOqN0ASEzIG3YPuv9R1JSVGsSOQQzE3rgtVD9Qk230Lgt/image_fx_%20%285%29.jpg"
}

prediction = replicate.predictions.create(
  model="kwaivgi/kling-v1.6-pro",
  input=input
)
#=> Prediction(id='z3wbih3bs64of7lmykbk7tsdf4', ...)

Copy
Cancel a prediction
You may need to cancel a prediction. Perhaps the user has navigated away from the browser or canceled your application. To prevent unnecessary work and reduce runtime costs you can use prediction.cancel() method to call the predictions.cancel endpoint.

input = {
    "prompt": "Reflections in crystal mirrors, rainbow light, geometric world",
    "start_image": "https://replicate.delivery/pbxt/MNRLOqN0ASEzIG3YPuv9R1JSVGsSOQQzE3rgtVD9Qk230Lgt/image_fx_%20%285%29.jpg"
}

prediction = replicate.predictions.create(
  model="kwaivgi/kling-v1.6-pro",
  input=input
)

prediction.cancel()

Copy
Async Python methods
asyncio is a module built into Python's standard library for writing concurrent code using the async/await syntax.

Replicate's Python client has support for asyncio. Each of the methods has an async equivalent prefixed with async_<name>.

input = {
    "prompt": "Reflections in crystal mirrors, rainbow light, geometric world",
    "start_image": "https://replicate.delivery/pbxt/MNRLOqN0ASEzIG3YPuv9R1JSVGsSOQQzE3rgtVD9Qk230Lgt/image_fx_%20%285%29.jpg"
}

prediction = replicate.predictions.create(
  model="kwaivgi/kling-v1.6-pro",
  input=input
)

prediction = await replicate.predictions.async_create(
  model="kwaivgi/kling-v1.6-pro",
  input=input
)


### INPUT SCHEMA

| Key | Type | Description | Default | Maximum |
| --- | --- | --- | --- | --- |
| prompt | string | Text prompt for video generation |  |  |
| duration | integer | Duration of the video in seconds | 5 |  |
| cfg_scale | number | Flexibility in video generation; The higher the value, the lower the model's degree of flexibility, and the stronger the relevance to the user's prompt. | 0.5 | 1 |
| end_image | uri | Last frame of the video. A start or end image is required. |  |  |
| start_image | uri | First frame of the video. A start or end image is required. |  |  |
| aspect_ratio | string | Aspect ratio of the video. Ignored if start_image is provided. | "16:9" |  |
| negative_prompt | string | Things you do not want to see in the video |  |  |
| reference_images | array | Reference images to use in video generation (up to 4 images). Also known as scene elements. |  |  |

### Output schema

| Key | Type | Description |
| --- | --- | --- |
| output | uri |  |