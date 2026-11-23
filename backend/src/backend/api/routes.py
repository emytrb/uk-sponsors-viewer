from fastapi import APIRouter, Response

from backend.services.sponsors_fetcher import get_uk_sponsors_csv_file

router = APIRouter(prefix="/api/v1/test")


@router.get("/test_csv_fetch", response_class=Response)
def test_file() -> Response:
    csv_data = get_uk_sponsors_csv_file()
    headers = {"Content-Disposition": 'attachment; filename="sponsors.csv"'}
    return Response(
        content=csv_data.encode("utf-8"),
        media_type="text/csv",
        headers=headers,
    )
