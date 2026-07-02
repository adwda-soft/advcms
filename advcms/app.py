
import sys
import os

from starlette.applications import Starlette
from starlette.authentication import AuthCredentials, AuthenticationBackend, BaseUser

from starlette.middleware import Middleware
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from advcms.routes import app_routes
from advcms.settings import app_settings

class AuthenticatedUser(BaseUser):
    def __init__(self, user_id: int, username: str):
        self.id = user_id
        self.username = username

    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def display_name(self) -> str:
        return self.username

class SessionAuthBackend(AuthenticationBackend):
    async def authenticate(self, conn):
        if "user" not in conn.session:
            return

        session_user = conn.session["user"]
        return AuthCredentials(["authenticated"]), AuthenticatedUser(
            user_id=session_user["id"], username=session_user["username"]
        )

middleware = [
    Middleware(SessionMiddleware, secret_key=app_settings.WEBSERVER_SECRET_KEY),
    Middleware(AuthenticationMiddleware, backend=SessionAuthBackend()),
    Middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]),
]

app = Starlette(debug=app_settings.WEBSERVER_DEBUG, routes=app_routes, middleware=middleware)

