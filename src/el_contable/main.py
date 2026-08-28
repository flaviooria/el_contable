from fastapi import FastAPI

from el_contable.features.movements.router import router as movements_router

app = FastAPI()

app.include_router(movements_router)


@app.get("/")
async def read_root():
    return {"Hello": "World"}


@app.get("/health")
async def read_health():
    return {"Status": "OK"}
