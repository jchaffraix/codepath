#!/usr/bin/env python3

'''
Script to setup new students' machine for
the Technical Interview Preparation classes, both 101 & 102.

The script will:
* Install the latest version of VSCode (if not installed)
* Install the recommended extensions (when not installed)
# TODO: Add some logic to chooose auto-formatter (autopep8 or black)
'''
import argparse
import logging
import json
import os
import platform
import shutil
import subprocess
import tempfile
import urllib.request
import sys


# The list should be the full extension name in the MarketPlace:
# https://marketplace.visualstudio.com/
# You can find the full name in the URL and the command to install an individual extension.
COMMON_VSCODE_EXTENSIONS = ['ms-python.python']

# This is the list of recommended settings to set in .vscode/settings.json.
# See the function setup_vscode_settings for the merging behavior.
RECOMMENDED_VSCODE_SETTINGS = {
    "python.analysis.typeCheckingMode": "strict"
}

def vscode_download_url(version: str) -> str:
    logger.debug(f'Running on platform: {platform.system()}')
    match platform.system():
        case 'Linux':
            # TODO: This logic is pretty brittle.
            info = platform.freedesktop_os_release()
            id = info["ID"]
            logger.debug(f'Detected a Linux instance, with id={id}')
            match id:
                # Deb-based distributions.
                case 'ubuntu' | 'debian':
                    return f'https://update.code.visualstudio.com/{version}/linux-deb-x64/stable'
                # Rpm-based distributions.
                case 'rhel' | 'fedora':
                    return f'https://update.code.visualstudio.com/{version}/linux-rpm-x64/stable'
                case _:
                    logger.fatal(
                        f'Unhandled Linux version {id}. We only support DEB or RPM based distributions.\nIf that matches your distribution, let us know so we can fix it.')
                    return ''
        case 'Darwin':
            return f'https://update.code.visualstudio.com/{version}/darwin-universal/stable'
        case 'Windows':
            return f'https://update.code.visualstudio.com/{version}/win32-x64-user/stable'
        case _:
            logger.fatal(f'Unsupported platform {platform.system()}')
            return ''


def maybe_vscode_cmd() -> str | None:
    return shutil.which('code')

def vscode_cmd() -> str:
    maybe_cmd = maybe_vscode_cmd()
    if not maybe_cmd:
        logger.fatal('VSCode is not in PATH when it should have!')
    return maybe_cmd # type: ignore

def vscode_file_extension() -> str:
        match platform.system():
            case 'Linux':
                info = platform.freedesktop_os_release()
                id = info["ID"]
                match id:
                    # Deb-based distributions.
                    case 'ubuntu' | 'debian':
                        return '.deb'

                    # Rpm-based distributions.
                    case 'rhel' | 'fedora':
                        return '.rpm'
                    case _:
                        return ''
            case 'Darwin':
                return ''
            case 'Windows':
                return '.exe'
            case _:
                return ''


def maybe_install_vscode() -> bool:
    '''
        This function may install VSCode unless it exists on the system.

        Returns False if it encounters an error.
        Returns True if VScode is present on the system, either already installed or newly installed.
    '''
    if maybe_vscode_cmd() is not None:
        print('Found a VSCode installation, skipping installation... 🌟')
        return True

    logger.debug('About to download the stable versions of VSCode')
    content = urllib.request.urlopen(
        'https://update.code.visualstudio.com/api/releases/stable').read()
    if not content:
        logger.error('Got an empty payload instead of vscode binary')
        return False

    versions = json.loads(content)
    logger.debug(f'Got versions={versions}')
    if not isinstance(versions, list):
        logger.fatal(
            'Parsing latest VSCode version failed. Please let us know!')

    if not isinstance(versions[0], str):
        logger.fatal(
            'Parsing latest VSCode version failed. Please let us know!')

    logger.debug(f'Latest version {versions[0]}')
    url = vscode_download_url(versions[0])  # type: ignore
    logger.debug(f'About to download from {url}')
    content = urllib.request.urlopen(url).read()
    if not content:
        logger.error('Got an empty payload instead of vscode binary')
        return False
    logger.debug(f'Successfully downloaded VSCode')

    with tempfile.NamedTemporaryFile(suffix=vscode_file_extension()) as fp:
        logger.debug(f'Temporary file: {fp.name}')
        fp.write(content)
        match platform.system():
            case 'Linux':
                info = platform.freedesktop_os_release()
                id = info["ID"]
                logger.debug(f'Detected a Linux instance, with id={id}')
                match id:
                    # Deb-based distributions.
                    case 'ubuntu' | 'debian':
                        output = subprocess.run(['sudo', 'apt', 'install', '-y', fp.name])
                        return output.returncode == 0

                    # Rpm-based distributions.
                    case 'rhel' | 'fedora':
                        output = subprocess.run(['sudo', 'dnf', 'install', '-y', fp.name])
                        return output.returncode == 0

                    case _:
                        logger.fatal(
                            f'Unhandled Linux version {id}. We only support DEB or RPM based distributions.\nIf that matches your distribution, let us know so we can fix it.')
                        return False
            case 'Darwin' | 'Windows':
                # For MacOS/Windows, the file is an installer so make it runnable.
                os.chmod(fp.name, 0x755)
                output = subprocess.run([fp.name])
                return output.returncode == 0
            case _:
                logger.fatal(f'Unsupported platform {platform.system()}')
                return False


