import asyncio
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src import models, schemas
from src.auth import get_current_user
from src.database import get_db
from src.dependencies import get_project_or_404
from src.services.chicago_api import validate_artwork


router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=schemas.ProjectResponse, status_code=201)
async def create_project(
    body: schemas.ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.Project:
    place_inputs = body.places

    external_ids = [p.external_id for p in place_inputs]
    if len(external_ids) != len(set(external_ids)):
        raise HTTPException(status_code=400, detail="Duplicate external_id values in the places list")

    if place_inputs:
        artworks = await asyncio.gather(*[validate_artwork(p.external_id) for p in place_inputs])
        missing = [place_inputs[i].external_id for i, aw in enumerate(artworks) if aw is None]
        if missing:
            raise HTTPException(
                status_code=422,
                detail=f"Artworks not found in Chicago API: {missing}",
            )
    else:
        artworks = []

    project = models.Project(owner_id=current_user.id, **body.model_dump(exclude={"places"}))
    db.add(project)
    await db.flush()

    for place_in, artwork in zip(place_inputs, artworks):
        db.add(models.Place(
            project_id=project.id,
            external_id=place_in.external_id,
            title=artwork.get("title") or "Untitled",
            is_visited=False,
        ))

    await db.commit()
    return await get_project_or_404(project.id, current_user.id, db)


@router.get("", response_model=schemas.PaginatedResponse[schemas.ProjectResponse])
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    is_completed: Optional[bool] = Query(None, description="Filter by completion status"),
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> dict:
    filters = [models.Project.owner_id == current_user.id]
    if is_completed is not None:
        filters.append(models.Project.is_completed == is_completed)

    total = (await db.execute(select(func.count(models.Project.id)).where(*filters))).scalar_one()

    rows = await db.execute(
        select(models.Project)
        .options(selectinload(models.Project.places).selectinload(models.Place.notes))
        .where(*filters)
        .offset(skip)
        .limit(limit)
        .order_by(models.Project.id)
    )
    return {"items": rows.scalars().all(), "total": total, "skip": skip, "limit": limit}


@router.get("/{project_id}", response_model=schemas.ProjectResponse)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.Project:
    return await get_project_or_404(project_id, current_user.id, db)


@router.patch("/{project_id}", response_model=schemas.ProjectResponse)
async def update_project(
    project_id: int,
    body: schemas.ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> models.Project:
    project = await get_project_or_404(project_id, current_user.id, db)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(project, field, value)

    await db.commit()
    return await get_project_or_404(project_id, current_user.id, db)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
) -> None:
    project = await get_project_or_404(project_id, current_user.id, db)

    if any(p.is_visited for p in project.places):
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a project that has visited places",
        )

    await db.delete(project)
    await db.commit()
