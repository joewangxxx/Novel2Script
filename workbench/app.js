/**
 * 面向小说作者的 AI 剧本改编工作台 - 前端交互逻辑
 * 遵循 KIs 及 Vanilla JS + CSS 设计准则，利用液态玻璃设计实现流畅微交互
 */

// 主题管理
const ThemeManager = {
  init() {
    const savedTheme = localStorage.getItem("novel2script-theme") || "dark";
    document.documentElement.setAttribute("data-theme", savedTheme);
    const themeBtn = document.getElementById("theme-btn");
    if (themeBtn) {
      themeBtn.addEventListener("click", () => this.toggleTheme());
    }
  },
  toggleTheme() {
    const currentTheme = document.documentElement.getAttribute("data-theme");
    const newTheme = currentTheme === "light" ? "dark" : "light";
    document.documentElement.setAttribute("data-theme", newTheme);
    localStorage.setItem("novel2script-theme", newTheme);
    showToast(`主题已切换为 ${newTheme === "light" ? "💡 浅色" : "🌙 深色"}`);
  }
};

// 吐司提示 (Toast Notification)
function showToast(message, duration = 3000) {
  let toastContainer = document.getElementById("toast-container");
  if (!toastContainer) {
    toastContainer = document.createElement("div");
    toastContainer.id = "toast-container";
    toastContainer.style.position = "fixed";
    toastContainer.style.bottom = "24px";
    toastContainer.style.right = "24px";
    toastContainer.style.zIndex = "9999";
    toastContainer.style.display = "flex";
    toastContainer.style.flexDirection = "column";
    toastContainer.style.gap = "10px";
    document.body.appendChild(toastContainer);
  }

  const toast = document.createElement("div");
  toast.className = "toast-message glass-card";
  toast.style.padding = "12px 24px";
  toast.style.color = "var(--glass-text-primary)";
  toast.style.fontSize = "0.9rem";
  toast.style.fontWeight = "500";
  toast.style.borderLeft = "4px solid var(--primary-accent)";
  toast.style.boxShadow = "0 8px 32px 0 rgba(0, 0, 0, 0.2)";
  toast.style.animation = "slideIn 0.3s cubic-bezier(0.25, 0.8, 0.25, 1)";
  toast.style.backdropFilter = "blur(16px)";
  toast.style.borderRadius = "12px";
  toast.innerText = message;

  toastContainer.appendChild(toast);

  // 添加动画样式
  if (!document.getElementById("toast-animation-style")) {
    const style = document.createElement("style");
    style.id = "toast-animation-style";
    style.innerHTML = `
      @keyframes slideIn {
        from { transform: translateX(120%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
      }
      @keyframes fadeOut {
        from { opacity: 1; transform: translateY(0); }
        to { opacity: 0; transform: translateY(-20px); }
      }
      .flash-active {
        animation: highlight-pulse 2s ease-in-out;
      }
      @keyframes highlight-pulse {
        0% { background: rgba(96, 165, 250, 0.4); border-color: var(--primary-accent); }
        50% { background: rgba(139, 92, 246, 0.3); border-color: #8b5cf6; }
        100% { background: transparent; }
      }
    `;
    document.head.appendChild(style);
  }

  setTimeout(() => {
    toast.style.animation = "fadeOut 0.4s ease forwards";
    setTimeout(() => toast.remove(), 400);
  }, duration);
}

// 全局工作台应用状态
class WorkbenchApp {
  constructor(data) {
    this.data = JSON.parse(JSON.stringify(data)); // 深拷贝初始数据便于重置
    this.selectedNovelParagraphId = null;
    this.selectedScreenplayElementId = null;
    this.activeFile = "test1_sanguo_screenplay.stage32.yaml";
  }

  init() {
    ThemeManager.init();
    this.renderHeader();
    this.renderFileList();
    this.initNovelPane();
    this.renderScreenplay();
    this.renderQualityDashboard();
    this.renderPatches();
    this.bindEvents();
    showToast("工作台初始化成功，已加载项目数据！");
  }

