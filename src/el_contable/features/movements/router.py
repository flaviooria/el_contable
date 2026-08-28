from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from el_contable.features.movements.parser import ParserError
from el_contable.features.movements.schemas import UploadError, UploadResponse
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
async def download_template(
    service: Annotated[MovementsService, Depends(get_movements_service)],
) -> FileResponse:
    template_path = Path(service.get_template_path())

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
