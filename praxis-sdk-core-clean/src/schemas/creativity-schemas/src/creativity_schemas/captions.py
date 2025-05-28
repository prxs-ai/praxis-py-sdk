from pydantic import BaseModel, Field
from typing import Optional


class CaptionOffset(BaseModel):
    x: float = Field(default=0.0, description="Offset on the x-axis")
    y: float = Field(default=0.0, description="Offset on the y-axis")


class CaptionSetting(BaseModel):
    style: str = Field(
        default="normal-black",
        description="Caption style (e.g., normal-black, neo, frenzy, etc.)",
    )
    offset: Optional[CaptionOffset] = Field(default=None, description="Caption offset settings")
    font_family: str = Field(
        default="Montserrat",
        description="Font family for captions (e.g., Montserrat, Jockey One, etc.)",
    )
    font_size: int = Field(default=70, ge=1, description="Font size for captions")
    font_style: Optional[str] = Field(
        default=None, description="Font style (e.g., font-bold, italic, etc.)"
    )
    background_color: Optional[str] = Field(
        default=None,
        regex=r"^#[A-Fa-f0-9]{6}[A-Fa-f0-9]{2}$",
        description="Background color with alpha channel in format #RRGGBBAA",
    )
    text_color: Optional[str] = Field(
        default=None,
        regex=r"^#[A-Fa-f0-9]{6}[A-Fa-f0-9]{2}$",
        description="Text color with alpha channel in format #RRGGBBAA",
    )
    highlight_text_color: Optional[str] = Field(
        default=None,
        regex=r"^#[A-Fa-f0-9]{6}[A-Fa-f0-9]{2}$",
        description="Highlight color for current spoken word",
    )
    max_width: Optional[int] = Field(
        default=None, description="Maximum width of captions in pixels"
    )
    line_height: Optional[float] = Field(default=None, description="Line height for captions")
    text_shadow: Optional[str] = Field(
        default=None, description="CSS-style text shadow for captions"
    )
    hidden: bool = Field(default=False, description="Whether captions are hidden or not")
