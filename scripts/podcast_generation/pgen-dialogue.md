# Workflow for Podcast Dialogue

1. Setup Project file as per namiong convention in `scripts/podcast_generation/test_create_podcast_dialogue.py`

2. Use `scripts/podcast_generation/test_create_podcast_dialogue.py` to generate json files and script txt using open router. Here is what `scripts/podcast_generation/test_create_podcast_dialogue.py` is supposed to do:
    a. Take in prompt and optional pdf as input like `scripts/podcast_generation/test_create_podcast_monologue.py`. We will use open router API chat GPT 4o (`documentation/openrouter-api.md` for guidance) to generate a two person conversation script as per the given prompt in format [Speaker 1 name] <dialogue> [Speaker 2 name] <dialogue> [Speaker 1 name] <dialogue> [Speaker 2 name] <dialogue> and save it as text file in the project folder.
    b. Use this text file to make json file which will have these dialogues <speaker number> <speaker name> <speaker dialogue line>. 
    c. Use the json file and make 2 json file which contains lines of dialoges for that speaker. 
    d. naming convention of json files will be <project name>-<speaker name (both names for the total file and for single file, speaker name)>-<script>.<extension>.

3. Use `scripts/podcast_generation/test_create_podcast_monologue.py` as subprocess to generate the audio TTS files from the audio sample URL provided (saving locations in the folder, respecting naming convention) for both speaker. Basically 2 parallel processes to run for each speaker. File naming convention to be maintained as per `scripts/podcast_generation/test_create_podcast_monologue.py`.

4. Use the `scripts/podcast_generation/test_create_podcast_monologue.py` script to generate image -> podcast background -> image to silent video for both speaker. Basically 2 parallel processes to run for each speaker. File naming convention to be maintained as per `scripts/podcast_generation/test_create_podcast_monologue.py`.

5. Use `scripts/podcast_generation/test_create_podcast_monologue.py` script to generate lipsync for both the speakers.  Basically 2 parallel processes to run for each speaker. File naming convention to be maintained as per `scripts/podcast_generation/test_create_podcast_monologue.py`.

6. Refer to the json file containing both speakers line in order and then use that to guide it how to order the lipsync videos i.e. S1-D1 (speaker 1 dialogue 1) S2-D1 then S1-D2 then S2-D2 and so on and then stich them together to make final conversational video output. 