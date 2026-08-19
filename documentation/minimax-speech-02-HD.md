## Basic model info

Model name: minimax/speech-02-hd
Model description: Text-to-Audio (T2A) that offers voice synthesis, emotional expression, and multilingual capabilities. Optimized for high-fidelity applications like voiceovers and audiobooks.


## Model inputs

- text: Text to convert to speech. Every character is 1 token. Maximum 5000 characters. Use <#x#> between words to control pause duration (0.01-99.99s). (string)
- voice_id: Desired voice ID. Use a voice ID you have trained (https://replicate.com/minimax/voice-cloning), or one of the following system voice IDs: Wise_Woman, Friendly_Person, Inspirational_girl, Deep_Voice_Man, Calm_Woman, Casual_Guy, Lively_Girl, Patient_Man, Young_Knight, Determined_Man, Lovely_Girl, Decent_Boy, Imposing_Manner, Elegant_Man, Abbess, Sweet_Girl_2, Exuberant_Girl (string)
- speed: Speech speed (number)
- volume: Speech volume (number)
- pitch: Speech pitch (integer)
- emotion: Speech emotion (string)
- english_normalization: Enable English text normalization for better number reading (slightly increases latency) (boolean)
- sample_rate: Sample rate for the generated speech (integer)
- bitrate: Bitrate for the generated speech (integer)
- channel: Number of audio channels (string)
- language_boost: Enhance recognition of specific languages and dialects (string)


## Model output schema

{
  "type": "string",
  "title": "Output",
  "format": "uri"
}

If the input or output schema includes a format of URI, it is referring to a file.


## Example inputs and outputs

Use these example outputs to better understand the types of inputs the model accepts, and the types of outputs the model returns:

### Example (https://replicate.com/p/x5bb6hzstnrm80cpjas8hx5n8m)

#### Input

```json
{
  "text": "Speech-02-series is a Text-to-Audio and voice cloning technology that offers voice synthesis, emotional expression, and multilingual capabilities.\n\nThe HD version is optimized for high-fidelity applications like voiceovers and audiobooks. While the turbo one is designed for real-time applications with low latency.\n\nWhen using this model on Replicate, each character represents 1 token.",
  "pitch": 0,
  "speed": 1,
  "volume": 1,
  "bitrate": 128000,
  "channel": "mono",
  "emotion": "happy",
  "voice_id": "Friendly_Person",
  "sample_rate": 32000,
  "language_boost": "English",
  "english_normalization": true
}
```

#### Output

```json
"https://replicate.delivery/xezq/V5fclDfiEXq1GUvPTIC6zc4CWhYvZagKvPgkHlR9YldH3toUA/tmpdgbymb15.mp3"
```


## Model readme

> # Speech-02-series
> 
> Speech-02-series is a Text-to-Audio (T2A) and voice cloning technology that offers voice synthesis, emotional expression, and multilingual capabilities.
> 
> ## Models
> 
> - **[Speech-02-HD](https://replicate.com/minimax/speech-02-hd)**: Optimized for high-fidelity applications like voiceovers and audiobooks
> - **[Speech-02-Turbo](https://replicate.com/minimax/speech-02-turbo)**: Designed for real-time applications with low latency
> - **[Voice-Cloning](https://replicate.com/minimax/voice-cloning)**: Clone voices for use with speech-02-hd and speech-02-turbo
> 
> ## Key Features
> 
> ### Voice Cloning
> 
> - 10-second voice cloning with 99% reported vocal similarity
> - 300+ pre-built voices across different demographics
> - Controls for pitch, speed, and volume
> 
> ### Emotion Control
> 
> - Auto-detect mode that matches emotional tone to text context
> - Manual customization options for emotional expression
> 
> ### Language Support
> 
> - 30+ languages with native accents
> - English variants: US, UK, Australian, Indian
> - Asian languages: Mandarin, Cantonese, Japanese, Korean, Vietnamese, Indonesian
> - European languages: French, German, Spanish, Portuguese (Brazilian), Turkish, Russian, Ukrainian
> - Recently added: Thai, Polish, Romanian, Greek, Czech, Finnish, Hindi
> 
> ## Technical Specifications
> 
> ### Deployment
> 
> - Virtual machine and private cloud deployment options
> - Isolated environment for security and privacy
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
> 
> ## MiniMax TTS Voice List
> 
> A complete list of pre-trained voices available for us with the hd and turbo models:
> 
> - English_Trustworth_Man
> - English_Aussie_Bloke
> - English_CalmWoman
> - English_UpsetGirl
> - English_Gentle-voiced_man
> - English_Whispering_girl
> - English_Diligent_Man
> - English_Graceful_Lady
> - English_ReservedYoungMan
> - English_PlayfulGirl
> - English_ManWithDeepVoice
> - English_MaturePartner
> - English_FriendlyPerson
> - English_MatureBoss
> - English_Debator
> - English_LovelyGirl
> - English_Steadymentor
> - English_Deep-VoicedGentleman
> - English_Wiselady
> - English_CaptivatingStoryteller
> - English_DecentYoungMan
> - English_SentimentalLady
> - English_ImposingManner
> - English_SadTeen
> - English_PassionateWarrior
> - English_WiseScholar
> - English_Soft-spokenGirl
> - English_SereneWoman
> - English_ConfidentWoman
> - English_PatientMan
> - English_Comedian
> - English_BossyLeader
> - English_Strong-WilledBoy
> - English_StressedLady
> - English_AssertiveQueen
> - English_AnimeCharacter
> - English_Jovialman
> - English_WhimsicalGirl
> - English_Kind-heartedGirl
> - Chinese (Mandarin)_Reliable_Executive
> - Chinese (Mandarin)_News_Anchor
> - Chinese (Mandarin)_Unrestrained_Young_Man
> - Chinese (Mandarin)_Mature_Woman
> - Arrogant_Miss
> - Robot_Armor
> - Chinese (Mandarin)_Kind-hearted_Antie
> - Chinese (Mandarin)_Refreshing_Young_Man
> - Chinese (Mandarin)_HK_Flight_Attendant
> - Chinese (Mandarin)_Humorous_Elder
> - Chinese (Mandarin)_Gentleman
> - Chinese (Mandarin)_Warm_Bestie
> - Chinese (Mandarin)_Stubborn_Friend
> - Chinese (Mandarin)_Sweet_Lady
> - Chinese (Mandarin)_Southern_Young_Man
> - Chinese (Mandarin)_Wise_Women
> - Chinese (Mandarin)_Gentle_Youth
> - Chinese (Mandarin)_Warm_Girl
> - Chinese (Mandarin)_Male_Announcer
> - Chinese (Mandarin)_Kind-hearted_Elder
> - Chinese (Mandarin)_Cute_Spirit
> - Chinese (Mandarin)_Radio_Host
> - Chinese (Mandarin)_Lyrical_Voice
> - Chinese (Mandarin)_Straightforward_Boy
> - Chinese (Mandarin)_Sincere_Adult
> - Chinese (Mandarin)_Gentle_Senior
> - Chinese (Mandarin)_Crisp_Girl
> - Chinese (Mandarin)_Pure-hearted_Boy
> - Chinese (Mandarin)_Soft_Girl
> - Chinese (Mandarin)_IntellectualGirl
> - Chinese (Mandarin)_Warm_HeartedGirl
> - Chinese (Mandarin)_Laid_BackGirl
> - Chinese (Mandarin)_ExplorativeGirl
> - Chinese (Mandarin)_Warm-HeartedAunt
> - Chinese (Mandarin)_BashfulGirl
> - Japanese_IntellectualSenior
> - Japanese_DecisivePrincess
> - Japanese_LoyalKnight
> - Japanese_DominantMan
> - Japanese_SeriousCommander
> - Japanese_ColdQueen
> - Japanese_DependableWoman
> - Japanese_GentleButler
> - Japanese_KindLady
> - Japanese_CalmLady
> - Japanese_OptimisticYouth
> - Japanese_GenerousIzakayaOwner
> - Japanese_SportyStudent
> - Japanese_InnocentBoy
> - Japanese_GracefulMaiden
> - Cantonese_ProfessionalHost（F)
> - Cantonese_GentleLady
> - Cantonese_ProfessionalHost（M)
> - Cantonese_PlayfulMan
> - Cantonese_CuteGirl
> - Cantonese_KindWoman
> - Korean_SweetGirl
> - Korean_CheerfulBoyfriend
> - Korean_EnchantingSister
> - Korean_ShyGirl
> - Korean_ReliableSister
> - Korean_StrictBoss
> - Korean_SassyGirl
> - Korean_ChildhoodFriendGirl
> - Korean_PlayboyCharmer
> - Korean_ElegantPrincess
> - Korean_BraveFemaleWarrior
> - Korean_BraveYouth
> - Korean_CalmLady
> - Korean_EnthusiasticTeen
> - Korean_SoothingLady
> - Korean_IntellectualSenior
> - Korean_LonelyWarrior
> - Korean_MatureLady
> - Korean_InnocentBoy
> - Korean_CharmingSister
> - Korean_AthleticStudent
> - Korean_BraveAdventurer
> - Korean_CalmGentleman
> - Korean_WiseElf
> - Korean_CheerfulCoolJunior
> - Korean_DecisiveQueen
> - Korean_ColdYoungMan
> - Korean_MysteriousGirl
> - Korean_QuirkyGirl
> - Korean_ConsiderateSenior
> - Korean_CheerfulLittleSister
> - Korean_DominantMan
> - Korean_AirheadedGirl
> - Korean_ReliableYouth
> - Korean_FriendlyBigSister
> - Korean_GentleBoss
> - Korean_ColdGirl
> - Korean_HaughtyLady
> - Korean_CharmingElderSister
> - Korean_IntellectualMan
> - Korean_CaringWoman
> - Korean_WiseTeacher
> - Korean_ConfidentBoss
> - Korean_AthleticGirl
> - Korean_PossessiveMan
> - Korean_GentleWoman
> - Korean_CockyGuy
> - Korean_ThoughtfulWoman
> - Korean_OptimisticYouth
> - Spanish_SereneWoman
> - Spanish_MaturePartner
> - Spanish_CaptivatingStoryteller
> - Spanish_Narrator
> - Spanish_WiseScholar
> - Spanish_Kind-heartedGirl
> - Spanish_DeterminedManager
> - Spanish_BossyLeader
> - Spanish_ReservedYoungMan
> - Spanish_ConfidentWoman
> - Spanish_ThoughtfulMan
> - Spanish_Strong-WilledBoy
> - Spanish_SophisticatedLady
> - Spanish_RationalMan
> - Spanish_AnimeCharacter
> - Spanish_Deep-tonedMan
> - Spanish_Fussyhostess
> - Spanish_SincereTeen
> - Spanish_FrankLady
> - Spanish_Comedian
> - Spanish_Debator
> - Spanish_ToughBoss
> - Spanish_Wiselady
> - Spanish_Steadymentor
> - Spanish_Jovialman
> - Spanish_SantaClaus
> - Spanish_Rudolph
> - Spanish_Intonategirl
> - Spanish_Arnold
> - Spanish_Ghost
> - Spanish_HumorousElder
> - Spanish_EnergeticBoy
> - Spanish_WhimsicalGirl
> - Spanish_StrictBoss
> - Spanish_ReliableMan
> - Spanish_SereneElder
> - Spanish_AngryMan
> - Spanish_AssertiveQueen
> - Spanish_CaringGirlfriend
> - Spanish_PowerfulSoldier
> - Spanish_PassionateWarrior
> - Spanish_ChattyGirl
> - Spanish_RomanticHusband
> - Spanish_CompellingGirl
> - Spanish_PowerfulVeteran
> - Spanish_SensibleManager
> - Spanish_ThoughtfulLady
> - Portuguese_SentimentalLady
> - Portuguese_BossyLeader
> - Portuguese_Wiselady
> - Portuguese_Strong-WilledBoy
> - Portuguese_Deep-VoicedGentleman
> - Portuguese_UpsetGirl
> - Portuguese_PassionateWarrior
> - Portuguese_AnimeCharacter
> - Portuguese_ConfidentWoman
> - Portuguese_AngryMan
> - Portuguese_CaptivatingStoryteller
> - Portuguese_Godfather
> - Portuguese_ReservedYoungMan
> - Portuguese_SmartYoungGirl
> - Portuguese_Kind-heartedGirl
> - Portuguese_Pompouslady
> - Portuguese_Grinch
> - Portuguese_Debator
> - Portuguese_SweetGirl
> - Portuguese_AttractiveGirl
> - Portuguese_ThoughtfulMan
> - Portuguese_PlayfulGirl
> - Portuguese_GorgeousLady
> - Portuguese_LovelyLady
> - Portuguese_SereneWoman
> - Portuguese_SadTeen
> - Portuguese_MaturePartner
> - Portuguese_Comedian
> - Portuguese_NaughtySchoolgirl
> - Portuguese_Narrator
> - Portuguese_ToughBoss
> - Portuguese_Fussyhostess
> - Portuguese_Dramatist
> - Portuguese_Steadymentor
> - Portuguese_Jovialman
> - Portuguese_CharmingQueen
> - Portuguese_SantaClaus
> - Portuguese_Rudolph
> - Portuguese_Arnold
> - Portuguese_CharmingSanta
> - Portuguese_CharmingLady
> - Portuguese_Ghost
> - Portuguese_HumorousElder
> - Portuguese_CalmLeader
> - Portuguese_GentleTeacher
> - Portuguese_EnergeticBoy
> - Portuguese_ReliableMan
> - Portuguese_SereneElder
> - Portuguese_GrimReaper
> - Portuguese_AssertiveQueen
> - Portuguese_WhimsicalGirl
> - Portuguese_StressedLady
> - Portuguese_FriendlyNeighbor
> - Portuguese_CaringGirlfriend
> - Portuguese_PowerfulSoldier
> - Portuguese_FascinatingBoy
> - Portuguese_RomanticHusband
> - Portuguese_StrictBoss
> - Portuguese_InspiringLady
> - Portuguese_PlayfulSpirit
> - Portuguese_ElegantGirl
> - Portuguese_CompellingGirl
> - Portuguese_PowerfulVeteran
> - Portuguese_SensibleManager
> - Portuguese_ThoughtfulLady
> - Portuguese_TheatricalActor
> - Portuguese_FragileBoy
> - Portuguese_ChattyGirl
> - Portuguese_Conscientiousinstructor
> - Portuguese_RationalMan
> - Portuguese_WiseScholar
> - Portuguese_FrankLady
> - Portuguese_DeterminedManager
> - French_Male_Speech_New
> - French_Female_News Anchor
> - French_CasualMan
> - French_MovieLeadFemale
> - French_FemaleAnchor
> - French_MaleNarrator
> - Indonesian_SweetGirl
> - Indonesian_ReservedYoungMan
> - Indonesian_CharmingGirl
> - Indonesian_CalmWoman
> - Indonesian_ConfidentWoman
> - Indonesian_CaringMan
> - Indonesian_BossyLeader
> - Indonesian_DeterminedBoy
> - Indonesian_GentleGirl
> - German_FriendlyMan
> - German_SweetLady
> - German_PlayfulMan
> - Russian_HandsomeChildhoodFriend
> - Russian_BrightHeroine
> - Russian_AmbitiousWoman
> - Russian_ReliableMan
> - Russian_CrazyQueen
> - Russian_PessimisticGirl
> - Russian_AttractiveGuy
> - Russian_Bad-temperedBoy
> - Italian_BraveHeroine
> - Italian_Narrator
> - Italian_WanderingSorcerer
> - Italian_DiligentLeader
> - Dutch_kindhearted_girl
> - Dutch_bossy_leader
> - Vietnamese_kindhearted_girl
> - Arabic_CalmWoman
> - Arabic_FriendlyGuy
> - Turkish_CalmWoman
> - Turkish_Trustworthyman
> - Ukrainian_CalmWoman


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
    "text": "Speech-02-series is a Text-to-Audio and voice cloning technology that offers voice synthesis, emotional expression, and multilingual capabilities.\n\nThe HD version is optimized for high-fidelity applications like voiceovers and audiobooks. While the turbo one is designed for real-time applications with low latency.\n\nWhen using this model on Replicate, each character represents 1 token.",
    "emotion": "happy",
    "voice_id": "Friendly_Person",
    "language_boost": "English",
    "english_normalization": True
}

output = replicate.run(
    "minimax/speech-02-hd",
    input=input
)
with open("output.mp3", "wb") as file:
    file.write(output.read())
#=> output.mp3 written to disk

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
Webhooks
Webhooks provide real-time updates about your prediction. Specify an endpoint when you create a prediction, and Replicate will send HTTP POST requests to that URL when the prediction is created, updated, and finished.

It is possible to provide a URL to the predictions.create() function that will be requested by Replicate when the prediction status changes. This is an alternative to polling.

To receive webhooks you’ll need a web server. The following example uses AIOHTTP, a basic webserver built on top of Python’s asyncio library, but this pattern will apply to most frameworks.

Show example
Then create the prediction passing in the webhook URL and specify which events you want to receive out of "start" , "output" ”logs” and "completed".

input = {
    "text": "Speech-02-series is a Text-to-Audio and voice cloning technology that offers voice synthesis, emotional expression, and multilingual capabilities.\n\nThe HD version is optimized for high-fidelity applications like voiceovers and audiobooks. While the turbo one is designed for real-time applications with low latency.\n\nWhen using this model on Replicate, each character represents 1 token.",
    "emotion": "happy",
    "voice_id": "Friendly_Person",
    "language_boost": "English",
    "english_normalization": True
}

callback_url = "https://my.app/webhooks/replicate"
replicate.predictions.create(
  model="minimax/speech-02-hd",
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
    "text": "Speech-02-series is a Text-to-Audio and voice cloning technology that offers voice synthesis, emotional expression, and multilingual capabilities.\n\nThe HD version is optimized for high-fidelity applications like voiceovers and audiobooks. While the turbo one is designed for real-time applications with low latency.\n\nWhen using this model on Replicate, each character represents 1 token.",
    "emotion": "happy",
    "voice_id": "Friendly_Person",
    "language_boost": "English",
    "english_normalization": True
}

prediction = replicate.predictions.create(
  model="minimax/speech-02-hd",
  input=input
)
#=> Prediction(id='z3wbih3bs64of7lmykbk7tsdf4', ...)

Copy
Cancel a prediction
You may need to cancel a prediction. Perhaps the user has navigated away from the browser or canceled your application. To prevent unnecessary work and reduce runtime costs you can use prediction.cancel() method to call the predictions.cancel endpoint.

input = {
    "text": "Speech-02-series is a Text-to-Audio and voice cloning technology that offers voice synthesis, emotional expression, and multilingual capabilities.\n\nThe HD version is optimized for high-fidelity applications like voiceovers and audiobooks. While the turbo one is designed for real-time applications with low latency.\n\nWhen using this model on Replicate, each character represents 1 token.",
    "emotion": "happy",
    "voice_id": "Friendly_Person",
    "language_boost": "English",
    "english_normalization": True
}

prediction = replicate.predictions.create(
  model="minimax/speech-02-hd",
  input=input
)

prediction.cancel()

Copy
Async Python methods
asyncio is a module built into Python's standard library for writing concurrent code using the async/await syntax.

Replicate's Python client has support for asyncio. Each of the methods has an async equivalent prefixed with async_<name>.

input = {
    "text": "Speech-02-series is a Text-to-Audio and voice cloning technology that offers voice synthesis, emotional expression, and multilingual capabilities.\n\nThe HD version is optimized for high-fidelity applications like voiceovers and audiobooks. While the turbo one is designed for real-time applications with low latency.\n\nWhen using this model on Replicate, each character represents 1 token.",
    "emotion": "happy",
    "voice_id": "Friendly_Person",
    "language_boost": "English",
    "english_normalization": True
}

prediction = replicate.predictions.create(
  model="minimax/speech-02-hd",
  input=input
)

prediction = await replicate.predictions.async_create(
  model="minimax/speech-02-hd",
  input=input
)

| Key | Type | Description | Default | Minimum | Maximum |
| --- | --- | --- | --- | --- | --- |
| text | string | Text to convert to speech. Every character is 1 token. Maximum 5000 characters. Use <#x#> between words to control pause duration (0.01-99.99s). |  |  |  |
| pitch | integer | Speech pitch | 0 | -12 | 12 |
| speed | number | Speech speed | 1 | 0.5 | 2 |
| volume | number | Speech volume | 1 |  | 10 |
| bitrate | integer | Bitrate for the generated speech | 128000 |  |  |
| channel | string | Number of audio channels | "mono" |  |  |
| emotion | string | Speech emotion | "auto" |  |  |
| voice_id | string | Desired voice ID. Use a voice ID you have trained (https://replicate.com/minimax/voice-cloning), or one of the following system voice IDs: Wise_Woman, Friendly_Person, Inspirational_girl, Deep_Voice_Man, Calm_Woman, Casual_Guy, Lively_Girl, Patient_Man, Young_Knight, Determined_Man, Lovely_Girl, Decent_Boy, Imposing_Manner, Elegant_Man, Abbess, Sweet_Girl_2, Exuberant_Girl | "Wise_Woman" |  |  |
| sample_rate | integer | Sample rate for the generated speech | 32000 |  |  |
| language_boost | string | Enhance recognition of specific languages and dialects | "None" |  |  |
| english_normalization | boolean | Enable English text normalization for better number reading (slightly increases latency) | False |  |  |

Output:
| Type | Description |
| --- | --- |
| uri |  |