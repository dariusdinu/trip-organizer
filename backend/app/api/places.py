from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from backend.app.database.session import get_session
from backend.app.models import Place
from backend.app.schemas import PlaceRead

router = APIRouter()


def serialize_place(place: Place) -> PlaceRead:
    return PlaceRead(
        id=place.id,
        name=place.name,
        destination=place.destination.name if place.destination else None,
        category=place.category.name if place.category else None,
        address=place.address,
        url=place.url,
        latitude=place.latitude,
        longitude=place.longitude,
        note=place.note,
    )


@router.get("/places", response_model=list[PlaceRead])
def list_places(
    destination_id: int | None = Query(default=None, ge=1),
    category_id: int | None = Query(default=None, ge=1),
    session: Session = Depends(get_session),
) -> list[PlaceRead]:
    statement = select(Place).options(joinedload(Place.destination), joinedload(Place.category))
    if destination_id is not None:
        statement = statement.where(Place.destination_id == destination_id)
    if category_id is not None:
        statement = statement.where(Place.category_id == category_id)
    places = session.scalars(statement.order_by(Place.name)).all()
    return [serialize_place(place) for place in places]


@router.get("/places/{place_id}", response_model=PlaceRead)
def get_place(place_id: int, session: Session = Depends(get_session)) -> PlaceRead:
    statement = (
        select(Place)
        .options(joinedload(Place.destination), joinedload(Place.category))
        .where(Place.id == place_id)
    )
    place = session.scalar(statement)
    if place is None:
        raise HTTPException(status_code=404, detail="Place not found")
    return serialize_place(place)
