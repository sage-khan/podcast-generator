## Basic model info

Model name: flux-kontext-apps/portrait-series
Model description: Create a series of portrait photos from a single image


## Model inputs

- input_image: Image of the person to create a series of photos for. Must be jpeg, png, gif, or webp. (string)
- num_images: The number of poses to generate (integer)
- background: The background of the photo (string)
- randomize_images: Whether to randomize the poses (boolean)
- output_format: Output format for the generated image (string)
- safety_tolerance: Safety tolerance, 0 is most strict and 2 is most permissive. 2 is currently the maximum allowed. (integer)


## Model output schema

{
  "type": "array",
  "items": {
    "type": "string",
    "format": "uri"
  },
  "title": "Output"
}

If the input or output schema includes a format of URI, it is referring to a file.


## Example inputs and outputs

Use these example outputs to better understand the types of inputs the model accepts, and the types of outputs the model returns:

### Example (https://replicate.com/p/82starwxxhrme0cq2cnr8qr468)

#### Input

```json
{
  "background": "black",
  "num_images": 13,
  "input_image": "https://replicate.delivery/pbxt/N5DZJkCEuP5rWGtu8XcfyZj9sXzm4W3OXOSfdJnj9NmlirP2/mona-lisa.png",
  "randomize_images": true
}
```

#### Output

```json
[
  "https://replicate.delivery/xezq/aEGdLCUksRb6MxNwEq8If0pabporqCRjRalIpaf6QVrLF8wUA/tmp27lath6p.png",
  "https://replicate.delivery/xezq/SxqFUe728fuezoIFEcFHWYf7Zb43KN4Xsovv23QKzvXtUwDTB/tmpyigycvvl.png",
  "https://replicate.delivery/xezq/Q7XDAToouAKONBbTdGFmsLO0Dw6ygxFEwcvELeeKTAQLF8wUA/tmp6kma458r.png",
  "https://replicate.delivery/xezq/mpTzflspDLWdKSCC1cgW3nSI9z0ELncXA82nBQiXXZ5lCewUA/tmpwc_lidms.png",
  "https://replicate.delivery/xezq/eRVfn90CgAmdg0a6LpgPw5bYx4Cpf8eJFXj8OFdPcHRuUwDTB/tmptczdxx21.png",
  "https://replicate.delivery/xezq/JpDGO2IS2o7iEtbK2dO40rRpwEF4RBKqkd0tEe1ba12lCewUA/tmpfba7q94s.png",
  "https://replicate.delivery/xezq/tQsTiPHwIE4QLdx9dogFSJOeCcfRA2peHy1bJH97vHmWK4hpA/tmpr8w2yjyv.png",
  "https://replicate.delivery/xezq/qGCoegH9wsWeHEXmxtkINYYy4daxfzS8xJBzK0CNhfhuUwDTB/tmp8o8oxiyv.png",
  "https://replicate.delivery/xezq/PgrfRskOg6SqZ61S41RilKL5omnTpgCzNdcBSfxfoI4XK4hpA/tmpeoi83otz.png",
  "https://replicate.delivery/xezq/8QenrvxKACWFQifMiYQgATSvlssqTQde5ZjIwQXILGcXK4hpA/tmpoyg7u7af.png",
  "https://replicate.delivery/xezq/YdMOoi3wNrbHBFEdWdChqOfrireyZ1JaKgm8eXIfCsdvUwDTB/tmpv4q7w7yv.png",
  "https://replicate.delivery/xezq/xNkOXVm4eVWwcioeREq09gTqw6lDvCrTNbGHv6BTwNtLF8wUA/tmpts2s2qwu.png",
  "https://replicate.delivery/xezq/1neVe5dl2VjcE0dzA0LaGnX3QsPkaNmH9WBhUARf00CWK4hpA/tmpjn_j9alz.png"
]
```


## Model readme

