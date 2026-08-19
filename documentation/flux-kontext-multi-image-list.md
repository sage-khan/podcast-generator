## Basic model info

Model name: flux-kontext-apps/multi-image-list
Model description: FLUX Kontext max with list input for multiple images


## Model inputs

- prompt: Text description of how to combine or transform the input images (string)
- input_images: List of input images. Must be jpeg, png, gif, or webp. (array)
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

### Example (https://replicate.com/p/kt84j4e4xsrma0cq7cva557z38)

#### Input

```json
{
  "prompt": "Combine these photos into one fluid scene",
  "aspect_ratio": "9:16",
  "input_images": [
    "https://replicate.delivery/pbxt/N7yYZ1N9buFw4wd9i5c63gIcv8UdDzrY26rPf3hhbWieIIaX/tmp04o2q0cj.png",
    "https://replicate.delivery/pbxt/N7ygtM6Cdao8xTLYvg4VAZDzrajr2k6aIZ6iEdyYRlRoerJk/test_4.jpg",
    "https://replicate.delivery/pbxt/N7ygu9UBOy88Z7T8CPz0Dyv906b8VbTnvbMJCmGK6GOBqkn2/test.jpg"
  ],
  "output_format": "png",
  "safety_tolerance": 2
}
```

#### Output

```json
"https://replicate.delivery/xezq/efeF8dUE1DJfFSMZ5PjnZacJhhvzQJn3FwHkslBcwfk4yAcmC/tmp8f31xs5n.png"
```


## Model readme

> ## FLUX Kontext apps - Multi-Image list with Kontext Max
> 
> Combine multiple images using FLUX Kontext Max
> 
> ---
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
cURL is a command line tool for sending HTTP requests (same as your browser does) to a web server. It will show all the parts needed to make a similar request in the programming language of your choice, the URL, request headers and the request body. We’ve tried to keep these examples as clear as possible using tools that are commonly available on most computers.

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
    "prompt": "Combine these photos into one fluid scene. Make the woman in the first image wear the futuristic headgear in the second image. Then put the same woman the third image's scene.",
    "aspect_ratio": "1:1",
    "input_images": ["https://replicate.delivery/pbxt/N83LmkC1NAWFfeIkF6HBSkQGN2W3tr6Q7XIxhRcA1Eoh0uAC/tmp04o2q0cj.png","https://replicate.delivery/pbxt/N83LmgcB5EguqxLt5gQnmI2LXRa8H0eayIrtVw931df2xvtt/test_4.jpg","https://replicate.delivery/pbxt/N83Ln0m0xhzTsR5rY4RAREEpPLwzfXSB90Fmp24gQFHKoQ2D/test.jpg"]
}

output = replicate.run(
    "flux-kontext-apps/multi-image-list",
    input=input
)
with open("output.png", "wb") as file:
    file.write(output.read())
#=> output.png written to disk

Copy
You can learn about pricing for this model on the model page.

The run() function returns the output directly, which you can then use or pass as the input to another model. If you want to access the full prediction object (not just the output), use the replicate.predictions.create() method instead. This will return a Prediction object that includes the prediction id, status, logs, etc.

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
  model="flux-kontext-apps/multi-image-list",
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
    "prompt": "Combine these photos into one fluid scene. Make the woman in the first image wear the futuristic headgear in the second image. Then put the same woman the third image's scene.",
    "aspect_ratio": "1:1",
    "input_images": ["https://replicate.delivery/pbxt/N83LmkC1NAWFfeIkF6HBSkQGN2W3tr6Q7XIxhRcA1Eoh0uAC/tmp04o2q0cj.png","https://replicate.delivery/pbxt/N83LmgcB5EguqxLt5gQnmI2LXRa8H0eayIrtVw931df2xvtt/test_4.jpg","https://replicate.delivery/pbxt/N83Ln0m0xhzTsR5rY4RAREEpPLwzfXSB90Fmp24gQFHKoQ2D/test.jpg"]
}

