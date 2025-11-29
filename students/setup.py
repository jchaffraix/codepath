#!/usr/bin/env python3

'''
Script to setup new students' machine for
the Technical Interview Preparation classes, both 101 & 102.

The script will:
* Install the latest version of VSCode (if not installed)
* Install the recommended extensions (when not installed)
* Update settings.json on the student's chosen file.
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

from pathlib import Path


# The list should be the full extension name in the MarketPlace:
# https://marketplace.visualstudio.com/
# You can find the full name in the URL and the command to install an individual extension.
AUTOINSTALLED_VSCODE_EXTENSIONS = [
    'ms-python.python', 'ms-vsliveshare.vsliveshare']

# List of autoformatters. The user can select at most one to install.
AUTOFORMAT_VSCODE_EXTENSIONS = [
    'ms-python.autopep8',
    'ms-python.black-formatter',
]

# This is the list of recommended settings to set in .vscode/settings.json.
# See the function setup_vscode_settings for the merging behavior.
RECOMMENDED_VSCODE_SETTINGS = {
    'python.analysis.typeCheckingMode': 'strict'
}

# Cached (global) path to VSCode.
# This is needed as Mac installs VSCode outside of PATH.
_g_cached_vscode_path: str | None = None


def uprint(s: str):
    '''
        Small wrapper around `print` to handle different encoding

        This is useful for Windows as it may not use UTF-8.

        For more context, see the discussion on:
        https://stackoverflow.com/questions/14630288/unicodeencodeerror-charmap-codec-cant-encode-character-maps-to-undefined
    '''
    print(s.encode(sys.stdout.encoding, errors='replace'))


def vscode_download_url(version: str) -> str:
    logger.debug(f'Running on platform: {platform.system()}')
    match platform.system():
        case 'Linux':
            # TODO: This logic is pretty brittle.
            info = platform.freedesktop_os_release()
            id = info['ID']
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
    global _g_cached_vscode_path
    if _g_cached_vscode_path:
        return _g_cached_vscode_path
    _g_cached_vscode_path = shutil.which('code')
    return _g_cached_vscode_path


def vscode_cmd() -> str:
    maybe_cmd = maybe_vscode_cmd()
    if not maybe_cmd:
        logger.fatal('VSCode is not in PATH when it should have!')
    return maybe_cmd  # type: ignore


def vscode_file_extension() -> str:
    match platform.system():
        case 'Linux':
            info = platform.freedesktop_os_release()
            id = info['ID']
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
            return '.zip'
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
        uprint('Found a previous VSCode installation')
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
    uprint(f'Downloading the latest VSCode')
    logger.debug(f'Downloading latest VSCode from {url}')
    content = urllib.request.urlopen(url).read()
    if not content:
        logger.error('Got an empty payload instead of vscode binary')
        return False
    logger.debug(f'Successfully downloaded VSCode')

    # On Windows, a file can't open twice - for writing and executing.
    # The downloaded file should be first closed before executing it.
    # TODO: This doesn't cleans the file.
    downloaded_path: str = ''
    with tempfile.NamedTemporaryFile(suffix=vscode_file_extension(), delete=False) as fp:
        downloaded_path = fp.name
        fp.write(content)

    global _g_cached_vscode_path
    logger.debug(f'Wrote VSCode artifact to temporary file: {downloaded_path}')
    match platform.system():
        case 'Linux':
            info = platform.freedesktop_os_release()
            id = info['ID']
            logger.debug(f'Detected a Linux instance, with id={id}')
            match id:
                # Deb-based distributions.
                case 'ubuntu' | 'debian':
                    output = subprocess.run(
                        ['sudo', 'apt', 'install', '-y', downloaded_path])
                    return output.returncode == 0

                # Rpm-based distributions.
                case 'rhel' | 'fedora':
                    output = subprocess.run(
                        ['sudo', 'dnf', 'install', '-y', downloaded_path])
                    return output.returncode == 0

                case _:
                    logger.fatal(
                        f'Unhandled Linux version {id}. We only support DEB or RPM based distributions.\nIf that matches your distribution, let us know so we can fix it.')
                    return False
        case 'Windows':
            # For Windows, the file is an installer so make it runnable.
            os.chmod(downloaded_path, 0x755)
            output = subprocess.run([downloaded_path])
            return output.returncode == 0
        case 'Darwin':
            # For Mac, the file is a zip file to unzip in the user's
            # applications directory.
            app_path = Path.home() / 'Applications'
            vscode_app_path = app_path / 'Visual Studio Code.app'
            vscode_binary_path = vscode_app_path / \
                'Contents' / 'Resources' / 'app' / 'bin' / 'code'
            if vscode_binary_path.exists():
                logger.info(
                    f'Found an existing installation of VSCode in {str(vscode_app_path)}, reusing it...')
                _g_cached_vscode_path = str(vscode_binary_path)
                return True
            if vscode_app_path.exists():
                uprint(
                    f'''💥💥💥 Found an existing installation of VSCode in {str(vscode_app_path)}, but no binary.

