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
# Install DMD 2.097.0 and then set it as active
diva install dmd 2.097.0
# Install LDC v1.26.0
diva install ldc v1.26.0
# Install the most recently released version of dub
diva install dub latest

# List locally available versions of DMD
diva list dmd

# List all versions of LDC available to be installed
diva list ldc --remote

# Switch to another installed version of dub
diva use dub v1.24.0

# Show the current active versions of DMD, LDC, and dub
diva status

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
export PATH="$PATH:$DIVA_HOME/bin/dub"
export PATH="$PATH:$DIVA_HOME/bin/ldc"
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

## Commands list

These flags are recognized for every command:

- `--home` to override the `DIVA_HOME` environment variable and explicitly
set Diva's home directory for the duration of a command.

- `-v` or `--verbose` will cause Diva to log more detailed information about
what it's doing.

- `--silent` will cause Diva to log much less than usual, normally nothing.
You can check Diva's exit status code to determine if the operation was
completed successfully.

- `-y` or `--yes` will automatically respond with "yes" to interactive
yes/no prompts. These promps are normally presented before carrying through
with more unusual or destructive operations.

### diva version

Display Diva's own version.

```
pineapple:diva$ diva version
Diva 0.1.1 - D Language Interface for Versioned Applications
Diva is online at https://github.com/pineapplemachine/diva
```

### diva status

Displays the currently in-use versions for software managed by Diva.

```
pineapple:diva$ diva status
Diva's home directory is /home/pineapple/.diva
Using dmd 2.095.0
Not using any version of ldc
Using dub v1.26.0
```

### diva cleanup

Clean out Diva's downloads folder, which stores downloaded release
archives.

This is not the same as removing installations! Only the archives from
which the installations were extracted.
Use `diva uninstall [app] [version]` to remove installations.

```
pineapple:diva$ diva cleanup
Really remove all files in /home/pineapple/.diva/downloads? [y/N] y
Removing file /home/pineapple/.diva/downloads/dmd.2021.07.10.13.41.28.dmd.2.094.0.linux.zip
Removing file /home/pineapple/.diva/downloads/dmd.2021.07.10.01.58.09.dmd.2.029.zip
Removing file /home/pineapple/.diva/downloads/dmd.2021.07.10.13.44.06.dmd.2.095.0.linux.zip
Removing file /home/pineapple/.diva/downloads/dub.2021.07.10.13.53.29.v1.22.0.zip
Removing file /home/pineapple/.diva/downloads/dmd.2021.07.10.01.55.03.dmd.2.091.1.linux.zip
Finished removing 5 files in /home/pineapple/.diva/downloads
```

### diva list [app]

List available versions of a given version-managed software.

```
pineapple:diva$ diva list dmd
dmd 2.097.0
dmd 2.095.0 [Active]
dmd 2.094.2
dmd 2.094.1
dmd 2.094.0
dmd 2.091.1
dmd 2.072.2
dmd 2.072.1
dmd 2.072.0
dmd 1.054
```

Use the `--remote` flag to request a complete list of versions
from the internet that could be downloaded and installed.

```
pineapple:diva$ diva list dmd --remote | grep "dmd 2\.09"
dmd 2.097.0 [Installed] [Latest]
dmd 2.096.1
dmd 2.096.0
dmd 2.095.1
dmd 2.095.0 [Installed] [Active]
dmd 2.094.2 [Installed]
dmd 2.094.1 [Installed]
dmd 2.094.0 [Installed]
dmd 2.093.1
dmd 2.093.0
dmd 2.092.1
dmd 2.092.0
dmd 2.091.1 [Installed]
dmd 2.091.0
dmd 2.090.1
dmd 2.090.0
```

### diva install [app] [version]

Download and install a given version of managed software.

When `latest` is provided for the version argument, Diva will find
and install the most recent release.

Normally, the newly installed version is immediately made the active
and in-use version, overriding the previously active version.
If you want to install a new version without switching to it immediately,
you can use the `--inactive` flag, and then `diva use [app] [version]`
later on when you're ready for it.

