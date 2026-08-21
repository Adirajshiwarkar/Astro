from typing import Any
from pydantic import BaseModel, Field

from app.domain.image_intelligence.models import StructuredChartRepresentation


class ChartUploadResponse(BaseModel):
    success: bool = True
    message: str = "Chart successfully processed."
    chart_data: StructuredChartRepresentation
