---
title: Untag Command
layout: default
parent: Commands
nav_order: 4
---
# `untag`
The `untag` command removes the ".optimized" suffix from your optimized video files. Best for after you removed originals with [purge](purge.md)

{: .note }
This operation would be tedious. The files themselves are unchanged, only their names are modified. Reveresing would simply be a matter of renaming the files, adding them back in.

---
Full help output:
```
usage: NanoEncoder untag [-h] directory

positional arguments:
  directory   Path to the target directory

options:
  -h, --help  show this help message and exit
```
