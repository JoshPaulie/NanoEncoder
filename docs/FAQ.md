# FAQ
Well, more anticipated questions.

### Can you add X flag?
Depends. The current flags satisfy the 3 arguments which the [wiki](https://trac.ffmpeg.org/wiki/Encode/H.264#crf) suggest users pick, CRF + Preset + Tuning profile.

#### Lossless flag?
I'm unlikely to add a lossless flag. From what I've only seen, file sizes grow when the lossless feature is applied. Maybe I'm misunderstanding something.

FWIW, the wiki has the following to say:
> Tip: If you're looking for an output that is roughly "visually lossless" but not technically lossless, use a -crf value of around 17 or 18 (you'll have to experiment to see which value is acceptable for you). It will likely be indistinguishable from the source and not result in a huge, possibly incompatible file like true lossless mode.

#### Two pass flag?
Maybe. Don't like the complexity it would in terms of CLI flags, 

### What's the goal of this wrapper?
1. Batch processing (with some fault tolerance), recursively finding all videos in a folders.
2. Reduce the amount of flags and overall complexity that comes with FFmpeg for my less tech-literate friends

You could very easily rewrite this as a bash loop, and that would work for most. But for those who simply want to mass re-encode into HEVC, here's a slightly simpler solution.
