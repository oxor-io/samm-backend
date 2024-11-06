from fastapi import FastAPI

from api.db import init_db
from api.router import router

app = FastAPI()
app.include_router(router)


@app.on_event('startup')
async def on_startup():
    await init_db()


@app.get('/ping')
async def pong():
    return {'ping': 'pong!'}
