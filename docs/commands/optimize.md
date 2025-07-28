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

```sh
# Re-encode with default settings (crf: 28, preset: medium, tune: None)
nen optimize "/media/series/Mob Psycho"

# Re-encode with default settings, but stop if any file size increases
nen optimize --halt-on-increase "/media/series/Mob Psycho"

# Re-encode with default settings, but downscale the resolution to 720p
nen optimize --downscale 720 "/media/series/Mob Psycho"

# Re-encode at CRF 18, "virtually lossless"
nen optimize --crf 18 "/media/series/Mob Psycho"

# Re-encode with "ultrafast" preset AND "animation" tuning profile
nen optimize --preset ultrafast --tune animation "/media/series/Mob Psycho"

# Force re-encode, regardless if video is already in h.265 or not.
nen optimize --preset ultrafast --tune animation "/media/series/Mob Psycho"

# Re-encode and immediately replace originals with optimized versions
nen optimize --replace --crf 25 "/media/series/Mob Psycho"
```

### For shows
If you're re-encoding a show, you should test your CRF setting on a small sample of videos for each season. If your show spans a decade, the same settings may offer varying results.

### For movies
Sampling a portion of a movie isn't practical. For movies, use 17-18 CRF, which is considered "[visually lossless](../FAQ.md#lossless-flag)." 

### `--crf` flag (default: 28)
Use the crf to adjust the tradeoff between detail preservation and file size. It can be anywhere from 0-51. The "best" value is subjective and varies between files.

{: .warning }
Too low of CRF (<18) may actually INCREASE the size of your file! NanoEncoder will warn you of file increases.

Read the more at the [about-crf.md](../about-crf.md) page

### `--preset` flag (default: medium)
FFmpeg offers presets to further control how much size is saved, but this time in relation to encoding times. NanoEncoder uses the same default FFmpeg does for this encoding type, **medium**. The [documentation](https://trac.ffmpeg.org/wiki/Encode/H.265#ConstantRateFactorCRF) says "use the slowest preset you have patience", as this will result in the smallest video sizes.

Available presets: `ultrafast`, `superfast`, `veryfast`, `faster`, `fast`, `medium`, `slow`, `slower`, and `veryslow`.

### `--tune` flag (default: None)
Finally, for even further control, one can specify a tuning profile. Check out the official [documentation](https://x265.readthedocs.io/en/stable/presets.html) for more info, but the most commonly used tuning profiles are also the most self evident, `grain` and `animation`. `grain` is for older movies which tend to be grainer. `animation` is for cartoons, anime.

Available tuning profiles: `animation`, `grain`, `stillimage`, `fastdecode`, and `zerolatency`.

### `--downscale` flag (default: None)
You can resize your videos to further decrease file sizes. This flag takes a width as input, and the height is determined by the aspect ratio of the video. Examples sizes are 720 & 1080.

### `--halt-on-increase` flag (default: False)
Stop the a directory if any video's output size is larger than its input size. This is useful as a size increases often means that the CRF value is too low for efficient compression.

### `--replace-after` / `--replace` flag (default: False)
Automatically replace the original video files with their optimized versions after processing. This flag combines the functionality of the [purge](purge.md) and [untag](untag.md) commands into the optimization process.

When enabled, NanoEncoder will:
1. Optimize videos as usual with `.optimized` tags
2. After each video completes successfully, safely delete the original file (moved to trash/recycle bin)
3. Remove the `.optimized` tag from the optimized file, effectively replacing the original

{: .warning }
This doesn't allow you to have a chance to use [`health`](health.md#health) subcommand.

---
Full help output:
```
usage: NanoEncoder optimize [-h] [--crf CRF] [--downscale DOWNSCALE]
                            [--preset {ultrafast,superfast,veryfast,faster,fast,medium,slow,slower,veryslow}]
                            [--tune {animation,grain,stillimage,fastdecode,zerolatency}]
                            [--force] [--halt-on-increase] [--replace-after]
                            directory

positional arguments:
  directory             Path to the target directory

options:
  -h, --help            show this help message and exit
  --crf CRF             Constant rate factor, between 0-51 (default 28))
  --downscale DOWNSCALE
                        Downscale video resolution to a specified height
                        (e.g., 1080 or 720). Maintains aspect ratio (default
                        None)
  --preset {ultrafast,superfast,veryfast,faster,fast,medium,slow,slower,veryslow}
                        Set the encoding speed/efficiency preset (default:
                        medium)
  --tune {animation,grain,stillimage,fastdecode,zerolatency}
                        Set the tuning profile (default: None)
  --force               Force encode even if video is already in h.265 format
  --halt-on-increase    Stop processing if any video's size increases after
                        optimization
  --replace-after, --replace
                        Replace the original video file with the optimized
                        version (delete original and remove '.optimized' tag)

```
