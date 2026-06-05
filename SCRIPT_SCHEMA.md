# 剧本 YAML Schema 规范文档

> 版本：1.0 | 适用场景：AI 辅助小说转剧本工具

---

## 一、Schema 设计总览

本 Schema 用于描述从小说改编而来的影视剧本结构。设计目标：

1. **人机共读**：既适合 AI 生成与解析，也适合编剧手工编辑
2. **完整覆盖**：从元信息、角色、分幕到场景节拍，覆盖剧本全生命周期
3. **可追溯**：每个场景均可回溯到原始小说章节
4. **可扩展**：通过自定义字段支持不同剧种（电影/电视剧/短剧）的特殊需求

---

## 二、完整 Schema 定义

```yaml
# ============================================================
# 顶层结构
# ============================================================
meta:        Meta          # 剧本元信息（必填）
characters:  [Character]   # 角色列表（必填）
acts:        [Act]         # 分幕结构（必填）
scenes:      [Scene]       # 场景列表（必填）
revisions:   [Revision]    # 修订历史（可选）
```

---

### 2.1 Meta — 剧本元信息

```yaml
meta:
  script_title: string          # 剧本标题（必填）
  original_novel: string         # 原著小说名称（必填）
  original_author: string        # 原著作者（必填）
  adapter: string                # 改编者 / AI 模型名称（必填）
  script_version: string         # 剧本版本号，如 "1.0.0"（必填）
  created_at: datetime           # 创建时间，ISO 8601 格式（必填）
  updated_at: datetime           # 最后更新时间（必填）
  genre: [string]                # 类型标签，如 ["古装", "悬疑", "爱情"]（必填）
  script_type: enum              # 剧本类型: film | tv_series | short_drama | stage_play（必填）
  total_scenes: integer          # 场景总数（必填）
  total_episodes: integer        # 集数（tv_series 时必填）
  target_audience: string        # 目标受众，如 "18-35岁女性"（可选）
  synopsis: string               # 故事梗概，200-500 字（必填）
  theme_keywords: [string]       # 主题关键词（可选）
  adaptation_notes: string       # 改编说明，记录改编策略与取舍（可选）
```

**设计原因**：
- `adapter` 字段记录改编者，便于区分 AI 生成与人工修改的版本
- `script_type` 使用枚举约束，确保下游工具能正确解释剧本结构（电影无"集"概念，电视剧有）
- `adaptation_notes` 记录改编决策，方便团队协作时理解改编思路

---

### 2.2 Character — 角色定义

```yaml
characters:
  - character_id: string         # 角色唯一标识，如 "CHAR_001"（必填）
    name: string                 # 角色姓名（必填）
    aliases: [string]            # 别名/称呼（可选）
    role_type: enum              # 主角 | 反派 | 配角 | 客串（必填）
    gender: enum                 # 男 | 女 | 其他（可选）
    age_range: string            # 年龄范围，如 "25-30"（可选）
    occupation: string           # 职业/身份（可选）
    physical_description: string # 外貌描述（可选）
    personality_traits: [string] # 性格特征，如 ["坚韧", "内敛", "重情义"]（必填）
    background: string           # 角色背景故事（必填）
    motivation: string           # 核心动机/欲望（必填）
    arc_summary: string          # 角色弧光总结（必填）
    relationships:               # 与其他角色的关系（可选）
      - target_character_id: string
        relation_type: string    # 如 "师徒"、"恋人"、"仇敌"
        description: string
    first_appearance_scene: integer  # 首次出场场景编号（可选）
    speech_style: string         # 语言风格特征，如 "文雅古典"、"市井俚语"（可选）
```

**设计原因**：
- `character_id` 作为唯一标识，在 scene 中通过 ID 引用角色，避免姓名冲突
- `role_type` 使用枚举而非自由文本，确保分类一致性
- `arc_summary` 和 `motivation` 是编剧核心关注点，单独列出便于把握角色走向
- `speech_style` 帮助 AI 和编剧保持角色台词风格的一致性
- `relationships` 内嵌在角色内，相比独立的"关系表"更直观

---

### 2.3 Act — 分幕结构

```yaml
acts:
  - act_number: integer          # 幕序号，从 1 开始（必填）
    title: string                # 幕标题，如 "建置"（必填）
    description: string          # 幕描述（必填）
    scene_range:                 # 包含的场景范围（必填）
      start: integer
      end: integer
    narrative_function: string   # 叙事功能，如 "引入冲突"、"高潮"、"结局"（可选）
```

**设计原因**：
- 使用 `scene_range`（起止编号）而非枚举每个场景 ID，减少冗余，且方便范围查询
- `act_number` 支持传统三幕式（1-3），也支持多幕结构（电视剧/舞台剧）
- `narrative_function` 帮助确认每幕是否达成叙事目标

---

### 2.4 Scene — 场景（Schema 核心）

