<p align="center">
  <img src="imgs/Banner.png" width="600">
</p>

# NanoEncoder
A lightweight ffmpeg wrapper to reduce your video collection size (while preserving quality)

> [!warning]
>  Project in "Beta", feedback on small sample sizes welcome. Refrain from running on large portions of your media until full first release (on PyPI) 😄

**NanoEncoder** is for local media nerds who want to save storage space without sacrificing video quality. It provides:

- Smart batch processing of video directories into HEVC (h.265)
- Detailed reporting of space savings
- Safe cleanup of original files (only when you're ready)

## Installation
### Requirements
- Python 3.13+ (if not installing via `uv`)
- [FFmpeg](https://www.ffmpeg.org/download.html) (including `ffprobe`) 7.1+ installed system-wide

### uv (Recommended)
> [!note]
> uv allows you to install Python apps without even having Python itself installed.
>
> Check it out [here](https://docs.astral.sh/uv/getting-started/installation/). This is the preferred method for my friends wanting to use the NanoEncoder

```bash
# PyPI package coming soon™
uv tool install git+https://github.com/JoshPaulie/NanoEncoder.git
```

Check out the [https://bexli.dev/NanoEncoder/installation](installation) page for more details.

## Usage
```bash
nen optimize '/media/series/The Office (US)' # Re-encode a directory with HEVC (h.265)
nen health '/media/series/The Office (US)'  # Compare the original and optimized video files via SSIM
nen purge '/media/series/The Office (US)'  # Safely remove original files (sends to trash)
nen untag '/media/series/The Office (US)' # Remove the "tags" left behind by NanoEncoder

nen optimize --crf 23 '/media/series/Berserk (1997)' # Re-encode at specified CRF (Default is 28)
```

## Features
- **Greatly reduce file sizes** for videos by re-encoding with h.265/HEVC
- **Crossplatform**, tested on Windows, Linux, and MacOS
- Perfectly handles **multiple subtitle and audio tracks**[^1] (GREAT for anime)
- **CPU Multithreading** by default
- **Smart batch processing** skips already processed videos and recovers incomplete files
- **Dynamic bit allocation** with [CRF](docs/about-crf.md)
- **High fault tolerance**! If you have a power outage while encoding, you can simply run the script against the same directory, and it will pick up at the video where it left off[^2]

### Safety Measures
- No silent deletions: `purge` requires explicit user confirmation, and sends originals to system recycling bin
- Crash detection: Handles partially optimized files
- Comprehensive logging: All operations are recorded in `~/NanoEncoder.log`, and FFmpeg logs are recorded in `~/NanoEncoder_ffmpeg.log`

## Contributing
1. File an issue (optional)
2. Clone repo
3. Make venv `uv venv`
4. Install editable locally `uv pip install -e .`
5. Make branch 
6. PR

### Requirements
- [uv](https://github.com/astral-sh/uv) 
- [ruff](https://github.com/astral-sh/ruff) (110 line length)

---

[^1]: By literally not touching them at all and copying them as-is. 😎
[^2]: Well, near where it left off. It will delete the partially-encoded file (denoted by .optimizing still being in the name), and re-encode the original.
[^3]: Use `NanoEncoder.py optimize -h` for more details
