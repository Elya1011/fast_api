from typing import Optional, Literal
import pydantic
from pydantic import BaseModel


class IdResponse(BaseModel):
    id: int


class SuccessResponse(BaseModel):
    status: Literal["success"]


class AdvertisementFilter(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None

    @property
    def has_filters(self):
        return any([self.title, self.description, self.price is not None])


class CreateAdvertisementRequest(BaseModel):
    title: str
    description: str
    price: float
    user: str

    @pydantic.field_validator("title")
    @classmethod
    def title_length(cls, v: str) -> str:
        if len(v) > 50:
            raise ValueError(f"Maximal length of title is 50")
        return v


class CreateAdvertisementResponse(IdResponse):
    pass


class UpdateAdvertisement(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None


class GetAdvertisement(BaseModel):
    id: int
    title: str
    description: str
    price: float
    user: str


class SearchAdvResponse(BaseModel):
    results: list[GetAdvertisement]


class DeleteResponse(SuccessResponse):
    pass