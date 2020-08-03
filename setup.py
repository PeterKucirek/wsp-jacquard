from os import path
from pkg_resources import safe_version
from setuptools import setup, find_packages

version = {}
with open(path.join(path.dirname(path.realpath(__file__)), 'jacquard', 'version.py')) as fp:
    exec(fp.read(), {}, version)
version_string = safe_version(version['__version__'])

setup(
    name='wsp-jacquard',
    version=version_string,
    description='JSON-based configuration handler for models',
    url='https://github.com/wsp-sag/wsp-jacquard',
    author='WSP',
    maintatiner='Brian Cheung',
    maintainer_email='brian.cheung@wsp.com',
    classifiers=[
        'License :: OSI Approved :: MIT License'
    ],
    packages=find_packages(),
    install_requires=[
        'six>=1.10'
    ],
    python_requires='>=2.7'
)
