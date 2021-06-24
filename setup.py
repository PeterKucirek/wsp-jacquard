from setuptools import setup, find_packages

import versioneer

setup(
    name='wsp-jacquard',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    description='JSON-based configuration handler for models',
    url='https://github.com/wsp-sag/wsp-jacquard',
    author='WSP',
    maintainer='Brian Cheung',
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
