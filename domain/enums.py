"""领域枚举常量 — 不依赖任何外部模块。"""

from enum import StrEnum


class RoleType(StrEnum):
    PROTAGONIST = "主角"
    ANTAGONIST = "反派"
    SUPPORTING = "配角"
    CAMEO      = "客串"


class Gender(StrEnum):
    MALE   = "男"
    FEMALE = "女"
    OTHER  = "其他"


class ScriptType(StrEnum):
    FILM        = "film"
    TV_SERIES   = "tv_series"
    SHORT_DRAMA = "short_drama"
    STAGE_PLAY  = "stage_play"


class InteriorExterior(StrEnum):
    INTERIOR = "内"
    EXTERIOR = "外"


class TimeOfDay(StrEnum):
    DAY     = "日"
    NIGHT   = "夜"
    EVENING = "傍晚"
    MORNING = "清晨"
    DAWN    = "凌晨"


class SceneFunction(StrEnum):
    ADVANCE_PLOT  = "推进主线"
    DEVELOP_ROMANCE = "发展感情"
    WORLD_BUILDING   = "展示世界观"
    TRANSITION   = "过渡"
    FORESHADOW   = "伏笔"


class BeatType(StrEnum):
    DIALOGUE    = "dialogue"
    ACTION      = "action"
    DESCRIPTION = "description"
    VOICEOVER   = "voiceover"
    MONOLOGUE   = "monologue"
    TRANSITION  = "transition"


class Transition(StrEnum):
    CUT      = "切"
    FADE_IN  = "淡入"
    FADE_OUT = "淡出"
    DISSOLVE = "叠化"


class Language(StrEnum):
    """剧本输出语言。"""
    ZH = "zh"  # 中文（默认）
    EN = "en"  # 英文


class AdaptationMode(StrEnum):
    """改编模式 — 参考 Scriptify 的三种创作模式。"""
    FAST    = "fast"    # 快速模式：AI 直接生成完整初稿，快速出片
    DETAIL  = "detail"  # 精细模式：逐章深度分析，每步可人工介入
    HYBRID  = "hybrid"  # 混合模式：AI 提供框架，人工填充细节


class GenreStyle(StrEnum):
    """剧本风格模板 — 参考 Scriptify 的漫剧风格 + 常见题材。"""
    SUSPENSE     = "悬疑"     # 反转钩子，追剧欲望
    ROMANCE      = "甜宠"     # 恋爱甜度，心动瞬间
    ACTION       = "热血"     # 燃点密集，逆袭爽感
    COMEDY       = "沙雕"     # 搞笑搞怪，神转折
    URBAN        = "都市"     # 现实题材，情感共鸣
    HISTORICAL   = "古装"     # 权谋宫斗，古典韵味
    FANTASY      = "仙侠"     # 修仙体系，宏大的世界观
    SCI_FI       = "科幻"     # 未来设定，科技反思
    HORROR       = "惊悚"     # 氛围营造，心理恐惧
    AUTO         = "自动"     # 由 AI 自动从原文推断


class TaskStatus(StrEnum):
    PENDING    = "pending"
    PROCESSING = "processing"
    COMPLETED  = "completed"
    FAILED     = "failed"


# 枚举值集合（快速校验用）
VALID_ROLE_TYPES     = set(RoleType)
VALID_GENDERS        = set(Gender)
VALID_SCRIPT_TYPES   = set(ScriptType)
VALID_IE             = set(InteriorExterior)
VALID_TIMES          = set(TimeOfDay)
VALID_SCENE_FUNCTIONS = set(SceneFunction)
VALID_BEAT_TYPES     = set(BeatType)
VALID_TRANSITIONS    = set(Transition)
VALID_TASK_STATUSES  = set(TaskStatus)
