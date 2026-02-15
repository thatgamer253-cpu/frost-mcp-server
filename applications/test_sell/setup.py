from setuptools import setup, find_packages

setup(
    name='YourAppName',
    version='1.0.0',
    description='A comprehensive application with robust features and a modern interface.',
    author='Your Name',
    author_email='contact@yourdomain.com',
    url='https://yourappdomain.com',
    packages=find_packages(exclude=['tests*']),
    install_requires=[
        'PyQt5==5.15.7',
        'requests==2.31.0',
        'psutil==5.9.5',
        'logging==0.5.1.2',
        'typing-extensions==4.5.0',
        'pytest==7.4.0',
        'pytest-mock==3.10.0',
        'python-dotenv==1.0.0',
        'selenium==4.10.0',
        'pandas==2.1.1',
        'numpy==1.25.2',
        'matplotlib==3.8.0',
        'pydantic==2.1.1',
        'pydantic-settings==2.1.1',
        'fastapi==0.95.2',
        'moviepy==2.0.0'
    ],
    entry_points={
        'console_scripts': [
            'yourapp=app:main',
        ],
    },
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Programming Language :: Python :: 3.11',
    ],
    python_requires='>=3.8',
    include_package_data=True,
    package_data={
        '': ['*.txt', '*.md'],
        'ui': ['*.ui'],
    },
    license='MIT',
    keywords='application, PyQt5, automation, data processing',
    project_urls={
        'Documentation': 'https://yourappdomain.com/docs',
        'Source': 'https://github.com/yourusername/yourapp',
        'Tracker': 'https://github.com/yourusername/yourapp/issues',
    },
)