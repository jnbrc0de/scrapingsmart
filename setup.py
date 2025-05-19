from setuptools import setup, find_packages

setup(
    name="scrapingsmart",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi",
        "uvicorn",
        "pydantic",
        "pydantic-settings",
        "python-dotenv",
        "supabase",
        "requests",
        "beautifulsoup4",
        "selenium",
        "playwright",
        "aiohttp",
        "asyncio",
        "python-multipart",
        "websockets",
    ],
    python_requires=">=3.8",
    entry_points={
        'console_scripts': [
            'scrapingsmart=run:main',
        ],
    },
) 