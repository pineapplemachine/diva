"""
D Language Interface for Versioned Applications.
Manage installations of dmd, ldc, gdc, and dub.
"""

import argparse
import datetime
import json
import logging
import math
import os
import platform
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import zipfile

import requests

try:
    input = raw_input
except:
    pass

__version__ = "0.1.1"
__website__ = "https://github.com/pineapplemachine/diva"

DIVA_APPS = (
    "dmd",
    "ldc",
    "dub",
)

def get_argparser():
    # Common args
    parser = argparse.ArgumentParser(allow_abbrev=False, description=(
        "diva: D Language Versioned Application Manager."
    ))
    def add_common(parser):
        parser.add_argument("--home", type=str, default="", help=(
            "Override the DIVA_HOME environment variable to specifiy " +
            "in which directory diva should download, install, and search for " +
            "applications and versions."
        ))
        parser.add_argument("-v", "--verbose", action="store_true", help=(
            "Print more information than usual about what diva " +
            "is doing."
        ))
        parser.add_argument("--silent", action="store_true", help=(
            "Print less information than usual about what diva " +
            "is doing, normally none at all."
        ))
        parser.add_argument("-y", "--yes", action="store_true", help=(
            "Automatically respond \"yes\" to potentially dangerous actions " +
            "which would normally involve interactive prompts."
        ))
    # Sub parsers
    subparsers = parser.add_subparsers(help="sub-command help", dest="action")
    # diva list
    list_parser = subparsers.add_parser("list", help=(
        "Display a list of installed applications and versions."
    ))
    add_common(list_parser)
    list_parser.add_argument("application", type=str,
        choices=DIVA_APPS,
        help="List versions only for a specific application."
    )
    list_parser.add_argument("-r", "--remote", action="store_true", help=(
        "Don't just list locally installed versions. " +
        "List all versions that are available to be installed."
    ))
    # diva install
    install_parser = subparsers.add_parser("install", help=(
        "Install a new application or version."
    ))
    add_common(install_parser)
    install_parser.add_argument("application", type=str,
        choices=DIVA_APPS,
        help="Install a new version of this particular application."
    )
    install_parser.add_argument("version", type=str, default="latest", help=(
        "A version string or \"latest\", specifying which version to install."
    ))
    install_parser.add_argument("--inactive", action="store_true", help=(
        "Install this version, but don't immediately put it into active use."
    ))
    # diva uninstall
    uninstall_parser = subparsers.add_parser("uninstall", help=(
        "Remove a previously installed application or version."
    ))
    add_common(uninstall_parser)
    uninstall_parser.add_argument("application", type=str,
        choices=DIVA_APPS,
        help="Remove an installed version of this particular application."
    )
    uninstall_parser.add_argument("version", type=str, help=(
        "A version string specifying which version to uninstall, or \"all\"."
    ))
    # diva use
    use_parser = subparsers.add_parser("use", help=(
        "Choose a specific version of an application to make active."
    ))
    add_common(use_parser)
    use_parser.add_argument("application", type=str,
        choices=DIVA_APPS,
        help="Activate a given version of this particular application."
    )
    use_parser.add_argument("version", type=str, help=(
        "A version string or \"latest\" specifying which version to activate."
    ))
    # diva disuse
    disuse_parser = subparsers.add_parser("disuse", help=(
        "Deactivate any in-use version of an application."
    ))
    add_common(disuse_parser)
    disuse_parser.add_argument("application", type=str,
        choices=DIVA_APPS,
        help="Deactivate the in-use version of this particular application."
    )
    # diva version
    version_parser = subparsers.add_parser("version", help=(
        "Show the version of this Diva tool."
    ))
    add_common(version_parser)
    # diva status
    status_parser = subparsers.add_parser("status", help=(
        "Get information about currently active applications."
    ))
    add_common(status_parser)
    # diva cleanup
    cleanup_parser = subparsers.add_parser("cleanup", help=(
        "Clean up downloaded files. (This doesn't affect installations.)"
    ))
    add_common(cleanup_parser)
    return parser

def parse_args(args=None):
    return get_argparser().parse_args(args or sys.argv[1:])

def get_logger(name, verbose=False, silent=False):
    """
    Get a logger instance, respecting the given "verbose" and "silent"
    settings.
    """
    logger = logging.getLogger(name)
    if silent:
        logger.setLevel(logging.CRITICAL)
    elif verbose:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    stream_handler = logging.StreamHandler(sys.stdout)
    message_format = "%(message)s"
    formatter = logging.Formatter(message_format)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    logger.debug(
        "Logger initialized. verbose: %s, silent: %s.", verbose, silent
    )
    return logger

