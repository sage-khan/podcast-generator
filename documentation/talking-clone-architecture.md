# AI Clone For Free

---

by : Pranay Prajapati | Support me on

https://www.instagram.com/ask.pranay/

https://www.youtube.com/@AskPranay

Profile : https://www.linkedin.com/in/ask-pranay/ 

---

## System requirement

The most Important System Requirement is the GPU : It should be having at-least 16GB VRAM, (Can Run on Low VRAM with compromise on Quality)

## Creating an Avatar

Avatars are made of 2 Components 
1. Your Audio
2. Your Video

So we have clone our Audio as well as Prepare Image For Avatar

## Audio

### Step 1 : Get a Voice Sample

Get approximately 15s Audio Sample of yourself. this is Enough to clone your Voice

[Vocie Sample.mp3](attachment:82bc07df-f857-4d82-93a8-074ae4ae2b27:Vocie_Sample.mp3)

### Step 2 : Setup Chatterbox AI

Go to this Link: https://github.com/resemble-ai/chatterbox

And Set it up!

### Step 3 : Add Your Voice and Generate some Voice Outputs

Setting I Would Recommend (Would change based on your Audio Input) :

CFG: 0.65

Temperature: 1

Exaggeration: 1

### There You have your Audio Cloned

[Audio-Generated.wav](attachment:bc9e25a0-cb0e-4b5e-8fef-b02c2591454d:Audio-Generated.wav)

## Video

For Video you need an Image, 

1. You can Click one of your self

![image.png](attachment:94d01507-8ed7-461a-aab3-60a01cf28830:image.png)

1. Or Use Flux Kontext Dev to generate Few

![image-27.png](attachment:6bee054b-bcd5-4999-ad3f-e4928538d6c0:image-27.png)

![image-3.jpg](attachment:8b6f0fa5-111c-40c1-a39b-e9a05b4a6002:image-3.jpg)

![image-17.png](attachment:b122fc9c-d399-4a0d-8ca3-fe9833fe07e1:image-17.png)

### Flux Kontext Dev : https://bfl.ai/announcements/flux-1-kontext-dev

You can Also use : https://playground.bfl.ai/image/edit

### Meigen Multi talk

https://github.com/MeiGen-AI/MultiTalk

This uses Wan2.1 to generate the Video.

Add your Audio and Image Over here!

Some Setting I got the best results in

**Prompt**: Man Skydiving and Talking to the camera while skydiving

Number of Frames : ( Length of Audio * 25 ) - 5   |   *{for me it was (5s*25)-5=120}*

Sampling Steps : 100 *(For Low Vram try 50-60, Output will be compromised)*

[skydive try.mp4](attachment:d67350ce-ac3f-4b9c-a509-7e253e035761:skydive_try.mp4)

# And there you have your clone for free on your local machine!