  // 渲染头部元数据
  renderHeader() {
    document.getElementById("project-title").innerText = this.data.project_info.name;
    document.getElementById("project-version").innerText = `Version: ${this.data.project_info.version}`;
    
    const timeFormatted = new Date(this.data.project_info.last_modified).toLocaleString("zh-CN", {
      hour12: false
    });
    document.getElementById("project-time").innerText = `Last Sync: ${timeFormatted}`;
  }

  // 渲染左侧文件管理 (任务 9)
  renderFileList() {
    const fileTree = document.getElementById("file-tree");
    fileTree.innerHTML = "";

    this.data.files.forEach(file => {
      const li = document.createElement("li");
      li.className = `file-item ${file.name === this.activeFile ? 'active' : ''}`;
      
      let badgeClass = "badge-source";
      let statusText = "Source";
      if (file.status === "human_confirmed") {
        badgeClass = "badge-confirmed";
        statusText = "Confirmed";
      } else if (file.status === "ai_inferred") {
        badgeClass = "badge-inferred";
        statusText = "AI Inferred";
      } else if (file.status === "system_generated") {
        badgeClass = "badge-system";
        statusText = "Generated";
      }

      // 根据文件类型挑选文件 icon
      let fileIcon = "📄";
      if (file.type === "novel") fileIcon = "📖";
      else if (file.type === "screenplay") fileIcon = "🎬";
      else if (file.type === "story_map") fileIcon = "🗺️";
      else if (file.type === "character_bible") fileIcon = "👤";
      else if (file.type === "outline") fileIcon = "📝";
      else if (file.type === "quality_report") fileIcon = "📊";

      li.innerHTML = `
        <div class="file-meta">
          <span class="file-name" title="${file.name}">${fileIcon} ${file.name}</span>
          <span class="file-size">${file.size}</span>
        </div>
        <div style="display:flex; justify-content: flex-end; margin-top: 4px;">
          <span class="file-status-badge ${badgeClass}">${statusText}</span>
        </div>
      `;

      li.addEventListener("click", () => {
        document.querySelectorAll(".file-item").forEach(item => item.classList.remove("active"));
        li.classList.add("active");
        this.activeFile = file.name;
        showToast(`已选中项目文件: ${file.name}`);
        this.onFileSwitch(file);
      });

      fileTree.appendChild(li);
    });
  }

  onFileSwitch(file) {
    // 模拟文件切换
    const statusTag = document.getElementById("screenplay-status");
    if (file.type === "screenplay") {
      statusTag.innerText = file.status === "ai_inferred" ? "AI Inferred" : "Human Confirmed";
      statusTag.style.display = "inline-block";
    } else {
      statusTag.style.display = "none";
    }
  }

  // 绑定事件处理器
  bindEvents() {
    // 1. 流水线一键运行 (任务 9)
    const runBtn = document.getElementById("run-pipeline-btn");
    const progressContainer = document.getElementById("pipeline-progress-container");
    const progressFill = document.getElementById("pipeline-progress-fill");
    const progressText = document.getElementById("pipeline-progress-text");

    runBtn.addEventListener("click", () => {
      runBtn.disabled = true;
      progressContainer.classList.remove("hidden");
      progressFill.style.width = "0%";
      progressText.innerText = "正在初始化流水线...";

      const steps = [
        { progress: 15, text: "正在读取并解析小说原文..." },
        { progress: 35, text: "正在提取剧情语义与角色圣经..." },
        { progress: 55, text: "正在自动规划戏剧章节大纲..." },
        { progress: 75, text: "正在运行 Kimi/DeepSeek 协同改编与对白优化..." },
        { progress: 90, text: "正在进行剧本格式与质量契约评估..." },
        { progress: 100, text: "完成！正在刷新工作台..." }
      ];

      let stepIndex = 0;
      const interval = setInterval(() => {
        if (stepIndex < steps.length) {
          const currentStep = steps[stepIndex];
          progressFill.style.width = `${currentStep.progress}%`;
          progressText.innerText = currentStep.text;
          stepIndex++;
        } else {
          clearInterval(interval);
          setTimeout(() => {
            progressContainer.classList.add("hidden");
            runBtn.disabled = false;
            // 重置数据模拟
            this.data = JSON.parse(JSON.stringify(WORKBENCH_DATA));
            this.init();
            showToast("✨ 端到端改编流水线运行成功，已重载最新改编版本！");
          }, 800);
        }
      }, 700);
    });

    // 2. 章节选择
    const chapterSelect = document.getElementById("chapter-select");
    chapterSelect.addEventListener("change", (e) => {
      this.renderNovelContent(e.target.value);
    });
  }