def get_platform_is_64_bit():
    """
    Returns True when this is a 64-bit platform, and False otherwise.
    """
    return sys.maxsize >= 0x7fffffffffffffff

def get_timestamp():
    return datetime.datetime.now().strftime("%Y.%m.%d.%H.%M.%S")

def prompt_confirm(message, default=None):
    """
    Helper function to prompt the user interactively for a yes or no
    answer. Interactive prompts can help to guard the user from
    accidentally carrying out destructive operations.
    
    However, don't forget to make sure that interactive prompts can be
    bypassed with a command-line flag! Otherwise, the interactive
    prompts can stand in the way of automation tools.
    """
    repeat_text = " Please enter either \"yes\" or \"no\". "
    prompt = "[y/n]"
    choice = None
    repeated = False;
    if default:
        prompt = "[Y/n]"
    elif default is not None:
        prompt = "[y/N]"
    while choice is None:
        sys.stdout.write(
            message + (repeat_text if repeated else " ") + prompt + " "
        )
        choice_str = input().lower().strip()
        if choice_str in ("y", "yes"):
            choice = True
        elif choice_str in ("n", "no"):
            choice = False
        elif len(choice_str) == 0:
            choice = default
        repeated = True
    return choice

def download_file(path, url, silent):
    """
    Helper to download a file, displaying a handy little progress
    bar so you know the script isn't just hanging, but is working hard
    to deliver your software to you.
    """
    response = requests.get(url, stream=True)
    length = response.headers.get("content-length")
    length = int(length) if length else 0
    bytes_written = 0
    progress = 0
    if not (200 <= response.status_code < 300):
        return 0
    if not silent:
        if length:
            sys.stdout.write("%.2f MB | " % (length / 1024 / 1024))
        else:
            sys.stdout.write("?? MB | ")
        sys.stdout.flush()
    with open(path, "wb") as dest_file:
        for chunk in response.iter_content(chunk_size=4096):
            dest_file.write(chunk)
            bytes_written += len(chunk)
            if length:
                new_progress = math.ceil(bytes_written / length * 20)
            else:
                new_progress = bytes_written / 1024 / 1024 / 8
            while progress < new_progress and not silent:
                sys.stdout.write("#" if length else "?")
                sys.stdout.flush()
                progress += 1
    if not silent:
        sys.stdout.write(" | 100%\n")
    return bytes_written

def get_github_list(base_url):
    """
    Helper to traverse paginated results from the GitHub API.
    Used to retrieve lists of tags and releases.
    """
    results = []
    per_page = 100
    page_number = 1
    while True:
        response = requests.get("%s?per_page=%s&page=%s" %
            (base_url, per_page, page_number)
        )
        response_results = response.json()
        results.extend(response_results)
        page_number += 1
        if len(response_results) < per_page:
            break
    return results



def get_install_path(home, app, version):
    """
    Given an application and version, decide where it ought to be installed.
    """
    return os.path.join(home, "programs", "%s-%s" % (app, version))

def get_is_installed(home, app, version):
    """
    Check if a given version of an application is locally installed.
    """
    return os.path.exists(get_install_path(home, app, version))

def update_settings(home, app, version, logger):
    """
    This function maintains a JSON file indicating which versions of
    which apps are currently in use.
    
    This JSON file isn't actually used for anything right now...
    """
    # Downloaded and inflated program lives here
    install_path = get_install_path(home, app, version)
    # Settings get written to here
    json_path = os.path.join(home, "versions.json")
    # Read previous settings
    if os.path.exists(json_path):
        with open(json_path, "rt", encoding="utf-8") as json_file:
            settings = json.load(json_file)
        logger.debug("Loaded settings from path %s", json_path)
    else:
        settings = {}
    settings["home"] = home
    settings[app] = version
    with open(json_path, "wt", encoding="utf-8") as json_file:
        json.dump(settings, json_file)
    logger.debug("Updated settings at path %s", json_path)
    # Activate it
    use_ok = use_app_version(home, app, version, logger)
    if not use_ok:
        logger.error("Failed to activate %s %s", app, version)
    return use_ok

