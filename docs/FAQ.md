# FAQ
Well, more anticipated questions.

- TOC
{:toc}

### Why use a wrapper?
Here's how NanoEncoder simplifies FFmpeg usage:

- **Batch Processing**: No need to write loops or scripts to handle multiple files
- **Crash Recovery**: Automatically detects and recovers from crashes/interruptions
- **Quality Control**: Built-in SSIM analysis to validate your encoding settings
- **Safer File Management**: 
   - Moves originals to trash instead of permanent deletion
   - Requires confirmation before deleting
   - Won't delete originals until optimization is complete
- **Progress Tracking**:
   - [Rich](https://github.com/Textualize/rich/) progress bars
   - Time remaining estimates
   - Space savings reports
- **Sane Defaults**:
   - Uses recommended CRF values
   - Enables multithreading
   - Preserves subtitles and audio tracks
- **Simple CLI**:
   - No need to remember FFmpeg parameters
   - Simplified, clear, documented options
   - Help text explains each setting
- **Compatibility**:
   - Adds Apple/QuickTime compatibility flags
   - Maintains directory hierarchy and file organization
   - Preserves metadata

FFmpeg is an incredibly powerful piece of software. The only intention of this project to make it more accessible for my friends, not try to shadow or downplay its significance. It's the heavylifter behind all of this.

### Can you add X flag?
Depends. The current flags satisfy the 3 arguments which the [wiki](https://trac.ffmpeg.org/wiki/Encode/H.264#crf) suggest users pick, CRF + Preset + Tuning profile.

### Lossless flag?
I'm unlikely to add a lossless flag. From what I've only seen, file sizes grow when the lossless feature is applied. Maybe I'm misunderstanding something.

FWIW, the wiki has the following to say:
> Tip: If you're looking for an output that is roughly "visually lossless" but not technically lossless, use a -crf value of around 17 or 18 (you'll have to experiment to see which value is acceptable for you). It will likely be indistinguishable from the source and not result in a huge, possibly incompatible file like true lossless mode.

### Two pass flag?
Maybe. Don't like the complexity it would in terms of CLI flags, 

### What's the goal of this wrapper?
1. Batch processing (with some fault tolerance), recursively finding all videos in a folders.
2. Reduce the amount of flags and overall complexity that comes with FFmpeg for my less tech-literate friends

You could very easily rewrite this as a bash loop, and that would work for most. But for those who simply want to mass re-encode into HEVC, here's a slightly simpler solution.
