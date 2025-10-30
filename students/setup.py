#!/usr/bin/env python3

'''
Script to setup new students' machine for
the Technical Interview Preparation classes, both 101 & 102.

The script will:
* Install the latest version of VSCode (if not installed)
* Install the recommended extensions (when not installed)
# TODO: Add some logic to chooose auto-formatter (autopep8 or black)
# TODO: Add some logic for setting .vscode/settings.json (merge with existing)
'''
import logging
import json
import platform
import shutil
import subprocess
import tempfile
import urllib.request
import sys

logger = logging.getLogger(__name__)


# The list should be the full extension name in the MarketPlace:
# https://marketplace.visualstudio.com/
# You can find the full name in the URL and the command to install an individual extension.
COMMON_VSCODE_EXTENSIONS = ['ms-python.python']


def vscode_download_url(version: str) -> str:
    logger.debug(f'Running on platform: {platform.system()}')
    match platform.system():
        case 'Linux':
            # TODO: This logic is pretty brittle.
            info = platform.freedesktop_os_release()
            id = info["ID"]
            logger.debug('Detected a Linux instance, with id={id}')
            match id:
                # Deb-based distributions.
                case 'ubuntu' | 'debian':
                    return 'https://update.code.visualstudio.com/{version}/linux-deb-x64/stable'
                # Rpm-based distributions.
                case 'rhel' | 'fedora':
                    return 'https://update.code.visualstudio.com/{version}/linux-rpm-x64/stable'
                case _:
                    logger.fatal(
                        'Unhandled Linux version {id}. We only support DEB or RPM based distributions.\nIf that matches your distribution, let us know so we can fix it.')
                    return ''
        case 'Darwin':
            return f'https://update.code.visualstudio.com/{version}/darwin-universal/stable'
        case 'Windows':
            return f'https://update.code.visualstudio.com/{version}/win32-x64-user/stable'
        case _:
            logger.fatal(f'Unsupported platform {platform.system()}')
            return ''


def vscode_cmd() -> str | None:
    return shutil.which('code')


def maybe_install_vscode() -> bool:
    '''
        This function may install VSCode unless it exists on the system.

        Returns False if it encounters an error.
        Returns True if VScode is present on the system, either already installed or newly installed.
    '''
    if vscode_cmd() is not None:
        print('Found a VSCode installation, skipping installation... 🌟')
        return True

    content = urllib.request.urlopen(
        'https://update.code.visualstudio.com/api/releases/stable').read()
    if not content:
        logger.error('Got an empty payload instead of vscode binary')
        return False

    versions = json.loads(content)
    if not isinstance(versions, list):
        logger.fatal(
            'Parsing latest VSCode version failed. Please let us know!')

    if not isinstance(versions[0], str):
        logger.fatal(
            'Parsing latest VSCode version failed. Please let us know!')

    with tempfile.TemporaryFile() as fp:
        url = vscode_download_url(versions[0])  # type: ignore
        content = urllib.request.urlopen(url).read()
        if not content:
            logger.error('Got an empty payload instead of vscode binary')
            return False
        fp.write(content)
        output = subprocess.run(fp.name)
        return output.returncode == 0


def get_existing_vscode_extensions() -> set[str]:
    output = subprocess.run(['code', '--list-extensions'],
                            capture_output=True, encoding='utf8')
    if output.returncode != 0:
        logger.fatal(
            'Could not list VSCode extension: returnCode={output.returnCode}, stdout={output.stdout}, stderr={output.stderr}')
    return set(output.stdout.split('\n'))


def install_extension(ext: str) -> bool:
    output = subprocess.run(['code', '--install-extension', ext])
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


def install_all() -> None:
    # Check the Python version.
    logger.debug(f"sys.hexversion: {hex(sys.hexversion)}")
    if sys.hexversion < 0x030D00F0:
        logger.fatal('The version of Python is too old, make sure you have a version >= 3.13.\n\nYou can download a new version at:  https://www.python.org/downloads/\n\nThen check your version using: python --version')

    logger.info("Passed Python version check")
    if not maybe_install_vscode():
        print('Failed to install VSCode, let us know what happened so we can fix this script!\n\nYou can install to install it manually from: https://code.visualstudio.com/download')
    if not maybe_install_vscode_extensions():
        print('Failed to install VSCode extensions, let us know what happened so we can fix this script!\n\nYou can install to install it manually from: https://code.visualstudio.com/download')
    print('All done 🌟🌟🌟')


if __name__ == '__main__':
    install_all()
