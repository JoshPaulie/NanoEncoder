---
title: About CRF
---
# About CRF (Constant Rate Factor)
CRF (Constant Rate Factor) is the primary quality/size control setting for h.265 and h.264 encoders. **It adjusts the trade-off between file size and visual quality** by dynamically allocating bits where needed. It's on by default, and is a major contributor to the size savings from h.265.

**CRF is not the same as bitrate**. It adapts per scene, saving space in simpler frames while preserving detail in complex ones.

NanoEncoder defaults to **28 CRF**, the same default as FFmpeg. I personally use 23. Of course, that means I'm fine with slightly larger files.

{: .warning }
Again, too low of CRF may actually INCREASE the size of your file!