This may indicate a failed installation. You can safely delete {str(vscode_app_path)} and retry this script.''')
                return False

            output = subprocess.run(
                ['unzip', downloaded_path, '-d', str(app_path)])
            if output.returncode == 0:
                # Cache the VSCode path if we're successful.
                _g_cached_vscode_path = str(vscode_binary_path)
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


def maybe_install_vscode_extensions(extensions: list[str]) -> bool:
    '''
        This function may installs VSCode extensions that are missing on the system

        Return False if there was an error installing any extension or True otherwise.
        Returns True otherwise
    '''
    installed_extensions = get_existing_vscode_extensions()
    logger.debug(installed_extensions)

    exts: list[str] = []
    for ext in extensions:
        if ext not in installed_extensions:
            exts.append(ext)

    if not exts:
        uprint(f'No extensions to install')
        return True

    uprint(f'Installing the following extensions: {','.join(exts)}')
    for ext in exts:
        if not install_extension(ext):
            logger.error(f'Failed to install extension {ext}')
            return False

    return True


def setup_vscode_settings(path: str) -> None:
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
        existing_setting = settings.get(setting, None)  # type: ignore
        if existing_setting and existing_setting != val:
            uprint(
                f'Setting {setting} is already set to {existing_setting}. We won\'t touch it but recommend to set it to {val}')
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


def query_yes_no(question: str) -> bool:
    valid = {'yes': True, 'y': True, 'ye': True, 'no': False, 'n': False}
    prompt = ' [y/N] '

    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        # No input --> default to None.
        if choice == '':
            return False

        if choice in valid:
            return valid[choice]

        # Anything else, re-prompt.
        sys.stdout.write(
            "Please respond with 'yes' or 'no' (or 'y' or 'n').\n")


def query_auto_formatter() -> str | None:
    valid = {'1': 0, 'a': 0, 'auto': 0, 'autopep8': 0,
             '2': 1, 'b': 1, 'black': 1,
             '3': 2, 'n': 2, 'no': 2}
    prompt = '''We recommend installing one of the following autoformatter:
1. autopep8 [recommended]
2. black
3. Do not install an autoformatter

[1/2/3] (default: 3) '''

    while True:
        sys.stdout.write(prompt)
        choice = input().lower()
        # No input --> default to None.
        if choice == '':
            return None

        if choice in valid:
            idx = valid[choice]
            if idx >= len(AUTOFORMAT_VSCODE_EXTENSIONS):
                return None
            return AUTOFORMAT_VSCODE_EXTENSIONS[idx]

        # Anything else, re-prompt.
        sys.stdout.write(
            "Please respond with 1/2/3 (or 'auto' or 'black').\n")


def install_all() -> None:
    # Check the Python version.
    logger.debug(f'sys.hexversion: {hex(sys.hexversion)}')
    if sys.hexversion < 0x030D00F0:
        logger.fatal('''😢 Unfortunately your version of Python is too old!

You can download a new version at:  https://www.python.org/downloads/

Then check your version using "python --version" (without quotes). The version should be 3.13 or more.''')
    logger.info('Passed Python version check')

    uprint('''👋 Welcome!

This script will install and setup VSCode (the recommended IDE).

Before we get started, let's confirm the directory for the VSCode workspace.
This will be the directory where you want to create code for the class.
''')
    path = os.getcwd()
    if yes:
        uprint('🗒️ Check skipped due to -y/--yes')
    else:
        if not query_yes_no(f'We will set up a VSCode workspace in: {path}.\n\nIs that what you want?'):
            uprint(
                '''Ok, change the current directory to where you want. Bye for now! 👋''')
            return

    if not maybe_install_vscode():
        uprint('''❌ Failed to install VSCode!

If you're curious, you can get more details about what happened script by adding --log=DEBUG after the script.
Let us know what you found out as it is not expected.

Alternatively, you can install it manually from: https://code.visualstudio.com/download''')
        return
    uprint('✅ Installed VScode, adding some extension')

    extensions = AUTOINSTALLED_VSCODE_EXTENSIONS
    if not yes:
        formatter = query_auto_formatter()
        logger.debug(f'Chosen formatter: {formatter}')
        if formatter:
            extensions.append(formatter)
        # TODO: Include some extra settings for the auto formatter.

    if not maybe_install_vscode_extensions(extensions):
        uprint('''❌ Failed to install VSCode extensions

If you're curious, you can get more details about what happened script by adding --log=DEBUG after the script.
Let us know what you found out as it is not expected.''')
        return
    uprint('✅ Installed VScode extensions, writing to settings.json')

    setup_vscode_settings(path)

    uprint('''✅ All done 🌟🌟🌟

Next steps:
- Create a Python file in VSCode and run it to confirm that everything works.
- Make VSCode your own by installing a theme from https://vscodethemes.com
- Setup GitHub Copilot: https://code.visualstudio.com/docs/copilot/setup

Make sure to check your first unit's IDE tab for more tips''')


parser = argparse.ArgumentParser()
parser.add_argument(
    '-log', '--log', help='Set the logging level (default=WARNING). Options: info|debug|warning|error|critical.')
parser.add_argument(
    '-y', '--yes', help='Answer yes to all questions. Useful for automated testing.', action='store_true')

args = parser.parse_args()
log_level = args.log
yes: bool = args.yes
logging.basicConfig(level=log_level)
logger = logging.getLogger('setup.py')
logger.debug(f'Log level set to: {log_level}')

if __name__ == '__main__':
    install_all()
