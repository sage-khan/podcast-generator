# Flux-1.1-pro-ultra

## About
A new high-resolution capabilities to FLUX1.1 [pro], extending its functionality to support 4x higher image resolutions (up to 4MP) while maintaining an impressive generation time of only 10 seconds per sample.

model owner = black-forest-labs
modelname = flux-1.1-pro-ultra
version = None
model replicate link = https://replicate.com/black-forest-labs/flux-1.1-pro-ultra/readme


### Higher Resolution, No Compromise in Speed
FLUX1.1 [pro] – ultra mode: This option enables image generation at four times the resolution of standard FLUX1.1 [pro], without sacrificing prompt adherence. Unlike many high-resolution models that experience significant slowdowns at higher resolutions, our performance benchmarks show sustained fast generation times—over 2.5x faster than comparable high-resolution offerings. This model is available at a competitive price of $0.06 per image.

### Raw Mode
FLUX1.1 [pro] – raw mode: For creators seeking authenticity, our new raw mode captures the genuine feel of candid photography. Toggle this feature to generate images with a less synthetic, more natural aesthetic. Compared to other text-to-image models, raw mode significantly increases diversity in human subjects and enhances the realism of nature photography

### License
By using FLUX.1 [pro] through Replicate you agree to the Black Forest Labs API agreement and the Black Forest Labs Terms of Service.

## Authentication
Whenever you make an API request, you need to authenticate using a token. A token is like a password that uniquely identifies your account and grants you access.

The following examples all expect your Replicate access token to be available from the command line. Because tokens are secrets, they should not be in your code. They should instead be stored in environment variables. Replicate clients look for the REPLICATE_API_TOKEN environment variable and use it if available.

To set this up you can use:
```
export REPLICATE_API_TOKEN=r8_2no**********************************
```



Some application frameworks and tools also support a text file named .env which you can edit to include the same token:
```
REPLICATE_API_TOKEN=r8_2no**********************************
```



The Replicate API uses the Authorization HTTP header to authenticate requests. If you’re using a client library this is handled for you.

You can test that your access token is setup correctly by using our account.get endpoint:

```
curl https://api.replicate.com/v1/account -H "Authorization: Bearer $REPLICATE_API_TOKEN"
# {"type":"user","username":"aron","name":"Aron Carroll","github_url":"https://github.com/aron"}
```


If it is working correctly you will see a JSON object returned containing some information about your account, otherwise ensure that your token is available:
```
echo "$REPLICATE_API_TOKEN"
# "r8_xyz"
```


## Setup
First you’ll need to ensure you have a Python environment setup:
```
python -m venv .venv
source .venv/bin/activate
```

Then install the replicate Python library:
```
pip install replicate
```

In a main.py file, import replicate:
```
import replicate
```

This will use the REPLICATE_API_TOKEN API token you’ve set up in your environment for authorization.

### Run the model
Use the replicate.run() method to run the model:
```
input = {
    "prompt": "a majestic snow-capped mountain peak bathed in a warm glow of the setting sun",
    "aspect_ratio": "3:2"
}

output = replicate.run(
    "black-forest-labs/flux-1.1-pro-ultra",
    input=input
)
with open("output.jpg", "wb") as file:
    file.write(output.read())
#=> output.jpg written to disk
```

You can learn about pricing for this model on the model page.

The run() function returns the output directly, which you can then use or pass as the input to another model. If you want to access the full prediction object (not just the output), use the replicate.predictions.create() method instead. This will return a Prediction object that includes the prediction id, status, logs, etc.

## File inputs
This model accepts files as input, e.g. image_prompt. You can provide a file as input using a URL, a local file on your computer, or a base64 encoded object:

### Option 1: Hosted file
Use a URL as in the earlier example:

image_prompt = "https://example.com/path/to/image_prompt";


This is useful if you already have a file hosted somewhere on the internet.

### Option 2: Local file
You can provide Replicate with a file object and the library will handle the upload for you:

image_prompt = open("./path/to/my/image_prompt", "rb");


### Option 3: Data URI
Lastly, you can create a data URI consisting of the base64 encoded data for your file, but this is only recommended if the file is < 1mb:

import base64

with open("./path/to/my/image_prompt", 'rb') as file:
  data = base64.b64encode(file.read()).decode('utf-8')
  image_prompt = f"data:application/octet-stream;base64,{data}"


Then pass the file as part of the input:

input = {
    "prompt": "a majestic snow-capped mountain peak bathed in a warm glow of the setting sun",
    "aspect_ratio": "3:2",
    "image_prompt": image_prompt
}

output = replicate.run(
    "black-forest-labs/flux-1.1-pro-ultra",
    input=input
)
with open("output.jpg", "wb") as file:
    file.write(output.read())
#=> output.jpg written to disk


# Prediction lifecycle
Running predictions and trainings can often take significant time to complete, beyond what is reasonable for an HTTP request/response.

When you run a model on Replicate, the prediction is created with a “starting” state, then instantly returned. This will then move to "processing" and eventual one of “successful”, "failed" or "canceled".

Starting
Running
Succeeded
Failed
Canceled
You can explore the prediction lifecycle by using the prediction.reload() method update the prediction to it's latest state.

