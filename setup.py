from setuptools import setup, find_packages

setup(
    name="bookinfo",
    version="0.1.0",
    description="Extract book metadata from PDF/EPUB files using Google Books API.",
    author="Your Name",
    author_email="your.email@example.com",
    url="https://github.com/yourusername/bookinfo",
    packages=find_packages(),
    install_requires=[
        "pypdf==5.5.0",
        "pdfplumber>=0.10.0",
        "ebooklib>=0.18",
        "google-api-python-client>=2.0.0",
        "requests>=2.0.0",
        "tenacity>=8.0.0",
    ],
    python_requires=">=3.7",
    entry_points={"console_scripts": ["bookinfo=bookinfo.cli:main"]},
    license="MIT",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    include_package_data=True,
)
