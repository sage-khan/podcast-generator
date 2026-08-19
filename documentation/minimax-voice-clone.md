## Basic model info

Model name: minimax/voice-cloning
Model description: Clone voices to use with Minimax's speech-02-hd and speech-02-turbo


## Model inputs

- voice_file: Voice file to clone. Must be MP3, M4A, or WAV format, 10s to 5min duration, and less than 20MB. (string)
- need_noise_reduction: Enable noise reduction. Use this if the voice file has background noise. (boolean)
- model: The text-to-speech model to train (string)
- accuracy: Text validation accuracy threshold (0-1) (number)
- need_volume_normalization: Enable volume normalization (boolean)


## Model output schema

{
  "type": "object",
  "title": "VoiceCloningOutputs",
  "required": [
    "voice_id",
    "preview",
    "model"
  ],
  "properties": {
    "model": {
      "type": "string",
      "title": "Model"
    },
    "preview": {
      "type": "string",
      "title": "Preview",
      "format": "uri"
    },
    "voice_id": {
      "type": "string",
      "title": "Voice Id"
    }
  }
}

If the input or output schema includes a format of URI, it is referring to a file.


## Example inputs and outputs

Use these example outputs to better understand the types of inputs the model accepts, and the types of outputs the model returns:

### Example (https://replicate.com/p/m4cr30a4csrm80cpmnqr4rqdew)

#### Input

```json
{
  "model": "speech-02-turbo",
  "accuracy": 0.7,
  "voice_file": "https://replicate.delivery/czjl/21U5IFboRwrhBlKks9pmaz119Hvo1ISryE0LNUKuerpqS9UKA/output.wav",
  "need_noise_reduction": false,
  "need_volume_normalization": false
}
```

#### Output

```json
{
  "model": "speech-02-turbo",
  "preview": "https://replicate.delivery/xezq/p80hlWW4YWptBh3YGnNEDmR8ldh9QQDCxZNrICRge2HgT9UKA/tmpuo0ipa91.mp3",
  "voice_id": "R8_FDU1SV5S"
}
```


## Model readme

> ## Text-to-speech voice cloning
> 
> Clone voices to use with Minimax's [speech-02-hd](https://replicate.com/minimax/speech-02-hd) and [speech-02-turbo](https://replicate.com/minimax/speech-02-turbo) models.
> 
> Training is fast, and needs only 5s of audio. The more audio you give, the better the training accuracy.
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
    "voice_file": "https://replicate.delivery/czjl/21U5IFboRwrhBlKks9pmaz119Hvo1ISryE0LNUKuerpqS9UKA/output.wav"
}

output = replicate.run(
    "minimax/voice-cloning",
    input=input
)
print(output)
#=> {"model":"speech-02-turbo","preview":"https://replicate.d...

Copy
You can learn about pricing for this model on the model page.

The run() function returns the output directly, which you can then use or pass as the input to another model. If you want to access the full prediction object (not just the output), use the replicate.predictions.create() method instead. This will return a Prediction object that includes the prediction id, status, logs, etc.

File inputs
This model accepts files as input, e.g. voice_file. You can provide a file as input using a URL, a local file on your computer, or a base64 encoded object:

Option 1: Hosted file
Use a URL as in the earlier example:

voice_file = "https://replicate.delivery/czjl/21U5IFboRwrhBlKks9pmaz119Hvo1ISryE0LNUKuerpqS9UKA/output.wav";

Copy
This is useful if you already have a file hosted somewhere on the internet.

Option 2: Local file
You can provide Replicate with a file object and the library will handle the upload for you:

voice_file = open("./path/to/my/voice_file.wav", "rb");

Copy
Option 3: Data URI
Lastly, you can create a data URI consisting of the base64 encoded data for your file, but this is only recommended if the file is < 1mb:

import base64

with open("./path/to/my/voice_file.wav", 'rb') as file:
  data = base64.b64encode(file.read()).decode('utf-8')
  voice_file = f"data:application/octet-stream;base64,{data}"

Copy
Then pass the file as part of the input:

input = {
    "voice_file": voice_file
}

output = replicate.run(
    "minimax/voice-cloning",
    input=input
)
print(output)
#=> {"model":"speech-02-turbo","preview":"https://replicate.d...

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
    "voice_file": "https://replicate.delivery/czjl/21U5IFboRwrhBlKks9pmaz119Hvo1ISryE0LNUKuerpqS9UKA/output.wav"
}

callback_url = "https://my.app/webhooks/replicate"
replicate.predictions.create(
  model="minimax/voice-cloning",
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
    "voice_file": "https://replicate.delivery/czjl/21U5IFboRwrhBlKks9pmaz119Hvo1ISryE0LNUKuerpqS9UKA/output.wav"
}

prediction = replicate.predictions.create(
  model="minimax/voice-cloning",
  input=input
)
#=> Prediction(id='z3wbih3bs64of7lmykbk7tsdf4', ...)

Copy
Cancel a prediction
You may need to cancel a prediction. Perhaps the user has navigated away from the browser or canceled your application. To prevent unnecessary work and reduce runtime costs you can use prediction.cancel() method to call the predictions.cancel endpoint.

input = {
    "voice_file": "https://replicate.delivery/czjl/21U5IFboRwrhBlKks9pmaz119Hvo1ISryE0LNUKuerpqS9UKA/output.wav"
}

prediction = replicate.predictions.create(
  model="minimax/voice-cloning",
  input=input
)

prediction.cancel()

Copy
Async Python methods
asyncio is a module built into Python's standard library for writing concurrent code using the async/await syntax.

Replicate's Python client has support for asyncio. Each of the methods has an async equivalent prefixed with async_<name>.

input = {
    "voice_file": "https://replicate.delivery/czjl/21U5IFboRwrhBlKks9pmaz119Hvo1ISryE0LNUKuerpqS9UKA/output.wav"
}

prediction = replicate.predictions.create(
  model="minimax/voice-cloning",
  input=input
)

prediction = await replicate.predictions.async_create(
  model="minimax/voice-cloning",
  input=input
)
 
### Input schema
| Input        | Type   | Description                                                                                       | Default | Maximum |
|--------------|--------|---------------------------------------------------------------------------------------------------|---------|---------|
| model        | string | The text-to-speech model to train.                                                                | speech-02-turbo    |         |
| accuracy     | number | Text validation accuracy threshold (0-1)                                                           | 0.7      | 1       |
| voice_file   | uri    | Voice file to clone. Must be MP3, M4A, or WAV format, 10s to 5min duration, and less than 20MB.    |         |         |
| need_noise_reduction | boolean | Enable noise reduction. Use this if the voice file has background noise.                    |         |         |
| need_volume_normalization | boolean | Enable volume normalization.                                                        |         |         |

### Output schema
| Output        | Type   | Description                                                                                       |
|--------------|--------|---------------------------------------------------------------------------------------------------|
| model        | string | The text-to-speech model to train.                                                                |
| preview      | uri    | The URL of an audio file previewing the trained model.                                             |
| voice_id     | string | The voice ID of the trained model. This is the same as the model ID.                               |