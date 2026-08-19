## Basic model info

Model name: minimax/music-01
Model description: Quickly generate up to 1 minute of music with lyrics and vocals in the style of a reference track


## Model inputs

- lyrics: Lyrics with optional formatting. You can use a newline to separate each line of lyrics. You can use two newlines to add a pause between lines. You can use double hash marks (##) at the beginning and end of the lyrics to add accompaniment. Maximum 350 to 400 characters. (string)
- song_file: Reference song, should contain music and vocals. Must be a .wav or .mp3 file longer than 15 seconds. (string)
- voice_file: Voice reference. Must be a .wav or .mp3 file longer than 15 seconds. If only a voice reference is given, an a cappella vocal hum will be generated. (string)
- instrumental_file: Instrumental reference. Must be a .wav or .mp3 file longer than 15 seconds. If only an instrumental reference is given, a track without vocals will be generated. (string)
- voice_id: Reuse a previously uploaded voice ID (string)
- instrumental_id: Reuse a previously uploaded instrumental ID (string)
- sample_rate: Sample rate for the generated music (integer)
- bitrate: Bitrate for the generated music (integer)


## Model output schema

{
  "type": "string",
  "title": "Output",
  "format": "uri"
}

If the input or output schema includes a format of URI, it is referring to a file.


## Example inputs and outputs

Use these example outputs to better understand the types of inputs the model accepts, and the types of outputs the model returns:

### Example (https://replicate.com/p/80xvdzv50xrgc0cktkzszcb904)

#### Input

```json
{
  "lyrics": "[intro]\n\nUpload my heart to the digital sky\nAlgorithm love, you make me feel so high\nBinary kisses, ones and zeros fly (fly)\nOoooh ooooh\n\n[chorus]\nYour neural network's got me feeling so alive",
  "bitrate": 256000,
  "song_file": "https://replicate.delivery/pbxt/M9zum1Y6qujy02jeigHTJzn0lBTQOemB7OkH5XmmPSC5OUoO/MiniMax-Electronic.wav",
  "sample_rate": 44100
}
```

#### Output

```json
"https://replicate.delivery/czjl/fl2vRaNO7AVGBanu1tKydFV4o2nEQfiBXc7vDJPZc3t7sz7TA/tmp4cjd840o.mp3"
```


## Model readme

> # Music-01
> 
> https://minimaxi.com/en/news/music-01
> 
> An AI music generation model for synthesizing multi-style music with accompaniment and vocals.
> 
> ## Features
> 
> - Simultaneous generation of accompaniment and vocals
> - Style learning from reference music uploads 
> - Lyrics-to-music generation
> - Multiple genre support including classical, pop, rock, electronic, and others
> - Maximum output duration: 60 seconds (3 minutes planned for next release)
> 
> ## Usage
> 
> 1. Upload reference music for style analysis
> 2. Input desired lyrics
> 3. Generate new music piece with learned style characteristics
> 
> ## Applications
> 
> - Film/TV soundtrack creation
> - AI singer compositions 
> - Musical reinterpretations
> - General music production
> 
> ## Technical Details
> 
> The model uses deep learning to analyze and reproduce musical patterns, rhythms, and vocal styles from reference tracks.
> 
> ## Limitations
> 
> - Current maximum output length: 60 seconds (Max lyrics is 400 characters)
> - Reference track required for style learning
> 
> ## Future Development
> 
> - Planned support for 3-minute generation in next major release
> 
> ## Privacy policy
> 
> Data from this model is sent from Replicate to MiniMax.
> 
> Check their Privacy Policy for details:
> 
> https://intl.minimaxi.com/protocol/privacy-policy
> 
> ## Terms of Service
> 
> https://intl.minimaxi.com/protocol/terms-of-service

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
    "lyrics": "[intro]\n\nUpload my heart to the digital sky\nAlgorithm love, you make me feel so high\nBinary kisses, ones and zeros fly (fly)\nOoooh ooooh\n\n[chorus]\nYour neural network's got me feeling so alive",
    "song_file": "https://replicate.delivery/pbxt/M9zum1Y6qujy02jeigHTJzn0lBTQOemB7OkH5XmmPSC5OUoO/MiniMax-Electronic.wav"
}

