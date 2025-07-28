---
title: Logging
nav_order: 6
---

# Logging

NanoEncoder creates detailed logs to help with troubleshooting and monitoring operations.

## Log Locations

**Default locations by OS:**
- **macOS**: `~/Library/Logs/NanoEncoder/`
- **Windows**: `%LOCALAPPDATA%/NanoEncoder/logs/`
- **Linux**: `~/.local/share/NanoEncoder/logs/` (or `$XDG_DATA_HOME/NanoEncoder/logs/` if set)

**Override**: Set `NEN_LOG_DIR` environment variable to use a custom location.

## Log Files

- **`NanoEncoder.log`** - Main application events, errors, and progress
- **`NanoEncoder_ffmpeg.log`** - FFmpeg command output and debugging details

## Usage

Check logs when:
- Operations fail unexpectedly
- You need to verify what files were processed
- Troubleshooting encoding issues
- Monitoring batch operations

All log entries include timestamps for easy tracking.
