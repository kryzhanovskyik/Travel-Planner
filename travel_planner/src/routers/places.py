from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src import models, schemas
from src.auth import get_current_user
from src.database import get_db
from src.dependencies import get_note_or_404, get_place_or_404, get_project_or_404
from src.services.chicago_api import validate_artwork


router = APIRouter(prefix="/projects", tags=["places & notes"])


MAX_PLACES = 10


async def sync_project_completion(project: models.Project, db: AsyncSession) -> None:
    """Mark project as completed when all its places are visited, or revert if not."""
    if project.places and all(p.is_visited for p in project.places):
        project.is_completed = True
    else:
        project.is_completed = False


@router.post("/{project_id}/places", response_model=schemas.PlaceResponse, status_code=201)
async def add_place(
    project_id: int,
    body: schemas.PlaceCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.Place:
    project = await get_project_or_404(project_id, current_user.id, db)

    if len(project.places) >= MAX_PLACES:
        raise HTTPException(status_code=400, detail="A project can have at most 10 places")

    if any(p.external_id == body.external_id for p in project.places):
        raise HTTPException(status_code=400, detail="This artwork is already in the project")

    artwork = await validate_artwork(body.external_id)
    if artwork is None:
        raise HTTPException(
            status_code=422,
            detail=f"Artwork with id={body.external_id} was not found in the Chicago API",
        )

    place = models.Place(
        project_id=project_id,
        external_id=body.external_id,
        title=artwork.get("title") or "Untitled",
        is_visited=False,
    )
    db.add(place)
    await db.commit()
    await db.refresh(place)
    return place


@router.get("/{project_id}/places", response_model=schemas.PaginatedResponse[schemas.PlaceResponse])
async def list_places(
    project_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    is_visited: Optional[bool] = Query(None, description="Filter by visited status"),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict:
    await get_project_or_404(project_id, current_user.id, db)

    filters = [models.Place.project_id == project_id]
    if is_visited is not None:
        filters.append(models.Place.is_visited == is_visited)

    total = (await db.execute(select(func.count(models.Place.id)).where(*filters))).scalar_one()

    rows = await db.execute(
        select(models.Place)
        .options(selectinload(models.Place.notes))
        .where(*filters)
        .offset(skip)
        .limit(limit)
        .order_by(models.Place.id)
    )
    return {"items": rows.scalars().all(), "total": total, "skip": skip, "limit": limit}

@router.get("/{project_id}/places/{place_id}", response_model=schemas.PlaceResponse)
async def get_place(
    project_id: int,
    place_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.Place:
    await get_project_or_404(project_id, current_user.id, db)
    return await get_place_or_404(project_id, place_id, db)


@router.patch("/{project_id}/places/{place_id}", response_model=schemas.PlaceResponse)
async def update_place(
    project_id: int,
    place_id: int,
    body: schemas.PlaceUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.Place:
    await get_project_or_404(project_id, current_user.id, db)
    place = await get_place_or_404(project_id, place_id, db)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(place, field, value)

    await db.commit()
    await db.refresh(place)
    return place

@router.patch("/{project_id}/places/{place_id}/visit", response_model=schemas.PlaceResponse)
async def mark_place_visited(
    project_id: int,
    place_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.Place:
    project = await get_project_or_404(project_id, current_user.id, db)
    place = await get_place_or_404(project_id, place_id, db)

    place.is_visited = True
    await db.flush()

    project = await get_project_or_404(project_id, current_user.id, db)
    await sync_project_completion(project, db)

    await db.commit()
    await db.refresh(place)
    return place


@router.post(
    "/{project_id}/places/{place_id}/notes",
    response_model=schemas.NoteResponse,
    status_code=201,
)
async def add_note(
    project_id: int,
    place_id: int,
    body: schemas.NoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.Note:
    await get_project_or_404(project_id, current_user.id, db)
    await get_place_or_404(project_id, place_id, db)

    note = models.Note(place_id=place_id, text=body.text)
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


@router.get(
    "/{project_id}/places/{place_id}/notes/{note_id}",
    response_model=schemas.NoteResponse,
)
async def get_note(
    project_id: int,
    place_id: int,
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.Note:
    await get_project_or_404(project_id, current_user.id, db)
    await get_place_or_404(project_id, place_id, db)
    return await get_note_or_404(place_id, note_id, db)


@router.delete(
    "/{project_id}/places/{place_id}/notes/{note_id}",
    status_code=204,
)
async def delete_note(
    project_id: int,
    place_id: int,
    note_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> None:
    await get_project_or_404(project_id, current_user.id, db)
    await get_place_or_404(project_id, place_id, db)
    note = await get_note_or_404(place_id, note_id, db)
    await db.delete(note)
    await db.commit()


@router.patch(
    "/{project_id}/places/{place_id}/notes/{note_id}",
    response_model=schemas.NoteResponse,
)
async def update_note(
    project_id: int,
    place_id: int,
    note_id: int,
    body: schemas.NoteUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.Note:
    await get_project_or_404(project_id, current_user.id, db)
    await get_place_or_404(project_id, place_id, db)
    note = await get_note_or_404(place_id, note_id, db)

    note.text = body.text
    note.updated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(note)
    return note