def get_existing_vscode_extensions() -> set[str]:
    output = subprocess.run([vscode_cmd(), '--list-extensions'],
                            capture_output=True, encoding='utf8')
    if output.returncode != 0:
        logger.fatal(
            'Could not list VSCode extension: returnCode={output.returnCode}, stdout={output.stdout}, stderr={output.stderr}')
    return set(output.stdout.split('\n'))


def install_extension(ext: str) -> bool:
    output = subprocess.run([vscode_cmd(), '--install-extension', ext])
    return output.returncode == 0


def maybe_install_vscode_extensions() -> bool:
    '''
        This function may installs VSCode extensions that are missing on the system

        Return False if there was an error installing any extension or True otherwise.
        Returns True otherwise
    '''
    installed_extensions = get_existing_vscode_extensions()
    logger.debug(installed_extensions)

    exts: list[str] = []
    for ext in COMMON_VSCODE_EXTENSIONS:
        if ext not in installed_extensions:
            exts.append(ext)

    if not exts:
        print(f'No extensions to install 🌟')
        return True

    print(f'Installing {exts}')
    for ext in exts:
        if not install_extension(ext):
            logger.error(f'Failed to install extension {ext}')
            return False

    return True

def setup_vscode_settings(path: str) -> bool:
    '''
        Set up .vscode/settings.json based on RECOMMENDED_VSCODE_SETTINGS.

        This function reads the existing settings file.
        For each recommended settings, it does the following:
        - If a setting is absent in the file, the function sets it.
        - If a setting exists and doesn't match the recommended value, the function prints a warning.
        - If a setting exists and matches the recommended value, the function does nothing.
    '''
    settings_dir = os.path.join(path, '.vscode')
    settings_path = os.path.join(settings_dir, 'settings.json')
    settings = {}
    if os.path.isfile(settings_path):
        with open(settings_path) as fp:
            settings = json.load(fp)

    didChange = False
    for setting, val in RECOMMENDED_VSCODE_SETTINGS.items():
        existing_setting = settings.get(setting, None) # type: ignore
        if existing_setting and existing_setting != val:
            print(f'Setting {setting} is already set to {existing_setting}. We won\'t touch it but recommend to set it to {val}')
            continue
        if existing_setting == val:
            continue

        settings[setting] = val
        didChange = True

    if didChange:
        logger.info(f'Detected some changes, dumping them to {settings_path}')
        if not os.path.isdir(settings_dir):
            logger.debug(f'Directory {settings_dir} is missing, creating it')
            os.mkdir(settings_dir)

        with open(settings_path, 'wt+') as fp:
            fp.write(json.dumps(settings))
        logger.debug(f'Done writing settings at {settings_path}')
    else:
        logger.info('No changes detected')

    return True

def query_yes_no(question: str) -> bool:
    valid = {"yes": True, "y": True, "ye": True, "no": False, "n": False}
    prompt = " [y/N] "

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        # No input --> default to None.
        if choice == "":
            return False

        if choice in valid:
            return valid[choice]

        # Anything else, re-prompt.
        sys.stdout.write("Please respond with 'yes' or 'no' " "(or 'y' or 'n').\n")

def install_all() -> None:
    # Check the Python version.
    logger.debug(f"sys.hexversion: {hex(sys.hexversion)}")
    if sys.hexversion < 0x030D00F0:
        logger.fatal('The version of Python is too old, make sure you have a version >= 3.13.\n\nYou can download a new version at:  https://www.python.org/downloads/\n\nThen check your version using: python --version')

    logger.info("Passed Python version check")
    path = os.getcwd()
    if not yes and not query_yes_no(f"We are about to set up a VSCode workspace in the following directory: {path}.\n\n Do you want to proceed?"):
        return

    if not maybe_install_vscode():
        print('Failed to install VSCode, let us know what happened so we can fix this script!\n\nYou can install to install it manually from: https://code.visualstudio.com/download')
        return

    if not maybe_install_vscode_extensions():
        print('Failed to install VSCode extensions, let us know what happened so we can fix this script!\n\nYou can install to install it manually from: https://code.visualstudio.com/download')
        return

    if not setup_vscode_settings(path):
        print('Failed to set up the .vscode/settings file, let us know what happened so we can fix this script!')
        return

    print('All done 🌟🌟🌟')


parser = argparse.ArgumentParser()
parser.add_argument(
    "-log", "--log", help="Provide logging level. Example --log debug'")
parser.add_argument(
    "-y", "--yes", help="Answer yes to all answers.'", action='store_true')

args = parser.parse_args()
log_level = args.log
yes: bool = args.yes
logging.basicConfig(level=log_level)
logger = logging.getLogger('setup.py')
logger.debug(log_level)

if __name__ == '__main__':
    install_all()
