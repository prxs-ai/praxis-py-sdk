from typing import TypedDict

from pydantic import BaseModel
from schemas.enums import (
    AspectRatio,
    BackgroundFit,
    CaptionStyle,
    FontStyle,
)


class Offset(BaseModel):
    x: float
    y: float


class CaptionSetting(BaseModel):
    style: CaptionStyle
    offset: Offset | None = None
    font_family: str
    font_size: int
    font_style: FontStyle | None = None
    background_color: str | None = None
    text_color: str | None = None
    highlight_text_color: str | None = None
    max_width: int | None = None
    line_height: int | None = None
    text_shadow: str | None = None
    hidden: bool = False


class Voice(BaseModel):
    type: str
    input_text: str | None = None
    voice_id: str | None = None
    volume: float | None = None


class Background(BaseModel):
    type: str
    url: str | None = None
    fit: BackgroundFit
    effect: str | None = None


class TransitionEffect(TypedDict, total=False):
    transition_in: str
    transition_out: str


class CTALogo(TypedDict, total=False):
    url: str
    scale: float
    offset: Offset


class CTACaption(TypedDict, total=False):
    caption: str
    caption_setting: CaptionSetting


class CTA(BaseModel):
    cta_logo: CTALogo | None = None
    cta_caption: CTACaption | None = None
    cta_background_blur: bool | None = None
    transition_effect: TransitionEffect | None = None
    cta_duration: int | None = None
    cta_background: Background | None = None


class VideoInput(BaseModel):
    character: dict
    voice: Voice
    caption_setting: CaptionSetting
    background: Background
    transition_effect: TransitionEffect | None = None
    cta: CTA | None = None


class BackgroundMusic(TypedDict, total=False):
    url: str
    volume: float


class LipsyncV2Request(BaseModel):
    video_inputs: list[VideoInput]
    aspect_ratio: AspectRatio
    background_music: BackgroundMusic | None = None
    cta_end: CTA | None = None
    webhook_url: str | None = None


class LipsyncV2Response(BaseModel):
    id: str
    name: str | None = None
    output: str | None = None
    created_at: str
    updated_at: str
    credits_used: int
    progress: str | None = None
    failed_reason: str | None = None
    media_job: str | None = None
    status: str
    webhook_url: str | None = None
    preview: str | None = None
