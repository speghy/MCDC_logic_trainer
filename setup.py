from setuptools import setup, find_packages

setup(
    name="logic_trainer",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[],
    entry_points={
        'console_scripts': [
            'logic-trainer=logic_trainer.main:main',
        ],
    },
)