```
import time

prediction = replicate.predictions.create(
  model="black-forest-labs/flux-1.1-pro-ultra",
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
```

### Webhooks
Webhooks provide real-time updates about your prediction. Specify an endpoint when you create a prediction, and Replicate will send HTTP POST requests to that URL when the prediction is created, updated, and finished.

It is possible to provide a URL to the predictions.create() function that will be requested by Replicate when the prediction status changes. This is an alternative to polling.

To receive webhooks you’ll need a web server. The following example uses AIOHTTP, a basic webserver built on top of Python’s asyncio library, but this pattern will apply to most frameworks.

```
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
```

Then create the prediction passing in the webhook URL and specify which events you want to receive out of "start" , "output" ”logs” and "completed".
```
input = {
    "prompt": "a majestic snow-capped mountain peak bathed in a warm glow of the setting sun",
    "aspect_ratio": "3:2"
}

callback_url = "https://my.app/webhooks/replicate"
replicate.predictions.create(
  model="black-forest-labs/flux-1.1-pro-ultra",
  input=input,
  webhook=callback_url,
  webhook_events_filter=["completed"]
)

# The server will now handle the event and log:
#=> Prediction(id='z3wbih3bs64of7lmykbk7tsdf4', ...)
```

The replicate.run() method is not used here. Because we're using webhooks, and we don’t need to poll for updates.

From a security perspective it is also possible to verify that the webhook came from Replicate, check out our documentation on verifying webhooks for more information.

### Access a prediction
You may wish to access the prediction object. In these cases it’s easier to use the replicate.predictions.create() function, which return the prediction object.

Though note that these functions will only return the created prediction, and it will not wait for that prediction to be completed before returning. Use replicate.predictions.get() to fetch the latest prediction.
```
import replicate

input = {
    "prompt": "a majestic snow-capped mountain peak bathed in a warm glow of the setting sun",
    "aspect_ratio": "3:2"
}

prediction = replicate.predictions.create(
  model="black-forest-labs/flux-1.1-pro-ultra",
  input=input
)
#=> Prediction(id='z3wbih3bs64of7lmykbk7tsdf4', ...)
```

### Cancel a prediction
You may need to cancel a prediction. Perhaps the user has navigated away from the browser or canceled your application. To prevent unnecessary work and reduce runtime costs you can use prediction.cancel() method to call the predictions.cancel endpoint.
```
input = {
    "prompt": "a majestic snow-capped mountain peak bathed in a warm glow of the setting sun",
    "aspect_ratio": "3:2"
}

prediction = replicate.predictions.create(
  model="black-forest-labs/flux-1.1-pro-ultra",
  input=input
)

prediction.cancel()
```

### Async Python methods
asyncio is a module built into Python's standard library for writing concurrent code using the async/await syntax.

Replicate's Python client has support for asyncio. Each of the methods has an async equivalent prefixed with async_<name>.
```
input = {
    "prompt": "a majestic snow-capped mountain peak bathed in a warm glow of the setting sun",
    "aspect_ratio": "3:2"
}

prediction = replicate.predictions.create(
  model="black-forest-labs/flux-1.1-pro-ultra",
  input=input
)

prediction = await replicate.predictions.async_create(
  model="black-forest-labs/flux-1.1-pro-ultra",
  input=input
)
```


### Sample JSON Prediction response

This can be found from replicate.com/p/<prediction_id> 

For instance here is https://replicate.com/p/rcfap78c61rme0cphg7b9qnnzm

```json
{
  "completed_at": "2025-05-01T13:34:22.987964Z",
  "created_at": "2025-05-01T13:34:13.040000Z",
  "data_removed": false,
  "error": null,
  "id": "rcfap78c61rme0cphg7b9qnnzm",
  "input": {
    "raw": false,
    "prompt": "A detailed portrait of a cyberpunk samurai with neon helmet",
    "aspect_ratio": "1:1",
    "output_format": "jpg",
    "safety_tolerance": 2,
    "image_prompt_strength": 0.1
  },
  "logs": "Running prediction...\nUsing seed: 46132\nGenerating image...\nGenerated image in 9.8sec\nDownloaded image in 0.11sec",
  "metrics": {
    "image_count": 1,
    "predict_time": 9.940275137,
    "total_time": 9.947964
  },
  "output": "https://replicate.delivery/xezq/l0JESQY6VyoWNZ05XX3gAiRZt6C6EwxPfp4fltmpCBXeSlQpA/tmpckfzds_q.jpg",
  "started_at": "2025-05-01T13:34:13.047689Z",
  "status": "succeeded",
  "urls": {
    "stream": "https://stream.replicate.com/v1/files/bcwr-wu3fqu7nz6aptcwlwsm7exfj6zx5unqpzwvfjkmxsy3jnrnyfeqa",
    "get": "https://api.replicate.com/v1/predictions/rcfap78c61rme0cphg7b9qnnzm",
    "cancel": "https://api.replicate.com/v1/predictions/rcfap78c61rme0cphg7b9qnnzm/cancel"
  },
  "version": "hidden"
}
```

