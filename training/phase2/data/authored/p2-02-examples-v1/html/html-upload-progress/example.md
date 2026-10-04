# Plex P2 example draft-html-progress

## Request

Show upload progress for 3 of 8 files with a visible label and a machine-readable progress value.

## Solution

```html
<label for="upload-progress">Upload progress</label>
<progress id="upload-progress" value="3" max="8">3 of 8 files</progress>
```
