## Basic model info

Model name: flux-kontext-apps/multi-image-kontext-max
Model description: An experimental FLUX Kontext model that can combine two input images


## Model inputs

- prompt: Text description of how to combine or transform the two input images (string)
- input_image_1: First input image. Must be jpeg, png, gif, or webp. (string)
- input_image_2: Second input image. Must be jpeg, png, gif, or webp. (string)
- aspect_ratio: Aspect ratio of the generated image. Use 'match_input_image' to match the aspect ratio of the input image. (string)
- seed: Random seed. Set for reproducible generation (integer)
- output_format: Output format for the generated image (string)
- safety_tolerance: Safety tolerance, 0 is most strict and 2 is most permissive. 2 is currently the maximum allowed. (integer)


## Model output schema

{
  "type": "string",
  "title": "Output",
  "format": "uri"
}

If the input or output schema includes a format of URI, it is referring to a file.


## Example inputs and outputs

Use these example outputs to better understand the types of inputs the model accepts, and the types of outputs the model returns:

### Example (https://replicate.com/p/y9khwmsxxsrme0cq3hh8b1rpbc)

#### Input

```json
{
  "prompt": "Put Elsa and Mona Lisa dancing together at a deep house rave",
  "aspect_ratio": "3:2",
  "input_image_1": "https://replicate.delivery/pbxt/N5qwPSq6UtqIHdHfJmrntyLNGeCpHIF7BrJ7KwWvw0mOOhFv/elsa.jpg",
  "input_image_2": "https://replicate.delivery/pbxt/N5qwP15NEUY6uYQKeX65DNlpLmpOpbkIZAOseLRur0XM6ymW/mona-lisa.png"
}
```

#### Output

```json
"https://replicate.delivery/xezq/TfGjkMa5dyUkWKCfNWfwMLUMvZW6EfTHHEexStAWGMDUjOMmC/tmpmco14zt1.png"
```


## Model readme