  // 初始化小说面板
  initNovelPane() {
    const chapterSelect = document.getElementById("chapter-select");
    chapterSelect.innerHTML = "";

    this.data.novel.chapters.forEach(ch => {
      const option = document.createElement("option");
      option.value = ch.id;
      option.innerText = ch.title;
      chapterSelect.appendChild(option);
    });

    if (this.data.novel.chapters.length > 0) {
      this.renderNovelContent(this.data.novel.chapters[0].id);
    }
  }

  // 渲染对应章节的小说原文
  renderNovelContent(chapterId) {
    const novelContent = document.getElementById("novel-content");
    novelContent.innerHTML = "";

    const chapter = this.data.novel.chapters.find(ch => ch.id === chapterId);
    if (!chapter) return;

    chapter.paragraphs.forEach(p => {
      const div = document.createElement("div");
      div.className = "novel-paragraph";
      div.id = `para-${p.id}`;
      div.setAttribute("data-p-id", p.id);
      div.innerText = p.text;

      // 双向定位：点击小说原文高亮并滚动定位剧本行
      div.addEventListener("click", () => {
        this.selectNovelParagraph(p.id, true);
      });

      novelContent.appendChild(div);
    });
  }

  // 选中并高亮小说段落
  selectNovelParagraph(paragraphId, triggerScrollToScreenplay = false) {
    this.selectedNovelParagraphId = paragraphId;

    // 清除小说段落的高亮
    document.querySelectorAll(".novel-paragraph").forEach(p => {
      p.classList.remove("highlight");
    });

    const targetPara = document.getElementById(`para-${paragraphId}`);
    if (targetPara) {
      targetPara.classList.add("highlight");
      // 平滑滚动小说段落到中间
      targetPara.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    // 获取小说文本并在原著溯源面板显示
    let paragraphText = "";
    this.data.novel.chapters.forEach(ch => {
      const found = ch.paragraphs.find(p => p.id === paragraphId);
      if (found) paragraphText = found.text;
    });

    this.updateTraceabilityCard([paragraphId], paragraphText);

    // 如果需要联动滚动到剧本
    if (triggerScrollToScreenplay) {
      this.scrollToAssociatedScreenplay(paragraphId);
    }
  }

  // 渲染改编剧本 (任务 8)
  renderScreenplay() {
    const spContent = document.getElementById("screenplay-content");
    spContent.innerHTML = "";

    this.data.screenplay.scenes.forEach(scene => {
      // 1. Scene Heading
      const sceneDiv = document.createElement("div");
      sceneDiv.className = "screenplay-element sp-scene-heading";
      sceneDiv.id = `sp-element-${scene.id}`;
      sceneDiv.innerText = scene.heading;
      sceneDiv.setAttribute("data-type", "scene");
      sceneDiv.setAttribute("data-source-paragraphs", scene.source_trace?.paragraph_ids?.join(",") || "");
      
      sceneDiv.addEventListener("click", () => {
        this.selectScreenplayElement(scene.id, scene.source_trace?.paragraph_ids || []);
      });
      spContent.appendChild(sceneDiv);

      // 2. Beats
      scene.beats.forEach(beat => {
        const beatDiv = document.createElement("div");
        beatDiv.className = "screenplay-element sp-beat-objective";
        beatDiv.id = `sp-element-${beat.id}`;
        beatDiv.innerText = `[剧本节奏目标] ${beat.objective}`;
        beatDiv.setAttribute("data-type", "beat");
        beatDiv.setAttribute("data-source-paragraphs", beat.source_trace?.paragraph_ids?.join(",") || "");

        beatDiv.addEventListener("click", () => {
          this.selectScreenplayElement(beat.id, beat.source_trace?.paragraph_ids || []);
        });
        spContent.appendChild(beatDiv);
      });

      // 3. Elements (Actions, Dialogues)
      scene.elements.forEach((el, index) => {
        const elId = `el-${scene.id}-${index}`;
        const elDiv = document.createElement("div");
        elDiv.id = `sp-element-${elId}`;
        elDiv.setAttribute("data-source-paragraphs", el.source_trace?.paragraph_ids?.join(",") || "");

        // 判断 AI 标签
        const isAiInferred = el.ai_tags?.inferred || false;
        const aiTagHtml = isAiInferred ? `<span class="ai-element-tag" title="置信度: ${el.ai_tags.confidence || '高'}">AI Inferred</span>` : "";

        if (el.type === "action") {
          elDiv.className = "screenplay-element sp-action";
          elDiv.innerHTML = `${el.text} ${aiTagHtml}`;
          elDiv.setAttribute("data-type", "action");
        } else if (el.type === "dialogue") {
          elDiv.className = "screenplay-element sp-dialogue";
          elDiv.setAttribute("data-type", "dialogue");
          // 查找人物名称
          const character = this.data.screenplay.characters.find(c => c.id === el.character_id);
          const name = character ? character.name : "未知人物";
          
          elDiv.innerHTML = `
            <span class="dialogue-char">${name}</span>
            <span class="dialogue-text">${el.text.replace(/\n/g, "<br>")} ${aiTagHtml}</span>
          `;
        } else if (el.type === "note") {
          elDiv.className = "screenplay-element sp-note";
          elDiv.innerHTML = `Note: ${el.text}`;
          elDiv.setAttribute("data-type", "note");
        }

        elDiv.addEventListener("click", () => {
          this.selectScreenplayElement(elId, el.source_trace?.paragraph_ids || []);
        });

        spContent.appendChild(elDiv);
      });
    });
  }

  // 选中并高亮剧本元素
  selectScreenplayElement(elementId, sourceParagraphIds) {
    this.selectedScreenplayElementId = elementId;

    // 清除剧本中的所有高亮
    document.querySelectorAll(".screenplay-element").forEach(el => {
      el.classList.remove("highlight");
    });

    const targetEl = document.getElementById(`sp-element-${elementId}`);
    if (targetEl) {
      targetEl.classList.add("highlight");
      targetEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    // 触发左侧小说原文的高亮与对齐
    if (sourceParagraphIds && sourceParagraphIds.length > 0) {
      const firstParaId = sourceParagraphIds[0];
      
      // 清除别的小说原文高亮，把匹配到的全高亮
      document.querySelectorAll(".novel-paragraph").forEach(p => p.classList.remove("highlight"));
      
      let combinedText = [];
      sourceParagraphIds.forEach(pId => {
        const pEl = document.getElementById(`para-${pId}`);
        if (pEl) {
          pEl.classList.add("highlight");
          combinedText.push(pEl.innerText);
        }
      });

      // 滚动第一个匹配的小说段落到视野中
      const firstEl = document.getElementById(`para-${firstParaId}`);
      if (firstEl) {
        firstEl.scrollIntoView({ behavior: "smooth", block: "center" });
      }

      this.updateTraceabilityCard(sourceParagraphIds, combinedText.join("\n\n"));
    } else {
      this.updateTraceabilityCard([], null);
    }
  }

  // 根据小说原文段落 ID 寻找关联的剧本元素并滚动
  scrollToAssociatedScreenplay(paragraphId) {
    const screenplayElements = document.querySelectorAll(".screenplay-element");
    let found = false;

    for (let el of screenplayElements) {
      const sourceParaStr = el.getAttribute("data-source-paragraphs");
      if (sourceParaStr) {
        const paraIds = sourceParaStr.split(",");
        if (paraIds.includes(paragraphId)) {
          // 选中并高亮剧本元素（不联动小说滚动以避免循环死锁）
          const elementId = el.id.replace("sp-element-", "");
          this.selectedScreenplayElementId = elementId;

          document.querySelectorAll(".screenplay-element").forEach(x => x.classList.remove("highlight"));
          el.classList.add("highlight");
          el.scrollIntoView({ behavior: "smooth", block: "center" });
          found = true;
          break; // 定位第一个匹配项
        }
      }
    }

    if (!found) {
      showToast("此小说段落尚未映射到具体剧本 Scene 或 Beat 行");
    }
  }

  // 更新原著溯源卡片内容
  updateTraceabilityCard(paragraphIds, text) {
    const card = document.getElementById("traceability-card");
    if (!text || paragraphIds.length === 0) {
      card.className = "empty-traceability-card glass-subcard";
      card.innerHTML = `<p class="placeholder-text">点击左侧剧本中的 AI 片段或行以触发原著平滑双向溯源定位...</p>`;
      return;
    }

    card.className = "traceability-card-content glass-subcard";
    card.innerHTML = `
      <div class="trace-header">
        <span>段落 ID: ${paragraphIds.join(", ")}</span>
        <span>双向平滑溯源</span>
      </div>
      <p class="trace-quote">${text}</p>
    `;
  }

  // 渲染质量 Dashboard
  renderQualityDashboard() {
    const report = this.data.quality_report;
    document.getElementById("quality-score").innerText = report.readiness.score;
    
    const decisionBadge = document.getElementById("quality-decision");
    decisionBadge.innerText = report.readiness.decision.toUpperCase();
    
    if (report.readiness.decision === "pass") {
      decisionBadge.style.color = "var(--success-accent)";
      decisionBadge.style.backgroundColor = "rgba(52, 211, 153, 0.15)";
      decisionBadge.style.borderColor = "rgba(52, 211, 153, 0.3)";
    } else {
      decisionBadge.style.color = "var(--danger-accent)";
      decisionBadge.style.backgroundColor = "rgba(248, 113, 113, 0.15)";
      decisionBadge.style.borderColor = "rgba(248, 113, 113, 0.3)";
    }

    const dimsList = document.getElementById("quality-dimensions");
    dimsList.innerHTML = "";

    report.dimensions.forEach(dim => {
      const div = document.createElement("div");
      div.className = "dim-item";
      
      const isPass = dim.status === "pass";
      const scoreColor = isPass ? "var(--success-accent)" : "var(--warning-accent)";
      const barColor = isPass ? "var(--success-accent)" : "var(--warning-accent)";

      div.innerHTML = `
        <div style="display: flex; flex-direction: column; width: 100%;">
          <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
            <span class="dim-name">${dim.name}</span>
            <span class="dim-score" style="color: ${scoreColor}; font-weight: bold;">${dim.score}%</span>
          </div>
          <div style="width: 100%; height: 6px; background: rgba(255, 255, 255, 0.08); border-radius: 99px; overflow: hidden;">
            <div style="width: ${dim.score}%; height: 100%; background: ${barColor}; border-radius: 99px; transition: width 0.5s ease-out;"></div>
          </div>
        </div>
      `;
      dimsList.appendChild(div);
    });
  }

  // 渲染修改建议 Patch
  renderPatches() {
    const container = document.getElementById("patches-container");
    container.innerHTML = "";

    const activePatches = this.data.reviewer_patches;
    if (activePatches.length === 0) {
      container.innerHTML = `<p class="placeholder-text">当前暂无待处理的审校建议。</p>`;
      return;
    }

    activePatches.forEach(patch => {
      const card = document.createElement("div");
      card.className = "glass-subcard patch-card";
      card.id = `patch-card-${patch.id}`;

      let actionHtml = "";
      if (patch.status === "pending") {
        actionHtml = `
          <div class="patch-actions" style="margin-top: 8px;">
            <button class="btn-patch btn-accept" data-patch-id="${patch.id}">采纳</button>
            <button class="btn-patch btn-reject" data-patch-id="${patch.id}">拒绝</button>
          </div>
        `;
      } else if (patch.status === "accepted") {
        actionHtml = `<div style="text-align: right; font-size: 0.8rem; color: var(--success-accent); font-weight: 600; margin-top: 6px;">✓ 已采纳</div>`;
      } else {
        actionHtml = `<div style="text-align: right; font-size: 0.8rem; color: var(--danger-accent); font-weight: 600; margin-top: 6px;">✗ 已拒绝</div>`;
      }

      let agentBadgeColor = "var(--warning-accent)";
      if (patch.agent_id === "source_fidelity_reviewer") {
        agentBadgeColor = "var(--primary-accent)";
      }

      card.innerHTML = `
        <div class="patch-header">
          <span class="patch-agent-tag" style="color: ${agentBadgeColor}; border-color: ${agentBadgeColor}; background: rgba(255,255,255,0.02);">${patch.agent_id}</span>
          <span class="patch-confidence">置信度: ${patch.confidence === 'high' ? '🔥 高' : '⚡ 中'}</span>
        </div>
        <div class="patch-text" style="margin: 6px 0;">${patch.proposed_text}</div>
        <div class="patch-rationale" style="font-size: 0.72rem; color: var(--glass-text-muted); line-height: 1.4;">
          <strong>建议理由:</strong> ${patch.rationale}
        </div>
        ${actionHtml}
      `;

      // 事件绑定
      if (patch.status === "pending") {
        card.querySelector(".btn-accept").addEventListener("click", () => this.applyPatch(patch.id));
        card.querySelector(".btn-reject").addEventListener("click", () => this.rejectPatch(patch.id));
      }

      container.appendChild(card);
    });
  }

  // 采纳审校建议 (任务 8)
  applyPatch(patchId) {
    const patch = this.data.reviewer_patches.find(p => p.id === patchId);
    if (!patch) return;

    patch.status = "accepted";
    showToast(`✓ 已采纳建议: ${patch.agent_id}`);

    // 执行剧本回填与修改：
    // 根据 patch 的 target（例如 { scene_id: "scene_001", beat_id: "beat_001" }）
    // 我们可以直接在 `screenplay.scenes` 中找到对应的 scene 并更新其下的 beat 或者动作。
    const target = patch.target;
    let modifiedElementId = null;

    if (target) {
      const scene = this.data.screenplay.scenes.find(s => s.id === target.scene_id);
      if (scene) {
        if (target.beat_id) {
          // 修改 beat 的 objective
          const beat = scene.beats.find(b => b.id === target.beat_id);
          if (beat) {
            beat.objective = patch.proposed_text;
            modifiedElementId = beat.id;
          }
          
          // 如果是冲突增强，也可以直接在 scene 里面寻找合适的 action element 替换，或者插入一个新的 action
          // 为了演示高精度的回填，如果在 elements 中有匹配的 source_trace，我们将其 text 进行替换
          // 我们这里对 beat 修改同时，寻找 scene 下第一个 action，替换或者追加
          if (patch.agent_id === "beat_dramaturgy_agent") {
            const firstAction = scene.elements.find(el => el.type === "action");
            if (firstAction) {
              firstAction.text = patch.proposed_text;
              firstAction.ai_tags = { inferred: true, confidence: "high", needs_human_review: false };
              modifiedElementId = `el-${scene.id}-0`; // 对应渲染的 el 元素 ID
            }
          }
        }
      }
    }

    // 重新渲染剧本与修改建议栏
    this.renderScreenplay();
    this.renderPatches();

    // 如果修改了元素，加上高光闪烁动效
    if (modifiedElementId) {
      const elDom = document.getElementById(`sp-element-${modifiedElementId}`);
      if (elDom) {
        elDom.classList.add("flash-active");
        elDom.scrollIntoView({ behavior: "smooth", block: "center" });
        setTimeout(() => {
          elDom.classList.remove("flash-active");
        }, 2000);
      }
    }
  }

  // 拒绝审校建议
  rejectPatch(patchId) {
    const patch = this.data.reviewer_patches.find(p => p.id === patchId);
    if (!patch) return;

    patch.status = "rejected";
    showToast(`✗ 已拒绝建议: ${patch.agent_id}`);
    this.renderPatches();
  }
}

// 页面加载完毕后运行
window.addEventListener("DOMContentLoaded", () => {
  if (typeof WORKBENCH_DATA !== "undefined") {
    window.app = new WorkbenchApp(WORKBENCH_DATA);
    window.app.init();
  } else {
    console.error("Error: WORKBENCH_DATA is not defined. Please check data_fixture.js");
  }
});
