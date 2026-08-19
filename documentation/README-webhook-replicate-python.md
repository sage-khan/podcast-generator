# Replicate Python client

This is a Python client for [Replicate](https://replicate.com). It lets you run models from your Python code or Jupyter notebook, and do various other things on Replicate.

## Breaking Changes in 1.0.0

The 1.0.0 release contains breaking changes:

- The `replicate.run()` method now returns `FileOutput`s instead of URL strings by default for models that output files. `FileOutput` implements an iterable interface similar to `httpx.Response`, making it easier to work with files efficiently.

To revert to the previous behavior, you can opt out of `FileOutput` by passing `use_file_output=False` to `replicate.run()`:

```python
output = replicate.run("acmecorp/acme-model", use_file_output=False)
```

In most cases, updating existing applications to call `output.url` should resolve any issues. But we recommend using the `FileOutput` objects directly as we have further improvements planned to this API and this approach is guaranteed to give the fastest results.

> [!TIP]
> **👋** Check out an interactive version of this tutorial on [Google Colab](https://colab.research.google.com/drive/1K91q4p-OhL96FHBAVLsv9FlwFdu6Pn3c).
>
> [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/drive/1K91q4p-OhL96FHBAVLsv9FlwFdu6Pn3c)

## Requirements

- Python 3.8+

## Install

```sh
pip install replicate
```

## Authenticate

Before running any Python scripts that use the API, you need to set your Replicate API token in your environment.

Grab your token from [replicate.com/account](https://replicate.com/account) and set it as an environment variable:

```
export REPLICATE_API_TOKEN=<your token>
```

We recommend not adding the token directly to your source code, because you don't want to put your credentials in source control. If anyone used your API key, their usage would be charged to your account.

## Run a model

Create a new Python file and add the following code, replacing the model identifier and input with your own:

```python
>>> import replicate
>>> outputs = replicate.run(
        "black-forest-labs/flux-schnell",
        input={"prompt": "astronaut riding a rocket like a horse"}
    )
[<replicate.helpers.FileOutput object at 0x107179b50>]
>>> for index, output in enumerate(outputs):
        with open(f"output_{index}.webp", "wb") as file:
            file.write(output.read())
```

`replicate.run` raises `ModelError` if the prediction fails.
You can access the exception's `prediction` property 
to get more information about the failure.

```python
import replicate
from replicate.exceptions import ModelError

try:
  output = replicate.run("stability-ai/stable-diffusion-3", { "prompt": "An astronaut riding a rainbow unicorn" })
except ModelError as e
  if "(some known issue)" in e.prediction.logs:
    pass

  print("Failed prediction: " + e.prediction.id)
```

> [!NOTE]
> By default the Replicate client will hold the connection open for up to 60 seconds while waiting
> for the prediction to complete. This is designed to optimize getting the model output back to the
> client as quickly as possible.
>
> The timeout can be configured by passing `wait=x` to `replicate.run()` where `x` is a timeout
> in seconds between 1 and 60. To disable the sync mode you can pass `wait=False`.

## AsyncIO support

You can also use the Replicate client asynchronously by prepending `async_` to the method name. 

Here's an example of how to run several predictions concurrently and wait for them all to complete:

```python
import asyncio
import replicate
 
# https://replicate.com/stability-ai/sdxl
model_version = "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b"
prompts = [
    f"A chariot pulled by a team of {count} rainbow unicorns"
    for count in ["two", "four", "six", "eight"]
]

async with asyncio.TaskGroup() as tg:
    tasks = [
        tg.create_task(replicate.async_run(model_version, input={"prompt": prompt}))
        for prompt in prompts
    ]

results = await asyncio.gather(*tasks)
print(results)
```

To run a model that takes a file input you can pass either
a URL to a publicly accessible file on the Internet
or a handle to a file on your local device.

```python
>>> output = replicate.run(
        "andreasjansson/blip-2:f677695e5e89f8b236e52ecd1d3f01beb44c34606419bcc19345e046d8f786f9",
        input={ "image": open("path/to/mystery.jpg") }
    )

"an astronaut riding a horse"
```

## Run a model and stream its output

Replicate’s API supports server-sent event streams (SSEs) for language models. 
Use the `stream` method to consume tokens as they're produced by the model.

```python
import replicate

for event in replicate.stream(
    "meta/meta-llama-3-70b-instruct",
    input={
        "prompt": "Please write a haiku about llamas.",
    },
):
    print(str(event), end="")
```

> [!TIP]
> Some models, like [meta/meta-llama-3-70b-instruct](https://replicate.com/meta/meta-llama-3-70b-instruct), 
> don't require a version string. 
> You can always refer to the API documentation on the model page for specifics.

You can also stream the output of a prediction you create.
This is helpful when you want the ID of the prediction separate from its output.

```python
prediction = replicate.predictions.create(
    model="meta/meta-llama-3-70b-instruct",
    input={"prompt": "Please write a haiku about llamas."},
    stream=True,
)

for event in prediction.stream():
    print(str(event), end="")
```

For more information, see
["Streaming output"](https://replicate.com/docs/streaming) in Replicate's docs.


## Run a model in the background

You can start a model and run it in the background using async mode:

```python
>>> model = replicate.models.get("kvfrans/clipdraw")
>>> version = model.versions.get("5797a99edc939ea0e9242d5e8c9cb3bc7d125b1eac21bda852e5cb79ede2cd9b")
>>> prediction = replicate.predictions.create(
    version=version,
    input={"prompt":"Watercolor painting of an underwater submarine"})

>>> prediction
Prediction(...)

>>> prediction.status
'starting'

>>> dict(prediction)
{"id": "...", "status": "starting", ...}

>>> prediction.reload()
>>> prediction.status
'processing'

>>> print(prediction.logs)
iteration: 0, render:loss: -0.6171875
iteration: 10, render:loss: -0.92236328125
iteration: 20, render:loss: -1.197265625
iteration: 30, render:loss: -1.3994140625

>>> prediction.wait()

>>> prediction.status
'succeeded'

>>> prediction.output
<replicate.helpers.FileOutput object at 0x107179b50>

>>> with open("output.png", "wb") as file:
        file.write(prediction.output.read())
```

## Run a model in the background and get a webhook

You can run a model and get a webhook when it completes, instead of waiting for it to finish:

```python
model = replicate.models.get("ai-forever/kandinsky-2.2")
version = model.versions.get("ea1addaab376f4dc227f5368bbd8eff901820fd1cc14ed8cad63b29249e9d463")
prediction = replicate.predictions.create(
    version=version,
    input={"prompt":"Watercolor painting of an underwater submarine"},
    webhook="https://example.com/your-webhook",
    webhook_events_filter=["completed"]
)
```

For details on receiving webhooks, see [replicate.com/docs/webhooks](https://replicate.com/docs/webhooks).

## Compose models into a pipeline

You can run a model and feed the output into another model:

```python
laionide = replicate.models.get("afiaka87/laionide-v4").versions.get("b21cbe271e65c1718f2999b038c18b45e21e4fba961181fbfae9342fc53b9e05")
swinir = replicate.models.get("jingyunliang/swinir").versions.get("660d922d33153019e8c263a3bba265de882e7f4f70396546b6c9c8f9d47a021a")
image = laionide.predict(prompt="avocado armchair")
upscaled_image = swinir.predict(image=image)
```

## Get output from a running model

Run a model and get its output while it's running:

```python
iterator = replicate.run(
    "pixray/text2image:5c347a4bfa1d4523a58ae614c2194e15f2ae682b57e3797a5bb468920aa70ebf",
    input={"prompts": "san francisco sunset"}
)

for index, image in enumerate(iterator):
    with open(f"file_{index}.png", "wb") as file:
        file.write(image.read())
```

## Cancel a prediction

You can cancel a running prediction:

```python
>>> model = replicate.models.get("kvfrans/clipdraw")
>>> version = model.versions.get("5797a99edc939ea0e9242d5e8c9cb3bc7d125b1eac21bda852e5cb79ede2cd9b")
>>> prediction = replicate.predictions.create(
        version=version,
        input={"prompt":"Watercolor painting of an underwater submarine"}
    )

>>> prediction.status
'starting'

>>> prediction.cancel()

>>> prediction.reload()
>>> prediction.status
'canceled'
```

## List predictions

You can list all the predictions you've run:

```python
replicate.predictions.list()
# [<Prediction: 8b0ba5ab4d85>, <Prediction: 494900564e8c>]
```

Lists of predictions are paginated. You can get the next page of predictions by passing the `next` property as an argument to the `list` method:

```python
page1 = replicate.predictions.list()

if page1.next:
    page2 = replicate.predictions.list(page1.next)
```

## Load output files

Output files are returned as `FileOutput` objects:

```python
import replicate
from PIL import Image # pip install pillow

output = replicate.run(
    "stability-ai/stable-diffusion:27b93a2413e7f36cd83da926f3656280b2931564ff050bf9575f1fdf9bcd7478",
    input={"prompt": "wavy colorful abstract patterns, oceans"}
    )

# This has a .read() method that returns the binary data.
with open("my_output.png", "wb") as file:
  file.write(output[0].read())
  
# It also implements the iterator protocol to stream the data.
background = Image.open(output[0])
```

### FileOutput

Is a [file-like](https://docs.python.org/3/glossary.html#term-file-object) object returned from the `replicate.run()` method that makes it easier to work with models that output files. It implements `Iterator` and `AsyncIterator` for reading the file data in chunks as well as `read()` and `aread()` to read the entire file into memory.

> [!NOTE]
> It is worth noting that at this time `read()` and `aread()` do not currently accept a `size` argument to read up to `size` bytes.

Lastly, the URL of the underlying data source is available on the `url` attribute though we recommend you use the object as an iterator or use its `read()` or `aread()` methods, as the `url` property may not always return HTTP URLs in future.

```python
print(output.url) #=> "data:image/png;base64,xyz123..." or "https://delivery.replicate.com/..."
```

To consume the file directly:

```python
with open('output.bin', 'wb') as file:
    file.write(output.read())
```

Or for very large files they can be streamed:

```python
with open(file_path, 'wb') as file:
    for chunk in output:
        file.write(chunk)
```

Each of these methods has an equivalent `asyncio` API.

```python
async with aiofiles.open(filename, 'w') as file:
    await file.write(await output.aread())

async with aiofiles.open(filename, 'w') as file:
    await for chunk in output:
        await file.write(chunk)
```

For streaming responses from common frameworks, all support taking `Iterator` types:

**Django**

```python
@condition(etag_func=None)
def stream_response(request):
    output = replicate.run("black-forest-labs/flux-schnell", input={...}, use_file_output =True)
    return HttpResponse(output, content_type='image/webp')
```
  
**FastAPI**

```python
@app.get("/")
async def main():
    output = replicate.run("black-forest-labs/flux-schnell", input={...}, use_file_output =True)
    return StreamingResponse(output)
```

**Flask**

```python
@app.route('/stream')
def streamed_response():
    output = replicate.run("black-forest-labs/flux-schnell", input={...}, use_file_output =True)
    return app.response_class(stream_with_context(output))
```

You can opt out of `FileOutput` by passing `use_file_output=False` to the `replicate.run()` method.

```python
const replicate = replicate.run("acmecorp/acme-model", use_file_output=False);
```

## List models

You can list the models you've created:

```python
replicate.models.list()
```

Lists of models are paginated. You can get the next page of models by passing the `next` property as an argument to the `list` method, or you can use the `paginate` method to fetch pages automatically.

```python
# Automatic pagination using `replicate.paginate` (recommended)
models = []
for page in replicate.paginate(replicate.models.list):
    models.extend(page.results)
    if len(models) > 100:
        break

# Manual pagination using `next` cursors
page = replicate.models.list()
while page:
    models.extend(page.results)
    if len(models) > 100:
          break
    page = replicate.models.list(page.next) if page.next else None
```

You can also find collections of featured models on Replicate:

```python
>>> collections = [collection for page in replicate.paginate(replicate.collections.list) for collection in page]
>>> collections[0].slug
"vision-models"
>>> collections[0].description
"Multimodal large language models with vision capabilities like object detection and optical character recognition (OCR)"

>>> replicate.collections.get("text-to-image").models
[<Model: stability-ai/sdxl>, ...]
```

## Create a model

You can create a model for a user or organization
with a given name, visibility, and hardware SKU:

```python
import replicate

model = replicate.models.create(
    owner="your-username",
    name="my-model",
    visibility="public",
    hardware="gpu-a40-large"
)
```

Here's how to list of all the available hardware for running models on Replicate:

```python
>>> [hw.sku for hw in replicate.hardware.list()]
['cpu', 'gpu-t4', 'gpu-a40-small', 'gpu-a40-large']
```

## Fine-tune a model

Use the [training API](https://replicate.com/docs/fine-tuning) to fine-tune models to make them better at a particular task.  To see what **language models** currently support fine-tuning,  check out Replicate's [collection of trainable language models](https://replicate.com/collections/trainable-language-models).

If you're looking to fine-tune **image models**, check out Replicate's [guide to fine-tuning image models](https://replicate.com/docs/guides/fine-tune-an-image-model).

Here's how to fine-tune a model on Replicate:

```python
training = replicate.trainings.create(
    model="stability-ai/sdxl",
    version="39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b",
    input={
      "input_images": "https://my-domain/training-images.zip",
      "token_string": "TOK",
      "caption_prefix": "a photo of TOK",
      "max_train_steps": 1000,
      "use_face_detection_instead": False
    },
    # You need to create a model on Replicate that will be the destination for the trained version.
    destination="your-username/model-name"
)
```

## Customize client behavior

The `replicate` package exports a default shared client. This client is initialized with an API token set by the `REPLICATE_API_TOKEN` environment variable.

You can create your own client instance to pass a different API token value, add custom headers to requests, or control the behavior of the underlying [HTTPX client](https://www.python-httpx.org/api/#client):

```python
import os
from replicate.client import Client

replicate = Client(
    api_token=os.environ["SOME_OTHER_REPLICATE_API_TOKEN"]
    headers={
        "User-Agent": "my-app/1.0"
    }
)
```

> [!WARNING]
> Never hardcode authentication credentials like API tokens into your code.
> Instead, pass them as environment variables when running your program.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md)


## MORE

To receive webhook events, specify a webhook URL in the request body when creating a prediction or a training.

Here's an example using the replicate JavaScript client to create a prediction and request a webhook event when the prediction is completed:

await replicate.predictions.create({
  version: "d55b9f2d...",
  input: { prompt: "call me later maybe" },
  webhook: "https://example.com/replicate-webhook",
  webhook_events_filter: ["completed"], // optional
});

Webhook events filter
By default, we will send requests to your webhook URL whenever there are new outputs or the prediction has finished. You can change which events trigger webhook requests by specifying webhook_events_filter in the prediction request:

start: immediately on prediction start
output: each time a prediction generates an output (note that predictions can generate multiple outputs)
logs: each time log output is generated by a prediction
completed: when the prediction reaches a terminal state (succeeded/canceled/failed)
For example, if you only wanted requests to be sent at the start and end of the prediction, you would provide:

Webhook events filter
By default, we will send requests to your webhook URL whenever there are new outputs or the prediction has finished. You can change which events trigger webhook requests by specifying webhook_events_filter in the prediction request:

start: immediately on prediction start
output: each time a prediction generates an output (note that predictions can generate multiple outputs)
logs: each time log output is generated by a prediction
completed: when the prediction reaches a terminal state (succeeded/canceled/failed)
For example, if you only wanted requests to be sent at the start and end of the prediction, you would provide:

{
  "input": {
    "text": "Alice"
  },
  "webhook": "https://example.com/my-webhook",
  "webhook_events_filter": ["start", "completed"]
}

Requests for event types output and logs will be sent at most once every 500ms.

If you request start and completed webhooks, then they'll always be sent regardless of throttling.

Webhooks for trainings
In addition to predictions, you can also receive webhooks when fine-tuning models with the training API:

await replicate.trainings.create({
  version: "d55b9f2d...",
  destination: "my-username/my-model",
  input: { training_data: "..." },
  webhook: "https://example.com/replicate-webhook",
});



Receive webhooks


The request body is a prediction object in JSON format. This object has the same structure as the object returned by the get a prediction API. Here's an example of an unfinished prediction:





Add query params to your webhook URL to pass along extra metadata, like an internal ID you're using for a prediction. For example: https://example.com/replicate-webhook?customId=123

Replicate can send an HTTP POST request to the URL you specified whenever the prediction is created, has new logs, new output, or is completed.

{
  "id": "ufawqhfynnddngldkgtslldrkq",
  "version": "5c7d5dc6dd8bf75c1acaa8565735e7986bc5b66206b55cca93cb72c9bf15ccaa",
  "created_at": "2022-04-26T22:13:06.224088Z",
  "started_at": null,
  "completed_at": null,
  "status": "starting",
  "input": {
    "text": "Alice"
  },
  "output": null,
  "error": null,
  "logs": null,
  "metrics": {}
}

Refer to Prediction status (https://replicate.com/docs/topics/predictions/lifecycle) for the list of possible status values.

Here's an example of a Next.js webhook handler:

// pages/api/replicate-webhook.js
export default async function handler(req, res) {
  console.log("🪝 incoming webhook!", req.body.id);
  const prediction = req.body;
  await saveToMyDatabase(prediction);
  await sendSlackNotification(prediction);
  res.end();
}

Your endpoint should respond with a 2xx status code within a few seconds; otherwise, the webhook might be retried.

Filtering webhook events
By default, Replicate sends requests to your webhook URL whenever there are new outputs or the prediction has finished. You can change which events trigger webhook requests by specifying a webhook_events_filter array in the JSON body of the prediction request.

start: immediately on prediction start
output: each time a prediction generates an output (note that predictions can generate multiple outputs)
logs: each time log output is generated by a prediction
completed: when the prediction reaches a terminal state (succeeded/canceled/failed)
For example, if you only wanted requests to be sent at the start and end of the prediction, you would provide:

{
  "input": {
    "text": "Alice"
  },
  "webhook": "https://example.com/my-webhook",
  "webhook_events_filter": ["start", "completed"]
}


Requests for event types output and logs will be sent at most once every 500ms. If you request start and completed webhooks, then they'll always be sent regardless of throttling.

Retries
When Replicate sends the terminal webhook for a prediction (where the status is succeeded, failed or canceled), we check the response status we get. If we can't make the request at all, or if we get a 4xx or 5xx response, we'll retry the webhook. We retry several times on an exponential backoff. The final retry is sent about 1 minute after the prediction completed.

We do not retry any webhooks for intermediate states.

Idempotency
Make webhook handlers idempotent. Identical webhooks can be sent more than once, so you'll need handle potentially duplicate information.

Ordering
In rare cases, webhooks for a single prediction may arrive out of order. We recommend you include logic in your application to ignore all webhooks for a prediction after the terminal webhook (where the status is succeeded, failed or canceled). If you are using output or logs events, you may also want to ignore webhooks that regress the status of the prediction (for example, by emitting less output or fewer logs).

 Verify webhooks

 To prevent unauthorized requests, Replicate signs every webhook and its metadata with a unique key for each user or organization. You can use this signature to verify the webhook indeed comes from Replicate before you process it.

Why verify webhooks?
A webhook is an HTTP POST from an unknown source. Attackers can impersonate services by simply sending a fake webhook to an endpoint.

Another potential security hole is a replay attack, wherein an attacker intercepts a valid webhook payload (including the signature) and re-transmits it to your endpoint. This payload will pass signature validation, and will therefore be acted upon. To mitigate replay attacks, Replicate includes a timestamp indicating when the webhook attempt occurred.

Manually validating webhook data
Each webhook delivery includes three HTTP headers with additional information that you can use to verify the authenticity of the request:

webhook-id: The unique message identifier for the webhook messages. This identifier is unique across all messages but will be the same when a webhook is being resent (e.g. retried).
webhook-timestamp: timestamp in seconds since epoch.
webhook-signature: the Base64 encoded list of signatures (space delimited).
Constructing the signed content
As a webhook receiver, you are responsible for constructing this signed content and performing the validation steps. To validate a webhook, the signed data must be constructed into a well-defined structure from the payload data (body), webhook-id, and webhook-timestamp headers.

The content to sign is composed by concatenating the id, timestamp, and data, separated by the full-stop character (.).

In code it will look something like:

const signedContent = `${webhook_id}.${webhook_timestamp}.${body}`


In the example above, body is the raw body of the request. The signature is sensitive to any changes, so even a small change in the body will cause the signature to be completely different. This means that you should not change the body in any way before verifying.

Retrieving the webhook signing key
Replicate provides an API endpoint you can use to retrieve the signing key. The signing key is unique to your user or organization. The endpoint will return only the signing key associated with the API token and its corresponding user or organization.

For optimal performance of the webhook receiver, it is advised to locally cache the signing key. By doing so, you eliminate the need for the receiver to make a request to the Replicate API for validation every time a webhook is received.

GET https://api.replicate.com/v1/webhooks/default/secret


Example cURL request:




{
    "key": "whsec_C2FVsBQIhrscChlQIMV+b5sSYspob7oD"
}

The response will be a JSON object with a single key field:


{
    "key": "whsec_C2FVsBQIhrscChlQIMV+b5sSYspob7oD"
}

Determining the expected signature
Replicate uses an HMAC with SHA-256 to sign its webhooks.

To calculate the expected signature, you should HMAC the signed_content from above using the base64 portion of the signing secret (this is the part after the whsec_ prefix) as the key. For example, given a secret whsec_C2FVsBQIhrscChlQIMV+b5sSYspob7oD, you will want to use C2FVsBQIhrscChlQIMV+b5sSYspob7oD.

Here's an example of how you can calculate the signature in Node.js:


const crypto = require('crypto');
 
const signedContent = `${webhook_id}.${webhook_timestamp}.${body}`
const secret = "whsec_C2FVsBQIhrscChlQIMV+b5sSYspob7oD";
 
// Base64 decode the secret
const secretBytes = new Buffer(secret.split('_')[1], "base64");
const signature = crypto
  .createHmac('sha256', secretBytes)
  .update(signedContent)
  .digest('base64');
console.log(signature);


This generated signature should match one of the ones sent in the webhook-signature header.

The webhook-signature header is composed of a list of space-delimited signatures and their corresponding version identifiers. The signature list is most commonly of length one, though there could be any number of signatures. For example:

v1,g0hM9SsE+OTPJTGt/tmIKtSyZlE3uFJELVlNIOLJ1OE= v1,bm9ldHUjKzFob2VudXRob2VodWUzMjRvdWVvdW9ldQo= v2,MzJsNDk4MzI0K2VvdSMjMTEjQEBAQDEyMzMzMzEyMwo=

Make sure to remove the version prefix and delimiter (e.g. v1,) before verifying the signature.

Please note that to compute the signatures it's recommended to use a constant-time string comparison method in order to prevent timing attacks.

An example of how to do this in Node.js:





const expectedSignatures = webhookSignatures.split(' ').map(sig => sig.split(',')[1]);
const isValid = expectedSignatures.some(expectedSignature => expectedSignature === computedSignature);
console.log(isValid);


Verify timestamp
As mentioned above, Replicate also sends the timestamp of the attempt in the webhook-timestamp header. You should compare the timestamp against your system timestamp and make sure it's within your tolerance in order to prevent replay attacks.


Test your webhook code
When writing the code for your new webhook handler, it's useful to be able to receive real webhooks in your development environment so you can verify your code is handling them as expected.

ngrok is a free reverse proxy tool that can create a secure tunnel to your local machine so you can receive webhooks. If you have Node.js installed, run ngrok directly from the command line using the npx command that's included with Node.js.

npx ngrok http 3000

The command above will generate output that looks like thiS

Session Status                online
Session Expires               1 hour, 59 minutes
Version                       2.3.41
Region                        United States (us)
Web Interface                 http://127.0.0.1:4040
Forwarding                    http://3e48-20-171-41-18.ngrok.io -> http://localhost:3000
Forwarding                    https://3e48-20-171-41-18.ngrok.io -> http://localhost:3000


The HTTPS URL in the output (http://3e48-20-171-41-18.ngrok.io in the example above) is a temporary URL pointing to your local machine. Copy that URL and use it as the base of your webhook URL.

Here's an example using the replicate JavaScript client:


await replicate.predictions.create({
  version: "d55b9f2d...",
  input: { prompt: "call me later maybe" },
  webhook: "https://3e48-20-171-41-18.ngrok.io/replicate-webhook",
});


Your webhook handler should now receive webhooks from Replicate. Once you've deployed your app, change the value of the webhook URL to your production webhook handler endpoint when creating predictions.

For a real-world example of webhook handling in Next.js, check out Scribble Diffusion's codebase (https://github.com/replicate/scribble-diffusion/pull/27/commits/627c872c78aad89cadd02798d37d4696e3278a12).




## Example Response from replicate site on webhooks

Prediction example on https://replicate.com/p/a5fx7rawgsrmc0cphme99z248m?output=json

```
Model = bytedance/hyper-flux-16step:382cf8959fb0f0d665b26e7e80b8d6dc3faaef1510f14ce017e8c732bb3d1eb7
ID = a5fx7rawgsrmc0cphme99z248m (prediction id from replicate)
Status = Succeeded
Source = API
Hardware = H100
Total duration = 3.3s
Created = less than a minute ago (as pf 1 May 25 time 23:32)
Webhooks = All successful
```
Json Response is as follows:

```json
{
  "completed_at": "2025-05-01T18:29:31.628720Z",
  "created_at": "2025-05-01T18:29:28.326000Z",
  "data_removed": false,
  "error": null,
  "id": "a5fx7rawgsrmc0cphme99z248m",
  "input": {
    "width": 1280,
    "height": 720,
    "prompt": "Intense close-up of character's face, fear and determination. Style: Action movie, high-energy, fast-paced, dynamic composition, dramatic lighting, intense action, close-ups, dramatic camera angles Lighting: Dramatic, high-contrast, shadows, spotlight, neon lights. modest clothing, fully clothed, Additional: 4K resolution, sharp focus, -blurry, -out of focus, -simple, -slow motion, -time lapse, -fisheye lens, -tilt-shift",
    "num_outputs": 1,
    "aspect_ratio": "custom",
    "output_format": "jpg",
    "guidance_scale": 3.5,
    "output_quality": 80,
    "num_inference_steps": 16,
    "disable_safety_checker": true
  },
  "logs": "Using seed: 27934\nPrompt: Intense close-up of character's face, fear and determination. Style: Action movie, high-energy, fast-paced, dynamic composition, dramatic lighting, intense action, close-ups, dramatic camera angles Lighting: Dramatic, high-contrast, shadows, spotlight, neon lights. modest clothing, fully clothed, Additional: 4K resolution, sharp focus, -blurry, -out of focus, -simple, -slow motion, -time lapse, -fisheye lens, -tilt-shift\ntxt2img mode\nThe following part of your input was truncated because CLIP can only handle sequences up to 77 tokens: [', - out of focus, - simple, - slow motion, - time lapse, - fisheye lens, - tilt - shift']\n  0%|          | 0/16 [00:00<?, ?it/s]\n  6%|▋         | 1/16 [00:00<00:02,  5.09it/s]\n 12%|█▎        | 2/16 [00:00<00:02,  6.44it/s]\n 19%|█▉        | 3/16 [00:00<00:02,  5.74it/s]\n 25%|██▌       | 4/16 [00:00<00:02,  5.45it/s]\n 31%|███▏      | 5/16 [00:00<00:02,  5.30it/s]\n 38%|███▊      | 6/16 [00:01<00:01,  5.21it/s]\n 44%|████▍     | 7/16 [00:01<00:01,  5.18it/s]\n 50%|█████     | 8/16 [00:01<00:01,  5.15it/s]\n 56%|█████▋    | 9/16 [00:01<00:01,  5.12it/s]\n 62%|██████▎   | 10/16 [00:01<00:01,  5.10it/s]\n 69%|██████▉   | 11/16 [00:02<00:00,  5.10it/s]\n 75%|███████▌  | 12/16 [00:02<00:00,  5.08it/s]\n 81%|████████▏ | 13/16 [00:02<00:00,  5.07it/s]\n 88%|████████▊ | 14/16 [00:02<00:00,  5.05it/s]\n 94%|█████████▍| 15/16 [00:02<00:00,  5.03it/s]\n100%|██████████| 16/16 [00:03<00:00,  5.03it/s]\n100%|██████████| 16/16 [00:03<00:00,  5.17it/s]",
  "metrics": {
    "predict_time": 3.296609687,
    "total_time": 3.30272
  },
  "output": [
    "https://replicate.delivery/xezq/B8wA296w4J5DEVV77MY4tZO4kNkXjnNAe3NduFBBGmtFfWoUA/out-0.jpg"
  ],
  "started_at": "2025-05-01T18:29:28.332111Z",
  "status": "succeeded",
  "urls": {
    "stream": "https://stream.replicate.com/v1/files/bcwr-mpfwu4akuhyeiwiaukr6htfc4uji7fr3fqdwiodapikiazvjjraq",
    "get": "https://api.replicate.com/v1/predictions/a5fx7rawgsrmc0cphme99z248m",
    "cancel": "https://api.replicate.com/v1/predictions/a5fx7rawgsrmc0cphme99z248m/cancel"
  },
  "version": "382cf8959fb0f0d665b26e7e80b8d6dc3faaef1510f14ce017e8c732bb3d1eb7"
}
```

Webhooks details this prediction were: 
```
https://api.example.com/replicate/webhook?context%5Bmodel_id%5D=374688&context%5Bmodel_type%5D=faceless

prediction.succeeded

Thu, 01 May 2025 18:29:31 GMT

Status code

200

Response

{"message":"Webhook Handled"}
```





Some models generate files as output, like images, audio, or video. With the release of version 1.0.0 of our client libraries, the way you handle these output files has changed.

[](#fileoutput-objects)FileOutput Objects
-----------------------------------------

When a model generates files, `replicate.run()` now returns `FileOutput` objects instead of URLs. These objects provide direct access to the file data, simplifying your code and speeding up your applications.

Here’s how you can work with `FileOutput` objects:

### [](#python)Python

```python
import replicate
output = replicate.run(
    "black-forest-labs/flux-schnell",
    input={"prompt": "A majestic lion"}
)
# If the model returns a single output
with open('output.png', 'wb') as f:
    f.write(output[0].read())
# If the model returns multiple outputs
for idx, file_output in enumerate(output):
    with open(f'output_{idx}.png', 'wb') as f:
        f.write(file_output.read())
# You can also stream the file by using its iterator methods:
for chunk in output:
  print(chunk)
```

### [](#javascript)JavaScript

```javascript
import Replicate from "replicate";
const replicate = new Replicate();
const output = await replicate.run(
    "black-forest-labs/flux-schnell",
    { input: { prompt: "A majestic lion" }}
);
// If the model returns a single output
fs.writeFileSync("output.png", output);
// If the model returns multiple outputs
output.forEach((fileOutput, idx) => {
    fs.writeFileSync(`output_${idx}.png`, fileOutput);
});
```

[](#fileoutput-properties-and-methods)FileOutput Properties and Methods
-----------------------------------------------------------------------

The `FileOutput` type mimics a file-like object available on the platform.

Each Python `FileOutput` object implements `Iterator[bytes]` and `AsyncIterator[bytes]` and provides:

*   `read()`: Returns the binary content of the file
*   `url`: The URL of the underlying data source

Each JavaScript `FileOutput` object is a [`ReadableStream`](https://developer.mozilla.org/en-US/docs/Web/API/Streams_API/Using_readable_streams) that also provides:

*   `blob()`: Reads the binary content of the file
*   `pipe()`: Stream the file data to a `WriteableStream` instance.
*   `url()`: The URL of the underlying data source

### [](#streaming-responses)Streaming Responses

In Python, `FileOutput` implements `Iterator[bytes]` and `AsyncIterator[bytes]` which means you can pass it to any function that takes one as input:

```python
with open("output.png", "wb") as f:
    for chunk in output:
        f.write(chunk)
# Using asyncio
import aiofiles
async with aiofiles.open('output.png', mode='wb') as f:
    async for chunk in output:
        await f.write(chunk)
```

In JavaScript, `FileOutput` implements `ReadableStream` which means you can pass it to any function that takes one as input (such as `Response` and `fs.writeFile`) to stream large files efficiently:

```javascript
const fileStream = fs.createWriteStream("output.png");
output[0].pipe(fileStream);
```

### [](#working-with-urls)Working with URLs

Sometimes you might want to use the file’s URL directly - for example, when displaying images in a web application or passing the URL to another service. Each `FileOutput` object has a `url` property:

```python
# Get the URL of the first output
url = output[0].url
print(f"File available at: {url}")
``````javascript
// Get the URL of the first output
const url = output[0].url;
// Example: Using the URL in an HTML image
const img = document.createElement('img');
img.src = url;  // Works with both HTTP URLs and data URIs
document.body.appendChild(img);
```

Remember: URLs for files will point to `replicate.delivery` and will expire after one hour.

[](#migrating-from-earlier-versions)Migrating from Earlier Versions
-------------------------------------------------------------------

If you’re updating from a version before 1.0.0:

1.  Replace any code that fetches URLs with direct use of the `FileOutput` object
2.  Use `read()` or `pipe()` to access file data instead of downloading from URLs
3.  Remove any URL handling or Authorization header logic
4.  If you need URLs (e.g., for displaying images), use the `url` property of the `FileOutput` object

[](#opting-out-of-the-blocking-api)Opting Out of the Blocking API
-----------------------------------------------------------------

If you prefer not to use the blocking API, you can opt for the polling mode. This allows you to handle predictions asynchronously and can be useful if you want to avoid holding a connection open. To use polling mode, pass the relevant argument to the `run()` method in your favorite language:

### [](#python-1)Python

```python
output = replicate.run(
    "black-forest-labs/flux-schnell",
    input={"prompt": "A majestic lion"},
    wait=False
)
```

### [](#javascript-1)JavaScript

```javascript
const output = await replicate.run(
    "black-forest-labs/flux-schnell",
    { input: { prompt: "A majestic lion" }, wait: { type: "poll" } }
);
```

You can also opt out of `FileOutput` objects entirely by configuring the client when you create it:

```javascript
const replicate = new Replicate({ useFileOutput: false });
```

This will make the client return URLs instead of `FileOutput` objects, which can be useful if you’re migrating from an older version or prefer to handle the files yourself.

[](#data-retention)Data Retention
---------------------------------

For predictions created through the API, output files are automatically deleted after an hour. You must save a copy of any files in the output if you’d like to continue using them. For more details on how to store prediction data, see the [webhooks docs](/docs/topics/webhooks).

For predictions created through the web interface, output files are kept indefinitely, unless you delete them manually.

[](#output-file-domains)Output File Domains
-------------------------------------------

Output files are served by `replicate.delivery` and its subdomains.

If you use an allow list of external domains for your assets, add `replicate.delivery` and `*.replicate.delivery` to it.

For example, if you’re building a [Next.js app that displays output files from Replicate](/docs/get-started/nextjs), update your Next.js config as follows:

```javascript
const nextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "replicate.delivery",
      },
      {
        protocol: "https",
        hostname: "*.replicate.delivery",
      }
    ]
  }
}
```

Remember to update your code to work with `FileOutput` objects if you’re using version 1.0.0 or later of our client libraries.


Some models generate files as output, like images, audio, or video. With the release of version 1.0.0 of our client libraries, the way you handle these output files has changed.

[](#fileoutput-objects)FileOutput Objects
-----------------------------------------

When a model generates files, `replicate.run()` now returns `FileOutput` objects instead of URLs. These objects provide direct access to the file data, simplifying your code and speeding up your applications.

Here’s how you can work with `FileOutput` objects:

### [](#python)Python

```python
import replicate
output = replicate.run(
    "black-forest-labs/flux-schnell",
    input={"prompt": "A majestic lion"}
)
# If the model returns a single output
with open('output.png', 'wb') as f:
    f.write(output[0].read())
# If the model returns multiple outputs
for idx, file_output in enumerate(output):
    with open(f'output_{idx}.png', 'wb') as f:
        f.write(file_output.read())
# You can also stream the file by using its iterator methods:
for chunk in output:
  print(chunk)
```

### [](#javascript)JavaScript

```javascript
import Replicate from "replicate";
const replicate = new Replicate();
const output = await replicate.run(
    "black-forest-labs/flux-schnell",
    { input: { prompt: "A majestic lion" }}
);
// If the model returns a single output
fs.writeFileSync("output.png", output);
// If the model returns multiple outputs
output.forEach((fileOutput, idx) => {
    fs.writeFileSync(`output_${idx}.png`, fileOutput);
});
```

[](#fileoutput-properties-and-methods)FileOutput Properties and Methods
-----------------------------------------------------------------------

The `FileOutput` type mimics a file-like object available on the platform.

Each Python `FileOutput` object implements `Iterator[bytes]` and `AsyncIterator[bytes]` and provides:

*   `read()`: Returns the binary content of the file
*   `url`: The URL of the underlying data source

Each JavaScript `FileOutput` object is a [`ReadableStream`](https://developer.mozilla.org/en-US/docs/Web/API/Streams_API/Using_readable_streams) that also provides:

*   `blob()`: Reads the binary content of the file
*   `pipe()`: Stream the file data to a `WriteableStream` instance.
*   `url()`: The URL of the underlying data source

### [](#streaming-responses)Streaming Responses

In Python, `FileOutput` implements `Iterator[bytes]` and `AsyncIterator[bytes]` which means you can pass it to any function that takes one as input:

```python
with open("output.png", "wb") as f:
    for chunk in output:
        f.write(chunk)
# Using asyncio
import aiofiles
async with aiofiles.open('output.png', mode='wb') as f:
    async for chunk in output:
        await f.write(chunk)
```

In JavaScript, `FileOutput` implements `ReadableStream` which means you can pass it to any function that takes one as input (such as `Response` and `fs.writeFile`) to stream large files efficiently:

```javascript
const fileStream = fs.createWriteStream("output.png");
output[0].pipe(fileStream);
```

### [](#working-with-urls)Working with URLs

Sometimes you might want to use the file’s URL directly - for example, when displaying images in a web application or passing the URL to another service. Each `FileOutput` object has a `url` property:

```python
# Get the URL of the first output
url = output[0].url
print(f"File available at: {url}")
``````javascript
// Get the URL of the first output
const url = output[0].url;
// Example: Using the URL in an HTML image
const img = document.createElement('img');
img.src = url;  // Works with both HTTP URLs and data URIs
document.body.appendChild(img);
```

Remember: URLs for files will point to `replicate.delivery` and will expire after one hour.

[](#migrating-from-earlier-versions)Migrating from Earlier Versions
-------------------------------------------------------------------

If you’re updating from a version before 1.0.0:

1.  Replace any code that fetches URLs with direct use of the `FileOutput` object
2.  Use `read()` or `pipe()` to access file data instead of downloading from URLs
3.  Remove any URL handling or Authorization header logic
4.  If you need URLs (e.g., for displaying images), use the `url` property of the `FileOutput` object

[](#opting-out-of-the-blocking-api)Opting Out of the Blocking API
-----------------------------------------------------------------

If you prefer not to use the blocking API, you can opt for the polling mode. This allows you to handle predictions asynchronously and can be useful if you want to avoid holding a connection open. To use polling mode, pass the relevant argument to the `run()` method in your favorite language:

### [](#python-1)Python

```python
output = replicate.run(
    "black-forest-labs/flux-schnell",
    input={"prompt": "A majestic lion"},
    wait=False
)
```

### [](#javascript-1)JavaScript

```javascript
const output = await replicate.run(
    "black-forest-labs/flux-schnell",
    { input: { prompt: "A majestic lion" }, wait: { type: "poll" } }
);
```

You can also opt out of `FileOutput` objects entirely by configuring the client when you create it:

```javascript
const replicate = new Replicate({ useFileOutput: false });
```

This will make the client return URLs instead of `FileOutput` objects, which can be useful if you’re migrating from an older version or prefer to handle the files yourself.

[](#data-retention)Data Retention
---------------------------------

For predictions created through the API, output files are automatically deleted after an hour. You must save a copy of any files in the output if you’d like to continue using them. For more details on how to store prediction data, see the [webhooks docs](/docs/topics/webhooks).

For predictions created through the web interface, output files are kept indefinitely, unless you delete them manually.

[](#output-file-domains)Output File Domains
-------------------------------------------

Output files are served by `replicate.delivery` and its subdomains.

If you use an allow list of external domains for your assets, add `replicate.delivery` and `*.replicate.delivery` to it.

For example, if you’re building a [Next.js app that displays output files from Replicate](/docs/get-started/nextjs), update your Next.js config as follows:

```javascript
const nextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "replicate.delivery",
      },
      {
        protocol: "https",
        hostname: "*.replicate.delivery",
      }
    ]
  }
}
```

Remember to update your code to work with `FileOutput` objects if you’re using version 1.0.0 or later of our client libraries.

Learn how to run a model on Replicate from within your Python code. It could be an app, a notebook, an evaluation script, or anywhere else you want to use machine learning.

Tip

Check out an interactive notebook version of this tutorial on [Google Colab](https://colab.research.google.com/drive/1K91q4p-OhL96FHBAVLsv9FlwFdu6Pn3c).

[](#install-the-python-library)Install the Python library
---------------------------------------------------------

We maintain an [open-source Python client](https://github.com/replicate/replicate-python#readme) for the API. Install it with pip:

```plaintext
pip install replicate
```

[](#authenticate)Authenticate
-----------------------------

Generate an API token at [replicate.com/account/api-tokens](https://replicate.com/account/api-tokens), copy the token, then set it as an environment variable in your shell:

```shell
export REPLICATE_API_TOKEN=r8_....
```

[](#run-a-model)Run a model
---------------------------

You can run [any public model](https://replicate.com/explore) on Replicate from your Python code. Here’s an example that runs [black-forest-labs/flux-schnell](https://replicate.com/black-forest-labs/flux-schnell) to generate an image:

```python
import replicate
output = replicate.run(
  "black-forest-labs/flux-schnell",
  input={"prompt": "an iguana on the beach, pointillism"}
)
# Save the generated image
with open('output.png', 'wb') as f:
    f.write(output[0].read())
print(f"Image saved as output.png")
```

[](#using-local-files-as-inputs)Using local files as inputs
-----------------------------------------------------------

Some models take files as inputs. You can use a local file on your machine as input, or you can provide an HTTPS URL to a file on the public internet.

Here’s an example that uses a local file as input to the [LLaVA vision model](https://replicate.com/yorickvp/llava-13b), which takes an image and a text prompt as input and responds with text:

```python
import replicate
image = open("my_fridge.jpg", "rb")
output = replicate.run(
    "yorickvp/llava-13b:a0fdc44e4f2e1f20f2bb4e27846899953ac8e66c5886c5878fa1d6b73ce009e5",
    input={
        "image": image,
        "prompt": "Here's what's in my fridge. What can I make for dinner tonight?"
    }
)
print(output)
# You have a well-stocked refrigerator filled with various fruits, vegetables, and ...
```

[](#using-urls-as-inputs)Using URLs as inputs
---------------------------------------------

URLs are more efficient if your file is already in the cloud somewhere, or it is a large file.

Here’s an example that uses an HTTPS URL of an image on the internet as input to a model:

```python
image = "https://example.com/my_fridge.jpg"
output = replicate.run(
    "yorickvp/llava-13b:a0fdc44e4f2e1f20f2bb4e27846899953ac8e66c5886c5878fa1d6b73ce009e5",
    input={
        "image": image,
        "prompt": "Here's what's in my fridge. What can I make for dinner tonight?"
    }
)
print(output)
# You have a well-stocked refrigerator filled with various fruits, vegetables, and ...
```

[](#handling-output)Handling output
-----------------------------------

Some models stream output as the model is running. They will return an iterator, and you can iterate over that output.

Here’s an example that uses the [Claude 3.7 Sonnet model](https://replicate.com/anthropic/claude-3.7-sonnet) to generate text:

```python
iterator = replicate.run(
  "anthropic/claude-3.7-sonnet",
  input={"prompt": "Who was Dolly the sheep?"},
)
for text in iterator:
    print(text, end="")
# Dolly the sheep was the first mammal to be successfully cloned from an adult cell...
```

[](#handling-file-outputs)Handling file outputs
-----------------------------------------------

Some models generate files as output, such as images or audio. These are returned as `FileOutput` objects, which you can easily save or process:

```python
output = replicate.run(
    "black-forest-labs/flux-schnell",
    input={"prompt": "A majestic lion"}
)
# Save the generated image
with open('lion.png', 'wb') as f:
    f.write(output[0].read())
print("Image saved as lion.png")
# Handle multiple outputs
output = replicate.run(
    "black-forest-labs/flux-schnell",
    input={"prompt": "A majestic lion", "num_outputs": 2}
)
for idx, file_output in enumerate(output):
    with open(f'output_{idx}.png', 'wb') as f:
        f.write(file_output.read())

```

For more details on handling output files, see [Output Files](/docs/topics/predictions/output-files).

[](#next-steps)Next steps
-------------------------

Read the [full Python client documentation on GitHub.](https://github.com/replicate/replicate-python#readme)

This guide will walk you through the best practices for pushing a reliable, fast, and user-friendly model to Replicate.

[](#getting-started)Getting started
-----------------------------------

All models on Replicate use [Cog](https://github.com/replicate/cog), an open-source tool that lets you package machine learning models in a standard, production-ready container. It’s based on Docker.

If you’re new to Cog, we recommend starting from our docs: [Push a model to Replicate](https://replicate.com/docs/guides/push-a-model)

In short, you need to:

1.  define the Docker environment your model runs in with `cog.yaml`
2.  define how predictions are run with `predict.py`
3.  test your model by running predictions locally, for example: `cog predict -i image=@input.jpg`
4.  push the model to Replicate with `cog push`

For the rest of this guide we’ll assume you’re familiar with Cog and you know how to push a model to Replicate.

[](#make-your-model-easy-to-understand)Make your model easy to understand
-------------------------------------------------------------------------

People must be able to use your model without reading the source code.

### [](#naming-your-model)Naming your model

All names on Replicate are lowercase and use dashes instead of spaces. For example, `llama-2-70b-chat`.

Best practice is to use the model’s official name, like the name of the Github repo or HuggingFace model.

Where there are variations of a model, we recommend adding those variations to the end of the name to make the model distinct. These are commonly different parameter sizes or fine-tunes, such as `codellama-34b` and `codellama-34b-instruct`.

### [](#include-a-clear-description)Include a clear description

A short one line description explaining what the model does. Avoid technical terms and abbreviations in your description.

Some good examples:

*   For the `autocaption` model: “Automatically add captions to a video”
*   For the `llama-2-70b-chat`: “A 70 billion parameter language model from Meta, fine tuned for chat completions”

### [](#use-well-named-model-inputs)Use well named model inputs

Do not prematurely shorten names. Use `negative_prompt` instead of `n_prompt`.

### [](#order-your-inputs)Order your inputs

Put the most important inputs first.

Group related inputs together. For example, `prompt` and `negative_prompt` should be together in your `predict.py` inputs. Users usually want to change them together.

For models with many inputs, consider prefixing fields with a group name. For example, `controlnet_strength`, `controlnet_image` and `controlnet_model`.

### [](#add-guidance-to-explain-inputs)Add guidance to explain inputs

Even when obvious to you. For example, not everyone knows how to use a negative prompt. Guidance like this would help them:

> A negative prompt is a prompt containing all the things you do not want in your output

### [](#pick-defaults-that-balance-speed-and-quality)Pick defaults that balance speed and quality

Good defaults get quality outputs quickly.

For example, with SDXL you get good images at 768x768 with 25 inference steps, which is 3x faster than 1024x1024 at 50 steps.

### [](#give-guidance-on-recommended-ranges)Give guidance on recommended ranges

A model should make it difficult to get bad results while remaining flexible for anyone wanting to experiment.

Keep wide input ranges, but use guidance text to explain where the best results lie.

### [](#handle-image-inputs-well)Handle image inputs well

If your model takes images as inputs, it should accept all the common image formats users will try. For example, JPEG, PNG, GIF and WEBP, as well as images with alpha channels (transparency).

Where inference would fail with a given input (like an RGBA image), convert images to a format that works.

An image that’s too big will often cause out of memory errors. Scale images to a size that works best with your model, but maintain aspect ratio.

Some models need dimensions that are multiples of 8, or similar (for example Stable Diffusion). In these cases, automatically scale images to the nearest multiple.

Make image scaling easy and automatic, so users can throw any image at your model and get good results. But add controls so they can override defaults and control sizing if they need to.

[](#dependencies)Dependencies
-----------------------------

Keep dependencies to a minimum. Fewer dependencies mean smaller containers and faster builds.

Use pinned versions. Pinning your dependencies to specific versions makes your model more reproducible. It will make it easier to debug.

OpenCV is a big dependency. If you’re using it, we recommend using the headless version [opencv-python-headless](https://pypi.org/project/opencv-python-headless/) which is a smaller version for server use.

[](#model-weights)Model weights
-------------------------------

Download weights and push them with your model. Do not try to download them at runtime. If you’re using HuggingFace Diffusers, you can also push the model cache.

If you have weights that are especially large, contact the Replicate team and we’ll help you keep your model size down and your model fast. We’re working on making this better.

Learn how to package your own trained model using [Cog](https://github.com/replicate/cog) and push it to Replicate.

By the end of this guide your model will have an interactive GUI and its own HTTP API. You’ll also have the option to publicly share your model so anyone can try it.

![Replicate's GUI](https://user-images.githubusercontent.com/14149230/216632189-c700efb3-128d-4882-99ad-ef8843eb5eaf.png)

_By the end of this guide, your model will have its own [interactive GUI](https://replicate.com/stability-ai/stable-diffusion) and [HTTP API](https://replicate.com/stability-ai/stable-diffusion/api)._

[](#prerequisites)Prerequisites
-------------------------------

*   **A trained model in a directory on your computer.** Your model’s saved weights, alongside any code that is needed to run it. If you don’t already have your own trained model, you can use one from [replicate/cog-examples](https://github.com/replicate/cog-examples).
*   **Docker.** You’ll be using the Cog command-line tool to build and push your model. Cog uses Docker to create a container for your model. You’ll need to [install and start Docker](https://docs.docker.com/get-docker/) before you can run Cog. You can confirm Docker is running by typing `docker info` in your terminal.
*   **An account on Replicate.**

[](#create-a-model-page-on-replicate)Create a model page on Replicate
---------------------------------------------------------------------

Next you’ll [create a page for your model](/docs/topics/models/create-a-model) on Replicate, if you haven’t already. Visit [replicate.com/create](https://replicate.com/create) to choose a name for your model, and specify whether it should be public or private.

[](#install-cog)Install Cog
---------------------------

Cog is an open source tool that makes it easy to put a machine learning model in a Docker container. Run the following commands to install it and set the correct permissions:

```bash
sudo curl -o /usr/local/bin/cog -L https://github.com/replicate/cog/releases/latest/download/cog_`uname -s`_`uname -m`
sudo chmod +x /usr/local/bin/cog
```

Refer to GitHub for [more information about Cog and its full documentation.](https://github.com/replicate/cog)

[](#initialize-cog)Initialize Cog
---------------------------------

To configure your project for use with Cog, you’ll need to add two files to the directory containing your model:

*   [`cog.yaml` defines system requirements, Python package dependencies, etc.](https://github.com/replicate/cog/blob/main/docs/yaml.md)
*   [`predict.py` describes the prediction interface for your model](https://github.com/replicate/cog/blob/main/docs/python.md)

Use the `cog init` command to generate these files in your project:

```bash
cd path/to/your/model
cog init
```

[](#define-your-dependencies)Define your dependencies
-----------------------------------------------------

The `cog.yaml` file defines all of the different things that need to be installed for your model to run. You can think of it as a simple way of defining a Docker image.

For example:

```yaml
build:
  python_version: "3.12"
  python_packages:
    - "torch==2.3.1"
```

This will generate a Docker image with Python 3.12 and PyTorch 2.3.1 installed and various other sensible best practices.

### [](#using-gpus)Using GPUs

To use GPUs, add the `gpu: true` option to the `build` section of your `cog.yaml`:

```yaml
build:
  gpu: true
  # ...
```

Cog will use the [nvidia-docker](https://github.com/NVIDIA/nvidia-docker) base image and automatically figure out what versions of CUDA and cuDNN to use based on the version of Python, PyTorch, and Tensorflow that you’re using.

### [](#running-commands)Running commands

To run a command inside this environment, prefix it with `cog run`:

```bash
$ cog run python
Building Docker image from cog.yaml...
[...]
Running 'python' in Docker with the current directory mounted as a volume...
Python 3.12.6 (main, Sep  9 2024, 18:06:16) [GCC 12.2.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>>
```

This is handy for ensuring a consistent environment for development or training.

With `cog.yaml`, you can also install system packages and other things. [Take a look at the full reference to explore what else you can do.](https://github.com/replicate/cog/blob/main/docs/yaml.md)

[](#define-how-to-run-predictions)Define how to run predictions
---------------------------------------------------------------

The next step is to update `predict.py` to define the interface for running [predictions](/docs/topics/predictions) on your model. The `predict.py` generated by `cog init` looks something like this:

```python
from cog import BasePredictor, Path, Input
import torch
class Predictor(BasePredictor):
    def setup(self):
        """Load the model into memory to make running multiple predictions efficient"""
        self.net = torch.load("weights.pth")
    def predict(self,
            image: Path = Input(description="Image to enlarge"),
            scale: float = Input(description="Factor to scale image by", default=1.5)
    ) -> Path:
        """Run a single prediction on the model"""
        # ... pre-processing ...
        output = self.net(input)
        # ... post-processing ...
        return output
```

Edit your `predict.py` file and fill in the functions with your own model’s setup and prediction code. You might need to import parts of your model from another file.

You should keep your model weights in the same directory as your `predict.py` file, or a subdirectory underneath it, and load them directly off disk in your `setup()` function, as shown in the example above. This will make it more efficient to load and easier to version because it will get copied into the Docker image that Cog produces.

You also need to define the inputs to your model as arguments to the `predict()` function, as demonstrated above. For each argument, you need to annotate with a type. The supported types are:

*   `str`: a string
*   `int`: an integer
*   `float`: a floating point number
*   `bool`: a boolean
*   `cog.File`: a file-like object representing a file
*   `cog.Path`: a path to a file on disk

You can provide more information about the input with the `Input()` function, as shown above. It takes these basic arguments:

*   `description`: A description of what to pass to this input for users of the model
*   `default`: A default value to set the input to. If this argument isn’t passed, then the input is required. If it’s explicitly set to `None`, the input is optional.
*   `ge`: For `int` or `float` types, the value should be greater than or equal to this number.
*   `le`: For `int` or `float` types, the value should be less than or equal to this number.
*   `choices`: For `str` or `int` types, a list of possible values for this input.

There are some more advanced options you can pass, too. For more details, refer to [the prediction interface documentation](https://github.com/replicate/cog/blob/main/docs/python.md).

Next, add the line `predict: "predict.py:Predictor"` to your `cog.yaml`, so it looks something like this:

```yaml
build:
  python_version: "3.12"
  python_packages:
    - "torch==2.3.1"
predict: "predict.py:Predictor"
```

That’s it!

[](#test-your-model-locally)Test your model locally
---------------------------------------------------

To test that this works, try running a prediction on the model:

```bash
$ cog predict -i image=@input.jpg
 Building Docker image from cog.yaml... Successfully built 664ef88bc1f4
 Model running in Docker image 664ef88bc1f4
Written output to output.png
```

To pass more inputs to the model, you can add more `-i` options:

```bash
$ cog predict -i image=@image.jpg -i scale=2.0
```

In this case it’s just a number, not a file, so you don’t need the `@` prefix.

[](#push-your-model)Push your model
-----------------------------------

Now that you’ve configured your model for use with Cog and you have a corresponding model page on Replicate, it’s time to publish it to Replicate’s registry:

```shell
cog login
cog push r8.im/<your-username>/<your-model-name>
```

Your username and model name must match the values you set on Replicate.

Note

You can also set the [image](https://github.com/replicate/cog/blob/main/docs/yaml.md#image) property in your `cog.yaml` file. This allows you to run `cog push` without specifying the image, and also makes your model page on Replicate more discoverable for folks reading your model’s source code.

[](#run-predictions)Run predictions
-----------------------------------

Once you’ve pushed your model to Replicate it will be visible on the website, and you can use the web-based form to run predictions using your model.

To run predictions in the cloud from your code, you can use the [Python client library](https://github.com/replicate/replicate-python).

Install it from pip:

```bash
pip install replicate
```

Authenticate by setting your token in an environment variable:

```shell
export REPLICATE_API_TOKEN=r8_******
```

Then, you can use the model from your Python code:

```python
import replicate
output = replicate.run(
    "replicate/hello-world:5c7d5dc6dd8bf75c1acaa8565735e7986bc5b66206b55cca93cb72c9bf15ccaa",
    input={"text": "python"}
)
print(output)  # "hello python"
```

To pass a file as an input, use a file handle or URL:

```python
image = open("mystery.jpg", "rb")
# or...
image = "https://example.com/mystery.jpg"
output = replicate.run(
    "replicate/resnet:dd782a3d531b61af491d1026434392e8afb40bfb53b8af35f727e80661489767",
    input={"image": image}
)
# If your model returns a file, save it like this:
with open('output.png', 'wb') as f:
    f.write(output[0].read())
```

URLs are more efficient if your file is already in the cloud somewhere, or it’s a large file.

For more details about handling file outputs, see the [Output files documentation](/docs/topics/predictions/output-files).

You can also run your model with the raw HTTP API. [Refer to the HTTP API reference](https://replicate.com/docs/reference/http) for more details.

Learn how to package your own trained model using [Cog](https://github.com/replicate/cog) and push it to Replicate.

By the end of this guide your model will have an interactive GUI and its own HTTP API. You’ll also have the option to publicly share your model so anyone can try it.

![Replicate's GUI](https://user-images.githubusercontent.com/14149230/216632189-c700efb3-128d-4882-99ad-ef8843eb5eaf.png)

_By the end of this guide, your model will have its own [interactive GUI](https://replicate.com/stability-ai/stable-diffusion) and [HTTP API](https://replicate.com/stability-ai/stable-diffusion/api)._

[](#prerequisites)Prerequisites
-------------------------------

*   **A trained model in a directory on your computer.** Your model’s saved weights, alongside any code that is needed to run it. If you don’t already have your own trained model, you can use one from [replicate/cog-examples](https://github.com/replicate/cog-examples).
*   **Docker.** You’ll be using the Cog command-line tool to build and push your model. Cog uses Docker to create a container for your model. You’ll need to [install and start Docker](https://docs.docker.com/get-docker/) before you can run Cog. You can confirm Docker is running by typing `docker info` in your terminal.
*   **An account on Replicate.**

[](#create-a-model-page-on-replicate)Create a model page on Replicate
---------------------------------------------------------------------

Next you’ll [create a page for your model](/docs/topics/models/create-a-model) on Replicate, if you haven’t already. Visit [replicate.com/create](https://replicate.com/create) to choose a name for your model, and specify whether it should be public or private.

[](#install-cog)Install Cog
---------------------------

Cog is an open source tool that makes it easy to put a machine learning model in a Docker container. Run the following commands to install it and set the correct permissions:

```bash
sudo curl -o /usr/local/bin/cog -L https://github.com/replicate/cog/releases/latest/download/cog_`uname -s`_`uname -m`
sudo chmod +x /usr/local/bin/cog
```

Refer to GitHub for [more information about Cog and its full documentation.](https://github.com/replicate/cog)

[](#initialize-cog)Initialize Cog
---------------------------------

To configure your project for use with Cog, you’ll need to add two files to the directory containing your model:

*   [`cog.yaml` defines system requirements, Python package dependencies, etc.](https://github.com/replicate/cog/blob/main/docs/yaml.md)
*   [`predict.py` describes the prediction interface for your model](https://github.com/replicate/cog/blob/main/docs/python.md)

Use the `cog init` command to generate these files in your project:

```bash
cd path/to/your/model
cog init
```

[](#define-your-dependencies)Define your dependencies
-----------------------------------------------------

The `cog.yaml` file defines all of the different things that need to be installed for your model to run. You can think of it as a simple way of defining a Docker image.

For example:

```yaml
build:
  python_version: "3.12"
  python_packages:
    - "torch==2.3.1"
```

This will generate a Docker image with Python 3.12 and PyTorch 2.3.1 installed and various other sensible best practices.

### [](#using-gpus)Using GPUs

To use GPUs, add the `gpu: true` option to the `build` section of your `cog.yaml`:

```yaml
build:
  gpu: true
  # ...
```

Cog will use the [nvidia-docker](https://github.com/NVIDIA/nvidia-docker) base image and automatically figure out what versions of CUDA and cuDNN to use based on the version of Python, PyTorch, and Tensorflow that you’re using.

### [](#running-commands)Running commands

To run a command inside this environment, prefix it with `cog run`:

```bash
$ cog run python
Building Docker image from cog.yaml...
[...]
Running 'python' in Docker with the current directory mounted as a volume...
Python 3.12.6 (main, Sep  9 2024, 18:06:16) [GCC 12.2.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>>
```

This is handy for ensuring a consistent environment for development or training.

With `cog.yaml`, you can also install system packages and other things. [Take a look at the full reference to explore what else you can do.](https://github.com/replicate/cog/blob/main/docs/yaml.md)

[](#define-how-to-run-predictions)Define how to run predictions
---------------------------------------------------------------

The next step is to update `predict.py` to define the interface for running [predictions](/docs/topics/predictions) on your model. The `predict.py` generated by `cog init` looks something like this:

```python
from cog import BasePredictor, Path, Input
import torch
class Predictor(BasePredictor):
    def setup(self):
        """Load the model into memory to make running multiple predictions efficient"""
        self.net = torch.load("weights.pth")
    def predict(self,
            image: Path = Input(description="Image to enlarge"),
            scale: float = Input(description="Factor to scale image by", default=1.5)
    ) -> Path:
        """Run a single prediction on the model"""
        # ... pre-processing ...
        output = self.net(input)
        # ... post-processing ...
        return output
```

Edit your `predict.py` file and fill in the functions with your own model’s setup and prediction code. You might need to import parts of your model from another file.

You should keep your model weights in the same directory as your `predict.py` file, or a subdirectory underneath it, and load them directly off disk in your `setup()` function, as shown in the example above. This will make it more efficient to load and easier to version because it will get copied into the Docker image that Cog produces.

You also need to define the inputs to your model as arguments to the `predict()` function, as demonstrated above. For each argument, you need to annotate with a type. The supported types are:

*   `str`: a string
*   `int`: an integer
*   `float`: a floating point number
*   `bool`: a boolean
*   `cog.File`: a file-like object representing a file
*   `cog.Path`: a path to a file on disk

You can provide more information about the input with the `Input()` function, as shown above. It takes these basic arguments:

*   `description`: A description of what to pass to this input for users of the model
*   `default`: A default value to set the input to. If this argument isn’t passed, then the input is required. If it’s explicitly set to `None`, the input is optional.
*   `ge`: For `int` or `float` types, the value should be greater than or equal to this number.
*   `le`: For `int` or `float` types, the value should be less than or equal to this number.
*   `choices`: For `str` or `int` types, a list of possible values for this input.

There are some more advanced options you can pass, too. For more details, refer to [the prediction interface documentation](https://github.com/replicate/cog/blob/main/docs/python.md).

Next, add the line `predict: "predict.py:Predictor"` to your `cog.yaml`, so it looks something like this:

```yaml
build:
  python_version: "3.12"
  python_packages:
    - "torch==2.3.1"
predict: "predict.py:Predictor"
```

That’s it!

[](#test-your-model-locally)Test your model locally
---------------------------------------------------

To test that this works, try running a prediction on the model:

```bash
$ cog predict -i image=@input.jpg
 Building Docker image from cog.yaml... Successfully built 664ef88bc1f4
 Model running in Docker image 664ef88bc1f4
Written output to output.png
```

To pass more inputs to the model, you can add more `-i` options:

```bash
$ cog predict -i image=@image.jpg -i scale=2.0
```

In this case it’s just a number, not a file, so you don’t need the `@` prefix.

[](#push-your-model)Push your model
-----------------------------------

Now that you’ve configured your model for use with Cog and you have a corresponding model page on Replicate, it’s time to publish it to Replicate’s registry:

```shell
cog login
cog push r8.im/<your-username>/<your-model-name>
```

Your username and model name must match the values you set on Replicate.

Note

You can also set the [image](https://github.com/replicate/cog/blob/main/docs/yaml.md#image) property in your `cog.yaml` file. This allows you to run `cog push` without specifying the image, and also makes your model page on Replicate more discoverable for folks reading your model’s source code.

[](#run-predictions)Run predictions
-----------------------------------

Once you’ve pushed your model to Replicate it will be visible on the website, and you can use the web-based form to run predictions using your model.

To run predictions in the cloud from your code, you can use the [Python client library](https://github.com/replicate/replicate-python).

Install it from pip:

```bash
pip install replicate
```

Authenticate by setting your token in an environment variable:

```shell
export REPLICATE_API_TOKEN=r8_******
```

Then, you can use the model from your Python code:

```python
import replicate
output = replicate.run(
    "replicate/hello-world:5c7d5dc6dd8bf75c1acaa8565735e7986bc5b66206b55cca93cb72c9bf15ccaa",
    input={"text": "python"}
)
print(output)  # "hello python"
```

To pass a file as an input, use a file handle or URL:

```python
image = open("mystery.jpg", "rb")
# or...
image = "https://example.com/mystery.jpg"
output = replicate.run(
    "replicate/resnet:dd782a3d531b61af491d1026434392e8afb40bfb53b8af35f727e80661489767",
    input={"image": image}
)
# If your model returns a file, save it like this:
with open('output.png', 'wb') as f:
    f.write(output[0].read())
```

URLs are more efficient if your file is already in the cloud somewhere, or it’s a large file.

For more details about handling file outputs, see the [Output files documentation](/docs/topics/predictions/output-files).

You can also run your model with the raw HTTP API. [Refer to the HTTP API reference](https://replicate.com/docs/reference/http) for more details.

[](#what-is-mcp)What is MCP?
----------------------------

The Model Context Protocol (MCP) is an open standard developed by Anthropic that defines how applications share context with large language models (LLMs).

MCP extends the capabilities of apps like [Claude Desktop](https://claude.ai/download), [Cursor](https://www.cursor.com/), or [GitHub Copilot](https://docs.github.com/en/copilot/customizing-copilot/extending-copilot-chat-with-mcp) by feeding them [OpenAPI schemas](/docs/reference/openapi) that describe tools or services, like Replicate’s HTTP API.

MCP lets you give natural language instructions to a language model, and it can discover and run APIs automatically on your behalf.

Here are some examples of the kinds of prompts you can use:

> Search Replicate for upscaler models and compare them

> Show me the latest Replicate models created by @fofr

> Generate an image using black-forest-labs/flux-schnell

> Upscale that image using the best upscaler model

[](#replicates-mcp-server)Replicate’s MCP server
------------------------------------------------

Replicate’s MCP server is published as an [npm package](https://www.npmjs.com/package/replicate-mcp) that is automatically updated whenever we add new features to Replicate’s HTTP API:

[npm.im/replicate-mcp](https://www.npmjs.com/package/replicate-mcp)

The server supports all of the operations in Replicate’s HTTP API. Once you’ve got it wired up you can use natural language chat to do things like:

*   Search for models (using [`models.search`](/docs/reference/http#models.search) under the hood)
*   Compare models (using [`models.list`](/docs/reference/http#models.list) under the hood)
*   Fetch model metadata (using [`models.get`](/docs/reference/http#models.get) under the hood)
*   Run models (using [`predictions.create`](/docs/reference/http#predictions.create) under the hood)
*   Fetch predictions (using [`predictions.get`](/docs/reference/http#predictions.get) under the hood)
*   [etc…](/docs/reference/http)

[](#running-the-mcp-server)Running the MCP server
-------------------------------------------------

The `replicate-mcp` npm package is a self-contained HTTP server that you can run using the Node.js `npx` command, which downloads and executes npm packages by name without you having to install them first.

Use this command to start the MCP server:

```plaintext
npx -y replicate-mcp
```

☝️ This command will fire up a local HTTP server, but in practice you won’t usually run it this way. Instead, you’ll add some JSON configuration to your Claude, Cursor, or VS Code settings that will quietly and automatically run these local MCP servers on your machine.

Stop your server by pressing `Ctrl+c` in the terminal:

```plaintext
^c
```

Then read on to learn how to configure your apps to run the MCP server automatically.

[](#using-replicate-mcp-with-claude-desktop)Using Replicate MCP with Claude Desktop
-----------------------------------------------------------------------------------

[Claude Desktop](https://claude.ai/download) supports local MCP servers out of the box. Note that this only works with the Claude desktop app, not the web app.

Here’s how to set it up:

1.  Create a [Replicate API token](https://replicate.com/account/api-tokens?new-token-name=replicate-mcp-claude) and copy it.
    
2.  Open Claude Desktop.
    
3.  Click the Claude menu and select **Settings…** (not the in-app account settings).
    
4.  In the Settings window, click **Developer** in the sidebar, then click **Edit Config**. This will open (or create) a `claude_desktop_config.json` file.
    
5.  Add the following JSON to the file, substituting your Replicate API token for `your-token-here`:
    
    ```json
    {
      "mcpServers": {
        "replicate": {
          "command": "npx",
          "args": ["-y", "replicate-mcp"],
          "env": {
            "REPLICATE_API_TOKEN": "your-token-here"
          }
        }
      }
    }
    ```
6.  Restart Claude Desktop. Click the **Search and Tools** icon in the input box. You should see `replicate` listed as a tool:
    

![Claude Tools](/_content/assets/mcp-claude-tools.CutSK3Lq_ZRke3J.webp)

Now that you’ve got the MCP server running, you can use it to search for models, run predictions, and fetch model metadata.

Try these prompts in Claude Desktop:

> Search Replicate for upscaler models and compare them

> Show me the latest Replicate models created by @fofr

> Generate an image using black-forest-labs/flux-schnell

> Upscale that image using the best upscaler model

![Claude Chat](/_content/assets/mcp-claude-chat.CfCmb2p4_Z1gnLo0.webp)

[](#using-replicate-mcp-with-cursor)Using Replicate MCP with Cursor
-------------------------------------------------------------------

[Cursor](https://www.cursor.com/) supports the Model Context Protocol (MCP), allowing you to connect external tools and data sources—like Replicate’s HTTP API—directly to your code editor. With Replicate’s MCP server, you can search for models, run predictions, and fetch model metadata from within Cursor using natural language.

Here’s how to set it up:

1.  Create a [Replicate API token](https://replicate.com/account/api-tokens?new-token-name=replicate-mcp-cursor) and copy it.
    
2.  In your project, create a `.cursor/mcp.json` file with the following content:
    
    ```json
    {
      "mcpServers": {
        "replicate": {
          "command": "npx",
          "args": ["-y", "replicate-mcp"],
          "env": {
            "REPLICATE_API_TOKEN": "your-token-here"
          }
        }
      }
    }
    ```
    
    Replace `your-token-here` with your Replicate API token.
    
3.  Open Cursor. The MCP server will be started automatically when you use a tool that requires it, or you can start it manually from the MCP settings page.
    
4.  In Cursor, open the **MCP settings** (search for “MCP” in the command palette or find it in the settings sidebar). You should see `replicate` listed as an available tool.
    

![Cursor MCP](/_content/assets/mcp-cursor.B2H2azRC_1L58Lp.webp)

Now you can use Replicate tools in Cursor’s Composer Agent:

> Search Replicate for upscaler models and compare them

> Generate an image using black-forest-labs/flux-schnell

> Upscale that image using the best upscaler model

You can also configure MCP servers globally by creating a `~/.cursor/mcp.json` file, making Replicate’s tools available in all your Cursor workspaces.

For more details, see the [Cursor MCP documentation](https://docs.cursor.com/context/model-context-protocol).

[](#using-replicate-mcp-with-github-copilot-in-vs-code)Using Replicate MCP with GitHub Copilot in VS Code
---------------------------------------------------------------------------------------------------------

You can use Replicate’s MCP server with GitHub Copilot Chat in Visual Studio Code to access Replicate’s API tools directly from chat. To set it up:

1.  Install [Visual Studio Code](https://code.visualstudio.com/) version 1.99 or later and make sure you have access to Copilot Chat.
    
2.  Create a [Replicate API token](https://replicate.com/account/api-tokens?new-token-name=replicate-mcp-copilot) and copy it.
    
3.  In your project, create a `.vscode/mcp.json` file with the following content:
    
    ```json
    {
      "servers": {
        "replicate": {
          "command": "npx",
          "args": ["-y", "replicate-mcp"],
          "env": {
            "REPLICATE_API_TOKEN": "your-token-here"
          }
        }
      }
    }
    ```
    
    Replace `your-token-here` with your Replicate API token.
    
4.  Open the `.vscode/mcp.json` file in VS Code and click the **Start** button that appears to launch the MCP server.
    
5.  Open Copilot Chat, select **Agent** from the chat menu, and use Replicate tools in natural language (e.g., “Search Replicate for upscaler models”).
    

You can also configure the MCP server to run globally in VS Code by adding the configuration to your user `settings.json`. For instructions, see the [GitHub Copilot documentation on using existing MCP configurations](https://docs.github.com/en/copilot/customizing-copilot/extending-copilot-chat-with-mcp#using-existing-mcp-configurations).

For more details and advanced configuration, see the [official GitHub Copilot documentation](https://docs.github.com/en/copilot/customizing-copilot/extending-copilot-chat-with-mcp).