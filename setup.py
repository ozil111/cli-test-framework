from setuptools import setup, find_packages

setup(
    name="cli-test-framework",
    version="0.1.0",
    author="Xiaotong Wang",
    author_email="xiaotongwang98@gmail.com",
    description="A small command line testing framework in Python.",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        # List your project dependencies here
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)