import uuid
from datetime import date
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse

from el_contable.features.movements.parser import ParserError
from el_contable.features.movements.schemas import (
    MovementTotalsResponse,
    PeriodSummaryResponse,
    UploadError,
    UploadResponse,
)
from el_contable.features.movements.service import (
    MovementsService,
    get_movements_service,
)

router = APIRouter(prefix="/api/v1/movements", tags=["movements"])


@router.get(
    "/template",
    response_class=FileResponse,
    summary="Download movements template",
)
async def download_template() -> FileResponse:
    template_path = Path("src/el_contable/templates/plantilla_movimientos.xlsx")

    if not template_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template file not found",
        )

    return FileResponse(
        path=template_path,
        filename="plantilla_movimientos.xlsx",
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


ALLOWED_EXTENSIONS = {".xlsx", ".csv"}


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": UploadError, "description": "Invalid file or parsing error"},
        415: {"model": UploadError, "description": "Unsupported file type"},
    },
    summary="Upload movements file",
)
async def upload_movements(
    file: Annotated[UploadFile, File(description="Excel or CSV file with movements")],
    account_id: Annotated[uuid.UUID, Query(description="Account ID for this upload")],
    service: Annotated[MovementsService, Depends(get_movements_service)],
) -> UploadResponse:
    filename = file.filename or ""

    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    try:
        contents = await file.read()
        return service.upload(file_content=contents, filename=filename)
    except ParserError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e


@router.get(
    "/totals",
    response_model=MovementTotalsResponse,
    summary="Get movement totals by type for an account",
    responses={
        404: {"description": "Account not found"},
        422: {"description": "Validation error"},
    },
)
async def get_movement_totals(
    account_id: Annotated[uuid.UUID, Query(description="Account ID")],
    service: Annotated[MovementsService, Depends(get_movements_service)],
) -> MovementTotalsResponse:
    try:
        return service.get_totals(account_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.get(
    "/period-summary",
    response_model=PeriodSummaryResponse,
    summary="Get period summary with income, expenses, and remaining balance",
    responses={
        404: {"description": "Account not found"},
        422: {"description": "Validation error"},
    },
)
async def get_period_summary(
    account_id: Annotated[uuid.UUID, Query(description="Account ID")],
    start_date: Annotated[date, Query(description="Start date of the period (YYYY-MM-DD)")],
    service: Annotated[MovementsService, Depends(get_movements_service)],
) -> PeriodSummaryResponse:
    try:
        return service.get_period_summary(account_id, start_date)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e
