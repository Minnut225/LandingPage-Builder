// Studio Client Application Logic — Modular Section & Property Builder
(function () {
  let currentProjectId = null;
  let activeVersion = null;
  let versionsList = [];
  let versionFormInputs = {};
  let eventSource = null;
  let currentOutputFormat = "html_css";
  let isBusyGenerating = false;

  // Template & Modular Section State
  let templatesData = null;
  let selectedTemplateId = "personal_portfolio";
  let selectedStyle = "modern_clean";
  let selectedPaletteId = "tech_blue";
  let customColor = "#2563EB";
  let isCreationCollapsed = false;
  let sectionStateByTemplate = {};
  let itemUidCounter = 1;

  // DOM Elements
  const projectIdDisplay = document.getElementById("project-id-display");
  const btnNewProject = document.getElementById("btn-new-project");
  const taskStatusBadge = document.getElementById("task-status-badge");
  const formatSelect = document.getElementById("format-select");

  // Creation / Properties Panel Elements
  const creationHeader = document.getElementById("creation-header");
  const creationBody = document.getElementById("creation-body");
  const creationSummaryBadge = document.getElementById("creation-summary-badge");
  const creationToggleIcon = document.getElementById("creation-toggle-icon");
  const btnToggleCreation = document.getElementById("btn-toggle-creation");

  const templateSelect = document.getElementById("template-select");
  const templateDesc = document.getElementById("template-desc");
  const styleSelector = document.getElementById("style-selector");
  const colorPaletteSelector = document.getElementById("color-palette-selector");
  const customColorPicker = document.getElementById("custom-color-picker");
  const sectionPickerBar = document.getElementById("section-picker-bar");
  const dynamicFormFields = document.getElementById("dynamic-form-fields");

  const btnTogglePromptPreview = document.getElementById("btn-toggle-prompt-preview");
  const promptPreviewIcon = document.getElementById("prompt-preview-icon");
  const promptPreviewContainer = document.getElementById("prompt-preview-container");
  const promptPreviewText = document.getElementById("prompt-preview-text");

  const btnCreate = document.getElementById("btn-create");
  const btnCreateText = document.getElementById("btn-create-text");
  const btnCreateSpinner = document.getElementById("btn-create-spinner");

  // Status & Iteration Elements
  const activityBox = document.getElementById("activity-box");
  const activityText = document.getElementById("activity-text");
  const versionsContainer = document.getElementById("versions-container");
  const activeVersionPill = document.getElementById("active-version-pill");
  const qaScoreBadge = document.getElementById("qa-score-badge");
  const qaList = document.getElementById("qa-list");
  const feedbackInput = document.getElementById("feedback-input");
  const btnRevise = document.getElementById("btn-revise");
  const btnApprove = document.getElementById("btn-approve");
  const btnRollback = document.getElementById("btn-rollback");
  const btnExport = document.getElementById("btn-export");

  // Preview elements
  const previewIframe = document.getElementById("preview-iframe");
  const previewPlaceholder = document.getElementById("preview-placeholder");
  const previewUrlDisplay = document.getElementById("preview-url-display");
  const linkExternal = document.getElementById("link-external");
  const btnReloadPreview = document.getElementById("btn-reload-preview");
  const codeInspector = document.getElementById("code-inspector");
  const codeDisplay = document.getElementById("code-display");
  const wrapper = document.getElementById("viewport-frame-wrapper");

  // Viewport buttons
  const btnVpDesktop = document.getElementById("btn-vp-desktop");
  const btnVpTablet = document.getElementById("btn-vp-tablet");
  const btnVpMobile = document.getElementById("btn-vp-mobile");

  // Tab buttons
  const btnTabPreview = document.getElementById("btn-tab-preview");
  const btnTabCode = document.getElementById("btn-tab-code");

  // Settings Modal elements
  const btnSettings = document.getElementById("btn-settings");
  const settingsModal = document.getElementById("settings-modal");
  const btnCloseSettings = document.getElementById("btn-close-settings");
  const btnSaveSettings = document.getElementById("btn-save-settings");
  const cfgBackendUrl = document.getElementById("cfg-backend-url");
  const cfgProvider = document.getElementById("cfg-provider");
  const cfgApiKey = document.getElementById("cfg-api-key");

  function nextItemId() {
    const id = `item_${itemUidCounter}`;
    itemUidCounter += 1;
    return id;
  }

  function getApiBaseUrl() {
    return localStorage.getItem("LP_BACKEND_URL") || (window.ENV_CONFIG && window.ENV_CONFIG.BACKEND_URL) || "";
  }

  function normalizeTagTokens(raw) {
    if (!raw) return [];
    const list = Array.isArray(raw) ? raw : String(raw).split(/[\n,]+/);
    const seen = new Set();
    const out = [];
    list.forEach((entry) => {
      if (entry === null || entry === undefined) return;
      String(entry)
        .split(/[\n,]+/)
        .forEach((piece) => {
          const clean = piece.trim();
          if (!clean) return;
          const lower = clean.toLowerCase();
          if (!seen.has(lower)) {
            seen.add(lower);
            out.push(clean);
          }
        });
    });
    return out;
  }

  async function init() {
    const urlParams = new URLSearchParams(window.location.search);
    const pid = urlParams.get("project");

    await loadTemplates();

    if (pid) {
      await loadProject(pid);
    } else {
      syncActionButtons();
    }

    if (creationHeader) {
      creationHeader.addEventListener("click", () => toggleCreationPanel(!isCreationCollapsed));
    }
    if (btnToggleCreation) {
      btnToggleCreation.addEventListener("click", (e) => {
        e.stopPropagation();
        toggleCreationPanel(!isCreationCollapsed);
      });
    }

    if (templateSelect) {
      templateSelect.addEventListener("change", (e) => {
        selectedTemplateId = e.target.value;
        updateTemplateDescription();
        ensureTemplateSectionState(selectedTemplateId);
        renderSectionPickerBar(selectedTemplateId);
        renderModularSections(selectedTemplateId);
        updatePromptPreviewIfOpen();
      });
    }

    if (customColorPicker) {
      customColorPicker.addEventListener("input", (e) => {
        customColor = e.target.value;
        document.querySelectorAll(".palette-card").forEach((c) => c.classList.remove("active", "border-blue-600", "bg-blue-50"));
        selectedPaletteId = "custom";
        updatePromptPreviewIfOpen();
      });
    }

    if (btnTogglePromptPreview) {
      btnTogglePromptPreview.addEventListener("click", togglePromptPreview);
    }

    if (btnNewProject) {
      btnNewProject.addEventListener("click", handleResetNewProject);
    }

    btnCreate.addEventListener("click", handleSubmitCreationOrPropertyUpdate);
    btnRevise.addEventListener("click", handleReviseProject);
    btnApprove.addEventListener("click", handleApproveProject);
    btnRollback.addEventListener("click", handleRollbackProject);
    btnExport.addEventListener("click", handleExportZip);
    btnReloadPreview.addEventListener("click", reloadPreview);

    btnVpDesktop.addEventListener("click", () => setViewport("desktop"));
    btnVpTablet.addEventListener("click", () => setViewport("tablet"));
    btnVpMobile.addEventListener("click", () => setViewport("mobile"));

    btnTabPreview.addEventListener("click", () => setTab("preview"));
    btnTabCode.addEventListener("click", () => setTab("code"));

    formatSelect.addEventListener("change", (e) => {
      currentOutputFormat = e.target.value;
    });

    if (btnSettings && settingsModal) {
      btnSettings.addEventListener("click", () => {
        cfgBackendUrl.value = localStorage.getItem("LP_BACKEND_URL") || (window.ENV_CONFIG && window.ENV_CONFIG.BACKEND_URL) || "";
        cfgProvider.value = localStorage.getItem("LP_PROVIDER") || "gemini";
        cfgApiKey.value = localStorage.getItem("LP_API_KEY") || "";
        settingsModal.classList.remove("hidden");
      });
      btnCloseSettings.addEventListener("click", () => settingsModal.classList.add("hidden"));
      btnSaveSettings.addEventListener("click", () => {
        localStorage.setItem("LP_BACKEND_URL", cfgBackendUrl.value.trim());
        localStorage.setItem("LP_PROVIDER", cfgProvider.value);
        localStorage.setItem("LP_API_KEY", cfgApiKey.value.trim());
        settingsModal.classList.add("hidden");
        alert("Đã lưu cấu hình môi trường thành công!");
      });
    }
  }

  async function loadTemplates() {
    const baseApi = getApiBaseUrl();
    try {
      const res = await fetch(`${baseApi}/api/templates`);
      if (!res.ok) throw new Error("Không thể tải danh sách template");
      templatesData = await res.json();
    } catch (err) {
      console.warn("Lỗi tải templates từ API, sử dụng fallback mặc định:", err);
      templatesData = {
        templates: {
          personal_portfolio: {
            id: "personal_portfolio",
            name: "Hồ sơ cá nhân / Portfolio",
            icon: "👤",
            description: "Dành cho chuyên gia, kỹ sư, designer, freelancer.",
            fields: [
              { name: "full_name", label: "Họ và tên", type: "text", required: true, placeholder: "Nguyễn Văn A" },
              { name: "title", label: "Chức danh", type: "text", required: true, placeholder: "Senior Fullstack Engineer" },
              { name: "bio", label: "Giới thiệu ngắn", type: "textarea", required: true, placeholder: "Mô tả định hướng chuyên môn..." }
            ],
            sections: [
              {
                id: "about_me",
                title: "About Me",
                icon: "👤",
                kind: "single",
                required_section: true,
                default_enabled: true,
                allow_custom_props: true,
                properties: [
                  { name: "full_name", label: "Họ và tên", type: "text", required: true, placeholder: "Nguyễn Văn A" },
                  { name: "title", label: "Chức danh", type: "text", required: true, placeholder: "AI Engineer" },
                  { name: "school", label: "Trường / Đơn vị", type: "text", required: false, placeholder: "ĐH Bách Khoa" },
                  { name: "timeline", label: "Thời gian", type: "text", required: false, placeholder: "2022 – 2026" },
                  { name: "bio", label: "Mô tả ngắn", type: "textarea", required: true, placeholder: "Định hướng chuyên môn..." }
                ]
              },
              {
                id: "projects",
                title: "Dự án tiêu biểu",
                icon: "💼",
                kind: "repeater",
                required_section: false,
                default_enabled: true,
                add_label: "+ Thêm dự án",
                item_title_field: "name",
                allow_custom_props: true,
                properties: [
                  { name: "name", label: "Tên dự án", type: "text", required: true, placeholder: "LandingPage Builder" },
                  { name: "role", label: "Công việc / Vai trò", type: "text", required: false, placeholder: "Fullstack Dev" },
                  {
                    name: "tech_stack",
                    label: "Tech stack",
                    type: "tags",
                    required: false,
                    suggestions: ["Python", "TypeScript", "React", "FastAPI", "CrewAI", "Tailwind CSS"],
                    placeholder: "Nhập công nghệ + Enter..."
                  },
                  { name: "description", label: "Mô tả", type: "textarea", required: false, placeholder: "Kết quả chính..." }
                ]
              },
              {
                id: "skills",
                title: "Kỹ năng chuyên môn",
                icon: "⚡",
                kind: "tags",
                required_section: false,
                default_enabled: false,
                suggestions: ["Python", "FastAPI", "React", "TypeScript", "AI Agents", "Docker"],
                placeholder: "Nhập kỹ năng + Enter..."
              }
            ]
          }
        },
        styles: {
          modern_clean: { id: "modern_clean", name: "Hiện đại & Tối giản", description: "Nền sáng, thanh lịch." },
          tech_dark: { id: "tech_dark", name: "Tech Dark Mode", description: "Nền tối, ánh sáng neon." }
        },
        palettes: {
          tech_blue: { id: "tech_blue", name: "Tech Blue", primary: "#2563EB", surface: "#F8FAFC", accent: "#0284C7" },
          emerald_green: { id: "emerald_green", name: "Emerald Green", primary: "#059669", surface: "#F0FDF4", accent: "#10B981" }
        }
      };
    }

    renderTemplateSelector();
    renderStyleSelector();
    renderPaletteSelector();
    ensureTemplateSectionState(selectedTemplateId);
    renderSectionPickerBar(selectedTemplateId);
    renderModularSections(selectedTemplateId);
  }

  function createFreshTemplateSectionState(templateId) {
    const tpl = templatesData?.templates?.[templateId];
    const map = {};
    if (!tpl || !Array.isArray(tpl.sections)) return map;

    tpl.sections.forEach((sec) => {
      const enabled = Boolean(sec.required_section || sec.default_enabled);
      if (sec.kind === "single") {
        map[sec.id] = {
          enabled,
          collapsed: false,
          values: {},
          custom_properties: []
        };
      } else if (sec.kind === "repeater") {
        map[sec.id] = {
          enabled,
          collapsed: false,
          items: []
        };
      } else if (sec.kind === "tags") {
        map[sec.id] = {
          enabled,
          collapsed: false,
          tags: []
        };
      }
    });
    return map;
  }

  function ensureTemplateSectionState(templateId) {
    if (!sectionStateByTemplate[templateId]) {
      sectionStateByTemplate[templateId] = createFreshTemplateSectionState(templateId);
    }
    return sectionStateByTemplate[templateId];
  }

  function renderTemplateSelector() {
    if (!templateSelect || !templatesData) return;
    templateSelect.innerHTML = "";
    Object.values(templatesData.templates).forEach((tpl) => {
      const opt = document.createElement("option");
      opt.value = tpl.id;
      opt.textContent = `${tpl.icon || "📄"} ${tpl.name}`;
      if (tpl.id === selectedTemplateId) opt.selected = true;
      templateSelect.appendChild(opt);
    });
    updateTemplateDescription();
  }

  function updateTemplateDescription() {
    if (!templateDesc || !templatesData) return;
    const tpl = templatesData.templates[selectedTemplateId];
    templateDesc.textContent = tpl ? tpl.description : "";
  }

  function renderStyleSelector() {
    if (!styleSelector || !templatesData) return;
    styleSelector.innerHTML = "";
    Object.values(templatesData.styles).forEach((st) => {
      const card = document.createElement("div");
      card.className = `style-card p-2 rounded-lg border text-xs cursor-pointer ${
        st.id === selectedStyle ? "active border-blue-600 bg-blue-50 text-blue-900" : "border-slate-200 bg-white hover:bg-slate-50 text-slate-700"
      }`;
      card.innerHTML = `
        <div class="font-bold">${st.name}</div>
        <div class="text-[10px] text-slate-500 line-clamp-1">${st.description}</div>
      `;
      card.onclick = () => {
        document.querySelectorAll(".style-card").forEach((c) => c.classList.remove("active", "border-blue-600", "bg-blue-50", "text-blue-900"));
        card.classList.add("active", "border-blue-600", "bg-blue-50", "text-blue-900");
        selectedStyle = st.id;
        updatePromptPreviewIfOpen();
      };
      styleSelector.appendChild(card);
    });
  }

  function renderPaletteSelector() {
    if (!colorPaletteSelector || !templatesData) return;
    colorPaletteSelector.innerHTML = "";
    Object.values(templatesData.palettes).forEach((pal) => {
      const card = document.createElement("div");
      card.className = `palette-card p-2 rounded-lg border text-xs cursor-pointer ${
        pal.id === selectedPaletteId ? "active border-blue-600 bg-blue-50" : "border-slate-200 bg-white hover:bg-slate-50"
      }`;
      card.innerHTML = `
        <div class="flex items-center gap-1.5 mb-1">
          <span class="w-3.5 h-3.5 rounded-full inline-block" style="background-color: ${pal.primary}"></span>
          <span class="w-3.5 h-3.5 rounded-full inline-block border border-slate-200" style="background-color: ${pal.accent || pal.surface}"></span>
          <span class="font-bold text-[11px] text-slate-800">${pal.name}</span>
        </div>
      `;
      card.onclick = () => {
        document.querySelectorAll(".palette-card").forEach((c) => c.classList.remove("active", "border-blue-600", "bg-blue-50"));
        card.classList.add("active", "border-blue-600", "bg-blue-50");
        selectedPaletteId = pal.id;
        customColor = pal.primary;
        if (customColorPicker) customColorPicker.value = pal.primary;
        updatePromptPreviewIfOpen();
      };
      colorPaletteSelector.appendChild(card);
    });
  }

  // --- Modular Section Picker Bar & Property Cards ---

  function renderSectionPickerBar(templateId) {
    const pickerEl = document.getElementById("section-picker-bar") || sectionPickerBar;
    if (!pickerEl || !templatesData) return;
    pickerEl.innerHTML = "";

    const tpl = templatesData.templates[templateId];
    if (!tpl || !Array.isArray(tpl.sections)) return;

    const tplState = ensureTemplateSectionState(templateId);

    tpl.sections.forEach((sec) => {
      const secState = tplState[sec.id];
      if (!secState) return;

      const btn = document.createElement("button");
      btn.type = "button";

      if (secState.enabled) {
        btn.className = "section-pill-active";
        let countSuffix = "";
        if (sec.kind === "repeater" && secState.items.length > 0) {
          countSuffix = ` (${secState.items.length})`;
        } else if (sec.kind === "tags" && secState.tags.length > 0) {
          countSuffix = ` (${secState.tags.length})`;
        }
        btn.textContent = `✓ ${sec.title}${countSuffix}`;
        btn.title = sec.required_section ? "Khối bắt buộc — bấm để cuộn tới" : "Đang bật — bấm để cuộn tới khối";
        btn.onclick = () => {
          secState.collapsed = false;
          renderModularSections(templateId);
          const cardEl = document.getElementById(`mod-sec-${sec.id}`);
          if (cardEl) cardEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
        };
      } else {
        btn.className = "section-pill-inactive";
        btn.innerHTML = `<span class="text-blue-600 font-bold">+</span> <span>${sec.title}</span>`;
        btn.title = `Bật thêm khối ${sec.title}`;
        btn.onclick = () => {
          secState.enabled = true;
          secState.collapsed = false;
          if (sec.kind === "repeater" && secState.items.length === 0) {
            secState.items.push({
              id: nextItemId(),
              expanded: true,
              values: {},
              custom_properties: []
            });
          }
          renderSectionPickerBar(templateId);
          renderModularSections(templateId);
          updatePromptPreviewIfOpen();
          const cardEl = document.getElementById(`mod-sec-${sec.id}`);
          if (cardEl) cardEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
        };
      }

      pickerEl.appendChild(btn);
    });
  }

  function createTagWidget({ getTags, setTags, suggestions = [], placeholder = "Nhập tag + Enter..." }) {
    const wrapperEl = document.createElement("div");
    wrapperEl.className = "space-y-1.5";

    const boxEl = document.createElement("div");
    boxEl.className = "flex flex-wrap items-center gap-1.5 p-1.5 bg-white border border-slate-300 rounded-lg focus-within:ring-2 focus-within:ring-blue-500";

    const suggestionsEl = document.createElement("div");
    suggestionsEl.className = "flex flex-wrap gap-1";

    function addCommitTokens(rawText) {
      const incoming = normalizeTagTokens(rawText);
      if (!incoming.length) return false;
      const current = getTags();
      const merged = normalizeTagTokens([...current, ...incoming]);
      if (merged.length !== current.length) {
        setTags(merged);
        updatePromptPreviewIfOpen();
        return true;
      }
      return false;
    }

    function rebuild(focusInput = false) {
      boxEl.innerHTML = "";
      suggestionsEl.innerHTML = "";

      const activeTags = getTags();
      activeTags.forEach((tag, idx) => {
        const chip = document.createElement("span");
        chip.className = "tag-chip";
        const textSpan = document.createElement("span");
        textSpan.className = "truncate";
        textSpan.textContent = tag;

        const rmBtn = document.createElement("button");
        rmBtn.type = "button";
        rmBtn.className = "text-blue-500 hover:text-blue-900 font-bold leading-none ml-0.5";
        rmBtn.textContent = "×";
        rmBtn.onclick = (e) => {
          e.stopPropagation();
          const next = activeTags.filter((_, i) => i !== idx);
          setTags(next);
          rebuild(false);
          updatePromptPreviewIfOpen();
        };

        chip.appendChild(textSpan);
        chip.appendChild(rmBtn);
        boxEl.appendChild(chip);
      });

      const input = document.createElement("input");
      input.type = "text";
      input.placeholder = activeTags.length === 0 ? placeholder : "+ thêm...";
      input.className = "flex-1 min-w-[95px] text-xs bg-transparent border-0 focus:outline-none text-slate-800 placeholder-slate-400 py-0.5 px-1";

      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" || e.key === ",") {
          e.preventDefault();
          if (input.value.trim()) {
            addCommitTokens(input.value);
            input.value = "";
            rebuild(true);
          }
        } else if (e.key === "Backspace" && !input.value && activeTags.length > 0) {
          const next = activeTags.slice(0, -1);
          setTags(next);
          rebuild(true);
          updatePromptPreviewIfOpen();
        }
      });

      input.addEventListener("blur", () => {
        if (input.value.trim()) {
          if (addCommitTokens(input.value)) {
            input.value = "";
            rebuild(false);
          }
        }
      });

      boxEl.appendChild(input);
      boxEl.onclick = () => input.focus();

      const lowerSet = new Set(activeTags.map((t) => t.toLowerCase()));
      const remainingSuggestions = (suggestions || []).filter((s) => !lowerSet.has(String(s).toLowerCase()));
      remainingSuggestions.forEach((sug) => {
        const sugBtn = document.createElement("button");
        sugBtn.type = "button";
        sugBtn.className = "tag-suggestion-chip";
        sugBtn.textContent = `+ ${sug}`;
        sugBtn.onclick = () => {
          addCommitTokens([sug]);
          rebuild(false);
        };
        suggestionsEl.appendChild(sugBtn);
      });

      if (focusInput) {
        setTimeout(() => input.focus(), 0);
      }
    }

    rebuild(false);
    wrapperEl.appendChild(boxEl);
    wrapperEl.appendChild(suggestionsEl);
    return wrapperEl;
  }

  function renderPropertyRows(properties, valuesObj, idPrefix, onTitleInput) {
    const container = document.createElement("div");
    container.className = "space-y-2";

    (properties || []).forEach((prop) => {
      const row = document.createElement("div");
      const inputId = `${idPrefix}-${prop.name}`;

      if (prop.type === "textarea") {
        row.className = "space-y-1";
        const lbl = document.createElement("label");
        lbl.htmlFor = inputId;
        lbl.className = "block text-[11px] font-semibold text-slate-600";
        lbl.innerHTML = `${prop.label} ${prop.required ? '<span class="text-red-500">*</span>' : ""}`;

        const ta = document.createElement("textarea");
        ta.id = inputId;
        ta.rows = 2;
        ta.placeholder = prop.placeholder || "";
        ta.value = valuesObj[prop.name] || "";
        ta.className = "w-full text-xs p-2 bg-white border border-slate-300 rounded-lg text-slate-800 placeholder-slate-400 focus:ring-2 focus:ring-blue-500 focus:outline-none resize-y leading-relaxed";
        ta.addEventListener("input", () => {
          valuesObj[prop.name] = ta.value;
          if (onTitleInput) onTitleInput(prop.name, ta.value);
          updatePromptPreviewIfOpen();
        });

        row.appendChild(lbl);
        row.appendChild(ta);
      } else if (prop.type === "tags") {
        row.className = "prop-row-grid";
        const lbl = document.createElement("label");
        lbl.className = "text-[11px] font-semibold text-slate-600 pt-1.5 leading-snug";
        lbl.innerHTML = `${prop.label} ${prop.required ? '<span class="text-red-500">*</span>' : ""}`;

        if (!Array.isArray(valuesObj[prop.name])) {
          valuesObj[prop.name] = normalizeTagTokens(valuesObj[prop.name]);
        }
        const tagWidget = createTagWidget({
          getTags: () => valuesObj[prop.name] || [],
          setTags: (nextTags) => {
            valuesObj[prop.name] = nextTags;
            renderSectionPickerBar(selectedTemplateId);
          },
          suggestions: prop.suggestions || [],
          placeholder: prop.placeholder || "Nhập + Enter..."
        });

        row.appendChild(lbl);
        row.appendChild(tagWidget);
      } else {
        row.className = "prop-row-grid";
        const lbl = document.createElement("label");
        lbl.htmlFor = inputId;
        lbl.className = "text-[11px] font-semibold text-slate-600 pt-1.5 leading-snug";
        lbl.innerHTML = `${prop.label} ${prop.required ? '<span class="text-red-500">*</span>' : ""}`;

        const inp = document.createElement("input");
        inp.type = "text";
        inp.id = inputId;
        inp.placeholder = prop.placeholder || "";
        inp.value = valuesObj[prop.name] || "";
        inp.className = "w-full text-xs p-1.5 px-2 bg-white border border-slate-300 rounded-lg text-slate-800 placeholder-slate-400 focus:ring-2 focus:ring-blue-500 focus:outline-none";
        inp.addEventListener("input", () => {
          valuesObj[prop.name] = inp.value;
          if (onTitleInput) onTitleInput(prop.name, inp.value);
          updatePromptPreviewIfOpen();
        });

        row.appendChild(lbl);
        row.appendChild(inp);
      }

      container.appendChild(row);
    });

    return container;
  }

  function renderCustomPropertiesBlock(customPropsArray) {
    const wrap = document.createElement("div");
    wrap.className = "pt-1.5 border-t border-dashed border-slate-200 space-y-1.5";

    const rowsHolder = document.createElement("div");
    rowsHolder.className = "space-y-1.5";

    function drawRows(focusLast = false) {
      rowsHolder.innerHTML = "";
      customPropsArray.forEach((pair, idx) => {
        const row = document.createElement("div");
        row.className = "custom-prop-grid";

        const keyInp = document.createElement("input");
        keyInp.type = "text";
        keyInp.placeholder = "Thuộc tính...";
        keyInp.value = pair.key || "";
        keyInp.className = "text-[11px] p-1.5 bg-white border border-slate-300 rounded-md text-slate-700 font-medium placeholder-slate-400 focus:ring-1 focus:ring-blue-500 focus:outline-none";
        keyInp.addEventListener("input", () => {
          pair.key = keyInp.value;
          updatePromptPreviewIfOpen();
        });

        const valInp = document.createElement("input");
        valInp.type = "text";
        valInp.placeholder = "Giá trị...";
        valInp.value = pair.value || "";
        valInp.className = "text-[11px] p-1.5 bg-white border border-slate-300 rounded-md text-slate-800 placeholder-slate-400 focus:ring-1 focus:ring-blue-500 focus:outline-none";
        valInp.addEventListener("input", () => {
          pair.value = valInp.value;
          updatePromptPreviewIfOpen();
        });

        const delBtn = document.createElement("button");
        delBtn.type = "button";
        delBtn.className = "text-[11px] text-slate-400 hover:text-red-600 px-1.5 py-1 font-bold";
        delBtn.title = "Xóa thuộc tính này";
        delBtn.textContent = "✕";
        delBtn.onclick = () => {
          customPropsArray.splice(idx, 1);
          drawRows(false);
          updatePromptPreviewIfOpen();
        };

        row.appendChild(keyInp);
        row.appendChild(valInp);
        row.appendChild(delBtn);
        rowsHolder.appendChild(row);

        if (focusLast && idx === customPropsArray.length - 1) {
          setTimeout(() => keyInp.focus(), 0);
        }
      });
    }

    const addBtn = document.createElement("button");
    addBtn.type = "button";
    addBtn.className = "text-[11px] text-blue-600 hover:text-blue-800 font-semibold inline-flex items-center gap-1";
    addBtn.textContent = "+ Thuộc tính tùy chỉnh";
    addBtn.onclick = () => {
      customPropsArray.push({ key: "", value: "" });
      drawRows(true);
    };

    drawRows(false);
    wrap.appendChild(rowsHolder);
    wrap.appendChild(addBtn);
    return wrap;
  }

  function renderModularSections(templateId, focusItemId = null) {
    if (!dynamicFormFields || !templatesData) return;
    dynamicFormFields.innerHTML = "";

    const tpl = templatesData.templates[templateId];
    if (!tpl) return;

    // Fallback to legacy flat fields only if sections schema is absent
    if (!Array.isArray(tpl.sections)) {
      renderLegacyFlatFields(tpl);
      return;
    }

    const tplState = ensureTemplateSectionState(templateId);

    tpl.sections.forEach((sec) => {
      const secState = tplState[sec.id];
      if (!secState || !secState.enabled) return;

      const card = document.createElement("div");
      card.id = `mod-sec-${sec.id}`;
      card.className = "mod-section-card";

      // Card Header
      const header = document.createElement("div");
      header.className = "px-3 py-2 bg-slate-50 border-b border-slate-200 flex items-center justify-between gap-2";

      const leftTitle = document.createElement("button");
      leftTitle.type = "button";
      leftTitle.className = "flex items-center gap-1.5 text-left min-w-0 flex-1";

      let countText = "";
      if (sec.kind === "repeater") {
        countText = `<span class="text-[10px] bg-slate-200 text-slate-700 px-1.5 py-0.5 rounded-full font-semibold">${secState.items.length}</span>`;
      } else if (sec.kind === "tags" && secState.tags.length > 0) {
        countText = `<span class="text-[10px] bg-blue-100 text-blue-700 px-1.5 py-0.5 rounded-full font-semibold">${secState.tags.length}</span>`;
      }

      leftTitle.innerHTML = `
        <span class="text-xs">${sec.icon || "📦"}</span>
        <span class="text-xs font-bold text-slate-800 truncate">${sec.title}</span>
        ${sec.required_section ? '<span class="text-[10px] text-amber-700 bg-amber-50 border border-amber-200 px-1.5 rounded font-semibold">Cốt lõi</span>' : ""}
        ${countText}
      `;
      leftTitle.onclick = () => {
        secState.collapsed = !secState.collapsed;
        renderModularSections(templateId);
      };

      const rightControls = document.createElement("div");
      rightControls.className = "flex items-center gap-2 shrink-0";

      if (!sec.required_section) {
        const omitBtn = document.createElement("button");
        omitBtn.type = "button";
        omitBtn.className = "text-[10px] text-slate-400 hover:text-red-600 font-semibold transition";
        omitBtn.textContent = "Bỏ section";
        omitBtn.title = "Ẩn khối này khỏi Landing Page (dữ liệu nháp vẫn được giữ tạm)";
        omitBtn.onclick = (e) => {
          e.stopPropagation();
          secState.enabled = false;
          renderSectionPickerBar(templateId);
          renderModularSections(templateId);
          updatePromptPreviewIfOpen();
        };
        rightControls.appendChild(omitBtn);
      }

      const collapseBtn = document.createElement("button");
      collapseBtn.type = "button";
      collapseBtn.className = "text-[11px] text-slate-500 hover:text-slate-800 font-semibold px-1";
      collapseBtn.textContent = secState.collapsed ? "▸" : "▾";
      collapseBtn.onclick = () => {
        secState.collapsed = !secState.collapsed;
        renderModularSections(templateId);
      };
      rightControls.appendChild(collapseBtn);

      header.appendChild(leftTitle);
      header.appendChild(rightControls);
      card.appendChild(header);

      if (secState.collapsed) {
        dynamicFormFields.appendChild(card);
        return;
      }

      // Card Body
      const body = document.createElement("div");
      body.className = "p-3 space-y-2.5";

      if (sec.kind === "single") {
        const propsEl = renderPropertyRows(sec.properties, secState.values, `sec-${sec.id}`);
        body.appendChild(propsEl);
        if (sec.allow_custom_props) {
          body.appendChild(renderCustomPropertiesBlock(secState.custom_properties));
        }
      } else if (sec.kind === "tags") {
        const tagWidget = createTagWidget({
          getTags: () => secState.tags,
          setTags: (next) => {
            secState.tags = next;
            renderSectionPickerBar(templateId);
          },
          suggestions: sec.suggestions || [],
          placeholder: sec.placeholder || "Nhập tag + Enter..."
        });
        body.appendChild(tagWidget);
      } else if (sec.kind === "repeater") {
        const listWrap = document.createElement("div");
        listWrap.className = "space-y-2";

        if (secState.items.length === 0) {
          const emptyHint = document.createElement("div");
          emptyHint.className = "text-[11px] text-slate-400 italic py-1 px-2 bg-slate-50 rounded border border-dashed border-slate-200";
          emptyHint.textContent = `Chưa có mục nào. Bấm "${sec.add_label || "+ Thêm mục"}" bên dưới để nhập thuộc tính.`;
          listWrap.appendChild(emptyHint);
        }

        const titleField = sec.item_title_field || "name";
        const firstTagProp = (sec.properties || []).find((p) => p.type === "tags");

        secState.items.forEach((item, idx) => {
          const itemCard = document.createElement("div");
          itemCard.className = "repeater-item-card";

          const itemHead = document.createElement("div");
          itemHead.className = "px-2.5 py-2 bg-slate-100/80 flex items-center justify-between gap-2 cursor-pointer";

          const titleWrap = document.createElement("div");
          titleWrap.className = "min-w-0 flex-1 flex items-center gap-1.5 flex-wrap";

          const itemTitleSpan = document.createElement("span");
          itemTitleSpan.className = "text-xs font-semibold text-slate-800 truncate";
          const curTitle = (item.values[titleField] || "").trim();
          itemTitleSpan.textContent = `${idx + 1}. ${curTitle || "(Chưa đặt tên)"}`;
          titleWrap.appendChild(itemTitleSpan);

          if (!item.expanded && firstTagProp && Array.isArray(item.values[firstTagProp.name])) {
            item.values[firstTagProp.name].slice(0, 3).forEach((tg) => {
              const mini = document.createElement("span");
              mini.className = "text-[10px] px-1.5 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200 font-medium";
              mini.textContent = tg;
              titleWrap.appendChild(mini);
            });
          }

          const actionsWrap = document.createElement("div");
          actionsWrap.className = "flex items-center gap-1.5 shrink-0";

          const editToggleBtn = document.createElement("button");
          editToggleBtn.type = "button";
          editToggleBtn.className = "text-[11px] text-blue-600 hover:text-blue-800 font-semibold px-1";
          editToggleBtn.textContent = item.expanded ? "Thu gọn" : "✎ Sửa";
          editToggleBtn.onclick = (e) => {
            e.stopPropagation();
            item.expanded = !item.expanded;
            renderModularSections(templateId);
          };

          const deleteItemBtn = document.createElement("button");
          deleteItemBtn.type = "button";
          deleteItemBtn.className = "text-[11px] text-red-500 hover:text-red-700 font-semibold px-1";
          deleteItemBtn.textContent = "✕ Xóa";
          deleteItemBtn.onclick = (e) => {
            e.stopPropagation();
            secState.items = secState.items.filter((it) => it.id !== item.id);
            renderSectionPickerBar(templateId);
            renderModularSections(templateId);
            updatePromptPreviewIfOpen();
          };

          actionsWrap.appendChild(editToggleBtn);
          actionsWrap.appendChild(deleteItemBtn);

          itemHead.onclick = () => {
            item.expanded = !item.expanded;
            renderModularSections(templateId);
          };

          itemHead.appendChild(titleWrap);
          itemHead.appendChild(actionsWrap);
          itemCard.appendChild(itemHead);

          if (item.expanded) {
            const itemBody = document.createElement("div");
            itemBody.className = "p-2.5 bg-white border-t border-slate-200 space-y-2";

            const itemPropsEl = renderPropertyRows(
              sec.properties,
              item.values,
              `sec-${sec.id}-${item.id}`,
              (propName, newVal) => {
                if (propName === titleField) {
                  itemTitleSpan.textContent = `${idx + 1}. ${(newVal || "").trim() || "(Chưa đặt tên)"}`;
                }
              }
            );
            itemBody.appendChild(itemPropsEl);

            if (sec.allow_custom_props) {
              if (!Array.isArray(item.custom_properties)) item.custom_properties = [];
              itemBody.appendChild(renderCustomPropertiesBlock(item.custom_properties));
            }

            itemCard.appendChild(itemBody);

            if (focusItemId && focusItemId === item.id && sec.properties && sec.properties.length > 0) {
              const firstPropName = sec.properties[0].name;
              setTimeout(() => {
                const firstInput = document.getElementById(`sec-${sec.id}-${item.id}-${firstPropName}`);
                if (firstInput) firstInput.focus();
              }, 0);
            }
          }

          listWrap.appendChild(itemCard);
        });

        const addItemBtn = document.createElement("button");
        addItemBtn.type = "button";
        addItemBtn.className = "w-full py-1.5 px-3 text-xs font-semibold text-blue-700 bg-blue-50 hover:bg-blue-100 border border-dashed border-blue-300 rounded-lg transition flex items-center justify-center gap-1";
        addItemBtn.textContent = sec.add_label || "+ Thêm mục";
        addItemBtn.onclick = () => {
          const newItem = {
            id: nextItemId(),
            expanded: true,
            values: {},
            custom_properties: []
          };
          secState.items.push(newItem);
          renderSectionPickerBar(templateId);
          renderModularSections(templateId, newItem.id);
          updatePromptPreviewIfOpen();
        };

        body.appendChild(listWrap);
        body.appendChild(addItemBtn);
      }

      card.appendChild(body);
      dynamicFormFields.appendChild(card);
    });
  }

  function renderLegacyFlatFields(tpl) {
    (tpl.fields || []).forEach((field) => {
      const container = document.createElement("div");
      container.className = "flex flex-col gap-1";
      const label = document.createElement("label");
      label.className = "text-[11px] font-semibold text-slate-700";
      label.innerHTML = `${field.label} ${field.required ? '<span class="text-red-500">*</span>' : ""}`;

      const inputEl = field.type === "textarea" ? document.createElement("textarea") : document.createElement("input");
      if (field.type === "textarea") inputEl.rows = 2;
      else inputEl.type = "text";
      inputEl.name = field.name;
      inputEl.id = `field-${field.name}`;
      inputEl.placeholder = field.placeholder || "";
      inputEl.className = "w-full text-xs p-2 bg-white border border-slate-300 rounded-lg text-slate-800";
      inputEl.addEventListener("input", updatePromptPreviewIfOpen);

      container.appendChild(label);
      container.appendChild(inputEl);
      dynamicFormFields.appendChild(container);
    });
  }

  function getStructuredFormData() {
    const tpl = templatesData?.templates?.[selectedTemplateId];
    if (!tpl || !Array.isArray(tpl.sections)) {
      const flat = {};
      if (dynamicFormFields) {
        dynamicFormFields.querySelectorAll("input, textarea").forEach((el) => {
          if (el.name) flat[el.name] = el.value.trim();
        });
      }
      return flat;
    }

    const tplState = ensureTemplateSectionState(selectedTemplateId);
    const sectionsPayload = {};

    tpl.sections.forEach((sec) => {
      const st = tplState[sec.id];
      if (!st) return;

      if (sec.kind === "single") {
        const cleanVals = {};
        (sec.properties || []).forEach((p) => {
          if (p.type === "tags") {
            cleanVals[p.name] = normalizeTagTokens(st.values[p.name]);
          } else {
            cleanVals[p.name] = String(st.values[p.name] || "").trim();
          }
        });
        sectionsPayload[sec.id] = {
          enabled: Boolean(st.enabled),
          values: cleanVals,
          custom_properties: (st.custom_properties || []).map((cp) => ({
            key: String(cp.key || "").trim(),
            value: String(cp.value || "").trim()
          }))
        };
      } else if (sec.kind === "repeater") {
        sectionsPayload[sec.id] = {
          enabled: Boolean(st.enabled),
          items: (st.items || []).map((it) => {
            const itemVals = {};
            (sec.properties || []).forEach((p) => {
              if (p.type === "tags") {
                itemVals[p.name] = normalizeTagTokens(it.values[p.name]);
              } else {
                itemVals[p.name] = String(it.values[p.name] || "").trim();
              }
            });
            return {
              id: it.id,
              values: itemVals,
              custom_properties: (it.custom_properties || []).map((cp) => ({
                key: String(cp.key || "").trim(),
                value: String(cp.value || "").trim()
              }))
            };
          })
        };
      } else if (sec.kind === "tags") {
        sectionsPayload[sec.id] = {
          enabled: Boolean(st.enabled),
          tags: normalizeTagTokens(st.tags)
        };
      }
    });

    return { sections: sectionsPayload };
  }

  function isRepeaterItemNonEmpty(sec, item) {
    for (const p of sec.properties || []) {
      const v = item.values[p.name];
      if (p.type === "tags" && Array.isArray(v) && v.length > 0) return true;
      if (typeof v === "string" && v.trim() !== "") return true;
    }
    for (const cp of item.custom_properties || []) {
      if ((cp.key && cp.key.trim()) || (cp.value && cp.value.trim())) return true;
    }
    return false;
  }

  function validateActiveSections() {
    const tpl = templatesData?.templates?.[selectedTemplateId];
    if (!tpl || !Array.isArray(tpl.sections)) return true;

    const tplState = ensureTemplateSectionState(selectedTemplateId);

    for (const sec of tpl.sections) {
      const st = tplState[sec.id];
      if (!st || !st.enabled) continue; // Review Focus #1: skip disabled sections completely

      if (sec.kind === "single") {
        for (const prop of sec.properties || []) {
          if (!prop.required) continue;
          const val = st.values[prop.name];
          const isEmpty = prop.type === "tags" ? !Array.isArray(val) || val.length === 0 : !String(val || "").trim();
          if (isEmpty) {
            toggleCreationPanel(false);
            st.collapsed = false;
            renderModularSections(selectedTemplateId);
            alert(`Vui lòng điền thuộc tính bắt buộc "${prop.label}" trong khối "${sec.title}".`);
            const el = document.getElementById(`sec-${sec.id}-${prop.name}`);
            if (el) el.focus();
            return false;
          }
        }
      } else if (sec.kind === "repeater") {
        for (let idx = 0; idx < (st.items || []).length; idx += 1) {
          const item = st.items[idx];
          if (!isRepeaterItemNonEmpty(sec, item)) continue;
          for (const prop of sec.properties || []) {
            if (!prop.required) continue;
            const val = item.values[prop.name];
            const isEmpty = prop.type === "tags" ? !Array.isArray(val) || val.length === 0 : !String(val || "").trim();
            if (isEmpty) {
              toggleCreationPanel(false);
              st.collapsed = false;
              item.expanded = true;
              renderModularSections(selectedTemplateId);
              alert(`Vui lòng điền "${prop.label}" cho mục #${idx + 1} trong khối "${sec.title}".`);
              const el = document.getElementById(`sec-${sec.id}-${item.id}-${prop.name}`);
              if (el) el.focus();
              return false;
            }
          }
        }
      }
    }
    return true;
  }

  function hydrateFormInput(formInput) {
    if (!formInput || !templatesData) return;

    if (formInput.template_id && templatesData.templates[formInput.template_id]) {
      selectedTemplateId = formInput.template_id;
      if (templateSelect) templateSelect.value = selectedTemplateId;
      updateTemplateDescription();
    }
    if (formInput.style) {
      selectedStyle = formInput.style;
    }
    if (formInput.color_palette) {
      selectedPaletteId = formInput.color_palette.id || "custom";
      customColor = formInput.color_palette.primary || "#2563EB";
      if (customColorPicker) customColorPicker.value = customColor;
    }

    const tpl = templatesData.templates[selectedTemplateId];
    if (tpl && Array.isArray(tpl.sections)) {
      const freshState = createFreshTemplateSectionState(selectedTemplateId);
      const rawFormData = formInput.form_data || {};

      if (rawFormData.sections && typeof rawFormData.sections === "object") {
        // Hydrate modular sections state
        tpl.sections.forEach((sec) => {
          const incomingSec = rawFormData.sections[sec.id];
          const target = freshState[sec.id];
          if (!incomingSec || !target) return;

          target.enabled = Boolean(sec.required_section || incomingSec.enabled);

          if (sec.kind === "single") {
            const vals = incomingSec.values || {};
            (sec.properties || []).forEach((p) => {
              target.values[p.name] = p.type === "tags" ? normalizeTagTokens(vals[p.name]) : String(vals[p.name] || "");
            });
            target.custom_properties = Array.isArray(incomingSec.custom_properties)
              ? incomingSec.custom_properties.map((cp) => ({
                  key: String(cp.key || ""),
                  value: String(cp.value || "")
                }))
              : [];
          } else if (sec.kind === "repeater") {
            const items = Array.isArray(incomingSec.items) ? incomingSec.items : [];
            target.items = items.map((it) => {
              const vals = {};
              const srcVals = it.values || {};
              (sec.properties || []).forEach((p) => {
                vals[p.name] = p.type === "tags" ? normalizeTagTokens(srcVals[p.name]) : String(srcVals[p.name] || "");
              });
              return {
                id: it.id || nextItemId(),
                expanded: false,
                values: vals,
                custom_properties: Array.isArray(it.custom_properties)
                  ? it.custom_properties.map((cp) => ({
                      key: String(cp.key || ""),
                      value: String(cp.value || "")
                    }))
                  : []
              };
            });
          } else if (sec.kind === "tags") {
            target.tags = normalizeTagTokens(incomingSec.tags);
          }
        });
      } else {
        // Review Focus #5: Hydrate legacy flat form_data into modular sections cleanly
        tpl.sections.forEach((sec) => {
          const target = freshState[sec.id];
          if (!target) return;

          if (sec.kind === "single") {
            let hasAny = false;
            (sec.properties || []).forEach((p) => {
              if (rawFormData[p.name] !== undefined && String(rawFormData[p.name]).trim() !== "") {
                target.values[p.name] = p.type === "tags" ? normalizeTagTokens(rawFormData[p.name]) : String(rawFormData[p.name]);
                hasAny = true;
              }
            });
            if (sec.id === "contact" && rawFormData.contact_info && !target.values.email) {
              target.values.email = String(rawFormData.contact_info);
              hasAny = true;
            }
            if (hasAny) target.enabled = true;
          } else if (sec.kind === "tags") {
            if (rawFormData[sec.id]) {
              const parsed = normalizeTagTokens(rawFormData[sec.id]);
              if (parsed.length > 0) {
                target.tags = parsed;
                target.enabled = true;
              }
            }
          } else if (sec.kind === "repeater") {
            const rawBlock = rawFormData[sec.id];
            if (typeof rawBlock === "string" && rawBlock.trim() !== "") {
              const titleField = sec.item_title_field || "name";
              const descProp = (sec.properties || []).find((p) => p.type === "textarea");
              const lines = rawBlock
                .split("\n")
                .map((l) => l.trim())
                .filter(Boolean);
              target.items = lines.map((line) => {
                const colonIdx = line.indexOf(":");
                const vals = {};
                if (colonIdx > 0 && descProp) {
                  vals[titleField] = line.slice(0, colonIdx).trim();
                  vals[descProp.name] = line.slice(colonIdx + 1).trim();
                } else {
                  vals[titleField] = line;
                }
                return {
                  id: nextItemId(),
                  expanded: false,
                  values: vals,
                  custom_properties: []
                };
              });
              if (target.items.length > 0) target.enabled = true;
            }
          }
        });
      }

      sectionStateByTemplate[selectedTemplateId] = freshState;
    }

    renderStyleSelector();
    renderPaletteSelector();
    renderSectionPickerBar(selectedTemplateId);
    renderModularSections(selectedTemplateId);
  }

  function getSelectedPaletteObject() {
    if (selectedPaletteId !== "custom" && templatesData?.palettes?.[selectedPaletteId]) {
      return templatesData.palettes[selectedPaletteId];
    }
    return {
      id: "custom",
      name: "Custom Palette",
      primary: customColor || "#2563EB",
      surface: "#F8FAFC",
      accent: "#0284C7"
    };
  }

  function syncActionButtons() {
    if (btnNewProject) {
      if (currentProjectId) {
        btnNewProject.classList.remove("hidden");
      } else {
        btnNewProject.classList.add("hidden");
      }
    }

    if (!isBusyGenerating && btnCreateText) {
      btnCreateText.textContent = currentProjectId
        ? "Cập nhật theo Properties (Tạo bản mới)"
        : "Tạo Landing Page";
    }

    if (creationToggleIcon) {
      if (isCreationCollapsed) {
        creationToggleIcon.textContent = currentProjectId ? "▶ Mở để thêm/xóa mục" : "▶ Mở rộng";
      } else {
        creationToggleIcon.textContent = "▼ Thu gọn";
      }
    }
  }

  function toggleCreationPanel(collapsed) {
    isCreationCollapsed = collapsed;
    if (collapsed) {
      creationBody.classList.add("hidden");
      if (templatesData?.templates?.[selectedTemplateId]) {
        creationSummaryBadge.textContent = templatesData.templates[selectedTemplateId].name;
        creationSummaryBadge.classList.remove("hidden");
      }
    } else {
      creationBody.classList.remove("hidden");
      creationSummaryBadge.classList.add("hidden");
    }
    syncActionButtons();
  }

  let promptPreviewDebounceTimer = null;
  function updatePromptPreviewIfOpen() {
    if (promptPreviewContainer && !promptPreviewContainer.classList.contains("hidden")) {
      clearTimeout(promptPreviewDebounceTimer);
      promptPreviewDebounceTimer = setTimeout(fetchPromptPreview, 280);
    }
  }

  function togglePromptPreview() {
    if (!promptPreviewContainer) return;
    const isHidden = promptPreviewContainer.classList.contains("hidden");
    if (isHidden) {
      promptPreviewContainer.classList.remove("hidden");
      promptPreviewIcon.textContent = "▲";
      fetchPromptPreview();
    } else {
      promptPreviewContainer.classList.add("hidden");
      promptPreviewIcon.textContent = "▼";
    }
  }

  async function fetchPromptPreview() {
    if (!promptPreviewText) return;
    promptPreviewText.textContent = "Đang tổng hợp prompt từ Backend...";
    const baseApi = getApiBaseUrl();
    try {
      const res = await fetch(`${baseApi}/api/prompt/preview`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          template_id: selectedTemplateId,
          form_data: getStructuredFormData(),
          style: selectedStyle,
          color_palette: getSelectedPaletteObject()
        })
      });
      if (!res.ok) throw new Error("Không thể xem trước prompt");
      const data = await res.json();
      promptPreviewText.textContent = data.prompt;
    } catch (err) {
      promptPreviewText.textContent = `Lỗi xem trước prompt: ${err.message}`;
    }
  }

  async function handleSubmitCreationOrPropertyUpdate() {
    if (!validateActiveSections()) return;

    const structuredFormData = getStructuredFormData();
    const baseApi = getApiBaseUrl();

    if (!currentProjectId) {
      setGeneratingState(true, "Đang khởi tạo dự án và gửi yêu cầu sang Agent Pipeline...");
      try {
        const payload = {
          template_id: selectedTemplateId,
          form_data: structuredFormData,
          style: selectedStyle,
          color_palette: getSelectedPaletteObject(),
          output_format: currentOutputFormat
        };

        const res = await fetch(`${baseApi}/api/projects`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || "Không thể tạo dự án");
        }
        const data = await res.json();
        currentProjectId = data.project_id;
        projectIdDisplay.textContent = currentProjectId;

        const newUrl = new URL(window.location);
        newUrl.searchParams.set("project", currentProjectId);
        window.history.pushState({}, "", newUrl);

        syncActionButtons();
        toggleCreationPanel(true);
        connectSSE(currentProjectId);
      } catch (err) {
        alert(err.message);
        setGeneratingState(false);
      }
    } else {
      setGeneratingState(true, "Đang đối chiếu Properties và cập nhật sang phiên bản mới...");
      try {
        const extraFeedback = feedbackInput ? feedbackInput.value.trim() : "";
        const payload = {
          template_id: selectedTemplateId,
          form_data: structuredFormData,
          style: selectedStyle,
          color_palette: getSelectedPaletteObject(),
          feedback: extraFeedback
        };

        const res = await fetch(`${baseApi}/api/projects/${currentProjectId}/revise`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || "Không thể cập nhật Properties");
        }
        if (feedbackInput) feedbackInput.value = "";
        toggleCreationPanel(true);
        if (!eventSource) connectSSE(currentProjectId);
      } catch (err) {
        alert(err.message);
        setGeneratingState(false);
      }
    }
  }

  function handleResetNewProject() {
    if (eventSource) {
      eventSource.close();
      eventSource = null;
    }
    currentProjectId = null;
    activeVersion = null;
    versionsList = [];
    versionFormInputs = {};
    sectionStateByTemplate = {};
    isBusyGenerating = false;

    projectIdDisplay.textContent = "Chưa tạo";
    if (taskStatusBadge) taskStatusBadge.classList.add("hidden");
    if (activityBox) activityBox.classList.add("hidden");
    if (feedbackInput) feedbackInput.value = "";

    const cleanUrl = new URL(window.location);
    cleanUrl.searchParams.delete("project");
    window.history.pushState({}, "", cleanUrl);

    ensureTemplateSectionState(selectedTemplateId);
    renderSectionPickerBar(selectedTemplateId);
    renderModularSections(selectedTemplateId);
    renderVersionsList();
    renderQAReport(null);
    updatePreviewFrame();
    toggleCreationPanel(false);
    syncActionButtons();
    updatePromptPreviewIfOpen();
  }

  async function handleReviseProject() {
    const feedback = feedbackInput.value.trim();
    if (!feedback) {
      alert("Vui lòng nhập nội dung góp ý chỉnh sửa (hoặc mở bảng Thiết lập & Properties ở trên để thêm/xóa mục).");
      return;
    }
    if (!currentProjectId) return;

    const baseApi = getApiBaseUrl();
    setGeneratingState(true, "Đang đưa yêu cầu chỉnh sửa vào hàng đợi...");
    try {
      const res = await fetch(`${baseApi}/api/projects/${currentProjectId}/revise`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ feedback })
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Gửi phản hồi thất bại");
      }
      feedbackInput.value = "";
      if (!eventSource) connectSSE(currentProjectId);
    } catch (err) {
      alert(err.message);
      setGeneratingState(false);
    }
  }

  async function handleApproveProject() {
    if (!currentProjectId) return;
    const baseApi = getApiBaseUrl();
    try {
      const res = await fetch(`${baseApi}/api/projects/${currentProjectId}/approve`, {
        method: "POST"
      });
      if (!res.ok) throw new Error("Không thể duyệt trang");
      const data = await res.json();
      alert(`Dự án đã được duyệt thành công! Trạng thái: ${data.state}`);
      await loadProject(currentProjectId);
    } catch (err) {
      alert(err.message);
    }
  }

  async function handleRollbackProject() {
    if (!currentProjectId || !versionsList.length) return;
    const prevVersion = activeVersion > 1 ? activeVersion - 1 : 1;
    const target = prompt(`Nhập phiên bản muốn rollback (hiện tại: v${activeVersion}):`, String(prevVersion));
    if (!target) return;

    const baseApi = getApiBaseUrl();
    try {
      const res = await fetch(`${baseApi}/api/projects/${currentProjectId}/rollback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_version: parseInt(target, 10) })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Rollback thất bại");
      }
      await loadProject(currentProjectId);
    } catch (err) {
      alert(err.message);
    }
  }

  function handleExportZip() {
    if (!currentProjectId) return;
    const baseApi = getApiBaseUrl();
    window.location.href = `${baseApi}/api/projects/${currentProjectId}/export`;
  }

  async function loadProject(projectId) {
    const baseApi = getApiBaseUrl();
    try {
      const res = await fetch(`${baseApi}/api/projects/${projectId}`);
      if (!res.ok) throw new Error("Không tìm thấy dự án");
      const data = await res.json();
      currentProjectId = data.project_id;
      projectIdDisplay.textContent = currentProjectId;

      const manifest = data.manifest;
      formatSelect.value = manifest.output_format || "html_css";
      currentOutputFormat = manifest.output_format || "html_css";

      activeVersion = manifest.active_version;
      versionsList = manifest.versions || [];
      versionFormInputs = data.version_form_inputs || {};

      const activeSnapshot =
        (activeVersion && versionFormInputs[String(activeVersion)]) || manifest.form_input;
      if (activeSnapshot) {
        hydrateFormInput(activeSnapshot);
      }

      toggleCreationPanel(true);
      syncActionButtons();
      renderVersionsList();
      renderQAReport(data.qa_report);
      updatePreviewFrame();

      connectSSE(currentProjectId);
    } catch (err) {
      console.error(err);
    }
  }

  function connectSSE(projectId) {
    const baseApi = getApiBaseUrl();
    if (eventSource) eventSource.close();

    const streamUrl = `${baseApi}/api/projects/${projectId}/stream`;
    eventSource = new EventSource(streamUrl);

    eventSource.addEventListener("connected", () => {
      taskStatusBadge.textContent = "Đang kết nối...";
      taskStatusBadge.className = "text-xs px-2.5 py-1 rounded-full font-semibold bg-blue-100 text-blue-800";
      taskStatusBadge.classList.remove("hidden");
    });

    eventSource.addEventListener("progress", (e) => {
      const data = JSON.parse(e.data);
      const stage = data.stage;
      activityBox.classList.remove("hidden");
      activityText.textContent = `Agent đang thực thi: [${stage.toUpperCase()}]`;

      taskStatusBadge.textContent = `Đang xử lý: ${stage}`;
      taskStatusBadge.className = "text-xs px-2.5 py-1 rounded-full font-semibold bg-amber-100 text-amber-800";
      taskStatusBadge.classList.remove("hidden");
    });

    eventSource.addEventListener("completed", () => {
      activityBox.classList.add("hidden");
      setGeneratingState(false);

      taskStatusBadge.textContent = "Hoàn thành";
      taskStatusBadge.className = "text-xs px-2.5 py-1 rounded-full font-semibold bg-emerald-100 text-emerald-800";

      loadProject(projectId);
    });

    eventSource.addEventListener("failed", (e) => {
      const data = JSON.parse(e.data);
      activityBox.classList.add("hidden");
      setGeneratingState(false);

      taskStatusBadge.textContent = "Thất bại";
      taskStatusBadge.className = "text-xs px-2.5 py-1 rounded-full font-semibold bg-red-100 text-red-800";

      alert(`Thực thi thất bại: ${data.error || "Lỗi không xác định"}`);
      loadProject(projectId);
    });

    eventSource.onerror = () => {
      taskStatusBadge.textContent = "Mất kết nối SSE";
      taskStatusBadge.className = "text-xs px-2.5 py-1 rounded-full font-semibold bg-slate-200 text-slate-700";
    };
  }

  function setGeneratingState(isBusy, message) {
    isBusyGenerating = isBusy;
    btnCreate.disabled = isBusy;
    btnRevise.disabled = isBusy;
    if (btnCreateSpinner) {
      if (isBusy) {
        btnCreateSpinner.classList.remove("hidden");
        btnCreateText.textContent = "Đang xử lý...";
      } else {
        btnCreateSpinner.classList.add("hidden");
        syncActionButtons();
      }
    }
    if (message) {
      activityBox.classList.remove("hidden");
      activityText.textContent = message;
    } else if (!isBusy) {
      activityBox.classList.add("hidden");
    }
  }

  function setViewport(size) {
    [btnVpDesktop, btnVpTablet, btnVpMobile].forEach((btn) => btn.classList.remove("active"));
    if (size === "desktop") {
      btnVpDesktop.classList.add("active");
      wrapper.style.maxWidth = "100%";
    } else if (size === "tablet") {
      btnVpTablet.classList.add("active");
      wrapper.style.maxWidth = "768px";
    } else if (size === "mobile") {
      btnVpMobile.classList.add("active");
      wrapper.style.maxWidth = "375px";
    }
  }

  function setTab(tab) {
    if (tab === "preview") {
      btnTabPreview.classList.add("active");
      btnTabCode.classList.remove("active");
      codeInspector.classList.add("hidden");
      if (activeVersion) previewPlaceholder.classList.add("hidden");
    } else {
      btnTabCode.classList.add("active");
      btnTabPreview.classList.remove("active");
      codeInspector.classList.remove("hidden");
      loadCodeContent();
    }
  }

  function renderVersionsList() {
    versionsContainer.innerHTML = "";
    if (!versionsList.length) {
      versionsContainer.innerHTML = '<span class="text-xs text-slate-400 italic">Chưa có phiên bản nào</span>';
      activeVersionPill.textContent = "v0";
      btnExport.disabled = true;
      btnRevise.disabled = true;
      btnApprove.disabled = true;
      btnRollback.disabled = true;
      return;
    }

    versionsList.forEach((v) => {
      const btn = document.createElement("button");
      const isActive = v === activeVersion;
      btn.className = isActive
        ? "text-xs font-semibold px-3 py-1 rounded-lg bg-slate-900 text-white shadow-sm"
        : "text-xs font-medium px-3 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-200 transition";
      btn.textContent = isActive ? `v${v} (Active)` : `v${v}`;
      btn.onclick = () => selectVersion(v);
      versionsContainer.appendChild(btn);
    });

    activeVersionPill.textContent = activeVersion ? `v${activeVersion} Active` : "v0";
    btnExport.disabled = !activeVersion;
    btnRevise.disabled = !activeVersion;
    btnApprove.disabled = !activeVersion;
    btnRollback.disabled = versionsList.length < 2;
  }

  function renderQAReport(qaReport) {
    qaList.innerHTML = "";
    if (!qaReport || !qaReport.checks || !qaReport.checks.length) {
      qaScoreBadge.textContent = "Chưa có báo cáo";
      qaScoreBadge.className = "text-[11px] font-semibold text-slate-400";
      qaList.innerHTML = '<span class="text-slate-400 italic">Báo cáo QA sẽ xuất hiện tại đây khi Agent hoàn thành kiểm tra.</span>';
      return;
    }

    const checks = qaReport.checks;
    const passedCount = checks.filter((c) => String(c.status).toLowerCase() === "pass").length;
    qaScoreBadge.textContent = `${passedCount}/${checks.length} Passed`;
    qaScoreBadge.className =
      passedCount === checks.length
        ? "text-[11px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full"
        : "text-[11px] font-semibold text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full";

    checks.forEach((c) => {
      const isPass = String(c.status).toLowerCase() === "pass";
      const item = document.createElement("div");
      item.className = "flex items-start gap-2 py-0.5";
      item.innerHTML = `
        <span class="${isPass ? "text-emerald-600 font-bold" : "text-red-500 font-bold"}">${isPass ? "✓" : "✗"}</span>
        <div class="flex-1">
          <span class="font-medium text-slate-700">${c.name || c.id || "Tiêu chí"}</span>
          ${c.details ? `<p class="text-[10px] text-slate-500">${c.details}</p>` : ""}
        </div>
      `;
      qaList.appendChild(item);
    });
  }

  function updatePreviewFrame() {
    if (!currentProjectId || !activeVersion) {
      previewPlaceholder.classList.remove("hidden");
      previewIframe.src = "about:blank";
      previewUrlDisplay.textContent = "about:blank";
      linkExternal.classList.add("hidden");
      return;
    }

    const baseApi = getApiBaseUrl();
    previewPlaceholder.classList.add("hidden");
    const previewUrl = `${baseApi}/preview/${currentProjectId}/index.html?t=${Date.now()}`;
    previewIframe.src = previewUrl;
    previewUrlDisplay.textContent = `${baseApi || window.location.origin}/preview/${currentProjectId}/index.html`;
    linkExternal.href = `${baseApi}/preview/${currentProjectId}/index.html`;
    linkExternal.classList.remove("hidden");
  }

  function reloadPreview() {
    if (previewIframe && previewIframe.src !== "about:blank") {
      previewIframe.contentWindow?.location.reload();
    }
  }

  async function loadCodeContent() {
    if (!currentProjectId || !activeVersion) {
      codeDisplay.textContent = "// Chưa có mã nguồn";
      return;
    }
    const baseApi = getApiBaseUrl();
    try {
      codeDisplay.textContent = "// Đang tải mã nguồn...";
      const res = await fetch(`${baseApi}/preview/${currentProjectId}/index.html`);
      if (res.ok) {
        codeDisplay.textContent = await res.text();
      } else {
        codeDisplay.textContent = `// Không thể tải mã nguồn (HTTP ${res.status})`;
      }
    } catch (err) {
      codeDisplay.textContent = `// Lỗi tải mã nguồn: ${err.message}`;
    }
  }

  function selectVersion(v) {
    activeVersion = v;
    if (versionFormInputs && versionFormInputs[String(v)]) {
      hydrateFormInput(versionFormInputs[String(v)]);
      updatePromptPreviewIfOpen();
    }
    renderVersionsList();
    updatePreviewFrame();
  }

  document.addEventListener("DOMContentLoaded", init);
})();
