"""
Allow running the package as a module with python -m src
"""

from .main import main
import asyncio

if __name__ == '__main__':
    asyncio.run(main())