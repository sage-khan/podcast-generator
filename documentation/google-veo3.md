## Basic model info

Model name: google/veo-3
Model description: Sound on: Google’s flagship Veo 3 text to video model, with audio


## Model inputs

- prompt (required): Text prompt for video generation (string)
- enhance_prompt (optional): Use Gemini to enhance your prompts (boolean)
- negative_prompt (optional): Description of what to discourage in the generated video (string)
- seed (optional): Random seed. Omit for random generations (integer)


## Model output schema

{
  "type": "string",
  "title": "Output",
  "format": "uri"
}

If the input or output schema includes a format of URI, it is referring to a file.


## Example inputs and outputs

Use these example outputs to better understand the types of inputs the model accepts, and the types of outputs the model returns:

### Example (https://replicate.com/p/fmba0q1379rmc0cpyeas42r6kr)

#### Input

```json
{
  "prompt": "gorilla riding a moped through busy italian city",
  "aspect_ratio": "16:9"
}
```

#### Output

```json
"https://replicate.delivery/xezq/xfz0U06bqSw1AyiJsw7LjOjVXOBpmjJfe7K9XtRLifW26q7SB/tmpi29yh_f0.mp4"
```


## Model readme

> ##Veo 3 - Google
> 
> Veo3 is Google DeepMind’s latest advancement in text-to-video generation, pushing the boundaries of what AI can create from natural language prompts. With native audio generation, improved prompt adherence, and stunning realism, Veo3 is redefining multimedia content creation.
> 
> 
> 🔥 **Key Features**
> 
> Text to Image and Video: Generate high-fidelity visuals with cinematic detail directly from your text prompts.
> 
> Native Audio Generation: Add ambient noise, sound effects, and dialogue that sync naturally with visuals—no post-production needed.
> 
> Dialogue & Lip-Sync: Generate characters speaking your script with accurate lip-sync, opening doors to AI filmmaking and animated storytelling.
> 
> Game World Creation: Build immersive video game environments from just a sentence—Veo3’s spatial and physics understanding is a game-changer.
> 
> High Prompt Accuracy: Grounded in real-world physics and enhanced by deep prompt comprehension, Veo3 delivers consistent and context-aware outputs.
> 
> Cinematic Quality: Output videos in stunning quality, complete with smooth motion and realistic effects
> 
> 
> **Built by Google DeepMind**
> 
> Trained by world-class researchers at Google DeepMind, Veo3 is engineered for creators, developers, and visionaries looking to push the limits of AI-generated content.
> 
> ✨ Prompting Tips (from Google's Guide)
> To get the best results, try these prompt strategies:
> 
> Shot Composition: "Close-up," "two shot," "over-the-shoulder"
> 
> Lens & Focus: "Macro lens," "shallow focus," "wide-angle lens"
> 
> Genre & Style: "Sci-fi," "romantic comedy," "action movie"
> 
> Camera Motion: "Zoom shot," "dolly shot," "tracking shot," "pan shot"
> 
> **Example Prompt:**
> 
> Close up shot (composition) of melting icicles (subject) on a frozen rock wall (context) with cool blue tones (ambiance), zoomed in (camera motion) maintaining close-up detail of water drips (action).




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

## Run the model
Use the replicate.run() method to run the model:
```python
input = {
    "prompt": "A breaking news ident, followed by a TV news presenter excitedly telling us: We interrupt this programme to bring you some breaking news... Veo 3 is now live on Replicate. Then she shouts: Let's go!\n\nThe TV presenter is an epic and cool punk with pink and green hair and a t-shirt that says \"Veo 3 on Replicate\""
}

output = replicate.run(
    "google/veo-3",
    input=input
)
with open("output.mp4", "wb") as file:
    file.write(output.read())
#=> output.mp4 written to disk
```

You can learn about pricing for this model on the model page.

The run() function returns the output directly, which you can then use or pass as the input to another model. If you want to access the full prediction object (not just the output), use the replicate.predictions.create() method instead. This will return a Prediction object that includes the prediction id, status, logs, etc.

## Prediction lifecycle
Running predictions and trainings can often take significant time to complete, beyond what is reasonable for an HTTP request/response.

When you run a model on Replicate, the prediction is created with a “starting” state, then instantly returned. This will then move to "processing" and eventual one of “successful”, "failed" or "canceled".

Starting
Running
Succeeded
Failed
Canceled
You can explore the prediction lifecycle by using the prediction.reload() method update the prediction to it's latest state.

```python
import time

prediction = replicate.predictions.create(
  model="google/veo-3",
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

```python
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

```python   
input = {
    "prompt": "A breaking news ident, followed by a TV news presenter excitedly telling us: We interrupt this programme to bring you some breaking news... Veo 3 is now live on Replicate. Then she shouts: Let's go!\n\nThe TV presenter is an epic and cool punk with pink and green hair and a t-shirt that says \"Veo 3 on Replicate\""
}

callback_url = "https://my.app/webhooks/replicate"
replicate.predictions.create(
  model="google/veo-3",
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
    "prompt": "A breaking news ident, followed by a TV news presenter excitedly telling us: We interrupt this programme to bring you some breaking news... Veo 3 is now live on Replicate. Then she shouts: Let's go!\n\nThe TV presenter is an epic and cool punk with pink and green hair and a t-shirt that says \"Veo 3 on Replicate\""
}

prediction = replicate.predictions.create(
  model="google/veo-3", # Since we dont have version hash, you will use version="google/veo-3"
  input=input
)
#=> Prediction(id='z3wbih3bs64of7lmykbk7tsdf4', ...)
```

## Cancel a prediction
You may need to cancel a prediction. Perhaps the user has navigated away from the browser or canceled your application. To prevent unnecessary work and reduce runtime costs you can use prediction.cancel() method to call the predictions.cancel endpoint.

```python
input = {
    "prompt": "A breaking news ident, followed by a TV news presenter excitedly telling us: We interrupt this programme to bring you some breaking news... Veo 3 is now live on Replicate. Then she shouts: Let's go!\n\nThe TV presenter is an epic and cool punk with pink and green hair and a t-shirt that says \"Veo 3 on Replicate\""
}

prediction = replicate.predictions.create(
  model="google/veo-3",
  input=input
)

prediction.cancel()

Copy
Async Python methods
asyncio is a module built into Python's standard library for writing concurrent code using the async/await syntax.

Replicate's Python client has support for asyncio. Each of the methods has an async equivalent prefixed with async_<name>.
```python
input = {
    "prompt": "A breaking news ident, followed by a TV news presenter excitedly telling us: We interrupt this programme to bring you some breaking news... Veo 3 is now live on Replicate. Then she shouts: Let's go!\n\nThe TV presenter is an epic and cool punk with pink and green hair and a t-shirt that says \"Veo 3 on Replicate\""
}

prediction = replicate.predictions.create(
  model="google/veo-3", # Since we dont have version hash, you will use version="google/veo-3"
  input=input
)

prediction = await replicate.predictions.async_create(
  model="google/veo-3", # Since we dont have version hash, you will use version="google/veo-3"
  input=input
)
```
### Input schema

| Key | Type | Description | Default |
| --- | --- | --- | --- |
| seed | integer | Random seed. Omit for random generations |  |
| prompt | string | Text prompt for video generation |  |
| enhance_prompt | boolean | Use Gemini to enhance your prompts | true |
| negative_prompt | string | Description of what to discourage in the generated video |  |

### Output schema

| Key | Type | Description |
| --- | --- | --- |
| output | uri |  |