import setuptools

try:
    with open("README.md", "r") as readmeFile:
        longDescription = readmeFile.read()
except:
    longDescription = "Tools to access CHADO databases"

setuptools.setup(
    name="chado-tools",
    version="0.0.4",
    author="Christoph Puethe",
    author_email="path-help@sanger.ac.uk",
    description="Tools to access CHADO databases",
    long_description=longDescription,
    url="https://github.com/sanger-pathogens/chado-tools/",
    packages=setuptools.find_packages(),
    package_data={"pychado": ["data/*.yml"]},
    entry_points={
        "console_scripts": [
            "chado = scripts.chado_tools:main",
        ],
    },
    test_suite="nose.collector",
    tests_require=[
        "nose >= 1.3"
    ],
    install_requires=[
        'psycopg2',
        'pyyaml'
    ],
    license="GPLv3",
    classifiers=[
        "Programming Language :: Python :: 3 :: Only",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "Development Status :: 2 - Pre-Alpha"
    ]
)