output = replicate.run(
    "minimax/music-01",
    input=input
)
with open("output.mp3", "wb") as file:
    file.write(output.read())
#=> output.mp3 written to disk

Copy
You can learn about pricing for this model on the model page.

The run() function returns the output directly, which you can then use or pass as the input to another model. If you want to access the full prediction object (not just the output), use the replicate.predictions.create() method instead. This will return a Prediction object that includes the prediction id, status, logs, etc.

File inputs
This model accepts files as input, e.g. song_file. You can provide a file as input using a URL, a local file on your computer, or a base64 encoded object:

Option 1: Hosted file
Use a URL as in the earlier example:

song_file = "https://replicate.delivery/pbxt/M9zum1Y6qujy02jeigHTJzn0lBTQOemB7OkH5XmmPSC5OUoO/MiniMax-Electronic.wav";

Copy
This is useful if you already have a file hosted somewhere on the internet.

Option 2: Local file
You can provide Replicate with a file object and the library will handle the upload for you:

song_file = open("./path/to/my/song_file.wav", "rb");

Copy
Option 3: Data URI
Lastly, you can create a data URI consisting of the base64 encoded data for your file, but this is only recommended if the file is < 1mb:

import base64

with open("./path/to/my/song_file.wav", 'rb') as file:
  data = base64.b64encode(file.read()).decode('utf-8')
  song_file = f"data:application/octet-stream;base64,{data}"

Copy
Then pass the file as part of the input:

input = {
    "lyrics": "[intro]\n\nUpload my heart to the digital sky\nAlgorithm love, you make me feel so high\nBinary kisses, ones and zeros fly (fly)\nOoooh ooooh\n\n[chorus]\nYour neural network's got me feeling so alive",
    "song_file": song_file
}

output = replicate.run(
    "minimax/music-01",
    input=input
)
with open("output.mp3", "wb") as file:
    file.write(output.read())
#=> output.mp3 written to disk

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
```python
input = {
    "lyrics": "[intro]\n\nUpload my heart to the digital sky\nAlgorithm love, you make me feel so high\nBinary kisses, ones and zeros fly (fly)\nOoooh ooooh\n\n[chorus]\nYour neural network's got me feeling so alive",
    "song_file": "https://replicate.delivery/pbxt/M9zum1Y6qujy02jeigHTJzn0lBTQOemB7OkH5XmmPSC5OUoO/MiniMax-Electronic.wav"
}

callback_url = "https://my.app/webhooks/replicate"
replicate.predictions.create(
  model="minimax/music-01", #use version='minimax/music-01' instead of model if you only have model name and donot have the model hash or available.
  input=input,
  webhook=callback_url,
  webhook_events_filter=["completed"]
)
```
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
    "lyrics": "[intro]\n\nUpload my heart to the digital sky\nAlgorithm love, you make me feel so high\nBinary kisses, ones and zeros fly (fly)\nOoooh ooooh\n\n[chorus]\nYour neural network's got me feeling so alive",
    "song_file": "https://replicate.delivery/pbxt/M9zum1Y6qujy02jeigHTJzn0lBTQOemB7OkH5XmmPSC5OUoO/MiniMax-Electronic.wav"
}

prediction = replicate.predictions.create(
  model="minimax/music-01",
  input=input
)
#=> Prediction(id='z3wbih3bs64of7lmykbk7tsdf4', ...)

Copy
Cancel a prediction
You may need to cancel a prediction. Perhaps the user has navigated away from the browser or canceled your application. To prevent unnecessary work and reduce runtime costs you can use prediction.cancel() method to call the predictions.cancel endpoint.

