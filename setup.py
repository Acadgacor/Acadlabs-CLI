from setuptools import setup, find_packages

setup(
    name='Acadlabs-CLI',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        "typer",
        "rich",
        "httpx",
    ],
    entry_points={
        'console_scripts': [
            'acadlabs-cli=acadlabs_cli.main:app',
        ],
    },
)