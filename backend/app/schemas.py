from pydantic import BaseModel, ConfigDict


class NameRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class PlaceRead(BaseModel):
    id: int
    name: str
    destination: str | None
    category: str | None
    address: str | None
    url: str | None
    latitude: float | None
    longitude: float | None
    note: str | None
