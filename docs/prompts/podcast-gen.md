Guys!
Ive been facing some issues with kontext recently
Check this thing out:
https://replicate.com/runwayml/gen4-image?prediction=59b3s8xex1rme0craqtayeb51w
It allows you to put on tags for better referencing. Something  missing with kontext model for now.

### Host

Prompt:
```
Task: Composite Image 1 into Image 2.
Rules:

* Use the @man as the only person. His face, hair, and clothing must be preserved exactly. His body must be in proportional size matching the scene in @studio
* Use the background from @studio as the exact and unmodified environment.

Placement: Position the man in the chair behind the desk on the right side of the desk in @studio, microphone suitably placed, man sitting behind the desk.

Action: @man is looking off-camera.
Composition: Do not introduce new people, objects, or change the lighting, furniture, or layout of the background scene from @studio.
```

### GUEST

Even with a low quality photo (basically a thumbnail copied) of Senior @Austin Armstrong we have a more consistent setup.
Now we have 2 scenes available.
@Anand Butani I think this is another endpoint I will need to setup. So a slight change in the backend intended to be there now :slightly_smiling_face:
https://replicate.com/runwayml/gen4-image?prediction=bryg5k532srma0craqz8e0p8e8

Prompt:
```
Task: Composite Image 1 into Image 2.
Rules:

* Use the @man as the only person. His face, hair, and clothing must be preserved exactly. His body must be in proportional size matching the scene in @studio
* Use the background from @studio as the exact and unmodified environment.

Placement: Position the man in the chair behind the desk on the left side of the desk in @studio, microphone suitably placed, man sitting behind the desk.

Action: @man is looking off-camera.
Composition: Do not introduce new people, objects, or change the lighting, furniture, or layout of the background scene from @studio.
```