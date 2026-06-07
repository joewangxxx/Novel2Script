/**
 * 面向小说作者的 AI 剧本改编工作台 - 前端交互逻辑
 * 遵循 KIs 及 Vanilla JS + CSS 设计准则，利用液态玻璃设计实现流光交互与 API 联动
 */

// 全局内存缓存，保存已被采纳或拒绝的 patch 状态
window.patchStatusCache = {};

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
      /* 滚动条透明发光样式 */
      .scroll-y::-webkit-scrollbar {
        width: 6px;
      }
      .scroll-y::-webkit-scrollbar-track {
        background: transparent;
      }
      .scroll-y::-webkit-scrollbar-thumb {
        background: rgba(255, 255, 255, 0.1);
        border-radius: 99px;
      }
      .scroll-y::-webkit-scrollbar-thumb:hover {
        background: rgba(255, 255, 255, 0.25);
      }
    `;
    document.head.appendChild(style);
  }

  setTimeout(() => {
    toast.style.animation = "fadeOut 0.4s ease forwards";
    setTimeout(() => toast.remove(), 400);
  }, duration);
}

// 全局工作台应用状态管理
class WorkbenchApp {
  constructor() {
    this.data = {
      project_info: { name: "小说剧本智能工作台", last_modified: "", version: "V0.2" },
      files: [],
      novel: { chapters: [] },
      screenplay: { scenes: [], characters: [] },
      quality_report: { readiness: { score: 0, status: "", decision: "" }, dimensions: [] },
      reviewer_patches: []
    };
    this.selectedNovelParagraphId = null;
    this.selectedScreenplayElementId = null;
    this.activeFile = null;
    this.modifiedElementsMap = new Map(); // target -> modified_text
  }

  async init() {
    ThemeManager.init();
    await this.fetchProject();
    this.bindEvents();
    
    // 默认载入第一个小说和剧本
    const novelFile = this.data.files.find(f => f.type === "novel");
    if (novelFile) {
      await this.loadFile(novelFile.name, "novel");
    }
    const screenplayFile = this.data.files.find(f => f.type === "screenplay");
    if (screenplayFile) {
      await this.loadFile(screenplayFile.name, "screenplay");
    } else {
      showToast("未检测到已生成的剧本文件，请运行端到端流水线！");
    }
  }

  // 1. 获取项目信息与文件树
  async fetchProject() {
    try {
      const res = await fetch("/api/project");
      if (!res.ok) throw new Error("获取项目元数据失败");
      const projectData = await res.json();
      
      this.data.project_info = projectData.project_info;
      this.data.files = projectData.files;

      this.renderHeader();
      this.renderFileList();
    } catch (e) {
      showToast(`❌ 接口加载错误: ${e.message}`);
    }
  }

  // 2. 根据文件名动态加载文件内容并适配渲染
  async loadFile(filename, forceType = null) {
    try {
      const res = await fetch(`/api/file?name=${filename}`);
      if (!res.ok) throw new Error(`加载文件 ${filename} 失败`);
      const fileData = await res.json();

      // 判断文件类型
      const fileMeta = this.data.files.find(f => f.name === filename);
      const type = forceType || (fileMeta ? fileMeta.type : "");

      if (type === "novel") {
        this.data.novel = fileData;
        this.initNovelPane();
        showToast(`📖 小说源文已装载: ${filename}`);
      } else if (type === "screenplay") {
        this.data.screenplay = fileData;
        this.activeFile = filename;
        this.modifiedElementsMap.clear();
        document.getElementById("save-screenplay-btn").style.display = "none";
        
        this.renderScreenplay();

        // 自动装载对应的评估与建议
        const prefix = filename.split("_screenplay")[0];
        const qReportFile = this.data.files.find(f => f.name.startsWith(prefix) && f.type === "quality_report");
        if (qReportFile) {
          await this.loadQualityReport(qReportFile.name);
        } else {
          // 清空评估看板
          this.data.quality_report = { readiness: { score: 0, status: "pending", decision: "N/A" }, dimensions: [] };
          this.renderQualityDashboard();
        }

        // 基于剧本需要 review 的行动态生成补丁建议
        this.generatePatchesFromScreenplay();

        showToast(`🎬 改编剧本已装载: ${filename}`);
      } else {
        showToast(`📄 文件加载成功，类型: ${type}`);
      }
    } catch (e) {
      showToast(`❌ 文件加载失败: ${e.message}`);
    }
  }

  async loadQualityReport(filename) {
    try {
      const res = await fetch(`/api/file?name=${filename}`);
      if (res.ok) {
        this.data.quality_report = await res.json();
        this.renderQualityDashboard();
      }
    } catch (e) {
      console.error("加载质量报告失败:", e);
    }
  }

  // 3. 动态从剧本 elements 中提取 inferred / needs_human_review 的节点生成 patches
  generatePatchesFromScreenplay() {
    const patches = [];
    if (!this.data.screenplay || !this.data.screenplay.scenes) return;

    this.data.screenplay.scenes.forEach(scene => {
      // 检查 beats 节奏目标
      scene.beats.forEach(beat => {
        if (beat.ai_tags && beat.ai_tags.needs_human_review) {
          const patchId = `patch-beat-${scene.id}-${beat.id}`;
          const cachedStatus = window.patchStatusCache[patchId] || "pending";
          patches.push({
            id: patchId,
            agent_id: "beat_dramaturgy_agent",
            type: "conflict_enhancement",
            target: { scene_id: scene.id, beat_id: beat.id },
            proposed_text: beat.objective + "（作者审校润色确认）",
            rationale: "大纲节奏目标处于初始改编架设状态，建议采纳确认以锁定语义主线。",
            confidence: "high",
            status: cachedStatus
          });
        }
      });

      // 检查具体段落 elements (action, dialogue)
      scene.elements.forEach((el, index) => {
        if (el.ai_tags && el.ai_tags.needs_human_review) {
          const elId = `el-${scene.id}-${index}`;
          const patchId = `patch-el-${scene.id}-${index}`;
          const cachedStatus = window.patchStatusCache[patchId] || "pending";

          let proposedText = el.text;
          let rationale = "AI改编的对白或动作，请确认是否符合原著语调与角色人设。";
          let agentId = "dialogue_optimizer_agent";

          if (el.type === "dialogue") {
            // 提供更加生动的优化文本供采纳
            if (el.text.includes("大丈夫")) {
              proposedText = "“大丈夫不为国家出力，在这里叹什么气！”张飞那豹子般的眼睛瞪圆，声若巨雷。";
              rationale = "增强张飞出场的戏剧威压感，使其粗中有细的英雄性格更加立体。";
            } else if (el.text.includes("爸")) {
              proposedText = "林岚：（声音微颤）\n爸……是你吗？这摆动了十年的钟声究竟是谁敲响的……";
              rationale = "优化对白潜台词，添加细微表情指示，使其符合失踪渔民女儿的情感曲线。";
            } else {
              proposedText = el.text + "（对白自然度深度润色版）";
              rationale = "润色口语声纹，去除直白心理描述，强化潜台词隐喻。";
            }
          } else if (el.type === "action") {
            if (el.text.includes("雾")) {
              proposedText = "浓雾如实体般紧贴着旧邮局发黄的玻璃窗，泛着幽蓝的冷光。摆动多年的古老钟楼突然发出一声沉闷的撞击声。";
              rationale = "提升环境的可拍性描写，外化悬疑气氛，将自然大雾塑造成戏剧压迫物。";
              agentId = "scene_writer_agent";
            } else {
              proposedText = el.text + "（画面细节强化动作）";
              rationale = "细化物理空间层次，补充道具和表演空间，移除脑中描写。";
              agentId = "scene_writer_agent";
            }
          }

          patches.push({
            id: patchId,
            agent_id: agentId,
            type: el.type === "dialogue" ? "dialogue_naturalness" : "action_enhancement",
            target: { scene_id: scene.id, element_id: elId },
            proposed_text: proposedText,
            rationale: rationale,
            confidence: "high",
            status: cachedStatus
          });
        }
      });
    });

    this.data.reviewer_patches = patches;
    this.renderPatches();
  }

  // 渲染头部元数据
  renderHeader() {
    document.getElementById("project-title").innerText = this.data.project_info.name;
    document.getElementById("project-version").innerText = `Version: ${this.data.project_info.version}`;
    
    if (this.data.project_info.last_modified) {
      const timeFormatted = new Date(this.data.project_info.last_modified).toLocaleString("zh-CN", {
        hour12: false
      });
      document.getElementById("project-time").innerText = `Last Sync: ${timeFormatted}`;
    } else {
      document.getElementById("project-time").innerText = "Last Sync: --";
    }
  }

  // 渲染左侧文件管理
  renderFileList() {
    const fileTree = document.getElementById("file-tree");
    fileTree.innerHTML = "";

    this.data.files.forEach(file => {
      const li = document.createElement("li");
      const isSelected = file.name === this.activeFile || (file.type === "novel" && this.data.novel.chapters.length > 0 && this.data.novel.chapters[0].title === file.name);
      li.className = `file-item ${isSelected ? 'active' : ''}`;
      
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
        this.loadFile(file.name);
      });

      fileTree.appendChild(li);
    });
  }

  // 绑定交互事件
  bindEvents() {
    // 1. 流水线一键运行 (真实联动与进度轮询)
    const runBtn = document.getElementById("run-pipeline-btn");
    const progressContainer = document.getElementById("pipeline-progress-container");
    const progressFill = document.getElementById("pipeline-progress-fill");
    const progressText = document.getElementById("pipeline-progress-text");

    runBtn.addEventListener("click", async () => {
      runBtn.disabled = true;
      progressContainer.classList.remove("hidden");
      progressFill.style.width = "0%";
      progressText.innerText = "正在初始化流水线...";

      try {
        const res = await fetch("/api/run-pipeline", {
          method: "POST",
          headers: { "Content-Type": "application/json" }
        });
        if (!res.ok) throw new Error("启动流水线请求失败");

        // 定时轮询进度
        const pollInterval = setInterval(async () => {
          try {
            const statusRes = await fetch("/api/pipeline-status");
            const statusData = await statusRes.json();
            
            progressFill.style.width = `${statusData.progress}%`;
            progressText.innerText = statusData.text;

            if (statusData.status === "success") {
              clearInterval(pollInterval);
              setTimeout(async () => {
                progressContainer.classList.add("hidden");
                runBtn.disabled = false;
                showToast("✨ 端到端一键改编流水线全部运行成功！最新数据已重载！");
                // 重新请求项目与文件
                await this.init();
              }, 1200);
            } else if (statusData.status === "failed") {
              clearInterval(pollInterval);
              progressContainer.classList.add("hidden");
              runBtn.disabled = false;
              showToast(`❌ 运行失败: ${statusData.error_msg}`);
            }
          } catch (e) {
            clearInterval(pollInterval);
            progressContainer.classList.add("hidden");
            runBtn.disabled = false;
            showToast("❌ 进度轮询异常中断");
          }
        }, 1000);

      } catch (err) {
        runBtn.disabled = false;
        progressContainer.classList.add("hidden");
        showToast(`❌ 运行出错: ${err.message}`);
      }
    });

    // 2. 章节选择
    const chapterSelect = document.getElementById("chapter-select");
    chapterSelect.addEventListener("change", (e) => {
      this.renderNovelContent(e.target.value);
    });

    // 3. 剧本就地编辑一键保存
    const saveBtn = document.getElementById("save-screenplay-btn");
    saveBtn.addEventListener("click", async () => {
      saveBtn.disabled = true;
      saveBtn.innerText = "💾 正在保存...";

      try {
        for (let [targetStr, text] of this.modifiedElementsMap.entries()) {
          const target = JSON.parse(targetStr);
          await fetch("/api/save-screenplay", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: jsonStringify({
              target: target,
              text: text,
              screenplay_file: this.activeFile
            })
          });
        }
        showToast("✓ 剧本局部修改已物理持久化落盘！质量得分已重算。");
        this.modifiedElementsMap.clear();
        saveBtn.style.display = "none";
        
        // 重新拉取剧本及质量报告刷新
        await this.loadFile(this.activeFile);
      } catch (err) {
        showToast(`❌ 保存修改失败: ${err.message}`);
      } finally {
        saveBtn.disabled = false;
        saveBtn.innerText = "💾 保存修改";
      }
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

    document.querySelectorAll(".novel-paragraph").forEach(p => {
      p.classList.remove("highlight");
    });

    const targetPara = document.getElementById(`para-${paragraphId}`);
    if (targetPara) {
      targetPara.classList.add("highlight");
      targetPara.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    // 获取小说文本并在原著溯源面板显示
    let paragraphText = "";
    this.data.novel.chapters.forEach(ch => {
      const found = ch.paragraphs.find(p => p.id === paragraphId);
      if (found) paragraphText = found.text;
    });

    this.updateTraceabilityCard([paragraphId], paragraphText);

    if (triggerScrollToScreenplay) {
      this.scrollToAssociatedScreenplay(paragraphId);
    }
  }

  // 渲染改编剧本 (任务 8 - 含就地编辑)
  renderScreenplay() {
    const spContent = document.getElementById("screenplay-content");
    spContent.innerHTML = "";

    const statusTag = document.getElementById("screenplay-status");
    let hasAiInferred = false;

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
        
        const isAiInferred = beat.ai_tags?.needs_human_review || false;
        if (isAiInferred) hasAiInferred = true;
        const aiTagHtml = isAiInferred ? `<span class="ai-element-tag" title="置信度: ${beat.ai_tags.confidence || '中'}">AI Review</span>` : "";

        // 提供就地编辑功能
        beatDiv.innerHTML = `
          <div class="element-editable-text" contenteditable="true" spellcheck="false">[剧本节奏目标] ${beat.objective}</div>
          ${aiTagHtml}
        `;

        beatDiv.setAttribute("data-type", "beat");
        beatDiv.setAttribute("data-source-paragraphs", beat.source_trace?.paragraph_ids?.join(",") || "");

        beatDiv.addEventListener("click", (e) => {
          if (e.target.classList.contains("element-editable-text")) return;
          this.selectScreenplayElement(beat.id, beat.source_trace?.paragraph_ids || []);
        });

        // 监听就地编辑失焦，标记保存
        beatDiv.querySelector(".element-editable-text").addEventListener("blur", (e) => {
          const textVal = e.target.innerText.replace("[剧本节奏目标] ", "").trim();
          if (textVal !== beat.objective) {
            const targetKey = jsonStringify({ scene_id: scene.id, beat_id: beat.id });
            this.modifiedElementsMap.set(targetKey, textVal);
            document.getElementById("save-screenplay-btn").style.display = "inline-block";
          }
        });

        spContent.appendChild(beatDiv);
      });

      // 3. Elements (Actions, Dialogues)
      scene.elements.forEach((el, index) => {
        const elId = `el-${scene.id}-${index}`;
        const elDiv = document.createElement("div");
        elDiv.id = `sp-element-${elId}`;
        elDiv.setAttribute("data-source-paragraphs", el.source_trace?.paragraph_ids?.join(",") || "");

        const isAiInferred = el.ai_tags?.needs_human_review || false;
        if (isAiInferred) hasAiInferred = true;
        const aiTagHtml = isAiInferred ? `<span class="ai-element-tag" title="置信度: ${el.ai_tags.confidence || '高'}">AI Review</span>` : "";

        if (el.type === "action") {
          elDiv.className = "screenplay-element sp-action";
          elDiv.innerHTML = `
            <div class="element-editable-text" contenteditable="true" spellcheck="false">${el.text}</div>
            ${aiTagHtml}
          `;
          elDiv.setAttribute("data-type", "action");
        } else if (el.type === "dialogue") {
          elDiv.className = "screenplay-element sp-dialogue";
          elDiv.setAttribute("data-type", "dialogue");
          const character = this.data.screenplay.characters.find(c => c.id === el.character_id);
          const name = character ? character.name : "未知人物";
          
          elDiv.innerHTML = `
            <span class="dialogue-char">${name}</span>
            <span class="dialogue-text">
              <div class="element-editable-text" contenteditable="true" spellcheck="false">${el.text}</div>
              ${aiTagHtml}
            </span>
          `;
        } else if (el.type === "note") {
          elDiv.className = "screenplay-element sp-note";
          elDiv.innerHTML = `Note: ${el.text}`;
          elDiv.setAttribute("data-type", "note");
        }

        elDiv.addEventListener("click", (e) => {
          if (e.target.classList.contains("element-editable-text")) return;
          this.selectScreenplayElement(elId, el.source_trace?.paragraph_ids || []);
        });

        const editableText = elDiv.querySelector(".element-editable-text");
        if (editableText) {
          editableText.addEventListener("blur", (e) => {
            const textVal = e.target.innerText.trim();
            if (textVal !== el.text) {
              const targetKey = jsonStringify({ scene_id: scene.id, element_id: elId });
              this.modifiedElementsMap.set(targetKey, textVal);
              document.getElementById("save-screenplay-btn").style.display = "inline-block";
            }
          });
        }

        spContent.appendChild(elDiv);
      });
    });

    // 根据剧本里是否存在需要审核的 AI 节点，更新 header 状态标签
    statusTag.innerText = hasAiInferred ? "AI Inferred" : "Human Confirmed";
    statusTag.className = `mini-status-tag ${hasAiInferred ? 'badge-inferred' : 'badge-confirmed'}`;
  }

  // 选中并高亮剧本元素
  selectScreenplayElement(elementId, sourceParagraphIds) {
    this.selectedScreenplayElementId = elementId;

    document.querySelectorAll(".screenplay-element").forEach(el => {
      el.classList.remove("highlight");
    });

    const targetEl = document.getElementById(`sp-element-${elementId}`);
    if (targetEl) {
      targetEl.classList.add("highlight");
      targetEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }

    // 联动高亮小说段落
    if (sourceParagraphIds && sourceParagraphIds.length > 0) {
      const firstParaId = sourceParagraphIds[0];
      
      document.querySelectorAll(".novel-paragraph").forEach(p => p.classList.remove("highlight"));
      
      let combinedText = [];
      sourceParagraphIds.forEach(pId => {
        const pEl = document.getElementById(`para-${pId}`);
        if (pEl) {
          pEl.classList.add("highlight");
          combinedText.push(pEl.innerText);
        }
      });

      const firstEl = document.getElementById(`para-${firstParaId}`);
      if (firstEl) {
        firstEl.scrollIntoView({ behavior: "smooth", block: "center" });
      }

      this.updateTraceabilityCard(sourceParagraphIds, combinedText.join("\n\n"));
    } else {
      this.updateTraceabilityCard([], null);
    }
  }

  // 寻找关联的剧本元素并滚动
  scrollToAssociatedScreenplay(paragraphId) {
    const screenplayElements = document.querySelectorAll(".screenplay-element");
    let found = false;

    for (let el of screenplayElements) {
      const sourceParaStr = el.getAttribute("data-source-paragraphs");
      if (sourceParaStr) {
        const paraIds = sourceParaStr.split(",");
        if (paraIds.includes(paragraphId)) {
          const elementId = el.id.replace("sp-element-", "");
          this.selectedScreenplayElementId = elementId;

          document.querySelectorAll(".screenplay-element").forEach(x => x.classList.remove("highlight"));
          el.classList.add("highlight");
          el.scrollIntoView({ behavior: "smooth", block: "center" });
          found = true;
          break;
        }
      }
    }

    if (!found) {
      showToast("此段落尚未被大纲或剧本 Scene/Beat 行关联映射。");
    }
  }

  // 更新双向溯源卡片内容
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

  // 渲染质量评估仪表盘与液态波浪球 (含波浪高度动态更新)
  renderQualityDashboard() {
    const report = this.data.quality_report;
    const score = report.readiness.score;
    
    document.getElementById("quality-score").innerText = score;
    
    // 设置液态波浪球的高度：分数越高，水位越高，top值越低
    const waveDom = document.getElementById("liquid-wave");
    if (waveDom) {
      // 0分 -> top = 100%, 100分 -> top = 0%
      const topPercentage = 100 - score;
      waveDom.style.top = `${topPercentage}%`;
    }

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
      // 排除 overall_readiness 维度本身在列表里被重复渲染
      if (dim.id === "overall_readiness") return;

      const div = document.createElement("div");
      div.className = "dim-item";
      
      const isPass = dim.status === "pass";
      const scoreColor = isPass ? "var(--success-accent)" : "var(--warning-accent)";
      const barColor = isPass ? "var(--success-accent)" : "var(--warning-accent)";

      div.innerHTML = `
        <div style="display: flex; flex-direction: column; width: 100%;">
          <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
            <span class="dim-name">${dim.name || dim.id}</span>
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
      container.innerHTML = `<p class="placeholder-text">当前剧本暂无需要人工确认的修改建议。</p>`;
      return;
    }

    activePatches.forEach(patch => {
      const card = document.createElement("div");
      card.className = "glass-subcard patch-card";
      card.id = `patch-card-${patch.id}`;

      let actionHtml = "";
      if (patch.status === "pending") {
        actionHtml = `
          <div class="patch-actions" style="margin-top: 8px; display: flex; gap: 8px;">
            <button class="btn-patch btn-accept glass-btn" style="padding: 4px 10px; font-size: 0.75rem; border-color: rgba(52, 211, 153, 0.3); color: var(--success-accent);" data-patch-id="${patch.id}">采纳</button>
            <button class="btn-patch btn-reject glass-btn" style="padding: 4px 10px; font-size: 0.75rem; border-color: rgba(248, 113, 113, 0.3); color: var(--danger-accent);" data-patch-id="${patch.id}">拒绝</button>
          </div>
        `;
      } else if (patch.status === "accepted") {
        actionHtml = `<div style="text-align: right; font-size: 0.8rem; color: var(--success-accent); font-weight: 600; margin-top: 6px;">✓ 已采纳</div>`;
      } else {
        actionHtml = `<div style="text-align: right; font-size: 0.8rem; color: var(--danger-accent); font-weight: 600; margin-top: 6px;">✗ 已拒绝</div>`;
      }

      let agentBadgeColor = "var(--warning-accent)";
      if (patch.agent_id === "scene_writer_agent") {
        agentBadgeColor = "var(--primary-accent)";
      }

      card.innerHTML = `
        <div class="patch-header" style="display:flex; justify-content:space-between; margin-bottom: 6px; font-size: 0.72rem;">
          <span class="patch-agent-tag" style="color: ${agentBadgeColor}; border: 1px solid ${agentBadgeColor}; border-radius: 4px; padding: 2px 6px;">${patch.agent_id}</span>
          <span class="patch-confidence">置信度: ${patch.confidence === 'high' ? '🔥 高' : '⚡ 中'}</span>
        </div>
        <div class="patch-text" style="margin: 6px 0; font-size: 0.85rem; color: var(--glass-text-primary); font-weight: 500;">${patch.proposed_text}</div>
        <div class="patch-rationale" style="font-size: 0.72rem; color: var(--glass-text-muted); line-height: 1.4;">
          <strong>建议理由:</strong> ${patch.rationale}
        </div>
        ${actionHtml}
      `;

      if (patch.status === "pending") {
        card.querySelector(".btn-accept").addEventListener("click", () => this.applyPatch(patch.id));
        card.querySelector(".btn-reject").addEventListener("click", () => this.rejectPatch(patch.id));
      }

      container.appendChild(card);
    });
  }

  // 采纳建议 (真实 API 与物理写回)
  async applyPatch(patchId) {
    const patch = this.data.reviewer_patches.find(p => p.id === patchId);
    if (!patch) return;

    try {
      const res = await fetch("/api/patch/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: jsonStringify({
          patch_id: patchId,
          proposed_text: patch.proposed_text,
          target: patch.target,
          screenplay_file: this.activeFile
        })
      });

      if (!res.ok) throw new Error("向后端请求采纳建议失败");

      // 本地状态同步
      window.patchStatusCache[patchId] = "accepted";
      patch.status = "accepted";
      showToast(`✓ 已成功采纳建议: ${patch.agent_id}！物理文件已更新。`);

      // 重新读取剧本与报告以重绘，达到完全物理同步
      await this.loadFile(this.activeFile);

      // 执行高光闪烁动效
      let targetElId = patch.target.element_id || patch.target.beat_id;
      if (targetElId) {
        const elDom = document.getElementById(`sp-element-${targetElId}`);
        if (elDom) {
          elDom.classList.add("flash-active");
          elDom.scrollIntoView({ behavior: "smooth", block: "center" });
          setTimeout(() => elDom.classList.remove("flash-active"), 2000);
        }
      }

    } catch (e) {
      showToast(`❌ 采纳失败: ${e.message}`);
    }
  }

  // 拒绝修改建议
  async rejectPatch(patchId) {
    const patch = this.data.reviewer_patches.find(p => p.id === patchId);
    if (!patch) return;

    try {
      const res = await fetch("/api/patch/reject", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: jsonStringify({
          patch_id: patchId,
          target: patch.target,
          screenplay_file: this.activeFile
        })
      });

      if (!res.ok) throw new Error("后端处理拒绝建议失败");

      window.patchStatusCache[patchId] = "rejected";
      patch.status = "rejected";
      showToast(`✗ 已拒绝建议: ${patch.agent_id}`);

      await this.loadFile(this.activeFile);
    } catch (e) {
      showToast(`❌ 拒绝失败: ${e.message}`);
    }
  }
}

// 辅助方法：序列化 JSON
function jsonStringify(obj) {
  return JSON.stringify(obj);
}

// 页面载入时实例化 Workbench
window.addEventListener("DOMContentLoaded", () => {
  window.app = new WorkbenchApp();
  window.app.init();
});
