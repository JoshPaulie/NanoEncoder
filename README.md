<img src="imgs/Banner.png" width="600">

# NanoEncoder
A lightweight ffmpeg wrapper to reduce your video collection size (while preserving quality)

> [!warning]
> Core functionality works, customization features and logging changes underway. Project in "Beta", feedback on small sample sizes welcome. Refrain from running on large portions of your media until full first release (with PyPI release) 😄

**NanoEncoder** is for local media nerds who want to save storage space without sacrificing video quality. It provides:

- Smart batch processing of video directories into HEVC (h.265)
- Detailed reporting of space savings
- Safe cleanup of original files (only when you're ready)

## Installation
### Requirements
- Python 3.13+ (if not installing via `uv`)
- [FFmpeg](https://www.ffmpeg.org/download.html) installed system-wide

### uv (Recommended)
> [!note]
> uv allows you to install Python apps without even having Python itself installed.
>
> Check it out [here](https://docs.astral.sh/uv/getting-started/installation/). This is the preferred method for my friends wanting to use the NanoEncoder

```bash
# Install latest version
uv tool install git+https://github.com/JoshPaulie/NanoEncoder.git

# Update installation to latest
uv tool upgrade nanoencoder

# Uninstall NanoEncoder
uv tool uninstall nanoencoder

# Verify functionality
nen -h
```

### pipx
```bash
pipx install git+https://github.com/JoshPaulie/NanoEncoder.git
nen -h
```

## Usage
```bash
nen optimize '/media/series/The Office (US)' # Re-encode a directory with HEVC (h.265)
nen health '/media/series/The Office (US)'  # Compare the original and optimized video files via SSIM
nen purge '/media/series/The Office (US)'  # Safely remove original files (sends to trash)

nen optimize --crf 23 '/media/series/Berserk (1997)' # Re-encode at specified CRF (Default is 28)
```

## Features
- **Greatly reduce file sizes** for videos by re-encoding with h.265/HEVC
- Perfectly handles **multiple subtitle and audio tracks**[^1] (GREAT for anime)
- **CPU Multithreading** by default
- **Smart batch processing** skips already processed videos and recovers incomplete files
- **Dynamic bit allocation** with [CRF](#about-crf)
- **High fault tolerance**! If you have a power outage while encoding, you can simply run the script against the same directory, and it will pick up at the video where it left off[^2]

### Safety Measures
- No silent deletions: `purge` requires explicit user confirmation, and sends originals to system recycling bin
- Crash detection: Handles partially optimized files
- Comprehensive logging: All operations are recorded in `~/NanoEncoder.log`, and FFmpeg logs  arerecorded in `~/NanoEncoder_ffmpeg.log`

## Quality of optimized videos
Video quality will remain perceptively the same, unless it's an outrageously highly detailed video. You may see a decrease in quality, the higher the definition.

### About CRF (Constant Rate Factor)
CRF is the primary quality/size control setting for h.265 and h.264 encoders. It adjusts the trade-off between **file size** and **visual quality** by dynamically allocating bits where needed. It's on by default, and is a major contributor to the size savings from h.265.

> [!note]
> CRF is **not the same as bitrate**. It adapts per scene, saving space in simpler frames while preserving detail in complex ones.

NanoEncoder defaults to **CRF 28**. Experiment with the `nen encode --crf` flag on a sample of your media, then process the rest.

> [!warning]
> Too low of CRF (<18) may actually INCREASE the size of your file!
>
> How? Why? No idea. Just be aware. Always perform a small sample before processing an entire series.

## ffmpeg settings
The following command is what is ran against all found video files (by default)

```bash
ffmpeg -i input.mp4 -c:v libx265 -crf 28 -preset fast -threads 0 -c:a copy -c:s copy -tag:v hvc1 -loglevel error output.mp4
```

## Contributing
1. File an issue (optional)
2. Clone repo
3. Make venv `uv venv`
4. Install editable locally `uv pip install -e .`
5. Make branch 
6. PR

### Requirements
- [uv](https://github.com/astral-sh/uv) 
- [ruff](https://github.com/astral-sh/ruff)
  - 110 line length

---

[^1]: By literally not touching them at all and copying them as-is. 😎
[^2]: Well, near where it left off. It will delete the partially-encoded file (denoted by .optimizing still being in the name), and re-encode the original.
[^3]: Use `NanoEncoder.py optimize -h` for more details
