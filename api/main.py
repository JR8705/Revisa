from fastapi import FastAPI

app = FastAPI()


@app.get('/')
async def root():
    return {"message": "Hello World"}

@app.get('/veiculos/{veiculo_id}')
async def get_veiculo(veiculo_id: int):
    return {'veiculo_id': veiculo_id}