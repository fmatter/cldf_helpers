import setuptools

setuptools.setup(
    name="cldf_helpers",
    version="0.0.1",
    author="Florian Matter",
    author_email="florianmatter@gmail.com",
    description="An eclectic collection of functions in some related to a CLDF workflow",
    url="https://github.com/fmatter/cldf_helpers",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    install_requires=[
    "cldfbench",
    "pycldf",
    "pyperclip",
    "pyglottolog"
    ],
    entry_points = {
        'console_scripts': ['cldfhtex=cldf_helpers.cldfhtex:main'],
    },
    python_requires='>=3.6',
)
