from setuptools import setup, find_packages

setup(
    name="botlab",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "python-telegram-bot>=20.0",
        "aiohttp>=3.8.0",
        "python-dotenv>=0.19.0",
        "pytest>=7.0.0",
        "pytest-asyncio>=0.18.0",
        "pytest-cov>=3.0.0"
    ],
    author="Allen Day",
    author_email="allenday@gmail.com",
    description="A Telegram bot framework for experimenting with LLM agents",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/allenday/botlab",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
) 