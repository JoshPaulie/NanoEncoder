---
title: Health Command
layout: default
parent: Commands
nav_order: 2
---
# `health`
The `health` command is used to validate the quality of your optimized videos by comparing them to their originals. It uses FFmpeg's builtin SSIM (Structural Similarity Index Measure) analysis to grade how well the optimization preserved video quality.

- By default, it samples 5% of videos in a directory to save time
- Each video pair receives a SSIM score value
- Size differences are also shown for each pair
- All analysis is logged to `NanoEncoder_ffmpeg.log` for reference

{: .important }
SSIM is the "best" comparison tool built into FFmpeg, but is very mathematically objective. The "best" tool (in terms of human perception) would be [Netflix's vmaf](https://github.com/Netflix/vmaf), which would require users installing on their machines. Perhaps in a future update.

### `--sample-ratio` flag (default: 0.05)
Controls what percentage of video pairs to check. The default of 0.05 means 5% of videos will be checked. At least one video will always be checked, even if the ratio would select less than one video.

### `--all` flag
Check every video pair in the directory instead of using the sample ratio. This is useful for smaller directories or when you want to be thorough, but can take a long time for large collections.

---
Full help output:
```
usage: NanoEncoder health [-h] [--sample-ratio SAMPLE_RATIO] [--all] directory

positional arguments:
  directory             Check a small sample of original and optimized files, comparing similarity

options:
  -h, --help            show this help message and exit
  --sample-ratio SAMPLE_RATIO
                        Percentage of video to check (ignored if --all is set)
  --all                 Check all video pairs rather than a sample
```