```yaml
scenes:
  - scene_id: integer            # 场景唯一编号，从 1 开始（必填）
    episode: integer             # 所属集数（tv_series 时必填，film 可省略）
    scene_heading:               # 场景标题（必填）
      interior_exterior: enum    # 内 | 外
      location: string           # 地点，如 "京城·沈府书房"
      time: enum                 # 日 | 夜 | 傍晚 | 清晨 | 凌晨
      time_period: string        # 时代背景标注，如 "古代·大业三年"（可选）
    source_reference:            # 原著溯源（必填）
      novel_chapter: integer     # 对应原著章节号
      novel_chapter_title: string
      excerpt: string            # 关键原文摘录（可选）
    summary: string              # 场景概要，1-3 句话（必填）
    scene_function: enum         # 场景功能：推进主线 | 发展感情 | 展示世界观 | 过渡 | 伏笔（必填）
    emotional_tone: string       # 情感基调，如 "紧张"、"温馨"、"悲壮"（必填）
    characters_present: [string] # 在场角色 ID 列表（必填）
    props: [string]              # 关键道具（可选）
    beats:                       # 节拍序列（必填）
      - beat_id: string          # 节拍标识，如 "S1_B1"（场景1节拍1）（必填）
        beat_type: enum          # 节拍类型（必填）
        character_id: string     # 执行角色 ID（action/dialogue 时必填）
        content: string          # 节拍内容（必填）
        subtext: string          # 潜台词/内心活动（可选）
        emotion: string          # 当前情绪标注（可选）
        parenthetical: string    # 表演提示，如 "(压低声音)"、"(冷笑)"（dialogue 时可选）
        duration_hint: string    # 时长提示，如 "30s"、"2min"（可选）
        camera_hint: string      # 镜头提示，如 "特写"、"远景"、"跟拍"（可选）
    transition: enum             # 转场方式：切 | 淡入 | 淡出 | 叠化 | 划像（可选，默认 "切"）
    estimated_duration: string   # 预估时长，如 "3min"（可选）
    notes: string                # 编剧备注（可选）
```

**Beat 类型枚举（beat_type）**：

| 值 | 含义 | content 示例 |
|---|---|---|
| `dialogue` | 角色对白 | "我绝不会让你离开京城。" |
| `action` | 动作描述 | "沈墨拔出佩剑，剑锋直指对方咽喉。" |
| `description` | 环境/氛围描写 | "书房内烛火摇曳，墙上映出两人对峙的影子。" |
| `voiceover` | 旁白/画外音 | "那年冬天，京城下了第一场雪。" |
| `monologue` | 独白 | "（内心）这一剑下去，便再无回头之路。" |
| `transition` | 转场提示 | "画面渐暗，转至次日清晨。" |

**设计原因**：

1. **scene_heading 采用经典三要素**：`内/外` + `地点` + `时间` 是国际剧本标准格式，保证与现有编剧工具兼容
2. **source_reference 保持可追溯性**：每个场景标注对应的原著章节与摘录，方便编剧对比原著、评估改编保真度
3. **beats（节拍）替代传统分镜**：传统剧本的"分镜"偏导演视角，而"节拍"是编剧叙事的最小单元。将 `action`、`dialogue`、`description` 统一为 beat 序列，既能描述叙事节奏，又避免了过度导演化
4. **parenthetical 和 subtext 分离**：`parenthetical` 是给演员的外部表演提示，`subtext` 是角色的内心潜台词——二者在不同创作阶段服务于不同的角色（演员 vs 编剧/导演分析）
5. **camera_hint 为可选字段**：编剧阶段不应过度指定镜头，但允许关键镜头意图的标注，兼顾灵活性
6. **scene_function 和 emotional_tone**：帮助编剧检查每场戏是否承担了明确的叙事功能，以及整体情绪曲线是否合理

---

### 2.5 Revision — 修订历史（可选）

```yaml
revisions:
  - version: string              # 版本号
    timestamp: datetime          # 修订时间
    author: string               # 修订者
    summary: string              # 修订摘要
    changed_scenes: [integer]    # 修改的场景 ID 列表
```

---

## 三、完整示例

以下是一个简化的古装剧剧本片段示例：

