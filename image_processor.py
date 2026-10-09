from PIL import Image


def get_image_info(file_path: str) -> dict:
    image = Image.open(file_path)

    return {
        "format": image.format,
        "width": image.width,
        "height": image.height,
        "mode": image.mode
    }