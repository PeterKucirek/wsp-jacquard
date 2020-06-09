from setuptools import setup, find_packages

setup(
    name='wsp-jacquard',
    version='1.0.0',
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
