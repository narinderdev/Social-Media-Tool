from pathlib import Path

from app.storage import UPLOADS_DIR


def create_instagram_image(original_path: Path, original_filename: str) -> dict | None:
    suffix = original_path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return None

    from PIL import Image

    filename = f"{original_path.stem}-instagram.jpg"
    destination = UPLOADS_DIR / filename

    with Image.open(original_path) as image:
        image.thumbnail((1440, 1440))
        background = Image.new("RGB", image.size, (255, 255, 255))

        if image.mode in {"RGBA", "LA"}:
            alpha = image.getchannel("A")
            background.paste(image.convert("RGB"), mask=alpha)
        else:
            background.paste(image.convert("RGB"))

        background.save(destination, "JPEG", quality=92, optimize=True)

    return {
        "originalName": original_filename,
        "filename": filename,
        "mimeType": "image/jpeg",
        "size": destination.stat().st_size,
        "url": f"/uploads/{filename}",
    }
