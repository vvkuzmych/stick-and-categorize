"""py2app build of the menu-bar app. Build (from mac/packaging): ../.venv/bin/python setup.py py2app"""
from setuptools import setup

setup(
    app=["run_stick.py"],
    options={
        "py2app": {
            "plist": {
                "CFBundleName": "Stick",
                "CFBundleIdentifier": "dev.stick.app",
                "NSMicrophoneUsageDescription": "Stick records your voice notes.",
                "LSUIElement": True,
            },
            "packages": ["stick", "AVFoundation"],
        }
    },
    setup_requires=["py2app"],
)
