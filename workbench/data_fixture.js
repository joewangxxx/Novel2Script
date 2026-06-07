const WORKBENCH_DATA = {
  project_info: {
    name: "三国演义桃园结义改编项目",
    last_modified: "2026-06-07T17:40:00+08:00",
    version: "Stage 32 (Release)"
  },
  files: [
    { name: "test1_sanguo.txt", type: "novel", status: "source", size: "29.5 KB" },
    { name: "test1_sanguo_story_map.merged.yaml", type: "story_map", status: "human_confirmed", size: "11.1 KB" },
    { name: "test1_sanguo_outline.stage26.yaml", type: "outline", status: "human_confirmed", size: "9.1 KB" },
    { name: "test1_sanguo_character_bible.stage26.yaml", type: "character_bible", status: "human_confirmed", size: "8.4 KB" },
    { name: "test1_sanguo_screenplay.stage32.yaml", type: "screenplay", status: "ai_inferred", size: "7.2 KB" },
    { name: "test1_sanguo_quality_report.stage32.yaml", type: "quality_report", status: "system_generated", size: "8.7 KB" }
  ],
  novel: {
    chapters: [
      {
        id: "ch_001",
        title: "第一回 刘关张桃园结义",
        paragraphs: [
          { id: "p_001", text: "东汉末年，桓帝、灵帝宠信宦官，致使朝政日益腐败，民不聊生。到汉灵帝在位的时候，终于爆发一场大乱，形成诸侯割据、烽烟四起的局面。" },
          { id: "p_002", text: "巨鹿郡张角、张宝、张梁兄弟三人，在民间瘟疫流行之时，借治病之机广结会众，终于演发成为一场大起义。因起义军都头裹黄巾，故史称为“黄巾起义”。起义军多达四五十万人，声势浩大，所向披靡。灵帝急忙下令各路将领出兵征讨。一时间各路诸侯纷纷招兵买马，形成豪杰并起之势。幽州太守刘焉也发出榜文，招募义兵。" },
          { id: "p_003", text: "榜文行到涿县，引出了一位英雄。此人不甚好读书，生性宽和，寡言少语，喜怒不形于色；胸怀大志，专好结交天下豪杰。他身长七尺五寸，双手过膝，双耳垂肩，生得仪表堂堂。此人是汉中山靖王刘胜的后代，姓刘，名备，字玄德。刘备自幼丧父，对母亲很孝顺。他家境贫寒，一直以织草席卖草鞋为生。这年，刘备已二十八岁了。" },
          { id: "p_004", text: "刘备当日见了榜文，长长地叹息了一声。忽然听见身后一人厉声喝道：“大丈夫不为国家出力，叹什么气！”刘备回头看说话的人，只见他身高八尺，豹头环眼，燕颔虎须，声若巨雷。刘备见他相貌奇异，便问他姓名。这人道：“我姓张，名飞，字翼德，世代居住涿郡，以杀猪卖酒为业，喜欢结交天下豪杰。刚才看见你看榜时叹气，因此相问。”刘备道：“我是汉室宗亲，姓刘名备。现在黄巾作乱，我有心为国杀贼，却恨自己力量不足，因此而叹息。”张飞道：“我家里有不少财产，我们招募乡勇，共图大事，如何？”刘备大喜，便和张飞同到村中酒店饮酒商议。" },
          { id: "p_005", text: "饮酒之间，看见一个大汉推着车子停在店门口，进店就喊酒保：“快拿酒来，我等着进城去投军。”刘备打量此人，见他身高九尺，须长二尺，丹凤眼、卧蚕眉，面如重枣，威风凛凛，相貌堂堂。刘备邀请他同坐，问他姓名，那人道：“我姓关，名羽，字云长。因当年杀了恶霸，流落在外已经五六年了。听说这里招军，特来投奔。”刘备便将他们的打算告诉关羽，关羽大喜，于是一同到张飞的庄上商议。张飞说：“我庄后有一个桃园，花开正盛。明天，我们应当在园中祭告天地，结为兄弟，同心协力，共成大事。”" }
        ]
      }
    ]
  },
  screenplay: {
    scenes: [
      {
        id: "scene_001",
        heading: "INT. 涿县城门口 - 白天",
        source_trace: { chapter_id: "ch_001", paragraph_ids: ["p_003"] },
        beats: [
          {
            id: "beat_001",
            objective: "展现刘备见榜叹气，张飞怒喝引出相识",
            source_trace: { chapter_id: "ch_001", paragraph_ids: ["p_004"] }
          }
        ],
        elements: [
          { type: "action", text: "涿县城门墙上，一张幽州招募义兵的榜文贴在正中央。风吹动着榜文的边角，发出细碎的响声。", source_trace: { chapter_id: "ch_001", paragraph_ids: ["p_003"] } },
          { type: "action", text: "人群拥挤，人们在榜文前指指点点、议论纷纷。刘备站在人群外，身穿粗布衣，扁担靠在旁边的草鞋筐上。", source_trace: { chapter_id: "ch_001", paragraph_ids: ["p_003"] } },
          { type: "action", text: "刘备看着榜文，神色沉郁，重重地叹了口气。", source_trace: { chapter_id: "ch_001", paragraph_ids: ["p_004"] } },
          {
            type: "action",
            text: "她指尖悬在门把上，金属的凉意渗进指腹，三秒后才压下去。",
            source_trace: { chapter_id: "ch_001", paragraph_ids: ["p_004"] },
            ai_tags: { inferred: true, confidence: "high", needs_human_review: true, notes: ["Kimi dialogue candidate crecand_001 applied."] },
            creative_draft_candidate_id: "crecand_001",
            requires_author_approval: true,
            provider_profile: "kimi_creative"
          },
          { type: "dialogue", character_id: "char_002", text: "（在刘备身后爆雷般厉声喝道）\n大丈夫不为国家出力，在这里叹什么气！", source_trace: { chapter_id: "ch_001", paragraph_ids: ["p_004"] } },
          { type: "action", text: "刘备一惊，转过身去。只见张飞叉腰站在他身后，豹头环眼，威风凛凛。", source_trace: { chapter_id: "ch_001", paragraph_ids: ["p_004"] } }
        ]
      }
    ],
    characters: [
      { id: "char_001", name: "刘备", want: "重兴汉室", flaw: "优柔寡断" },
      { id: "char_002", name: "张飞", want: "铲除黄巾，共图大事", flaw: "鲁莽暴躁" }
    ]
  },
  quality_report: {
    readiness: {
      status: "ready_for_author_review",
      score: 98,
      decision: "pass"
    },
    dimensions: [
      { name: "Schema 契约校验", score: 100, status: "pass", description: "完美契约对齐，无任何格式缺陷。" },
      { name: "对白与人物一致性", score: 96, status: "pass", description: "对白语调符合人物设定，且有原文归因证据。" },
      { name: "Fountain 双向回写", score: 100, status: "pass", description: "往返行和映射完美同步，stale 状态更新正确。" },
      { name: "原著忠实度", score: 98, status: "pass", description: "故事节拍与段落源文高保真锚定，不存在幻觉扩张。" }
    ],
    next_actions: [
      "一击采纳 DeepSeek V4-Pro 审校 Agent 的戏剧冲突增强建议",
      "导出最终版交付 Fountain 剧本给排版制片方"
    ]
  },
  reviewer_patches: [
    {
      id: "patch_001",
      agent_id: "beat_dramaturgy_agent",
      type: "conflict_enhancement",
      target: { scene_id: "scene_001", beat_id: "beat_001" },
      proposed_text: "张飞的酒瓮重重地砸在地上，扬起一片尘土，引得旁人纷纷惊惶避让。刘备回头，正好撞上张飞那如鹰般锐利的目光。",
      rationale: "增强张飞出场时的物理压迫感与环境骚动，使刘备与张飞的首次碰撞更具戏剧张力。",
      ai_tags: { inferred: true, confidence: "high", needs_human_review: true },
      confidence: "high",
      status: "pending"
    },
    {
      id: "patch_002",
      agent_id: "source_fidelity_reviewer",
      type: "fidelity_warning",
      target: { scene_id: "scene_001", beat_id: "beat_001" },
      proposed_text: "（警告）剧本中提到刘备随身携带织草席的担子；但小说原文此段仅写‘见了榜文，长长叹息’，未提及随身草鞋。建议淡化挑担子的描摹。",
      rationale: "忠实于原文描写，避免过多后期舞台动作导致的时空不符。",
      ai_tags: { inferred: true, confidence: "medium", needs_human_review: true },
      confidence: "medium",
      status: "pending"
    }
  ]
};
