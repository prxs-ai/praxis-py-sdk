from pydantic import BaseModel, HttpUrl, Field
from typing import Optional

from schemas.enums import AspectRatio, CaptionStyle


class LipsyncRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=255, description="The name of the lipsync task.")
    text: Optional[str] = Field(
        None, max_length=3600, description="The text to be used for voiceover."
    )
    audio: Optional[HttpUrl] = Field(None, description="The URL of the audio file.")
    creator: Optional[str] = Field(
        None, description="The creator ID associated with the lipsync request."
    )
    aspect_ratio: AspectRatio
    green_screen: Optional[bool] = Field(
        False, description="Whether the background is transparent."
    )
    webhook_url: Optional[HttpUrl] = Field(
        None, max_length=200, description="Webhook URL for status updates."
    )
    accent: Optional[str] = Field(None, description="The avatar ID to be used for lipsync.")
    no_caption: Optional[bool] = Field(
        True, description="Whether to include captions in the video."
    )
    no_music: Optional[bool] = Field(True, description="Whether to include background music.")
    caption_style: Optional[CaptionStyle] = Field(None, description="Style of the captions.")
    caption_offset_x: Optional[str] = Field(
        None, description="Horizontal caption offset, range -0.5 to 0.5."
    )
    caption_offset_y: Optional[str] = Field(
        None, description="Vertical caption offset, range -0.5 to 0.5."
    )
    background_asset_image_url: Optional[HttpUrl] = Field(
        None, max_length=1024, description="URL of the background asset image."
    )


class LipsyncResponse(BaseModel):
    id: str
    name: Optional[str]
    text: Optional[str]
    creator: Optional[str]
    output: Optional[str]
    aspect_ratio: AspectRatio
    green_screen: bool
    created_at: str
    updated_at: str
    credits_used: int
    progress: str
    failed_reason: Optional[str]
    media_job: Optional[str]
    status: str
    is_hidden: bool
    audio_url: Optional[str]
    webhook_url: Optional[str]
    accent: Optional[str]
    preview: Optional[str]
    preview_audio: Optional[str]
    no_caption: bool
    no_music: bool
    caption_style: Optional[CaptionStyle]
    caption_offset_x: Optional[str]
    caption_offset_y: Optional[str]
    background_asset_image_url: Optional[str]


class LipsyncPreviewRequest(BaseModel):
    name: Optional[str] = Field(
        None, max_length=255, description="The name of the lipsync preview task."
    )
    text: Optional[str] = Field(
        None, max_length=3600, description="The text to be used for the voiceover."
    )
    audio: Optional[HttpUrl] = Field(None, description="The URL of the audio file for lipsync.")
    creator: Optional[str] = Field(
        None, description="The creator ID associated with the lipsync request."
    )
    aspect_ratio: AspectRatio
    green_screen: Optional[bool] = Field(
        False, description="Whether the background is transparent."
    )
    webhook_url: Optional[HttpUrl] = Field(
        None, max_length=200, description="Webhook URL for status updates."
    )
    accent: Optional[str] = Field(None, description="The avatar ID to be used for lipsync.")
    no_caption: Optional[bool] = Field(
        True, description="Whether captions are included in the preview video."
    )
    no_music: Optional[bool] = Field(True, description="Whether background music is included.")
    caption_style: Optional[CaptionStyle] = Field(None, description="Style of the captions.")
    caption_offset_x: Optional[str] = Field(
        None, description="Horizontal caption offset (-0.5 to 0.5)."
    )
    caption_offset_y: Optional[str] = Field(
        None, description="Vertical caption offset (-0.5 to 0.5)."
    )
    background_asset_image_url: Optional[HttpUrl] = Field(
        None, max_length=1024, description="URL of the background asset image."
    )


class LipsyncPreviewResponse(BaseModel):
    id: str
    name: Optional[str]
    text: Optional[str]
    creator: Optional[str]
    output: Optional[str]
    aspect_ratio: AspectRatio
    green_screen: bool
    created_at: str
    updated_at: str
    credits_used: int
    progress: str
    failed_reason: Optional[str]
    media_job: Optional[str]
    status: str
    is_hidden: bool
    audio_url: Optional[str]
    webhook_url: Optional[str]
    accent: Optional[str]
    preview: Optional[str]
    preview_audio: Optional[str]
    no_caption: bool
    no_music: bool
    caption_style: Optional[CaptionStyle]
    caption_offset_x: Optional[str]
    caption_offset_y: Optional[str]
    background_asset_image_url: Optional[str]