def disuse_app(home, app, logger):
    """
    Remove symlinks for the currently in-use version of an app.
    """
    bin_unlinked = False
    lib_unlinked = False
    bin_path = os.path.join(home, "bin", app)
    if os.path.islink(bin_path):
        logger.debug("Unlinking %s", bin_path)
        os.unlink(bin_path)
        bin_unlinked = True
    lib_path = os.path.join(home, "lib", app)
    if os.path.islink(lib_path):
        logger.debug("Unlinking %s", lib_path)
        os.unlink(lib_path)
        lib_unlinked = True
    return bin_unlinked, lib_unlinked

def use_app_version(home, app, version, logger):
    """
    Make symlinks and ensure binaries have permission to run
    when activating a given installation, e.g. with `diva use`.
    """
    install_path = get_install_path(home, app, version)
    if not os.path.exists(install_path):
        logger.debug("Install path for %s %s does not exist",
            app, version
        )
        return False
    binary_path, library_path = get_app_installation_paths(
        home, app, version, install_path
    )
    logger.debug("Got binary path for %s: %s", app, binary_path)
    logger.debug("Got library path for %s: %s", app, library_path)
    # Ensure binaries have run permission
    if binary_path:
        for root, dirs, files in os.walk(binary_path):
            for file_name in files:
                file_path = os.path.join(root, file_name)
                logger.debug("Assigning permissions for file %s", file_path)
                os.chmod(file_path, stat.S_IREAD | stat.S_IWRITE | stat.S_IEXEC)
    # Remove previous symlinks
    bin_unlinked, lib_unlinked = disuse_app(home, app, logger)
    if bin_unlinked or lib_unlinked:
        logger.info("Unlinked previously active %s version.", app)
    # Make symbolic link (binaries)
    if binary_path:
        symlink_path = os.path.join(home, "bin", app)
        if not os.path.exists(os.path.dirname(symlink_path)):
            logger.debug("Creating directory %s", os.path.dirname(symlink_path))
            os.makedirs(os.path.dirname(symlink_path))
        logger.info("Creating symlink %s => %s", symlink_path, binary_path)
        os.symlink(binary_path, symlink_path)
    # Make symbolic link (libraries)
    if library_path:
        symlink_path = os.path.join(home, "lib", app)
        if not os.path.exists(os.path.dirname(symlink_path)):
            logger.debug("Creating directory %s", os.path.dirname(symlink_path))
            os.makedirs(os.path.dirname(symlink_path))
        logger.info("Creating symlink %s => %s", symlink_path, library_path)
        os.symlink(library_path, symlink_path)
    return True

def iter_installed_versions(home, app):
    """
    Enumerate all the installed versions of an application.
    """
    for root, dirs, files in os.walk(os.path.join(home, "programs")):
        for dir_name in dirs:
            if dir_name.startswith(app + "-"):
                yield dir_name[len(app) + 1:]
        break

def get_active_version(home, app):
    """
    Determine the currently active version of an application.
    """
    bin_path = os.path.join(home, "bin", app)
    if not os.path.islink(bin_path):
        return None
    target_path = os.readlink(bin_path)
    common_path = os.path.commonpath([home, target_path])
    if common_path != home:
        return None
    parts = target_path[1 + len(common_path):].split(os.sep)
    if len(parts) < 2 or parts[0] != "programs":
        return None
    if not parts[1].startswith(app + "-"):
        return None
    return parts[1][len(app) + 1:]



def get_app_version_list(app, logger):
    """
    Request a list of available versions from the internet.
    """
    if app == "dmd":
        return get_dmd_version_list(logger)
    elif app == "dub":
        return get_dub_version_list(logger)
    elif app == "ldc":
        return get_ldc_version_list(logger)
    else:
        return []

def get_dmd_version_list(logger):
    VERSION_PATTERN = re.compile(r'href="/releases/\d.x/([^/]+)/"')
    versions = []
    list_urls = [
        "http://downloads.dlang.org/releases/2.x/",
        "http://downloads.dlang.org/releases/1.x/",
        "http://downloads.dlang.org/releases/0.x/"
    ]
    for list_url in list_urls:
        logger.debug("Requesting dmd versions url %s", list_url)
        response = requests.get(list_url)
        if not (200 <= response.status_code < 300):
            logger.error(
                "Found HTTP response status %d when attempting to read " +
                "dmd versions from content at url %s",
                response.status_code, list_url
            )
            continue
        for match in VERSION_PATTERN.finditer(response.text):
            versions.append(match.group(1))
    return versions

