from setuptools import setup

setup(
    name="tplt",
    version="0.0.1",
    py_modules=["tplt"],
    entry_points={"console_scripts": ["tplt=tplt:main"]},
)
