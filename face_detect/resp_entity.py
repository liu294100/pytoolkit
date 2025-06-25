from pydantic import BaseModel


class ImageStatus(BaseModel):
    legal: bool = False
    face_detected: bool = True
    face_probability: float = 0
    multiple_face: bool = False
    brightness: float = 0