def get_dub_version_list(logger):
    # Note that recent dub releases currently don't come back in the releases
    # list for some reason. That's why this is requesting tags instead.
    github_url = "https://api.github.com/repos/dlang/dub/tags"
    logger.debug("Requesting dub repository tags list from url %s", github_url)
    results = get_github_list(github_url)
    return list(map(
        lambda result: result["name"],
        results
    ))

def get_ldc_version_list(logger):
    github_url = "https://api.github.com/repos/ldc-developers/ldc/releases"
    logger.debug("Requesting ldc repository releases list from url %s", github_url)
    results = get_github_list(github_url)
    return list(map(
        lambda result: result["tag_name"],
        results
    ))



def get_app_installation_paths(home, app, version, install_path):
    """
    This function is for determining what paths, if any, should be
    assigned within Diva's bin/ and lib/ folders when making a
    given app installation active, e.g. via `diva use`.
    """
    if app == "dmd":
        return get_dmd_installation_paths(home, app, version, install_path)
    elif app == "dub":
        return get_dub_installation_paths(home, app, version, install_path)
    elif app == "ldc":
        return get_ldc_installation_paths(home, app, version, install_path)
    else:
        return None, None

def get_dmd_installation_paths(home, app, version, install_path):
    """
    Try to find binary and library paths in a dmd installation.
    Unfortunately these have moved around a lot.
    """
    system = platform.system()
    # 0.x versions put all the binaries in dmd/bin and libraries in dmd/lib
    if os.path.exists(os.path.join(install_path, "dmd/bin")):
        return (
            os.path.exists(os.path.join(install_path, "dmd/bin")),
            os.path.exists(os.path.join(install_path, "dmd/lib"))
        )
    # 1.x and 2.x differ in whether the root directory is "dmd" or "dmd2"
    dmd_root = os.path.join(install_path, "dmd")
    dmd2_root = os.path.join(install_path, "dmd2")
    root = dmd2_root
    if os.path.exists(dmd_root):
        root = dmd_root
    # Subdirectory containing binaries and libraries depends on platform
    if system == "Windows":
        root = os.path.join(root, "windows")
    elif system == "Darwin":
        root = os.path.join(root, "osx")
    elif system == "Linux":
        root = os.path.join(root, "linux")
    else:
        return None, None
    # Sometimes binaries are in "bin", sometimes "bin32"/"bin64"
    # Same deal with "lib", "lib32"/"lib64"
    binary_path = None
    library_path = None
    binx = os.path.join(root, "bin")
    bin64 = os.path.join(root, "bin64")
    bin32 = os.path.join(root, "bin32")
    libx = os.path.join(root, "lib")
    lib64 = os.path.join(root, "lib64")
    lib32 = os.path.join(root, "lib32")
    if get_platform_is_64_bit() and os.path.exists(bin64):
        binary_path = bin64
    elif os.path.exists(bin32):
        binary_path = bin32
    else:
        binary_path = binx
    if get_platform_is_64_bit() and os.path.exists(lib64):
        library_path = lib64
    elif os.path.exists(lib32):
        library_path = lib32
    else:
        library_path = libx
    return binary_path, library_path

def get_dub_installation_paths(home, app, version, install_path):
    install_path = get_install_path(home, app, version)
    src_dir_path = install_path
    for root, dirs, files in os.walk(install_path):
        for dir_name in dirs:
            src_dir_path = os.path.join(root, dir_name)
            break
        break
    binary_path = os.path.join(src_dir_path, "bin")
    return binary_path, None

def get_ldc_installation_paths(home, app, version, install_path):
    install_path = get_install_path(home, app, version)
    src_dir_path = install_path
    for root, dirs, files in os.walk(install_path):
        for dir_name in dirs:
            src_dir_path = os.path.join(root, dir_name)
            break
        break
    binary_path = os.path.join(src_dir_path, "bin")
    library_path = os.path.join(src_dir_path, "lib")
    return binary_path, library_path



def get_app_version_latest(home, app, logger):
    """
    Find the most recently released version of an application.
    """
    versions = get_app_version_list(app, logger)
    if len(versions):
        latest = versions[0]
        logger.info("Found latest %s version: %s", app, latest)
        return latest
    else:
        logger.error("Found no latest version for %s", app)
        return []



