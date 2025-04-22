---
title: Installation
---
# Installation
{: .note }
Still in Beta! Full release coming soon!

## Requirements
- Python 3.13+ (if not installing via `uv`)
- [FFmpeg](https://www.ffmpeg.org/download.html) (including `ffprobe`) 7.1+ installed system-wide

{: .tip }
Older versions of FFmpeg aren't officially supported (by FFmpeg or NanoEncoder), but might work. Not interested in lowering this "soft" requirement. If it works on earlier, great! But 7.1+ is still recommended

## [uv](https://docs.astral.sh/uv/getting-started/installation/) (Recommended)
`uv` doesn't require Python to be installed.

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

## [pipx](https://pipx.pypa.io/stable/installation/) (Untested)
```bash
# Install latest
pipx install git+https://github.com/JoshPaulie/NanoEncoder.git

# Update installation to latest
pipx upgrade nanoencoder

# Uninstall NanoEncoder
pipx uninstall nanoencoder

# Verify functionality
nen -h
```

## Manual (Untested)
Please consider using uvx/pipx.

```bash
git clone https://github.com/JoshPaulie/NanoEncoder.git
cd NanoEncoder
python -m venv .venv
python -m pip install .

# Update installation to latest
git pull
python -m pip install .

# Uninstall NanoEncoder
python -m pip uninstall .

# Verify functionality
nen -v
```

---
PRs welcome if you're interested in fleshing out alternative installation methods.
