"""
py2app setup script for Reviewinator.
"""

from setuptools import setup

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
        'CFBundleVersion': '0.1.0',
        'CFBundleShortVersionString': '0.1.0',
        'LSUIElement': True,  # Run as menu bar app (no dock icon)
        'NSHighResolutionCapable': True,
    }
}

setup(
    name='Reviewinator',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
