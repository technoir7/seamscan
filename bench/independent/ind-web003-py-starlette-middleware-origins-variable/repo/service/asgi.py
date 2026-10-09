from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.routing import Route
from starlette.responses import JSONResponse

ORIGINS = ["*"]


async def me(request):
    return JSONResponse({"user": request.cookies.get("sid")})


app = Starlette(
    routes=[Route("/me", me)],
    middleware=[
        Middleware(CORSMiddleware, allow_origins=ORIGINS, allow_credentials=True),
    ],
)
