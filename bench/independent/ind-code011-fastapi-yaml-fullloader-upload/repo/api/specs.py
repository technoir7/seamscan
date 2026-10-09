import yaml
from fastapi import FastAPI, UploadFile

app = FastAPI()


@app.post("/specs")
async def upload_spec(file: UploadFile):
    spec = yaml.load(await file.read(), Loader=yaml.FullLoader)
    return {"keys": list(spec)}
