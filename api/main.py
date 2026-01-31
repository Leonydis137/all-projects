from fastapi import FastAPI
from api.routes import router

app = FastAPI(title="COVENANT.AI")
app.include_router(router)
