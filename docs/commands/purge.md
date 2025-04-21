---
title: Purge Command
layout: default
parent: Commands
nav_order: 3
---
# `purge`
The `purge` command helps you clean up your original video files after you've confirmed the optimized versions are satisfactory. It will only remove original files that have corresponding optimized versions.

- By default, files are moved to your system's trash/recycle bin for safety
- Confirmation step with files to be removed before proceeding
- Requires explicit confirmation before taking action
- Will not remove files if any .optimizing files are present (unfinished optimization)

It's recommended to run the [health](health.md) command first to validate your optimized files before purging the originals.

### `--permanent` flag (aliases: `--perm`, `-p`)
Instead of moving files to the trash, permanently delete them. This is useful for saving space on systems where the trash is on the same drive, but use with caution as it cannot be undone.

{: .warning }
Using `--perm` will immediately and permanently delete your original files. Make sure you have verified your optimized files first!

---
Full help output:
```
usage: NanoEncoder purge [-h] [-p] directory

positional arguments:
  directory          Path to the target directory

options:
  -h, --help        show this help message and exit
  -p, --perm, --permanent
                    Permanently delete files instead of sending them to trash
```
