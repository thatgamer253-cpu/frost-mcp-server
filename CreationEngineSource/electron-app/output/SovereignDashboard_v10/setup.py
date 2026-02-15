from setuptools import setup, find_packages

setup(
    name='sovereign-dashboard',
    version='0.1',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'sovereign-dashboard=main:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
    include_package_data=True,
    package_data={
        '': ['icon.svg', 'SovereignSystemDashboard.desktop'],
    },
)