def get_app_download_urls(home, app, version, logger, nested=False):
    """
    Get a list of URLs or mirrors to try for downloading a
    given version of an app.
    
    This function returns a list of URLs to try instead of a single
    URL because sometimes inconsistent URL schemes between versions
    make it more practical to just try a handful of things it could
    potentially be, instead of trying to predict it for sure.
    """
    if version == "latest" and not nested:
        latest = get_app_version_latest(home, app, ogger)
        return get_app_download_urls(home, app, latest, logger, True)
    elif app == "dmd":
        return get_dmd_download_urls(home, app, version, logger)
    elif app == "dub":
        return get_dub_download_urls(home, app, version, logger)
    elif app == "ldc":
        return get_ldc_download_urls(home, app, version, logger)
    else:
        return []
    
def get_dmd_url_suffixes():
    """
    Return a list of possible suffixes a dmd version download url
    might have.
    """
    system = platform.system()
    if system == "Windows":
        return [".windows.zip", ".zip"]
    elif system == "Darwin":
        return [".osx.zip", ".zip"]
    elif system == "Linux":
        return [".linux.zip", ".zip"]
    else:
        raise None

def get_dmd_download_urls(home, app, version, logger):
    # NOTE: new nightlies not available since 2020-03-10
    suffixes = get_dmd_url_suffixes()
    if not suffixes:
        logger.error("Unsupported operating system.")
        return 1
    download_url_base = None
    download_url_x = (
        "%s.x" % version[0]
        if len(version) > 1 and version[1] == "."
        else "0.x"
    )
    download_url_base = (
        "http://downloads.dlang.org/releases/%s/%s/dmd.%s" %
        (download_url_x, version, version)
    )
    download_urls = list(map(
        lambda suffix: download_url_base + suffix,
        suffixes
    ))
    return download_urls

def get_dub_download_urls(home, app, version, logger):
    return [
        "https://github.com/dlang/dub/archive/refs/tags/%s.zip" % version
    ]

def get_ldc_download_urls(home, app, version, logger):
    system = platform.system()
    machine = platform.machine()
    is_64_bit = get_platform_is_64_bit()
    is_arm = machine.startswith("arm")
    release_url = (
        "https://api.github.com/repos/ldc-developers/ldc/releases/tags/%s" %
        version
    )
    logger.debug("Requesting release information from url %s", release_url)
    response = requests.get(release_url)
    if not (200 <= response.status_code < 300):
        return []
    assets = response.json()["assets"]
    download_asset = None
    # TODO: Build from source when a matching asset is not found
    for asset in assets:
        logger.debug("Checking asset with name %s", asset["name"])
        if system == "Windows":
            # Prefer 64-bit builds on 64-bit systems, but 32-bit works too
            if "windows-x64" in asset["name"] or "win64" in asset["name"] and is_64_bit:
                download_asset = asset
            if "windows-x86" in asset["name"] or "win32" in asset["name"]:
                download_asset = download_asset or asset
        elif system == "Darwin":
            if "osx-arm64" in asset["name"] and is_arm:
                download_asset = asset
            if "osx-x86_64" in asset["name"] and not is_arm:
                download_asset = asset
        elif system == "Linux":
            if "linux-arm" in asset["name"] and is_arm:
                download_asset = asset
            if "linux-x86_64" in asset["name"] and not is_arm:
                download_asset = asset
    if download_asset:
        logger.debug("Found release asset match with url %s",
            download_asset["browser_download_url"]
        )
        return [download_asset["browser_download_url"]]
    else:
        return []


def build_app(home, args, app, version, logger):
    """
    This step is for building software from source, or other build
    steps, when they might be necessary.
    """
    if app == "dub":
        return build_dub(home, args, app, version, logger)
    else:
        return 0

def build_dub(home, args, app, version, logger):
    install_path = get_install_path(home, app, version)
    logger.info("Building dub from source in directory %s", install_path)
    src_dir_path = install_path
    for root, dirs, files in os.walk(install_path):
        for dir_name in dirs:
            src_dir_path = os.path.join(root, dir_name)
            break
        break
    logger.info("This could take a few minutes...")
    src_path = os.path.join(src_dir_path, "build.d")
    process = subprocess.run(["dmd", "-O", "-inline", src_path],
        cwd=src_dir_path,
    )
    if process.returncode != 0:
        logger.error("Failed to build dub build.d in directory %s", install_path)
        return process.returncode
    build_dir_path = os.path.join(src_dir_path, "diva")
    bin_path = os.path.join(src_dir_path, "build")
    exe_path = os.path.join(src_dir_path, "build.exe")
    if os.path.exists(exe_path):
        bin_path = exe_path
    process = subprocess.run([bin_path],
        cwd=src_dir_path,
        stdout=subprocess.DEVNULL if not args.verbose else None,
    )
    if process.returncode != 0:
        logger.error("Failed to build dub in directory %s", install_path)
        return process.returncode
    return 0
    


