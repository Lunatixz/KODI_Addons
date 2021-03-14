pySSD
=====

Tiny little Solid-State Drive checker for Python.

Working on Windows, macOS and Linux.


Table of contents
-----------------

- [Status](#status)
- [Installation](#installation)
- [Usage](#usage)


Status
------

[![Travis Build Status](https://travis-ci.org/vuolter/pySSD.svg?branch=master)](https://travis-ci.org/vuolter/pySSD)
[![Requirements Status](https://requires.io/github/vuolter/pySSD/requirements.svg?branch=master)](https://requires.io/github/vuolter/pySSD/requirements/?branch=master)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/6ee47c32da944cbcac211ac3ac4ddff2)](https://www.codacy.com/app/vuolter/pySSD?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=vuolter/pySSD&amp;utm_campaign=Badge_Grade)
[![Scrutinizer Code Quality](https://scrutinizer-ci.com/g/vuolter/pySSD/badges/quality-score.png?b=master)](https://scrutinizer-ci.com/g/vuolter/pySSD/?branch=master)

[![PyPI Status](https://img.shields.io/pypi/status/ssd.svg)](https://pypi.python.org/pypi/ssd)
[![PyPI Version](https://img.shields.io/pypi/v/ssd.svg)](https://pypi.python.org/pypi/ssd)
[![PyPI Python Versions](https://img.shields.io/pypi/pyversions/ssd.svg)](https://pypi.python.org/pypi/ssd)
[![PyPI License](https://img.shields.io/pypi/l/ssd.svg)](https://pypi.python.org/pypi/ssd)


Installation
------------

Type in your command shell **with _administrator/root_ privileges**:

    pip install ssd

In Unix-based systems, this is generally achieved by superseding
the command `sudo`.

    sudo pip install ssd

If the above commands fail, consider installing it with the option
[`--user`](https://pip.pypa.io/en/latest/user_guide/#user-installs):

    pip install --user ssd

If the command `pip` is not found in your system, but you have the
[Python Interpreter](https://www.python.org) and the package `setuptools`
(>=20.8.1) installed, you can try to install it from the sources, in this way:

1. Get the latest tarball of the source code in format
[ZIP](https://github.com/vuolter/pySSD/archive/master.zip) or
[TAR](https://github.com/vuolter/pySSD/archive/master.tar.gz).
2. Extract the downloaded archive.
3. From the extracted path, launch the command
`python setup.py install`.


Usage
-----

Import in your script the module `sdd` and call its function `is_ssd`.

    from ssd import is_ssd

    is_ssd('/path/to/file-or-dir-or-dev')

Return value will be `True` if the drive, where the given path is located, was
recognized as SSD, otherwise `False`.

> **Note:** Ramdisks are always recognized as SSD under Windows.

_That's All Folks!_


------------------------------------------------
###### © 2017 Walter Purcaro <vuolter@gmail.com>
