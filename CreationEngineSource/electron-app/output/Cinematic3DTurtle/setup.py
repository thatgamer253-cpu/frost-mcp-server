from setuptools import setup, find_packages

setup(
    name='3D_Turtle_Studio',
    version='1.0.0',
    description='A 3D Turtle Graphics Studio',
    author='Your Name',
    author_email='your.email@example.com',
    url='https://yourprojecturl.com',
    packages=find_packages(),
    install_requires=[
        'PyQt5>=5.15.0',
    ],
    entry_points={
        'console_scripts': [
            '3d_turtle_studio=main:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
    include_package_data=True,
)