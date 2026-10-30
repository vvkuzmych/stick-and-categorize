"""py2app build for the Phase 0 mic spike. Build (from mac/packaging): ../.venv/bin/python setup.py py2app"""
from setuptools import setup

setup(
    app=["../spikes/record_spike.py"],
    options={
        "py2app": {
            "plist": {
                "CFBundleName": "StickSpike",
                "CFBundleIdentifier": "dev.stick.spike",
                "NSMicrophoneUsageDescription": "Stick records your voice notes.",
                "LSUIElement": True,
            },
            "packages": ["AVFoundation"],
        }
    },
    setup_requires=["py2app"],
)