def diva_list(home, args, logger):
    """
    Implements the command `diva list [app] [--remote?]`
    """
    app = args.application.strip().lower()
    active_version = get_active_version(home, app)
    installed_versions = iter_installed_versions(home, app)
    if args.remote:
        versions = get_app_version_list(app, logger)
        installed_versions = set(installed_versions)
        if not len(versions):
            logger.info("Found no remote versions")
        for version in versions:
            logger.info(app + " " + (version or "ERROR") +
                (" [Installed]" if version in installed_versions else "") +
                (" [Latest]" if version == versions[0] else "") +
                (" [Active]" if version == active_version else "")
            )
    else:
        installed_versions = list(installed_versions)
        installed_versions.sort(reverse=True)
        if not len(installed_versions):
            logger.info("Found no installed versions")
        for version in installed_versions:
            logger.info(app + " " + (version or "ERROR") +
                (" [Active]" if version == active_version else "")
            )

def diva_install(home, args, logger):
    """
    Implements the command `diva install [app] [version]`
    """
    app = args.application.strip().lower()
    version = args.version
    if version == "latest":
        version = get_app_version_latest(home, app, logger)
    timestamp = get_timestamp()
    download_urls = get_app_download_urls(home, app, version, logger)
    install_path = get_install_path(home, app, version)
    if not len(download_urls):
        logger.error("Found no download urls for %s %s", app, version)
        return 1
    if os.path.exists(install_path):
        logger.info(
            "Found an existing or partial installation for " +
            "%s %s at path %s",
            app, version, install_path
        )
        confirm_reinstall = args.yes or prompt_confirm(
            "Remove and reinstall this version?",
            default=False
        )
        if not confirm_reinstall:
            logger.info("Exiting without changing any installations.")
            return 0
        else:
            shutil.rmtree(install_path, ignore_errors=True)
            logger.info("Removed installation directory %s", install_path)
    download_success = False
    download_path = None
    for download_url in download_urls:
        logger.info("Attempting to download %s", download_url)
        downloads_dir_path = os.path.join(home, "downloads")
        download_path = os.path.join(downloads_dir_path, "%s.%s.%s" %
            (app, timestamp, os.path.basename(download_url))
        )
        if not os.path.exists(downloads_dir_path):
            logger.debug("Creating downloads directory path %s", downloads_dir_path)
            os.makedirs(downloads_dir_path)
        download_success = download_file(
            download_path, download_url, silent=args.silent
        )
        if download_success:
            logger.info("Downloaded file to path %s", download_path)
            break
        else:
            logger.debug("Failed to download %s", download_url)
    if not download_success:
        logger.error("Failed to download %s %s", app, version)
        return 1
    # TODO: Handle other archive types besides .zip and .tar.xz
    if not os.path.exists(install_path):
        logger.debug("Creating installation directory path %s", install_path)
        os.makedirs(install_path)
    logger.info("Extracting archive %s to path %s", download_path, install_path)
    if download_path.endswith(".zip"):
        logger.debug("Extracting zip archive.")
        with zipfile.ZipFile(download_path, "r") as zip_file:
            zip_file.extractall(install_path)
    elif download_path.endswith(".tar.xz"):
        logger.debug("Extracting tar archive.")
        with tarfile.open(download_path) as tar_file:
            tar_file.extractall(install_path)
    else:
        logger.error("Unsupported archive file type.")
        return 1
    build_status = build_app(home, args, app, version, logger)
    if build_status != 0:
        logger.debug("Encountered a build error, aborting installation.")
        return build_status
    if not hasattr(args, "inactive") or not args.inactive:
        settings_ok = update_settings(home, app, version, logger)
        if not settings_ok:
            logger.debug("Encountered an activation error, aborting installation.")
            return 1
    return 0
    
