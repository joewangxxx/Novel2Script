# Stage 24 Kimi Candidate Author Review

Review each candidate and edit the decisions YAML. Valid decisions: `accept`, `edit`, `reject`, `pending`.

## adaptation_planner / adaptplan_001

- Type: `scene_plan_adjustment`
- Target: `{'artifact': 'outline', 'path': 'outline.scene_plan[0]'}`
- Requires author approval: `True`
- AI inferred: `True`
- Confidence: `medium`
- Proposed text: SCENE 001 — 桃园初聚（刘备视角，内/外·市集→桃园）
BEAT 1 触发（0:00-0:45）：刘备于涿县市集观招募黄巾榜文，长叹。张飞厉声喝断——"大丈夫不为国家出力，何故长叹？"二人目光交锋，张力建立。
BEAT 2 结识（0:45-2:30）：移步酒馆，关羽携刀入。三人互报姓名，各述来历——刘备织席贩履之隐忍、张飞屠户之豪纵、关羽亡命之孤冷。价值观试探："乱世之中，何为大丈夫？"
BEAT 3 立誓（2:30-4:00）：次日桃园，乌牛白马祭礼。誓词核心："不求同生，但求同死"——以死契换生路，反讽乱世逻辑。刘备执杯先饮，确立隐性主导。
BEAT 4 定名（4:00-5:00）：铸造兵器，分授职分。刘备双股剑（双刃/两难隐喻），关羽青龙偃月（长柄/距离感），张飞丈八蛇矛（突刺/冲动性）。
视觉锚点：桃花纷飞贯穿全场景，花瓣沾血（BEAT 3祭刀）、落酒（BEAT 3举杯）、埋入泥土（BEAT 4兵器淬火）——"绚烂即凋零"的预设意象。
声效设计：市集鼓噪→酒馆寂静→桃园风声渐起，空间声学标记情绪升级。
- Rationale: 原scene_plan[0]仅标注'桃园结义'事件节点，未拆解叙事节拍与视听语法。源文本p_004刘备'长叹'与张飞'厉声喝道'构成强烈动作-反应链，具备影视化张力；但现有outline未提取该动力机制，亦未分配视角与时空节奏。本方案将单事件扩展为四节拍场景，嵌入视听锚点，使'结义'从情节符号转化为可拍摄的场面调度。

## character_bible_agent / charbible_001

- Type: `flaw`
- Target: `{'character_id': 'char_001', 'artifact': 'character_bible', 'path': 'character_bible.characters[0]'}`
- Requires author approval: `True`
- AI inferred: `True`
- Confidence: `medium`
- Proposed text: 深居宫中，宠信宦官，卖官鬻爵，致使朝政腐败、民不聊生，对黄巾之乱的爆发负有直接责任。
- Rationale: 原文明确指出桓帝、灵帝'宠信宦官，致使朝政日益腐败，民不聊生'，且汉灵帝在位时局面恶化，体现其核心性格缺陷为昏庸无能、纵容腐败。

## scene_writer_agent / scenewrite_001

- Type: `scene_action`
- Target: `{'artifact': 'screenplay', 'scene_id': 'scene_001', 'beat_id': 'beat_001', 'character_id': 'char_001', 'path': 'scenes[0].elements[0]'}`
- Requires author approval: `True`
- AI inferred: `True`
- Confidence: `high`
- Proposed text: EXT. TOWN SQUARE - DAY

A weathered NOTICE BOARD stands at the crossroads, CROWDS milling past. LIU BEI (30s, worn sandals, frayed robes—descended of imperial blood, yet sunk to weaving mats) stops before it. His eyes trace the OFFICIAL PROCLAMATION: a call to arms against the Yellow Turbans.

He exhales—a long, weighted SIGH. Shoulders slump. Fingers tighten on his woven satchel.

VOICE (O.S.)
(rough, contemptuous)
A true man who does nothing for his country—

Liu Bei turns.

Zhang Fei (40s, blacksmith's build, bristling beard) glares at him from two paces away, meat-wine breath, fists like hams.

The SOUND of the crowd DROPS AWAY. Two men locked in the first spark of history.
- Rationale: Establishes Liu Bei's low status against noble lineage (internal conflict), grounds the iconic sigh in physical action, and stages the confrontational meet-cute with Zhang Fei as visual tension rather than exposition. The beat transitions from solitary contemplation to interpersonal catalyst per source event evt_001.

## dialogue_optimizer_agent / dialogueopt_001

- Type: `dialogue_rewrite`
- Target: `{'artifact': 'screenplay', 'scene_id': 'scene_001', 'beat_id': 'beat_001', 'character_id': 'char_001', 'path': 'scenes[0].elements[0]'}`
- Requires author approval: `True`
- AI inferred: `True`
- Confidence: `medium`
- Proposed text: (turning from the notice, shoulders heavy)

LIU BEI
(sighs, low and long)

Another day. Another call to arms I'll never answer.

A VOICE (O.S.)
(sharp, cutting)

A real man doesn't sigh at his country's wounds!

Liu Bei turns. Behind him, ZHANG FEI — a towering figure, eyes blazing with contempt.
- Rationale: Converts expository narration into dramatic dialogue with visual blocking, subtext (Liu Bei's unspoken ambition vs. self-pity), and character-revealing confrontation. The sigh externalizes internal conflict; Zhang Fei's interruption creates immediate dramatic tension and establishes their dynamic from first meeting.