> ## FLUX Kontext apps
> 
> Here at Replicate we've created a collection of models that are powered by FLUX Kontext [pro]. They can all be used commercially.
> 
> ## Available apps
> 
> - [Professional headshot](https://replicate.com/flux-kontext-apps/professional-headshot): Generate a  professional headshot from any image
> - [Iconic locations](https://replicate.com/flux-kontext-apps/iconic-locations): Put yourself in front of famous landmarks
> - [Multi Image](https://replicate.com/flux-kontext-apps/multi-image-kontext): An experimental FLUX Kontext model that can combine two input images
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
    "background": "black",
    "num_images": 13,
    "input_image": "https://replicate.delivery/pbxt/N5DXcBZiATNE0n0Wu7ghgVh5i7VoNzzfYtyGoNdbKYnZic7L/replicate-prediction-f2d25rg6gnrma0cq257vdw2n4c.png",
    "randomize_images": True
}

output = replicate.run(
    "flux-kontext-apps/portrait-series",
    input=input
)
for index, item in enumerate(output):
    with open(f"output_{index}.png", "wb") as file:
        file.write(item.read())
#=> output_0.png, output_1.png, output_2.png, output_3.png, o...

Copy
You can learn about pricing for this model on the model page.

The run() function returns the output directly, which you can then use or pass as the input to another model. If you want to access the full prediction object (not just the output), use the replicate.predictions.create() method instead. This will return a Prediction object that includes the prediction id, status, logs, etc.

File inputs
This model accepts files as input, e.g. input_image. You can provide a file as input using a URL, a local file on your computer, or a base64 encoded object:

Option 1: Hosted file
Use a URL as in the earlier example:

input_image = "https://replicate.delivery/pbxt/N5DXcBZiATNE0n0Wu7ghgVh5i7VoNzzfYtyGoNdbKYnZic7L/replicate-prediction-f2d25rg6gnrma0cq257vdw2n4c.png";

Copy
This is useful if you already have a file hosted somewhere on the internet.

Option 2: Local file
You can provide Replicate with a file object and the library will handle the upload for you:

input_image = open("./path/to/my/input_image.png", "rb");

Copy
Option 3: Data URI
Lastly, you can create a data URI consisting of the base64 encoded data for your file, but this is only recommended if the file is < 1mb:

import base64

with open("./path/to/my/input_image.png", 'rb') as file:
  data = base64.b64encode(file.read()).decode('utf-8')
  input_image = f"data:application/octet-stream;base64,{data}"

Copy
Then pass the file as part of the input:

input = {
    "background": "black",
    "num_images": 13,
    "input_image": input_image,
    "randomize_images": True
}

output = replicate.run(
    "flux-kontext-apps/portrait-series",
    input=input
)
for index, item in enumerate(output):
    with open(f"output_{index}.png", "wb") as file:
        file.write(item.read())
#=> output_0.png, output_1.png, output_2.png, output_3.png, o...

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
    "background": "black",
    "num_images": 13,
    "input_image": "https://replicate.delivery/pbxt/N5DXcBZiATNE0n0Wu7ghgVh5i7VoNzzfYtyGoNdbKYnZic7L/replicate-prediction-f2d25rg6gnrma0cq257vdw2n4c.png",
    "randomize_images": True
}

callback_url = "https://my.app/webhooks/replicate"
replicate.predictions.create(
  model="flux-kontext-apps/portrait-series",
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
    "background": "black",
    "num_images": 13,
    "input_image": "https://replicate.delivery/pbxt/N5DXcBZiATNE0n0Wu7ghgVh5i7VoNzzfYtyGoNdbKYnZic7L/replicate-prediction-f2d25rg6gnrma0cq257vdw2n4c.png",
    "randomize_images": True
}

prediction = replicate.predictions.create(
  model="flux-kontext-apps/portrait-series",
  input=input
)
#=> Prediction(id='z3wbih3bs64of7lmykbk7tsdf4', ...)

Copy
Cancel a prediction
You may need to cancel a prediction. Perhaps the user has navigated away from the browser or canceled your application. To prevent unnecessary work and reduce runtime costs you can use prediction.cancel() method to call the predictions.cancel endpoint.

input = {
    "background": "black",
    "num_images": 13,
    "input_image": "https://replicate.delivery/pbxt/N5DXcBZiATNE0n0Wu7ghgVh5i7VoNzzfYtyGoNdbKYnZic7L/replicate-prediction-f2d25rg6gnrma0cq257vdw2n4c.png",
    "randomize_images": True
}

prediction = replicate.predictions.create(
  model="flux-kontext-apps/portrait-series",
  input=input
)

prediction.cancel()

Copy
Async Python methods
asyncio is a module built into Python's standard library for writing concurrent code using the async/await syntax.

Replicate's Python client has support for asyncio. Each of the methods has an async equivalent prefixed with async_<name>.

input = {
    "background": "black",
    "num_images": 13,
    "input_image": "https://replicate.delivery/pbxt/N5DXcBZiATNE0n0Wu7ghgVh5i7VoNzzfYtyGoNdbKYnZic7L/replicate-prediction-f2d25rg6gnrma0cq257vdw2n4c.png",
    "randomize_images": True
}

prediction = replicate.predictions.create(
  model="flux-kontext-apps/portrait-series",
  input=input
)

prediction = await replicate.predictions.async_create(
  model="flux-kontext-apps/portrait-series",
  input=input
)

# Input schema
 
| Key | Type | Description | Default | Minimum | Maximum |
| --- | --- | --- | --- | --- | --- |
| background | string | The background of the photo | "white" | - | - |
| num_images | integer | The number of poses to generate | 4 | 1 | 13 |
| input_image | uri | Image of the person to create a series of photos for. Must be jpeg, png, gif, or webp. | - | - | - |
| output_format | string | Output format for the generated image | "png" | - | - |
| randomize_images | boolean | Whether to randomize the poses | - | - | - |
| safety_tolerance | integer | Safety tolerance, 0 is most strict and 2 is most permissive. 2 is currently the maximum allowed. | 2 | - | 2 |

# Output schema

| Type | Description |
| --- | --- |
| uri[] |  |