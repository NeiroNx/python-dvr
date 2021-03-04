from setuptools import setup, find_packages
import pathlib

here = pathlib.Path(__file__).parent.resolve()

# Get the long description from the README file
long_description = (here / 'README.md').read_text(encoding='utf-8')

setup(
    name='python-dvr',

    version='0.0.0',

    description='Python library for configuring a wide range of IP cameras which use the NETsurveillance ActiveX plugin XMeye SDK',

    long_description=long_description,
    long_description_content_type='text/markdown',

    url='https://github.com/NeiroNx/python-dvr/',

    author='NeiroN',

    classifiers=[
        'Development Status :: 3 - Alpha',

        'Intended Audience :: Developers',
        'Topic :: Multimedia :: Video :: Capture',

        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3 :: Only',
    ],

    py_modules=["dvrip","DeviceManager"],

    python_requires='>=3.6, <3.9',

    project_urls={
        'Bug Reports': 'https://github.com/NeiroNx/python-dvr/issues',
        'Source': 'https://github.com/NeiroNx/python-dvr',
    },
)
