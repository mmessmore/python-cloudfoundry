#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import find_packages
from distutils.core import setup

setup(
    author=u'Matt Cowger',
    author_email='matt@cowger.us',
    name='python-cloudfoundry2',
    description='Python interface to CloudFoundry v2 API',
    version="0.1",
    url='https://github.com/mcowger/python-cloudfoundry',
    license='MIT License',
    packages = find_packages(),
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries',
        'Topic :: Software Development :: Libraries :: Python Modules',
        ],
    install_requires=[
        open("requirements.txt").readlines(),
    ],
)