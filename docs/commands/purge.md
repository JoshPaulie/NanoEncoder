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

It's important you manually check at least a few of your videos before purging. You could also run the [health](health.md) command to semi-validate your optimized files before purging the originals.

### `--permanent` flag (aliases: `--perm`, `-p`)
Instead of moving files to the trash, permanently delete them. This is useful for saving space on systems where the trash is on the same drive.

{: .warning }
Using `--perm` will won't just delete the file, it will _unlink_ it. Recovering this data is tedious and requires expertice, and only possible if the data isn't already overwritten. Make sure you have verified your optimized files first!

### `--skip-confirmation` (aliases: `--skip`, `--force`)
Totally skip the confirmation step. Especially dangerous with the `--perm` flag, but good for automation.

---
Full help output:
```
usage: NanoEncoder purge [-h] [-p] [--skip] directory

positional arguments:
  directory             Path to the target directory

options:
  -h, --help            show this help message and exit
  -p, --perm, --permanent
                        Permanently delete files instead of sending them to trash
  --skip, --skip-confirmation, --force
                        Skip confirmation when purging original files (DANGEROUS!)
```