input = {
    "lyrics": "[intro]\n\nUpload my heart to the digital sky\nAlgorithm love, you make me feel so high\nBinary kisses, ones and zeros fly (fly)\nOoooh ooooh\n\n[chorus]\nYour neural network's got me feeling so alive",
    "song_file": "https://replicate.delivery/pbxt/M9zum1Y6qujy02jeigHTJzn0lBTQOemB7OkH5XmmPSC5OUoO/MiniMax-Electronic.wav"
}

prediction = replicate.predictions.create(
  model="minimax/music-01",
  input=input
)

prediction.cancel()

Copy
Async Python methods
asyncio is a module built into Python's standard library for writing concurrent code using the async/await syntax.

Replicate's Python client has support for asyncio. Each of the methods has an async equivalent prefixed with async_<name>.

input = {
    "lyrics": "[intro]\n\nUpload my heart to the digital sky\nAlgorithm love, you make me feel so high\nBinary kisses, ones and zeros fly (fly)\nOoooh ooooh\n\n[chorus]\nYour neural network's got me feeling so alive",
    "song_file": "https://replicate.delivery/pbxt/M9zum1Y6qujy02jeigHTJzn0lBTQOemB7OkH5XmmPSC5OUoO/MiniMax-Electronic.wav"
}

prediction = replicate.predictions.create(
  model="minimax/music-01",
  input=input
)

prediction = await replicate.predictions.async_create(
  model="minimax/music-01",
  input=input


### Input schema

| Input Name | Input Type | Input Description | Default Value |
| --- | --- | --- | --- |
| lyrics | string | Lyrics with optional formatting. You can use a newline to separate each line of lyrics. You can use two newlines to add a pause between lines. You can use double hash marks (##) at the beginning and end of the lyrics to add accompaniment. Maximum 350 to 400 characters. |  |
| bitrate | integer | Bitrate for the generated music | 256000 |
| voice_id | string | Reuse a previously uploaded voice ID |  |
| song_file | uri | Reference song, should contain music and vocals. Must be a .wav or .mp3 file longer than 15 seconds. |  |
| voice_file | uri | Voice reference. Must be a .wav or .mp3 file longer than 15 seconds. If only a voice reference is given, an a cappella vocal hum will be generated. |  |
| sample_rate | integer | Sample rate for the generated music | 44100 |
| instrumental_id | string | Reuse a previously uploaded instrumental ID |  |
| instrumental_file | uri | Instrumental reference. Must be a .wav or .mp3 file longer than 15 seconds. If only an instrumental reference is given, a track without vocals will be generated. |  |

### Output schema
 
| Output Name | Output Type | Output Description |
| --- | --- | --- |
| output | string | URI of the generated music file. |

Music-01
https://minimaxi.com/en/news/music-01

An AI music generation model for synthesizing multi-style music with accompaniment and vocals.

Features
Simultaneous generation of accompaniment and vocals
Style learning from reference music uploads
Lyrics-to-music generation
Multiple genre support including classical, pop, rock, electronic, and others
Maximum output duration: 60 seconds (3 minutes planned for next release)
Usage
Upload reference music for style analysis
Input desired lyrics
Generate new music piece with learned style characteristics
Applications
Film/TV soundtrack creation
AI singer compositions
Musical reinterpretations
General music production
Technical Details
The model uses deep learning to analyze and reproduce musical patterns, rhythms, and vocal styles from reference tracks.

Limitations
Current maximum output length: 60 seconds (Max lyrics is 400 characters)
Reference track required for style learning
Future Development
Planned support for 3-minute generation in next major release
Privacy policy
Data from this model is sent from Replicate to MiniMax.

Check their Privacy Policy for details:

https://intl.minimaxi.com/protocol/privacy-policy

Terms of Service
https://intl.minimaxi.com/protocol/terms-of-service