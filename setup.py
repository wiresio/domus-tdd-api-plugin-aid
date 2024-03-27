#!/usr/bin/env python
from setuptools import setup, find_packages


from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()

setup(
    name="domus-tdd-api-plugin-aid",
    version="1.0.0",
    description="A TDD-API Plugin to add AID related routes",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Siemens & Logilab",
    maintainer="Christian Glomb",
    maintainer_email="christian.glomb@siemens.com",
    url="https://github.com/wiresio/domus-tdd-api-plugin-aid",
    keywords=[
        "web of things",
        "thing description directory",
        "wot",
        "tdd",
        "asset interfaces description",
    ],
    classifiers=["Programming Language :: Python", "Framework :: Flask"],
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
            "aas=domus_tdd_api_plugin_aid:blueprint",
        ],
        "tdd_api.plugins.transformers": [
            "aas=domus_tdd_api_plugin_aid.aas:td_to_aas",
        ],
    },
)
