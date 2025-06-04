from pydantic import BaseModel, Field, HttpUrl
from schemas.enums import AspectRatio, CaptionStyle


class LipsyncRequest(BaseModel):
    name: str | None = Field(
        None, max_length=255, description="The name of the lipsync task."
    )
    text: str | None = Field(
        None, max_length=3600, description="The text to be used for voiceover."
    )
    audio: HttpUrl | None = Field(None, description="The URL of the audio file.")
    creator: str | None = Field(
        None, description="The creator ID associated with the lipsync request."
    )
    aspect_ratio: AspectRatio
    green_screen: bool | None = Field(
        False, description="Whether the background is transparent."
    )
    webhook_url: HttpUrl | None = Field(
        None, max_length=200, description="Webhook URL for status updates."
    )
    accent: str | None = Field(
        None, description="The avatar ID to be used for lipsync."
    )
    no_caption: bool | None = Field(
        True, description="Whether to include captions in the video."
    )
    no_music: bool | None = Field(
        True, description="Whether to include background music."
    )
    caption_style: CaptionStyle | None = Field(
        None, description="Style of the captions."
    )
    caption_offset_x: str | None = Field(
        None, description="Horizontal caption offset, range -0.5 to 0.5."
    )
    caption_offset_y: str | None = Field(
        None, description="Vertical caption offset, range -0.5 to 0.5."
    )
    background_asset_image_url: HttpUrl | None = Field(
        None, max_length=1024, description="URL of the background asset image."
    )


class LipsyncResponse(BaseModel):
    id: str
    name: str | None
    text: str | None
    creator: str | None
    output: str | None
    aspect_ratio: AspectRatio
    green_screen: bool
    created_at: str
    updated_at: str
    credits_used: int
    progress: str
    failed_reason: str | None
    media_job: str | None
    status: str
    is_hidden: bool
    audio_url: str | None
    webhook_url: str | None
    accent: str | None
    preview: str | None
    preview_audio: str | None
    no_caption: bool
    no_music: bool
    caption_style: CaptionStyle | None
    caption_offset_x: str | None
    caption_offset_y: str | None
    background_asset_image_url: str | None


class LipsyncPreviewRequest(BaseModel):
    name: str | None = Field(
        None, max_length=255, description="The name of the lipsync preview task."
    )
    text: str | None = Field(
        None, max_length=3600, description="The text to be used for the voiceover."
    )
    audio: HttpUrl | None = Field(
        None, description="The URL of the audio file for lipsync."
    )
    creator: str | None = Field(
        None, description="The creator ID associated with the lipsync request."
    )
    aspect_ratio: AspectRatio
    green_screen: bool | None = Field(
        False, description="Whether the background is transparent."
    )
    webhook_url: HttpUrl | None = Field(
        None, max_length=200, description="Webhook URL for status updates."
    )
    accent: str | None = Field(
        None, description="The avatar ID to be used for lipsync."
    )
    no_caption: bool | None = Field(
        True, description="Whether captions are included in the preview video."
    )
    no_music: bool | None = Field(
        True, description="Whether background music is included."
    )
    caption_style: CaptionStyle | None = Field(
        None, description="Style of the captions."
    )
    caption_offset_x: str | None = Field(
        None, description="Horizontal caption offset (-0.5 to 0.5)."
    )
    caption_offset_y: str | None = Field(
        None, description="Vertical caption offset (-0.5 to 0.5)."
    )
    background_asset_image_url: HttpUrl | None = Field(
        None, max_length=1024, description="URL of the background asset image."
    )


class LipsyncPreviewResponse(BaseModel):
    id: str
    name: str | None
    text: str | None
    creator: str | None
    output: str | None
    aspect_ratio: AspectRatio
    green_screen: bool
    created_at: str
    updated_at: str
    credits_used: int
    progress: str
    failed_reason: str | None
    media_job: str | None
    status: str
    is_hidden: bool
    audio_url: str | None
    webhook_url: str | None
    accent: str | None
    preview: str | None
    preview_audio: str | None
    no_caption: bool
    no_music: bool
    caption_style: CaptionStyle | None
    caption_offset_x: str | None
    caption_offset_y: str | None
    background_asset_image_url: str | None