Downloaded release archives will be saved in `$DIVA_HOME/downloads`
and extracted to and built as needed in `$DIVA_HOME/programs`.
You should consider running `diva cleanup` periodically to remove
downloaded release archives, or `diva uninstall [app] [version]` to
remove no-longer-needed installations.

If the version you are trying to install can already be found in
Diva's installation list, then you will be prompted to answer yes/no
to whether you want to download and reinstall this version.
Use the `--yes` flag to automatically respond "yes" to this prompt
and reinstall the given version.

```
pineapple:diva$ diva install dmd 2.093.1
Attempting to download http://downloads.dlang.org/releases/2.x/2.093.1/dmd.2.093.1.linux.zip
49.52 MB | #################### | 100%
Downloaded file to path /home/pineapple/.diva/downloads/dmd.2021.07.10.13.54.53.dmd.2.093.1.linux.zip
Extracting archive /home/pineapple/.diva/downloads/dmd.2021.07.10.13.54.53.dmd.2.093.1.linux.zip to path /home/pineapple/.diva/programs/dmd-2.093.1
Unlinked previously active dmd version.
Creating symlink /home/pineapple/.diva/bin/dmd => /home/pineapple/.diva/programs/dmd-2.093.1/dmd2/linux/bin64
Creating symlink /home/pineapple/.diva/lib/dmd => /home/pineapple/.diva/programs/dmd-2.093.1/dmd2/linux/lib64
```

### diva uninstall [app] [version]

Remove a previously-installed version of some managed software.

You will be prompted to answer yes/no to whether you really want
to remove installed software.
Use the `--yes` flag to automatically respond "yes" to this prompt
and uninstall the given version.

```
pineapple:diva$ diva uninstall dmd 2.093.1
Really uninstall dmd 2.093.1? [y/N] y
Removed installation directory /home/pineapple/.diva/programs/dmd-2.093.1
```

### diva use [app] [version]

Change the currently in-use version of version-managed software.

```
pineapple:diva$ diva use dmd 2.094.0
Unlinked previously active dmd version.
Creating symlink /home/pineapple/.diva/bin/dmd => /home/pineapple/.diva/programs/dmd-2.094.0/dmd2/linux/bin64
Creating symlink /home/pineapple/.diva/lib/dmd => /home/pineapple/.diva/programs/dmd-2.094.0/dmd2/linux/lib64
Now using dmd 2.094.0
```

If you try to `use` a version that isn't locally installed, then you
will be prompted to answer yes/no to whether you'd like to immediately
try to download and install that version.
Use the `--yes` flag to automatically respond "yes" to this prompt
and install the missing version.

```
pineapple:diva$ diva use dmd 2.092.1
Installation not found. Install dmd 2.092.1? [y/N] y
Attempting to download http://downloads.dlang.org/releases/2.x/2.092.1/dmd.2.092.1.linux.zip
49.48 MB | #################### | 100%
Downloaded file to path /home/pineapple/.diva/downloads/dmd.2021.07.10.14.03.44.dmd.2.092.1.linux.zip
Extracting archive /home/pineapple/.diva/downloads/dmd.2021.07.10.14.03.44.dmd.2.092.1.linux.zip to path /home/pineapple/.diva/programs/dmd-2.092.1
Unlinked previously active dmd version.
Creating symlink /home/pineapple/.diva/bin/dmd => /home/pineapple/.diva/programs/dmd-2.092.1/dmd2/linux/bin64
Creating symlink /home/pineapple/.diva/lib/dmd => /home/pineapple/.diva/programs/dmd-2.092.1/dmd2/linux/lib64
```

### diva disuse [app]

Don't use any version of some version-managed software.

This will outright remove the symlinks that would place an in-use version
into your `PATH`.

```
pineapple:diva$ diva disuse dmd
Unlinked previously active dmd version.
```
