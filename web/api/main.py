from fastapi import FastAPI

# Load confing and all modules
import api.conf
from api.samm import models
from api.member import models
from api.token import models
from api.txn import models
from api.db import init_db
from api.samm.router import router as samm_router
from api.member.router import router as member_router
from api.token.router import router as token_router
from api.txn.router import router as txn_router

app = FastAPI()
app.include_router(samm_router)
app.include_router(member_router)
app.include_router(token_router)
app.include_router(txn_router)


@app.on_event('startup')
async def on_startup():
    await init_db()
