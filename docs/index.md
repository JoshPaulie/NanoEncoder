---
title: Homepage
nav_order: 1
---
# NanoEncoder docs
Here we'll detail the usage and behavior of NanoEncoder, as well as explain a bit about h.265 and its features.

[Installation](installation.md){: .btn .btn-green }

## Usage

```sh
nen optimize '/path/to/videos'  # Re-encode directory with HEVC (h.265)
nen health '/path/to/videos'    # Compare original vs optimized quality  
nen purge '/path/to/videos'     # Remove original files (sends to trash)
nen untag '/path/to/videos'     # Remove NanoEncoder tags from filenames
```

If you trust CRF to do a "good enough" job, or if you have limited disk space (i.e. you can't store both the original and optimizes versions at the same time), you can add the `--replace` flag. This handles most of the process, aside from the healthcheck.

```sh
nen optimize --replace '/path/to/videos' # Optimize with default CRF, but delete original and untag new files, effectively "replacing" the file with an HEVC version.
```

## Commands
- [Optimize](commands/optimize.md)
- [Health](commands/health.md)
- [Purge](commands/purge.md)
- [Untag](commands/untag.md)

## FFmpeg
- [About CRF](about-crf.md)
- [FFmpeg settings for NanoEncoder](ffmpeg-settings.md)

## Troubleshooting
- [Logging](logging.md)
