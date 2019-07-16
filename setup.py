import os

from setuptools import find_packages, setup

version = '0.1.0'

setup(
    name='gitops',
    version=version,
    author='Uptick',
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
