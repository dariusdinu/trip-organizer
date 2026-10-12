from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.database.session import get_session
from backend.app.models import Category, Destination
from backend.app.schemas import NameRead

router = APIRouter()


@router.get("/destinations", response_model=list[NameRead])
def list_destinations(session: Session = Depends(get_session)) -> list[Destination]:
    return list(session.scalars(select(Destination).order_by(Destination.name)))


@router.get("/categories", response_model=list[NameRead])
def list_categories(session: Session = Depends(get_session)) -> list[Category]:
    return list(session.scalars(select(Category).order_by(Category.name)))
