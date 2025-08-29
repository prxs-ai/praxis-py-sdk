from enum import StrEnum


class AspectRatio(StrEnum):
    RATIO_9X16 = "9x16"
    RATIO_16X9 = "16x9"
    RATIO_1X1 = "1x1"


class VideoStyle(StrEnum):
    _4K_REALISTIC = "4K realistic"
    _3D = "3D"
    CINEMATIC = "Cinematic"
    CARTOONISH = "Cartoonish"
    LINE_ART = "Line art"
    PIXEL_ART = "Pixel art"
    MYSTERIOUS = "Mysterious"
    STEAM_PUNK = "Steam punk"
    COLLAGE = "Collage"
    KAWAII = "Kawaii"


class CaptionStyle(StrEnum):
    NORMAL_BLACK = "normal-black"
    NORMAL_WHITE = "normal-white"
    NORMAL_RED = "normal-red"
    NORMAL_BLUE = "normal-blue"
    NEO = "neo"
    BRICK = "brick"
    FRENZY = "frenzy"
    VERANA = "verana"
    MUSTARD = "mustard"
    GLOW = "glow"
    MINT = "mint"
    COOLERS = "coolers"
    BILO = "bilo"
    TOONS = "toons"
    DEEP_BLUE = "deep-blue"
    MYSTIQUE = "mystique"
    CAUTION = "caution"
    DUALITY = "duality"


class FontStyle(StrEnum):
    BOLD = "font-bold"
    ITALIC = "italic"
    UNDERLINE = "underline"


class FontFamily(StrEnum):
    MONTSERRAT = "Montserrat"
    JOCKEY_ONE = "Jockey One"
    LILITA_ONE = "Lilita One"
    MCLAREN = "Mclaren"
    CORBEN = "Corben"
    DELA_GOTHIC_ONE = "Dela Gothic One"
    COMFORTAA = "Comfortaa"
    LUCKIEST_GUY = "Luckiest Guy"
    QUANTICO = "Quantico"
    POPPINS = "Poppins"


class VideoStatus(StrEnum):
    PENDING = "pending"
    IN_QUEUE = "in_queue"
    RUNNING = "running"
    FAILED = "failed"
    DONE = "done"
    REJECTED = "rejected"


class PermissionType(StrEnum):
    PRIVATE = "private"
    WORKSPACE = "workspace"
    PUBLIC = "public"


class TransitionEffect(StrEnum):
    FADE = "fade"
    SLIDE_LEFT = "slideLeft"
    SLIDE_RIGHT = "slideRight"


class BackgroundFit(StrEnum):
    COVER = "cover"
    CONTAIN = "contain"
