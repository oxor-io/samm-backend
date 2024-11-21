from fastapi import FastAPI

import api.conf
from api.db import init_db
from api.router import router as api_router
from api.token.router import router as token_router

app = FastAPI()
app.include_router(api_router)
app.include_router(token_router)


@app.on_event('startup')
async def on_startup():
    await init_db()

