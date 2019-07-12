#!/usr/bin/env python3

import setuptools
import os

try:
    with open(os.path.dirname(os.path.abspath(__file__)) + "/README.md") as readme_file:
        long_description = readme_file.read()
except FileNotFoundError or FileExistsError:
    long_description = "Tools to access CHADO databases. For a detailed description visit the GitHub repository."

setuptools.setup(
    name="chado-tools",
    version="0.2.13",
    author="Christoph Puethe",
    author_email="path-help@sanger.ac.uk",
    description="Tools to access CHADO databases",
    long_description_content_type="text/markdown",
    long_description=long_description,
    url="https://github.com/sanger-pathogens/chado-tools/",
    packages=setuptools.find_packages(),
    package_data={
        "pychado": [
            "data/*.yml",
            "sql/*.sql"
        ],
        "pychado.tests": [
            "data/*"
        ]
    },
    entry_points={
        "console_scripts": [
            "chado = pychado.chado_tools:main",
        ]
    },
    test_suite="nose.collector",
    tests_require=[
        "nose >= 1.3"
    ],
    install_requires=[
        "sqlalchemy >= 1.3.3",
        "sqlalchemy-utils >= 0.34.0",
        "psycopg2 >= 2.7.6",
        "pyyaml >= 5.1",
        "pronto >= 0.11.0",
        "gffutils >= 0.9",
        "biopython >= 1.73"
    ],
    license="GPLv3",
    classifiers=[
        "Programming Language :: Python :: 3 :: Only",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "Development Status :: 3 - Alpha"
    ]
)
