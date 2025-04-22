---
title: FFmpeg Settings
nav_exclude: true
---
## FFmpeg Settings
The following command is what is ran against all found video files (by default)

```bash
ffmpeg -i input.mp4 -c:v libx265 -crf 28 -preset fast -threads 0 -c:a copy -c:s copy -tag:v hvc1 -loglevel error output.mp4
```
