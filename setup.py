import os

from setuptools import find_packages, setup

version = '0.0.1'

setup(
    name='gitops',
    version=version,
    author='Luke Hodkinson',
    author_email='luke.hodkinson@uptickhq.com',
    maintainer='Luke Hodkinson',
    maintainer_email='luke.hodkinson@uptickhq.com',
    url='https://gitlab.org/uptick/gitops.git',
    description='',
    long_description=open(
        os.path.join(os.path.dirname(__file__), 'README.md')
    ).read(),
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
        'Programming Language :: Python :: 3.5'
    ],
    license='BSD',
    packages=find_packages(),
    include_package_data=True,
    package_data={'': ['*.txt', '*.js', '*.html', '*.*']},
    install_requires=[
        'sanic==0.7.0',
        'asyncio_extras==1.3.2',
        'pyyaml',
        'aiorequests'
    ],
    dependency_links=[
        'git+https://gitlab.com/structrs/aiorequests#egg=aiorequests'
    ],
    entry_points={
        'console_scripts': [
            'gitops=gitops.command_line:entrypoint'
        ]
    },
    zip_safe=False
)
