# FOFR CHARACTER CONSISTENCY

## About
Create images of a given character in different poses

model owner name and version = fofr/consistent-character:9c77a3c2f884193fcee4d89645f02a0b9def9434f9e03cb98460456b831c8772

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

### What is cURL?
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
    "prompt": "A closeup headshot photo of a young woman in a grey sweater",
    "subject": "https://replicate.delivery/pbxt/L0gy7uyLE5UP0uz12cndDdSOIgw5R3rV5N6G2pbt7kEK9dCr/0_3.webp",
    "number_of_outputs": 5
}

output = replicate.run(
    "fofr/consistent-character:9c77a3c2f884193fcee4d89645f02a0b9def9434f9e03cb98460456b831c8772",
    input=input
)
for index, item in enumerate(output):
    with open(f"output_{index}.webp", "wb") as file:
        file.write(item.read())
#=> output_0.webp, output_1.webp, output_2.webp, output_3.web...
```
You can learn about pricing for this model on the model page.

The run() function returns the output directly, which you can then use or pass as the input to another model. If you want to access the full prediction object (not just the output), use the replicate.predictions.create() method instead. This will return a Prediction object that includes the prediction id, status, logs, etc.

## File inputs
This model accepts files as input, e.g. subject. You can provide a file as input using a URL, a local file on your computer, or a base64 encoded object:

### Option 1: Hosted file
Use a URL as in the earlier example:

```subject = "https://replicate.delivery/pbxt/L0gy7uyLE5UP0uz12cndDdSOIgw5R3rV5N6G2pbt7kEK9dCr/0_3.webp";```

This is useful if you already have a file hosted somewhere on the internet.

### Option 2: Local file
You can provide Replicate with a file object and the library will handle the upload for you:

```subject = open("./path/to/my/subject.webp", "rb");```

### Option 3: Data URI
Lastly, you can create a data URI consisting of the base64 encoded data for your file, but this is only recommended if the file is < 1mb:
```
import base64

with open("./path/to/my/subject.webp", 'rb') as file:
  data = base64.b64encode(file.read()).decode('utf-8')
  subject = f"data:application/octet-stream;base64,{data}"
```
Then pass the file as part of the input:
```
input = {
    "prompt": "A closeup headshot photo of a young woman in a grey sweater",
    "subject": subject,
    "number_of_outputs": 5
}

output = replicate.run(
    "fofr/consistent-character:9c77a3c2f884193fcee4d89645f02a0b9def9434f9e03cb98460456b831c8772",
    input=input
)
for index, item in enumerate(output):
    with open(f"output_{index}.webp", "wb") as file:
        file.write(item.read())
#=> output_0.webp, output_1.webp, output_2.webp, output_3.web...
```
## Streaming
This model supports streaming. This allows you to receive output as the model is running:
```
input = {
    "prompt": "A closeup headshot photo of a young woman in a grey sweater",
    "subject": "https://replicate.delivery/pbxt/L0gy7uyLE5UP0uz12cndDdSOIgw5R3rV5N6G2pbt7kEK9dCr/0_3.webp",
    "number_of_outputs": 5
}

for event in replicate.stream(
    "fofr/consistent-character:9c77a3c2f884193fcee4d89645f02a0b9def9434f9e03cb98460456b831c8772",
    input=input
):
    print(event)
    #=> "https://replicate.delivery/xezq/Y1WvbO3AmbIUChf8egw5rTdTUCYTe3qFMZ03PIKNIYmlEArnA/ComfyUI_00001_.webp"

## Streaming in the browser
The Python library is intended to be run on the server. However once the prediction has been created its output can be streamed directly from the browser.

The streaming URL uses a standard format called Server Sent Events (or text/event-stream) built into all web browsers.

A common implementation is to use a web server to create the prediction using replicate.predictions.create , passing the stream property set to true . Then the urls.stream property of the response contains a url that can be returned to your frontend application:

input = {
    "prompt": "A closeup headshot photo of a young woman in a grey sweater",
    "subject": "https://replicate.delivery/pbxt/L0gy7uyLE5UP0uz12cndDdSOIgw5R3rV5N6G2pbt7kEK9dCr/0_3.webp",
    "number_of_outputs": 5
}

# POST /run_prediction
def handler(request):{
    prediction = replicate.predictions.create(
        version="9c77a3c2f884193fcee4d89645f02a0b9def9434f9e03cb98460456b831c8772",
        input=input,
        stream=True,
    )

    return Response.json({
        'url': prediction.urls['stream']
    })
    # Returns {"url": "https://replicate-stream..."}
}
```

Make a request to the server to create the prediction and use the built-in EventSource object to read the returned url.
```
const response = await fetch("/run_prediction", { method: "POST" });
const { url } = await response.json();

