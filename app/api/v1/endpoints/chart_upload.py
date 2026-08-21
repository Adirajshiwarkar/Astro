from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.domain.image_intelligence.pipeline import ImageIntelligencePipeline
from app.domain.image_intelligence.security import FileValidationError
from app.schemas.image_intelligence import ChartUploadResponse

router = APIRouter()
pipeline = ImageIntelligencePipeline()


@router.post(
    "/upload",
    response_model=ChartUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload and extract structured astrological data from a Kundli/chart image",
)
async def upload_chart_image(
    file: UploadFile = File(..., description="Chart image or document file (PNG, JPEG, WEBP, PDF, TIFF, BMP)"),
) -> ChartUploadResponse:
    """Uploads a Kundli or astrological chart, validates MIME and dimensions,

    performs layout detection, OCR, and extracts structured representation with confidences.
    """
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty file uploaded.",
        )

    try:
        chart_repr = await pipeline.process_image(
            file_bytes=file_bytes,
            declared_mime=file.content_type,
        )
        return ChartUploadResponse(
            success=True,
            message="Chart successfully processed.",
            chart_data=chart_repr,
        )
    except FileValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process chart image: {str(e)}",
        ) from e
