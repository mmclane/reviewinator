"""
py2app setup script for Reviewinator.
"""

from setuptools import setup
import tomli

# Read version from pyproject.toml
with open("pyproject.toml", "rb") as f:
    version = tomli.load(f)["project"]["version"]

APP = ['src/reviewinator/app.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'packages': ['rumps', 'github', 'pync', 'yaml', 'certifi'],
    'includes': ['reviewinator'],
    'plist': {
        'CFBundleName': 'Reviewinator',
        'CFBundleDisplayName': 'Reviewinator',
        'CFBundleIdentifier': 'com.reviewinator.app',
        'CFBundleVersion': version,
        'CFBundleShortVersionString': version,
        'LSUIElement': True,  # Run as menu bar app (no dock icon)
        'NSHighResolutionCapable': True,
    }
}

setup(
    name='Reviewinator',
    version=version,
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
)