callback_url = "https://my.app/webhooks/replicate"
replicate.predictions.create(
  model="flux-kontext-apps/multi-image-list",
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
    "prompt": "Combine these photos into one fluid scene. Make the woman in the first image wear the futuristic headgear in the second image. Then put the same woman the third image's scene.",
    "aspect_ratio": "1:1",
    "input_images": ["https://replicate.delivery/pbxt/N83LmkC1NAWFfeIkF6HBSkQGN2W3tr6Q7XIxhRcA1Eoh0uAC/tmp04o2q0cj.png","https://replicate.delivery/pbxt/N83LmgcB5EguqxLt5gQnmI2LXRa8H0eayIrtVw931df2xvtt/test_4.jpg","https://replicate.delivery/pbxt/N83Ln0m0xhzTsR5rY4RAREEpPLwzfXSB90Fmp24gQFHKoQ2D/test.jpg"]
}

prediction = replicate.predictions.create(
  model="flux-kontext-apps/multi-image-list",
  input=input
)
#=> Prediction(id='z3wbih3bs64of7lmykbk7tsdf4', ...)

Copy
Cancel a prediction
You may need to cancel a prediction. Perhaps the user has navigated away from the browser or canceled your application. To prevent unnecessary work and reduce runtime costs you can use prediction.cancel() method to call the predictions.cancel endpoint.

input = {
    "prompt": "Combine these photos into one fluid scene. Make the woman in the first image wear the futuristic headgear in the second image. Then put the same woman the third image's scene.",
    "aspect_ratio": "1:1",
    "input_images": ["https://replicate.delivery/pbxt/N83LmkC1NAWFfeIkF6HBSkQGN2W3tr6Q7XIxhRcA1Eoh0uAC/tmp04o2q0cj.png","https://replicate.delivery/pbxt/N83LmgcB5EguqxLt5gQnmI2LXRa8H0eayIrtVw931df2xvtt/test_4.jpg","https://replicate.delivery/pbxt/N83Ln0m0xhzTsR5rY4RAREEpPLwzfXSB90Fmp24gQFHKoQ2D/test.jpg"]
}

prediction = replicate.predictions.create(
  model="flux-kontext-apps/multi-image-list",
  input=input
)

prediction.cancel()

Copy
Async Python methods
asyncio is a module built into Python's standard library for writing concurrent code using the async/await syntax.

Replicate's Python client has support for asyncio. Each of the methods has an async equivalent prefixed with async_<name>.

input = {
    "prompt": "Combine these photos into one fluid scene. Make the woman in the first image wear the futuristic headgear in the second image. Then put the same woman the third image's scene.",
    "aspect_ratio": "1:1",
    "input_images": ["https://replicate.delivery/pbxt/N83LmkC1NAWFfeIkF6HBSkQGN2W3tr6Q7XIxhRcA1Eoh0uAC/tmp04o2q0cj.png","https://replicate.delivery/pbxt/N83LmgcB5EguqxLt5gQnmI2LXRa8H0eayIrtVw931df2xvtt/test_4.jpg","https://replicate.delivery/pbxt/N83Ln0m0xhzTsR5rY4RAREEpPLwzfXSB90Fmp24gQFHKoQ2D/test.jpg"]
}

prediction = replicate.predictions.create(
  model="flux-kontext-apps/multi-image-list",
  input=input
)

prediction = await replicate.predictions.async_create(
  model="flux-kontext-apps/multi-image-list",
  input=input
)


# Input Schema
| Field | Type | Description | Default | Maximum |
| --- | --- | --- | --- | --- |
| seed | integer | Random seed. Set for reproducible generation |  |  |
| prompt | string | Text description of how to combine or transform the input images |  |  |
| aspect_ratio | string | Aspect ratio of the generated image. Use 'match_input_image' to match the aspect ratio of the input image. | "match_input_image" |  |
| input_images | array | List of input images. Must be jpeg, png, gif, or webp. |  |  |
| output_format | string | Output format for the generated image | "png" |  |
| safety_tolerance | integer | Safety tolerance, 0 is most strict and 2 is most permissive. 2 is currently the maximum allowed. | 2 | 2 |



# Output schema

Type uri