# FAQ
Well, more like anticipated questions.

- TOC
{:toc}

## What's the goal of this wrapper?
1. Batch processing (with some fault tolerance), recursively finding all videos in a folders.
2. Reduce the amount of flags and overall complexity that comes with FFmpeg for my less tech-literate friends

You could very easily rewrite this as a bash loop, and that would work for most. But for those who simply want to mass re-encode into HEVC, here's a slightly simpler solution.

## Why use a wrapper?
I think the best way to illustrate why a wrapper would be best (for some) is to compare the same functionality from both NanoEncoder and vanilla FFmpeg + shell.

```bash
# NanoEncoder
nen optimize --downscale 720 --crf 18 "/media/movies/Star Wars"

# Shell
find "/media/movies/Star Wars" -type f \( -name "*.mp4" -o -name "*.mkv" -o -name "*.avi" \) | while read -r video; do
    output="${video%.*}.optimized.${video##*.}"
    ffmpeg -i "$video" \
        -c:v libx265 -crf 18 -preset medium \
        -vf "scale=-2:720,format=yuv420p" \
        -threads 0 -tag:v hvc1 \
        -c:a copy -c:s copy \
        -loglevel error \
        "$output"
done
```

### Basically, NanoEncoder handles the following for you
- **Batch Processing**: No need to write loops or scripts to handle multiple files
- **Crash Recovery**: Automatically detects and recovers from crashes/interruptions
- **Quality Control**: Built-in SSIM analysis to validate your encoding settings
- **Removal of old files**: After encoding, remove the originals
- **Simplified CLI**: Set many defaults behind the scenes, thus fewer flags
- **Compatibility support**: QuickTime and Mac compatibility by default

FFmpeg is an incredibly powerful piece of software. The only intention of this project to make it more accessible for my friends, not try to overshadow or downplay its role

For much cooler and feature rich alternatives to NanoEncoder, check out [these projects](alternative-projects.md)

## Can you add X flag?
Depends. The current flags satisfy the 3 arguments which the [wiki](https://trac.ffmpeg.org/wiki/Encode/H.265#ConstantRateFactorCRF) suggest users pick, CRF + Preset + Tuning profile.

### Can you add a lossless flag?
Lossless files end up being significantly bigger file sizes, which is [antithetical](#whats-the-goal-of-this-wrapper) to the goal of the project.

The [h.264 wiki](https://trac.ffmpeg.org/wiki/Encode/H.264#LosslessH.264) has the following to say:
> If you're looking for an output that is roughly **"visually lossless"** but not technically lossless, use a -crf value of around 17 or 18 (you'll have to experiment to see which value is acceptable for you). It will likely be indistinguishable from the source and not result in a huge, possibly incompatible file like true lossless mode.

This [self proclaimed](https://www.reddit.com/r/handbrake/comments/1egvyzl/comment/lfvrmtg/) "pixel peeper" from reddit recommends:
> CRF values also shift with presets.  But generally Slower CRF 17/18 or Very Slow 18/19 have been very close to visually lossless for me

### Can you add a two-pass flag?
Meh. Don't like the complexity it would in terms of CLI flags, and from what I understand, is strictly related to the output size, and not the quality of the re-encoding. For that reason, unlikely to.