def diva_uninstall(home, args, logger):
    """
    Implements the command `diva uninstall [app] [version]`
    """
    app = args.application.strip().lower()
    version = args.version
    install_path = get_install_path(home, app, version)
    if not os.path.exists(install_path):
        logger.error("No installation for %s %s was found.", app, version)
        logger.info("Exiting without uninstalling any software.")
        return 1
    confirm_uninstall = args.yes or prompt_confirm(
        "Really uninstall %s %s?" % (app, version),
        default=False
    )
    if not confirm_uninstall:
        logger.info("Exiting without uninstalling any software.")
        return 0
    active_version = get_active_version(home, app)
    if version == active_version:
        logger.debug("The %s version being uninstalled is currently in-use.", app)
        bin_unlinked, lib_unlinked = disuse_app(home, app, logger)
        if bin_unlinked or lib_unlinked:
            logger.info("Unlinked %s %s", app, version)
    logger.debug("About to remove installation directory %s", install_path)
    shutil.rmtree(install_path, ignore_errors=True)
    logger.info("Removed installation directory %s", install_path)
    
def diva_use(home, args, logger):
    """
    Implements the command `diva use [app] [version]`
    """
    app = args.application.strip().lower()
    version = args.version
    use_ok = use_app_version(home, args.application, args.version, logger)
    if use_ok:
        logger.info("Now using %s %s", app, version)
        return 0
    confirm_install = args.yes or prompt_confirm(
        "Installation not found. Install %s %s?" % (app, version),
        default=False
    )
    if confirm_install:
        return diva_install(home, args, logger)
    else:
        logger.info("Exiting without changing active %s version.", app)
        return 0

def diva_disuse(home, args, logger):
    """
    Implements the command `diva disuse [app]`
    """
    app = args.application.strip().lower()
    bin_unlinked, lib_unlinked = disuse_app(home, app, logger)
    if bin_unlinked or lib_unlinked:
        logger.info("Unlinked previously active %s version.", app)
    else:
        logger.info("Found no version of %s currently in use.", app)

def diva_version(home, args, logger):
    """
    Implements the command `diva version`
    """
    logger.info("Diva %s - D Language Interface for Versioned Applications",
        __version__
    )
    logger.info("Diva is online at %s", __website__)
            
def diva_status(home, args, logger):
    """
    Implements the command `diva status`
    """
    logger.info("Diva's home directory is %s", home)
    for app in DIVA_APPS:
        version = get_active_version(home, app)
        if version:
            logger.info("Using %s %s", app, version)
        else:
            logger.info("Not using any version of %s", app)

def diva_cleanup(home, args, logger):
    """
    Implements the command `diva cleanup`
    """
    downloads_path = os.path.join(home, "downloads")
    confirm_cleanup = args.yes or prompt_confirm(
        "Really remove all files in %s?" % downloads_path,
        default=False
    )
    if not confirm_cleanup:
        logger.info("Exiting without removing any files.")
        return 0
    count = 0
    for root, dirs, files in os.walk(downloads_path):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            logger.info("Removing file %s", file_path)
            os.remove(file_path)
            count += 1
    logger.info("Finished removing %s files in %s", count, downloads_path)
    return 0

def __main__():
    if len(sys.argv) <= 1:
        get_argparser().print_help()
        return 0
    args = parse_args()
    logger = get_logger("diva", verbose=args.verbose, silent=args.silent)
    home = args.home or os.environ.get("DIVA_HOME") or os.path.expanduser("~/.diva")
    logger.debug("Diva home path is %s", home)
    if not os.environ.get("DIVA_HOME"):
        logger.info(
            "Normally, you want to have the DIVA_HOME environment variable " +
            "set when running Diva. Currently, DIVA_HOME is not set."
        )
        logger.info(
            "Unless you are really sure of what you are doing, you should " +
            "read the Diva readme file and make sure that you have fully " +
            "followed the installation instructions."
        )
    if args.action == "list":
        return diva_list(home, args, logger)
    elif args.action == "install":
        return diva_install(home, args, logger)
    elif args.action == "uninstall":
        return diva_uninstall(home, args, logger)
    elif args.action == "use":
        return diva_use(home, args, logger)
    elif args.action == "disuse":
        return diva_disuse(home, args, logger)
    elif args.action == "version":
        return diva_version(home, args, logger)
    elif args.action == "status":
        return diva_status(home, args, logger)
    elif args.action == "cleanup":
        return diva_cleanup(home, args, logger)

if __name__ == "__main__":
    exit_status = __main__()
    sys.exit(exit_status)
