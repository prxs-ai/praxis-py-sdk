from pydantic import BaseModel, HttpUrl, Field
from typing import Optional

from schemas.creativity.captions import CaptionSetting


class AIShortRequest(BaseModel):
    aspect_ratio: str
    script: str
    style: str
    accent: Optional[str] = Field(default=None, description="Accent for the video, default is null")
    background_music_url: Optional[HttpUrl] = Field(
        default=None, description="URL for background music"
    )
    background_music_volume: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Volume for background music"
    )
    voiceover_volume: Optional[float] = Field(
        default=None, ge=0.0, le=1.0, description="Volume for voiceover"
    )
    webhook_url: Optional[HttpUrl] = Field(
        default=None, description="Webhook URL for status updates"
    )
    caption_setting: Optional[CaptionSetting] = Field(
        default=None, description="Settings for captions"
    )


class AIShortResponse(BaseModel):
    id: str
    media_job: Optional[str] = Field(default=None, description="Media job ID for the video")
    status: str
    video_output: Optional[str] = Field(default=None, description="URL to the generated video")
    preview: Optional[str] = Field(default=None, description="URL to the preview of the video")
    credits_used: int
    is_hidden: bool
    progress: int
    created_at: str
    updated_at: str
    permission_type: str
    name: Optional[str] = Field(default=None, description="Name of the video")
    script: Optional[str] = Field(default=None, description="Script used for generating the video")
    aspect_ratio: str
    style: str
    created_from_api: bool
    caption_setting: Optional[CaptionSetting] = Field(
        default=None, description="Settings for captions"
    )
    background_music_url: Optional[HttpUrl] = Field(
        default=None, description="URL for background music"
    )
    background_music_volume: Optional[float] = Field(
        default=None, description="Volume for background music"
    )
    voiceover_volume: Optional[float] = Field(default=None, description="Volume for voiceover")
    webhook_url: Optional[HttpUrl] = Field(
        default=None, description="Webhook URL for status updates"
    )
    user: Optional[int] = Field(default=None, description="User ID associated with the video")
    workspace: Optional[str] = Field(default=None, description="Workspace ID for the video")
    accent: Optional[str] = Field(default=None, description="Accent used in the video")
