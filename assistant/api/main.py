"""ASGI entrypoint: uvicorn assistant.api.main:app"""

from assistant.api.app import create_app

app = create_app()
