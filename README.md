# Quicksilver

[![Version](https://img.shields.io/badge/version-v1.0.0-blue)](https://github.com/yourusername/quicksilver/releases)
[![Python](https://img.shields.io/badge/python-3.12.6+-green)](https://github.com/yourusername/quicksilver/blob/main/requirements.txt)
[![Python](https://img.shields.io/badge/platform-windows-lightgrey)](https://en.wikipedia.org/wiki/Windows_NT)
[![License](https://img.shields.io/badge/license-MIT-blue)](https://github.com/yourusername/quicksilver/blob/main/LICENSE.md)

## Introduction
A scalable, easy-to-use, lightweight file transfer & detection system that uses both bluetooth and WLAN. Currently supports windows.

## Getting Started
### REQUIREMENTS
If you are installing the pre-packaged EXE version of Quicksilver, the only installation you would have to complete is that of a 64 bit version of Python 3.12.6 or higher. It is recommended to add it to path during the installation process.

If you planning to clone the source code and make your own modifications, be sure to run in your shell or terminal:
```
cd C:/full/cloned/repo/path
pip install -r requirements.txt
```
So the appropriate python packages would be available for your scripts to run. You can also check requirements.txt in the root directory for a list of all necessary packages.

### USER MANUAL
TBD

## Issue Tracker
- The IP broadcast function is raw and has issues regarding platform detection (currently non-existent) and IP validation. This will be fixed after the main app has been developed.
- PyBluez2 has known compatibility issues with Python 3.10.X and above, so the version used is an unofficial community version stored on GitHub. As of today, this version is available. In the case that it is no longer available, please replace line 1 in requirements.txt with PyBluez2, and, if possible, also open a PR with the change so everyone else can enjoy the functional scripted version of this project.
- The bluetooth sending & receiving pair is largely untested due to resource constraints. If any issues are found with preliminary testing, please let me know as soon as possible.