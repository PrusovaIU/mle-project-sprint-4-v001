from uvicorn import run
from app.app import app


if __name__ == '__main__':
    run(app, port=8080)
