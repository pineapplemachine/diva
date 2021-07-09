# Diva

Diva is an MIT-licensed command-line version manager for
[DMD](https://dlang.org/download.html),
[LDC](https://github.com/ldc-developers/ldc), and
[dub](https://github.com/dlang/dub/).

Diva works by automatically downloading release files, setting them
up as necessary, and then using symlinks to put the currently active
installation into your PATH.

Diva requires [Python 3](https://www.python.org/downloads/) to run.

**Notice:**
At the time of writing, I have only tested this on x86-64 Ubuntu.
Maybe it works for other platforms, maybe it doesn't.
For now, that's up to you to find out, and to fix it if not.
Sorry about that!

## Usage

``` bash
# Install DMD 2.097.0
diva install dmd 2.097.0
# Install LDC v1.26.0
diva install ldc v1.26.0
# Install the most recently released version of dub and then set it as active
diva install dub latest

# Show the current active versions of DMD, LDC, and dub
diva status

# List locally available versions of DMD
diva list dmd

# List all versions of LDC available to be installed
diva list ldc --remote

# Switch to another installed version of dub
diva use dub v1.24.0

# Remove an existing dub installation
diva uninstall dub v1.26.0

# Clean up the accumulated contents of Diva's downloads directory
diva cleanup
```

Note that you must have a working DMD installed before you can
`diva install dub`.
This is because the dub installation process involves building
from source.

## Installation

First, ensure that you have
[Python 3](https://www.python.org/downloads/) installed.

After cloning or otherwise downloading the repository, navigate
to the repository's root directory in a command line.
Run this local [pip](https://pypi.org/project/pip/) installation
to make `diva` available on the command line:

```
pip3 install -e .
```

Add these lines to your `~/.bashrc` or equivalent:

```
# Diva - D Language Interface for Versioned Applications
# This path is where Diva stores its files
export DIVA_HOME="$HOME/.diva"
# These put Diva's in-use D binaries into your PATH
export PATH="$PATH:$DIVA_HOME/bin/ldc"
export PATH="$PATH:$DIVA_HOME/bin/dub"
export PATH="$PATH:$DIVA_HOME/bin/dmd"
```

You can change the environment variable `DIVA_HOME` if you'd rather Diva
put the files that it manages, such as downloads and installations,
somewhere else. If you don't specify any `DIVA_HOME`, then `~/.diva` will
be used as a default.

If you need a `LIBRARY_PATH` environment variable for your project,
you can find the appropriate `lib` directory for your currently active
DMD or LDC installation at `$DIVA_HOME/lib/dmd` or `$DIVA_HOME/lib/ldc`.

If you need a `DMD` environment variable for your project,
you can assign it to, for example, `$DIVA_HOME/bin/dmd/dmd`.

## Contributing

I'm happy to accept contributions!

My own concern with this script pretty much starts and ends with whether
I can use it to manage D binaries on my own machines.
If Diva doesn't work for you, you can create an issue and I will have a look,
but ultimately it's probably going to be up to you to fix it.

Why is it written in Python instead of D? Because it was faster to
write it in Python. Sorry for the added dependency.
If there's anyone who would like to rewrite this tool in D, please do!

Here are some things that can probably use some attention:
- I will be astonished if this script works as-is on Windows.
- It might be important to support archives besides *.zip and *.tar.xz.
- Building LDC from source when there isn't a suitable binary release.
