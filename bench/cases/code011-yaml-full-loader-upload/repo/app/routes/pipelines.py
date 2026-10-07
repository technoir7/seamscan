import yaml
from fastapi import APIRouter, UploadFile

router = APIRouter()


@router.post("/pipelines/import")
async def import_pipeline(file: UploadFile):
    raw = await file.read()
    spec = yaml.load(raw, Loader=yaml.FullLoader)
    return {"name": spec.get("name"), "steps": len(spec.get("steps", []))}
