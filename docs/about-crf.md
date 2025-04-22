# About CRF (Constant Rate Factor)
CRF is the primary quality/size control setting for h.265 and h.264 encoders. **It adjusts the trade-off between file size and visual quality** by dynamically allocating bits where needed. It's on by default, and is a major contributor to the size savings from h.265.

**CRF is not the same as bitrate**. It adapts per scene, saving space in simpler frames while preserving detail in complex ones.

NanoEncoder defaults to **CRF 28**, the same default as FFmpeg. I personally use 23. Of course, that means I'm fine with slightly larger files.

{: .warning }
Too low of CRF may actually INCREASE the size of your file!

## For shows
If you're re-encoding a show, you should test your CRF setting on a small sample of videos for each season. If your show spans a decade, the same settings may offer varying results.

## For movies
If you're re-encoding, say, a movie, encoding a sample isn't possible. Or is it? One can encode a portion, cancel the operation with Ctrl+C, then review what has been re-encoded. This is very limited, and not very practical, but it's my best solution for now. By and large, the default setting should be sufficient for any media.
