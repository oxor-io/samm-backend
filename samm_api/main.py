from fastapi import FastAPI

from samm_api.db import init_db
from samm_api.router import router

app = FastAPI()
app.include_router(router)


@app.on_event('startup')
def on_startup():
    init_db()


@app.get('/ping')
async def pong():
    return {'ping': 'pong!'}