> ## FLUX Kontext apps
> 
> Here at Replicate we've created a collection of models that are powered by FLUX Kontext [pro]. They can all be used commercially.
> 
> ## Available apps
> 
> - [Professional headshot](https://replicate.com/flux-kontext-apps/professional-headshot): Generate a  professional headshot from any image
> - [Portrait series](https://replicate.com/flux-kontext-apps/portrait-series): Generate a series of portraits from a single image
> - [Iconic locations](https://replicate.com/flux-kontext-apps/iconic-locations): Put yourself in front of famous landmarks
> - [Impossible Scenarios](https://replicate.com/flux-kontext-apps/impossible-scenarios): Experience impossible adventures and extreme scenarios from a single image
> - [Depth of Field](https://replicate.com/flux-kontext-apps/depth-of-field): Bring your subjects into focus
> - [Cartoonify](https://replicate.com/flux-kontext-apps/cartoonify): Turn your image into a cartoon
> - [Text Removal](https://replicate.com/flux-kontext-apps/text-removal): Remove all text from an image
> - [Restore Image](https://replicate.com/flux-kontext-apps/restore-image): Use FLUX Kontext to restore, fix scratches and damage, and colorize old photos
> 
> ## About FLUX Kontext
> 
> FLUX.1 Kontext is a state-of-the-art image editing model from Black Forest Labs that allows you to edit images using text prompts. It's the best in class for text-guided image editing and offers superior results compared to other models like OpenAI's 4o/gpt-image-1.
> 
> ## Available Models
> 
> - **[FLUX.1 Kontext [pro]](https://replicate.com/black-forest-labs/flux-kontext-pro)**: State-of-the-art performance with high-quality outputs, great prompt following, and consistent results
> - **[FLUX.1 Kontext [max]](https://replicate.com/black-forest-labs/flux-kontext-max)**: Premium model with maximum performance and improved typography generation

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
    "prompt": "Put the woman into a white t-shirt with the text on it",
    "aspect_ratio": "1:1",
    "input_image_1": "https://replicate.delivery/pbxt/N5rSeJrCafWpmJuLb62moY8pSMEpSBBwSf7N6hxyIn4fNYMa/w8msa88d01rm80cq3hzsqrdehg.png",
    "input_image_2": "https://replicate.delivery/pbxt/N5rSdTCgBqIRvbkedcfLfS5xTSEEOqMtX9FsR1hLK9JYryml/0_1.webp"
}

output = replicate.run(
    "flux-kontext-apps/multi-image-kontext-max",
    input=input
)
with open("output.png", "wb") as file:
    file.write(output.read())
#=> output.png written to disk

Copy
You can learn about pricing for this model on the model page.

The run() function returns the output directly, which you can then use or pass as the input to another model. If you want to access the full prediction object (not just the output), use the replicate.predictions.create() method instead. This will return a Prediction object that includes the prediction id, status, logs, etc.

File inputs
This model accepts files as input, e.g. input_image_1. You can provide a file as input using a URL, a local file on your computer, or a base64 encoded object:

Option 1: Hosted file
Use a URL as in the earlier example:

input_image_1 = "https://replicate.delivery/pbxt/N5rSeJrCafWpmJuLb62moY8pSMEpSBBwSf7N6hxyIn4fNYMa/w8msa88d01rm80cq3hzsqrdehg.png";

Copy
This is useful if you already have a file hosted somewhere on the internet.

Option 2: Local file
You can provide Replicate with a file object and the library will handle the upload for you:

input_image_1 = open("./path/to/my/input_image_1.png", "rb");

Copy
Option 3: Data URI
Lastly, you can create a data URI consisting of the base64 encoded data for your file, but this is only recommended if the file is < 1mb:

import base64

with open("./path/to/my/input_image_1.png", 'rb') as file:
  data = base64.b64encode(file.read()).decode('utf-8')
  input_image_1 = f"data:application/octet-stream;base64,{data}"

Copy
Then pass the file as part of the input:

input = {
    "prompt": "Put the woman into a white t-shirt with the text on it",
    "aspect_ratio": "1:1",
    "input_image_1": input_image_1,
    "input_image_2": "https://replicate.delivery/pbxt/N5rSdTCgBqIRvbkedcfLfS5xTSEEOqMtX9FsR1hLK9JYryml/0_1.webp"
}

output = replicate.run(
    "flux-kontext-apps/multi-image-kontext-max",
    input=input
)
with open("output.png", "wb") as file:
    file.write(output.read())
#=> output.png written to disk

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
import time

prediction = replicate.predictions.create(
  model="flux-kontext-apps/multi-image-kontext-max",
  input=input
)
#=> Prediction(id='z3wbih3bs64of7lmykbk7tsdf4', status="starting", ...)

prediction.reload()
#=> Prediction(id='z3wbih3bs64of7lmykbk7tsdf4', status="processing", ...)


for i in range(5):
  prediction.reload()
  if prediction.status in {"succeeded", "failed", "canceled"}:
    break

  # Wait for 2 seconds and then try again.
  time.sleep(2)

print(prediction);
#=> Prediction(id='z3wbih3bs64of7lmykbk7tsdf4', status="successful", ...)

Copy
Webhooks
Webhooks provide real-time updates about your prediction. Specify an endpoint when you create a prediction, and Replicate will send HTTP POST requests to that URL when the prediction is created, updated, and finished.

It is possible to provide a URL to the predictions.create() function that will be requested by Replicate when the prediction status changes. This is an alternative to polling.

To receive webhooks you’ll need a web server. The following example uses AIOHTTP, a basic webserver built on top of Python’s asyncio library, but this pattern will apply to most frameworks.

Show example
from aiohttp import web

# NOTE: This should point to the internet facing endpoint for your application.
callback_url = "https://my.app/webhooks/replicate"

# Create a python webserver using aiohttp to handle the webhook and push
# the completed prediction into our queue.
routes = web.RouteTableDef()

# Add a request handler at /webhooks/replicate to receive the request.
@routes.post('/webhooks/replicate')
async def callback_replicate(request):
  prediction = await request.json()
  print(prediction)
  #=> Prediction(id='z3wbih3bs64of7lmykbk7tsdf4', ...)
  return web.Response(text="OK")

# Start the webserver.
app = web.Application()
app.add_routes(routes)

web.run_app(app)

Copy
Then create the prediction passing in the webhook URL and specify which events you want to receive out of "start" , "output" ”logs” and "completed".

input = {
    "prompt": "Put the woman into a white t-shirt with the text on it",
    "aspect_ratio": "1:1",
    "input_image_1": "https://replicate.delivery/pbxt/N5rSeJrCafWpmJuLb62moY8pSMEpSBBwSf7N6hxyIn4fNYMa/w8msa88d01rm80cq3hzsqrdehg.png",
    "input_image_2": "https://replicate.delivery/pbxt/N5rSdTCgBqIRvbkedcfLfS5xTSEEOqMtX9FsR1hLK9JYryml/0_1.webp"
}

callback_url = "https://my.app/webhooks/replicate"
replicate.predictions.create(
  model="flux-kontext-apps/multi-image-kontext-max",
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
    "prompt": "Put the woman into a white t-shirt with the text on it",
    "aspect_ratio": "1:1",
    "input_image_1": "https://replicate.delivery/pbxt/N5rSeJrCafWpmJuLb62moY8pSMEpSBBwSf7N6hxyIn4fNYMa/w8msa88d01rm80cq3hzsqrdehg.png",
    "input_image_2": "https://replicate.delivery/pbxt/N5rSdTCgBqIRvbkedcfLfS5xTSEEOqMtX9FsR1hLK9JYryml/0_1.webp"
}

prediction = replicate.predictions.create(
  model="flux-kontext-apps/multi-image-kontext-max",
  input=input
)
#=> Prediction(id='z3wbih3bs64of7lmykbk7tsdf4', ...)

Copy
Cancel a prediction
You may need to cancel a prediction. Perhaps the user has navigated away from the browser or canceled your application. To prevent unnecessary work and reduce runtime costs you can use prediction.cancel() method to call the predictions.cancel endpoint.

input = {
    "prompt": "Put the woman into a white t-shirt with the text on it",
    "aspect_ratio": "1:1",
    "input_image_1": "https://replicate.delivery/pbxt/N5rSeJrCafWpmJuLb62moY8pSMEpSBBwSf7N6hxyIn4fNYMa/w8msa88d01rm80cq3hzsqrdehg.png",
    "input_image_2": "https://replicate.delivery/pbxt/N5rSdTCgBqIRvbkedcfLfS5xTSEEOqMtX9FsR1hLK9JYryml/0_1.webp"
}

prediction = replicate.predictions.create(
  model="flux-kontext-apps/multi-image-kontext-max",
  input=input
)

prediction.cancel()

Copy
Async Python methods
asyncio is a module built into Python's standard library for writing concurrent code using the async/await syntax.

Replicate's Python client has support for asyncio. Each of the methods has an async equivalent prefixed with async_<name>.

input = {
    "prompt": "Put the woman into a white t-shirt with the text on it",
    "aspect_ratio": "1:1",
    "input_image_1": "https://replicate.delivery/pbxt/N5rSeJrCafWpmJuLb62moY8pSMEpSBBwSf7N6hxyIn4fNYMa/w8msa88d01rm80cq3hzsqrdehg.png",
    "input_image_2": "https://replicate.delivery/pbxt/N5rSdTCgBqIRvbkedcfLfS5xTSEEOqMtX9FsR1hLK9JYryml/0_1.webp"
}

prediction = replicate.predictions.create(
  model="flux-kontext-apps/multi-image-kontext-max",
  input=input
)

prediction = await replicate.predictions.async_create(
  model="flux-kontext-apps/multi-image-kontext-max",
  input=input
)



# Input schema
| Key | Type | Description | Default | Maximum |
| --- | --- | --- | --- | --- |
| seed | integer | Random seed. Set for reproducible generation |  |  |
| prompt | string | Text description of how to combine or transform the two input images |  |  |
| aspect_ratio | string | Aspect ratio of the generated image. Use 'match_input_image' to match the aspect ratio of the input image. | "match_input_image" |  |
| input_image_1 | uri | First input image. Must be jpeg, png, gif, or webp. |  |  |
| input_image_2 | uri | Second input image. Must be jpeg, png, gif, or webp. |  |  |
| output_format | string | Output format for the generated image | "png" |  |
| safety_tolerance | integer | Safety tolerance, 0 is most strict and 2 is most permissive. 2 is currently the maximum allowed. | 2 | 2 |


# Output schema
Type | uri