const source = new EventSource(url);
source.addEventListener("output", (evt) => {
  console.log(evt.data) //=> "https://replicate.delivery/xezq/Y1WvbO3AmbIUChf8egw5rTdTUCYTe3qFMZ03PIKNIYmlEArnA/ComfyUI_00001_.webp"
});
source.addEventListener("done", (evt) => {
  console.log("stream is complete");
});
```

## Prediction lifecycle
Running predictions and trainings can often take significant time to complete, beyond what is reasonable for an HTTP request/response.

When you run a model on Replicate, the prediction is created with a “starting” state, then instantly returned. This will then move to "processing" and eventual one of “successful”, "failed" or "canceled".

-Starting
-Running
-Succeeded
-Failed
-Canceled

You can explore the prediction lifecycle by using the prediction.reload() method update the prediction to it's latest state.

Show example:

```
import time

prediction = replicate.predictions.create(
  version="9c77a3c2f884193fcee4d89645f02a0b9def9434f9e03cb98460456b831c8772",
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

## Webhooks
Webhooks provide real-time updates about your prediction. Specify an endpoint when you create a prediction, and Replicate will send HTTP POST requests to that URL when the prediction is created, updated, and finished.

It is possible to provide a URL to the predictions.create() function that will be requested by Replicate when the prediction status changes. This is an alternative to polling.

To receive webhooks you’ll need a web server. The following example uses AIOHTTP, a basic webserver built on top of Python’s asyncio library, but this pattern will apply to most frameworks.

Show example
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
    "prompt": "A closeup headshot photo of a young woman in a grey sweater",
    "subject": "https://replicate.delivery/pbxt/L0gy7uyLE5UP0uz12cndDdSOIgw5R3rV5N6G2pbt7kEK9dCr/0_3.webp",
    "number_of_outputs": 5
}

callback_url = "https://my.app/webhooks/replicate"
replicate.predictions.create(
  version="9c77a3c2f884193fcee4d89645f02a0b9def9434f9e03cb98460456b831c8772",
  input=input,
  webhook=callback_url,
  webhook_events_filter=["completed"]
)

# The server will now handle the event and log:
#=> Prediction(id='z3wbih3bs64of7lmykbk7tsdf4', ...)
```

The replicate.run() method is not used here. Because we're using webhooks, and we don’t need to poll for updates.

From a security perspective it is also possible to verify that the webhook came from Replicate, check out our documentation on verifying webhooks for more information.

## Access a prediction
You may wish to access the prediction object. In these cases it’s easier to use the replicate.predictions.create() function, which return the prediction object.

Though note that these functions will only return the created prediction, and it will not wait for that prediction to be completed before returning. Use replicate.predictions.get() to fetch the latest prediction.
```
import replicate

input = {
    "prompt": "A closeup headshot photo of a young woman in a grey sweater",
    "subject": "https://replicate.delivery/pbxt/L0gy7uyLE5UP0uz12cndDdSOIgw5R3rV5N6G2pbt7kEK9dCr/0_3.webp",
    "number_of_outputs": 5
}

prediction = replicate.predictions.create(
  version="9c77a3c2f884193fcee4d89645f02a0b9def9434f9e03cb98460456b831c8772",
  input=input
)
#=> Prediction(id='z3wbih3bs64of7lmykbk7tsdf4', ...)
```

### Cancel a prediction
You may need to cancel a prediction. Perhaps the user has navigated away from the browser or canceled your application. To prevent unnecessary work and reduce runtime costs you can use prediction.cancel() method to call the predictions.cancel endpoint.
```
input = {
    "prompt": "A closeup headshot photo of a young woman in a grey sweater",
    "subject": "https://replicate.delivery/pbxt/L0gy7uyLE5UP0uz12cndDdSOIgw5R3rV5N6G2pbt7kEK9dCr/0_3.webp",
    "number_of_outputs": 5
}

prediction = replicate.predictions.create(
  version="9c77a3c2f884193fcee4d89645f02a0b9def9434f9e03cb98460456b831c8772",
  input=input
)

prediction.cancel()
```

## Async Python methods
asyncio is a module built into Python's standard library for writing concurrent code using the async/await syntax.

Replicate's Python client has support for asyncio. Each of the methods has an async equivalent prefixed with async_<name>.
```
input = {
    "prompt": "A closeup headshot photo of a young woman in a grey sweater",
    "subject": "https://replicate.delivery/pbxt/L0gy7uyLE5UP0uz12cndDdSOIgw5R3rV5N6G2pbt7kEK9dCr/0_3.webp",
    "number_of_outputs": 5
}

prediction = replicate.predictions.create(
  version="9c77a3c2f884193fcee4d89645f02a0b9def9434f9e03cb98460456b831c8772",
  input=input
)

prediction = await replicate.predictions.async_create(
  version="9c77a3c2f884193fcee4d89645f02a0b9def9434f9e03cb98460456b831c8772",
  input=input
)
```