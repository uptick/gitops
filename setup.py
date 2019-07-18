import codecs
import os
import re

from setuptools import find_packages, setup

here = os.path.abspath(os.path.dirname(__file__))


def read(*parts):
    return codecs.open(os.path.join(here, *parts), 'r').read()


def find_version(*file_paths):
    version_file = read(*file_paths)
    version_match = re.search(
        r"^__version__ = ['\"]([^'\"]*)['\"]",
        version_file, re.M
    )
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


setup(
    name='gitops',
    version=find_version('gitops', '__init__.py'),
    author='Uptick',
    url='https://gitlab.org/uptick/gitops.git',
    description='',
    long_description=read('README.md'),
    long_description_content_type='text/markdown',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    license='BSD',
    packages=find_packages(),
    include_package_data=True,
    package_data={'gitops': ['*.txt', '*.js', '*.html', '*.*']},
    install_requires=[
        'tabulate',
        'boto3',
        'boto',
        'invoke',
        'humanize',
    ],
    entry_points={
        'console_scripts': [
            'gitops=gitops.main:program.run'
        ]
    },
    zip_safe=False
)
