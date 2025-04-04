# NanoEncoder
A lightweight ffmpeg wrapper to reduce your video collection size (while preserving quality)

**NanoEncoder** is for local media nerds who want to save storage space without sacrificing video quality. It provides:

- Batch processing of video directories
- Smart detection of already optimized files
- Detailed reporting of space savings
- Safe cleanup of original files (only when you're ready)

## Installation
### Requirements
- Python 3.13+ (if not installing via `uv`)
- [FFmpeg](https://www.ffmpeg.org/download.html) installed system-wide
- Supported OS: macOS, Linux, Windows

### uv (Recommended)
> [!note]
> uv allows you to install Python apps without even having Python itself installed.
> 
> Check it out [here](https://docs.astral.sh/uv/getting-started/installation/). This is the preferred method for my friends wanting to use the NanoEncoder

```bash
uv tool install git+https://github.com/JoshPaulie/NanoEncoder.git
nen -h
```

### pipx
```bash
pipx install git+https://github.com/JoshPaulie/NanoEncoder.git
nen -h
```

## Usage
The CLI has 2 commands: `encode` and `purge`. Each take a directory to transact against.

```bash
nen encode '/media/series/The Office (US)' # Recursively find all videos and begin re-encoding
nen purge '/media/series/The Office (US)'  # Recursively remove original (source) files

nen encode --crf 28 '/media/series/Berserk (1997)' # Encode at specified CRF (Default is 23)
```

### Encode subcommand
`encode` is used to re-encode entire directories. Files are found recursively, meaning all video files (regardless if they're nested in other directories) are found and processed.

- While encoding, the files will have **.optimizing** inserted before the file extention.
- After encoding, the files will have **.optimized** inserted before the file extention.

### Purge subcommand
`purge` is used to delete any original source files which have a corresponding optimized file. Meant to be ran against a directory after using `encode`.

## Features
- Greatly reduce file sizes for videos encoded with h.264
- Files already encoded with h.265/HEVC will also see a modest reduction in size
- Perfectly handles multiple subtitle and audio tracks[^1]
- Multithreading by default
- Can determine if a file has already been optimized, and skip already-done videos
- Rather than messing with bitrates, we apply a modest a CRF pass, set to 23 by default. Learn more [here](#about-crf)
- High fault tolerance, meaning if you have a power outage while encoding, you can simply run the script against the same directory, and it will pick up on the video where it left off[^2]

## Safety Measures
- No silent deletions: `purge` requires explicit user confirmation
- User value validation: Ensures CRF values are within safe bounds
- Crash detection: Handles partially encoded files
- Comprehensive logging: All operations recorded in NanoEncoder.log

## Quality of optimized videos
Video quality will remain perceptively the same, unless it's an outrageously highly detailed source file. You may see a decrease in quality, the higher the definition. Movies and shows at 1080p are best suited for NanoEncoder.

- Live action shows and movies may have minor loss in quality.
- Anime content seem to lose no noticeable loss in quality, and are the ideal usecase.

### About CRF (Constant Rate Factor)
CRF is the primary quality/size control setting in **FFmpeg's H.265 (x265) and H.264 (x264) encoders**. It adjusts the trade-off between **file size** and **visual quality** by dynamically allocating bits where needed.  

> [!note]
> 🔹 CRF is **not the same as bitrate**—it adapts per scene, saving space in simpler frames while preserving detail in complex ones.

#### **How It Works:**  
- **Lower CRF (e.g., 18-22)** → Higher quality, larger files (near-lossless)  
- **Higher CRF (e.g., 23-28)** → Smaller files, slightly reduced quality (good for most uses)  
- **Very High CRF (e.g., 30+)** → Significant compression, noticeable quality loss  

#### **Recommended Values:**  
| CRF   | Use Case                                     |
| ----- | -------------------------------------------- |
| 16-18 | Archival/master quality (large files)        |
| 19-22 | High quality (good balance)                  |
| 23-26 | Default (great for streaming/local playback) |
| 27-30 | Smaller files (some quality loss)            |
| 31+   | Low-bitrate (not recommended for HD)         |

NanoEncoder defaults to **CRF 23**, a sweet spot for **good compression without obvious quality loss**. Adjust based on your storage needs with the `nen encode --crf [0]` flag.

> [!warning]
> Too low of CRF (<18) may actually INCREASE the size of your file!
> 
> How? Why? No idea. Just be aware.

## ffmpeg settings
The following command is what is ran against all found video files (though, the crf can be changed via flag[^3])

```bash
ffmpeg -i input.mp4 -c:v libx265 -crf 23 -preset fast -threads 0 -c:a copy -c:s copy -loglevel error output.mp4
```

---

[^1]: By literally not touching them at all and copying them as-is. 😎
[^2]: Well, near where it left off. It will delete the partially-encoded file (denoted by .optimizing still being in the name), and re-encode the original.
[^3]: Use `NanoEncoder.py encode -h` for more details
