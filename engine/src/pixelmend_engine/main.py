"""Expose the loopback-only PixelMend sidecar HTTP boundary."""

from io import BytesIO

from fastapi import Depends, FastAPI, File, HTTPException, Response, UploadFile, status

from .assets import AssetError, AssetInUseError, AssetNotFoundError, AssetStore
from .auth import require_session_token
from .imageio import ImageIOError


def create_app(*, session_token: str) -> FastAPI:
    """Create a production sidecar app with its private session asset store."""
    app = FastAPI(title="PixelMend Engine", docs_url=None, redoc_url=None)
    assets = AssetStore()
    token_dependency = require_session_token(session_token)

    @app.post("/assets", status_code=status.HTTP_201_CREATED)
    async def import_asset(
        image: UploadFile = File(...),
        _: None = Depends(token_dependency),
    ) -> dict[str, object]:
        """Normalize an uploaded image once without retaining its client filename."""
        try:
            imported = assets.import_image(BytesIO(await image.read()))
        except ImageIOError as error:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)) from error
        return {
            "asset_id": imported.asset_id,
            "width": imported.width,
            "height": imported.height,
            "warnings": list(imported.warnings),
        }

    @app.get("/assets/{asset_id}/preview")
    def get_asset_preview(
        asset_id: str,
        _: None = Depends(token_dependency),
    ) -> Response:
        """Return only a normalized PNG preview for an existing opaque asset id."""
        try:
            preview = assets.preview_bytes(asset_id)
        except AssetNotFoundError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="asset not found") from error
        return Response(content=preview, media_type="image/png")

    @app.delete("/assets/{asset_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_asset(
        asset_id: str,
        _: None = Depends(token_dependency),
    ) -> Response:
        """Dispose one idle session asset without accepting filesystem paths."""
        try:
            assets.delete(asset_id)
        except AssetInUseError as error:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="asset is in use") from error
        except AssetNotFoundError as error:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="asset not found") from error
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    return app
