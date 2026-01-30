from typing import Optional
from pydantic import BaseModel, Field, field_validator
import uuid


class IdResponse(BaseModel):
    id: int


class PaginationInfo(BaseModel):
    total: int
    limit: int
    offset: int
    has_more: bool


class AdvertisementFilter(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    price_min: Optional[float] = Field(gt=0)
    price_max: Optional[float] = Field(gt=0)
    search_mode: str = Field('AND', description='режим поиска: AND или OR')
    limit: int = Field(100, ge=1, le=1000, description='кол-во резутатов')
    offset: int = Field(0, ge=0, description='смещение')

    @property
    def has_filters(self):
        return any([
            self.title is not None,
            self.description is not None,
            self.price_min is not None,
            self.price_max is not None
        ])


class CreateAdvertisementRequest(BaseModel):
    title: str = Field(min_length=1, max_length=50, description='максимум 50 символов')
    description: str
    price: float = Field(gt=0, description='цена должна быть больше 0')
    user: str


class CreateAdvertisementResponse(IdResponse):
    pass


class UpdateAdvertisement(BaseModel):
    title: Optional[str] = Field(max_length=50)
    description: Optional[str] = None
    price: Optional[float] = None
    user: Optional[str] = None

    @field_validator('price')
    @classmethod
    def validate_price(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v <= 0:
            raise ValueError('Цена должна быть положительной')
        return v


class GetAdvertisement(BaseModel):
    id: int
    title: str
    description: str
    price: float
    user: str


class SearchAdvResponse(BaseModel):
    results: list[GetAdvertisement]
    pagination: PaginationInfo


class DeleteResponse(BaseModel):
    None


class BaseUserRequest(BaseModel):
    first_name: str
    last_name: str
    email: str
    password: str


class CreateUserRequest(BaseUserRequest):
    pass


class CreateUserResponse(IdResponse):
    pass


class LoginResponse(BaseModel):
    email: str
    token: uuid.UUID