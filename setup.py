#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name="TDD API plugin AAS",
    version="1.0",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        "tdd-api",
    ],
    extras_require={
        "dev": [
            "pytest",
            "mock",
        ]
    },
    entry_points={
        "tdd_api.plugins.blueprints": [
            "aas=tdd_api_plugin_aas:blueprint",
        ],
        "tdd_api.plugins.transformers": [
            "aas=tdd_api_plugin_aas.aas:td_to_aas",
        ],
    },
)