```yaml
meta:
  script_title: "长安十二时辰（改编剧本）"
  original_novel: "长安十二时辰"
  original_author: "马伯庸"
  adapter: "AI Script Assistant v1.0"
  script_version: "0.1.0"
  created_at: "2026-06-05T10:00:00+08:00"
  updated_at: "2026-06-05T10:00:00+08:00"
  genre: ["古装", "悬疑", "动作"]
  script_type: tv_series
  total_scenes: 45
  total_episodes: 12
  target_audience: "18-45岁男女"
  synopsis: "唐朝天宝三年，死囚张小敬被临时释放，需在十二时辰内破解长安城中的惊天阴谋……"
  theme_keywords: ["时间紧迫", "忠义抉择", "盛唐危机"]
  adaptation_notes: "保留原著紧张节奏，将多线叙事简化为双线并行，每集对应原著约2章内容。"

characters:
  - character_id: "CHAR_001"
    name: "张小敬"
    role_type: "主角"
    gender: "男"
    age_range: "35-40"
    occupation: "前不良帅 / 死囚"
    personality_traits: ["果决", "狠辣", "重情义", "不拘礼法"]
    background: "曾任万年县不良帅，因杀官被判处死刑，关押于长安狱中。"
    motivation: "找出幕后黑手，保护长安百姓，同时为自己争取一线生机。"
    arc_summary: "从只为活下去的死囚，逐渐找回守护长安的信念，最终坦然面对生死。"
    speech_style: "粗犷直接，偶尔带关中方言，关键时刻言辞犀利。"
    relationships:
      - target_character_id: "CHAR_002"
        relation_type: "搭档/师徒"
        description: "靖安司司丞，与张小敬从互不信任到生死相托。"

  - character_id: "CHAR_002"
    name: "李必"
    role_type: "主角"
    gender: "男"
    age_range: "22-25"
    occupation: "靖安司司丞"
    personality_traits: ["聪慧", "理想主义", "优柔寡断"]
    background: "少年天才，受太子信任执掌靖安司，一心守护长安。"
    motivation: "在十二时辰内阻止阴谋，证明靖安司的价值。"
    arc_summary: "从纸上谈兵的理想主义者，成长为能承受代价的真正决策者。"
    speech_style: "文雅有礼，多用典故，情绪激动时语速加快。"

acts:
  - act_number: 1
    title: "危机降临"
    description: "长安遭遇威胁，张小敬被临时启用，与李必联手追查线索。"
    scene_range:
      start: 1
      end: 15
    narrative_function: "建置世界观、引入核心冲突、建立主角搭档关系"

scenes:
  - scene_id: 1
    episode: 1
    scene_heading:
      interior_exterior: "外"
      location: "长安·西市"
      time: "日"
      time_period: "唐朝·天宝三年"
    source_reference:
      novel_chapter: 1
      novel_chapter_title: "巳正"
      excerpt: "长安城沐浴在正午的阳光下，一百零八坊如棋盘般整齐铺展。"
    summary: "长安西市繁华景象，一队突厥商队暗中携带可疑物品入城。"
    scene_function: "推进主线"
    emotional_tone: "平静中暗藏危机"
    characters_present: ["CHAR_003", "CHAR_004"]
    props: ["西域香料箱", "狼卫令牌"]
    beats:
      - beat_id: "S1_B1"
        beat_type: "description"
        content: "镜头俯瞰长安城，一百零八坊如棋盘般规整。西市人声鼎沸，胡商云集。"
        camera_hint: "航拍远景"
      - beat_id: "S1_B2"
        beat_type: "action"
        character_id: "CHAR_003"
        content: "曹破延混在商队中，低头穿过人群，手始终按在腰间短刀上。"
        emotion: "警惕"
      - beat_id: "S1_B3"
        beat_type: "dialogue"
        character_id: "CHAR_004"
        content: "大人，城门检查比往日严了许多。"
        parenthetical: "(压低声音，面露忧色)"
        subtext: "他怀疑计划已经泄露。"
      - beat_id: "S1_B4"
        beat_type: "dialogue"
        character_id: "CHAR_003"
        content: "无妨。东西分开放，分头进城。"
        emotion: "冷静"
        parenthetical: "(目光扫视四周)"
    transition: "切"
    estimated_duration: "2min"
```

---

## 四、Schema 设计原则总结

| 原则 | 体现 |
|---|---|
| **人机共读** | YAML 格式纯文本，Git 友好，IDE 可直接编辑；结构层次清晰，AI 可精确解析 |
| **与行业标准对齐** | scene_heading 采用"内/外 + 地点 + 时间"经典三要素；beat 概念源自编剧方法论 |
| **可追溯性** | 每个场景标注 source_reference，改编过程全程可溯源 |
| **关注点分离** | 角色档案（characters）、结构大纲（acts）、叙事内容（scenes）三层独立 |
| **渐进式细节** | 必填字段保证结构性，大量可选字段支持按需细化 |
| **多剧种兼容** | 通过 script_type 区分电影/电视剧/短剧/舞台剧，同一 Schema 满足不同产出需求 |

---

## 五、与现有标准的对比

与业界常用剧本格式的对比：

| 特性 | 本 Schema | Final Draft (.fdx) | Fountain | 纯文本剧本 |
|---|---|---|---|---|
| 结构化数据 | YAML，易于编程处理 | XML，冗长 | Markdown-like，半结构化 | 无结构 |
| 角色管理 | 独立角色档案，含关系网 | 仅角色名列表 | 无 | 无 |
| 原著溯源 | 内建 source_reference | 无 | 无 | 无 |
| AI 友好性 | 高（明确枚举、层次分明） | 中（XML 解析成本高） | 低（依赖约定） | 极低 |
| 人工可编辑性 | 高（纯文本 YAML） | 低（需专业软件） | 高 | 高 |
| 版本控制 | Git 友好 | 不友好（二进制 .fdx） | 友好 | 友好 |

本 Schema 的核心优势在于 **在结构化与可读性之间取得平衡**，既满足自动化处理需求，又不牺牲编剧手工编辑的体验。
