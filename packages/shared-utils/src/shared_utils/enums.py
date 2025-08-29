from enum import Enum


class AppPlatformEnum(str, Enum):
    ANDROID = "android"
    IOS = "ios"
    WP = "wp"
    BB = "bb"
    DESKTOP = "desktop"
    WEB = "web"
    UBP = "ubp"
    OTHER = "other"
