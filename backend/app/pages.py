"""Jinja2 화면 경로와 로그인 상태에 따른 접근 제어."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.auth import get_session_user
from app.config import APP_DIR
from app.models.user import User

router = APIRouter()
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))


@router.get("/", include_in_schema=False)
def index():
    return RedirectResponse(url="/login", status_code=307)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, user: Annotated[User | None, Depends(get_session_user)]):
    if user is not None:
        return RedirectResponse(url="/chat", status_code=303)
    return templates.TemplateResponse(request=request, name="login.html")


@router.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request, user: Annotated[User | None, Depends(get_session_user)]):
    if user is not None:
        return RedirectResponse(url="/chat", status_code=303)
    return templates.TemplateResponse(request=request, name="signup.html")


@router.get("/chat", response_class=HTMLResponse)
def chat_page(request: Request, user: Annotated[User | None, Depends(get_session_user)]):
    if user is None:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(
        request=request, name="chat.html", context={"user": user}, headers={"Cache-Control": "no-store"}
    )


@router.get("/history", response_class=HTMLResponse)
def history_page(request: Request, user: Annotated[User | None, Depends(get_session_user)]):
    if user is None:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse(
        request=request, name="history.html", context={"user": user}, headers={"Cache-Control": "no-store"}
    )
