---
title: Optimize Command
layout: default
parent: Commands
nav_order: 1
---
# `optimize`
The `optimize` command is the primary command. It finds all of the videos in a target directory, and re-encodes them into HEVC/h.265.

- While it's processing a video, it will have an **.optimizing** tag (i.e. `video.optimizing.mp4`)
- After processing, the tag will change to **.optimized** (i.e. `video.optimized.mp4`)

If an outage occurs while optimizing, simply re-run the command against the same directory. When NanoEncoder encounters a file with `.optimizing` still in the name, it will delete the partially optimized file and re-encode the original.

After a directory is fully processed, you may run the [health](health.md) command to get a grade on how well it did, the [purge](purge.md) command to remove the original video files, and the [untag](untag.md) command to safely remove the `.optimized` tags from the file names.

## Usage
One should experiment with a small sample of videos (like if you're optimizing a season of a show), at varying crf values, and visually comparing the results. A feature will be released soon™ to aid with process.

### For shows
If you're re-encoding a show, you should test your CRF setting on a small sample of videos for each season. If your show spans a decade, the same settings may offer varying results.

### For movies
If you're re-encoding, say, a movie, encoding a sample isn't possible. Or is it? One can encode a portion, cancel the operation with Ctrl+C, then review what has been re-encoded. This is very limited, and not very practical, but it's my best solution for now. Another feature for down the road. By and large, the default setting should be sufficient for most media.

### `--crf` flag (default: 28)
Use the crf to adjust the tradeoff between detail preservation and file size. It can be anywhere from 0-51. The "best" value is subjective and varies between files.

{: .warning }
Too low of CRF (<18) may actually INCREASE the size of your file! NanoEncoder will warn you of file increases.

Read the more at the [about-crf.md](docs/about-crf.md) page

### `--preset` flag (default: medium)
FFmpeg offers presets to further control how much size is saved, but this time in relation to encoding times. NanoEncoder uses the same default FFmpeg does for this encoding type, **medium**. The [documentation](https://trac.ffmpeg.org/wiki/Encode/H.265#ConstantRateFactorCRF) says "use the slowest preset you have patience", as this will result in the smallest video sizes.

### `--downscale` flag
You can resize your videos to further decrease file sizes. This flag takes a width as input, and the height is determined by the aspect ratio of the video. Examples sizes are 720 & 1080.

---
Full help output:
```
usage: NanoEncoder optimize [-h] [--crf CRF] [--downscale DOWNSCALE]
                            [--preset {ultrafast,superfast,veryfast,faster,fast,medium,slow,slower,veryslow}]
                            directory

positional arguments:
  directory             Path to the target directory

options:
  -h, --help            show this help message and exit
  --crf CRF             Constant rate factor (0-51, default: 28)
  --downscale DOWNSCALE
                        Downscale video resolution to a specified height (e.g., 1080 or 720). Maintains aspect ratio.
  --preset {ultrafast,superfast,veryfast,faster,fast,medium,slow,slower,veryslow}
                        Set the encoding speed/efficiency preset (default: medium)
```
