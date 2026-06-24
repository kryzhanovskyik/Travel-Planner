from datetime import date, datetime
from typing import Generic, List, Optional, TypeVar
from pydantic import BaseModel, ConfigDict, Field


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    skip: int
    limit: int


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=30)

class LoginRequest(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str

    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class NoteCreate(BaseModel):
    text: str = Field(..., min_length=1)
    
class NoteUpdate(BaseModel):
    text: str = Field(..., min_length=1)

class NoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    place_id: int
    text: str
    created_at: datetime
    updated_at: datetime


class PlaceCreate(BaseModel):
    external_id: int = Field(..., gt=0, description="Artwork ID from the Art Institute of Chicago API")

class PlaceUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=512)

class PlaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    external_id: int
    title: str
    is_visited: bool
    notes: List[NoteResponse] = []


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    start_date: Optional[date] = None
    places: List[PlaceCreate] = Field(
        default=[],
        max_length=10,
        description="Optional list of artworks to attach on creation (max 10)",
    )

class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    start_date: Optional[date] = None

class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: Optional[str] = None
    start_date: Optional[date] = None
    is_completed: bool
    places: List[PlaceResponse] = []