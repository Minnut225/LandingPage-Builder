// Studio Client Application Logic
(function () {
  let currentProjectId = null;
  let activeVersion = null;
  let versionsList = [];
  let eventSource = null;
  let currentOutputFormat = "html_css";

  // Template & Form State
  let templatesData = null;
  let selectedTemplateId = "personal_portfolio";
  let selectedStyle = "modern_clean";
  let selectedPaletteId = "tech_blue";
  let customColor = "#2563EB";
  let isCreationCollapsed = false;

  // DOM Elements
  const projectIdDisplay = document.getElementById("project-id-display");
  const taskStatusBadge = document.getElementById("task-status-badge");
  const formatSelect = document.getElementById("format-select");

  // Creation Panel Elements
  const creationPanel = document.getElementById("creation-panel");
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

  function getApiBaseUrl() {
    return localStorage.getItem("LP_BACKEND_URL") || (window.ENV_CONFIG && window.ENV_CONFIG.BACKEND_URL) || "";
  }

  async function init() {
    // Check URL parameters for project
    const urlParams = new URLSearchParams(window.location.search);
    const pid = urlParams.get("project");

    await loadTemplates();

    if (pid) {
      loadProject(pid);
    }

    // Event listeners
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
        renderFormFields(selectedTemplateId);
        updatePromptPreviewIfOpen();
      });
    }

    if (customColorPicker) {
      customColorPicker.addEventListener("input", (e) => {
        customColor = e.target.value;
        // Clear active preset palette styling
        document.querySelectorAll(".palette-card").forEach(c => c.classList.remove("active"));
        selectedPaletteId = "custom";
        updatePromptPreviewIfOpen();
      });
    }

    if (btnTogglePromptPreview) {
      btnTogglePromptPreview.addEventListener("click", togglePromptPreview);
    }

    btnCreate.addEventListener("click", handleCreateProject);
    btnRevise.addEventListener("click", handleReviseProject);
    btnApprove.addEventListener("click", handleApproveProject);
    btnRollback.addEventListener("click", handleRollbackProject);
    btnExport.addEventListener("click", handleExportZip);
    btnReloadPreview.addEventListener("click", reloadPreview);

    // Viewport resizing
    btnVpDesktop.addEventListener("click", () => setViewport("desktop"));
    btnVpTablet.addEventListener("click", () => setViewport("tablet"));
    btnVpMobile.addEventListener("click", () => setViewport("mobile"));

    // Preview / Code tabs
    btnTabPreview.addEventListener("click", () => setTab("preview"));
    btnTabCode.addEventListener("click", () => setTab("code"));

    formatSelect.addEventListener("change", (e) => {
      currentOutputFormat = e.target.value;
    });

    // Settings Modal
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
              { name: "bio", label: "Giới thiệu ngắn", type: "textarea", required: true, placeholder: "Mô tả định hướng chuyên môn..." },
              { name: "skills", label: "Kỹ năng chính", type: "textarea", required: false, placeholder: "Python, FastAPI\nReact, TypeScript" },
              { name: "cta_text", label: "Nút CTA", type: "text", required: true, placeholder: "Liên hệ ngay" }
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
    renderFormFields(selectedTemplateId);
  }

  function renderTemplateSelector() {
    if (!templateSelect || !templatesData) return;
    templateSelect.innerHTML = "";
    Object.values(templatesData.templates).forEach(tpl => {
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
    Object.values(templatesData.styles).forEach(st => {
      const card = document.createElement("div");
      card.className = `style-card p-2 rounded-lg border text-xs cursor-pointer ${
        st.id === selectedStyle ? "active border-blue-600 bg-blue-50 text-blue-900" : "border-slate-200 bg-white hover:bg-slate-50 text-slate-700"
      }`;
      card.innerHTML = `
        <div class="font-bold">${st.name}</div>
        <div class="text-[10px] text-slate-500 line-clamp-1">${st.description}</div>
      `;
      card.onclick = () => {
        document.querySelectorAll(".style-card").forEach(c => c.classList.remove("active", "border-blue-600", "bg-blue-50", "text-blue-900"));
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
    Object.values(templatesData.palettes).forEach(pal => {
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
        document.querySelectorAll(".palette-card").forEach(c => c.classList.remove("active", "border-blue-600", "bg-blue-50"));
        card.classList.add("active", "border-blue-600", "bg-blue-50");
        selectedPaletteId = pal.id;
        customColor = pal.primary;
        if (customColorPicker) customColorPicker.value = pal.primary;
        updatePromptPreviewIfOpen();
      };
      colorPaletteSelector.appendChild(card);
    });
  }

  function renderFormFields(templateId, initialData = {}) {
    if (!dynamicFormFields || !templatesData) return;
    dynamicFormFields.innerHTML = "";

    const tpl = templatesData.templates[templateId];
    if (!tpl || !tpl.fields) return;

    tpl.fields.forEach(field => {
      const container = document.createElement("div");
      container.className = "flex flex-col gap-1";

      const label = document.createElement("label");
      label.className = "text-[11px] font-semibold text-slate-700 flex items-center justify-between";
      label.innerHTML = `
        <span>${field.label} ${field.required ? '<span class="text-red-500">*</span>' : ''}</span>
      `;

      let inputEl;
      const initVal = initialData[field.name] || "";
      if (field.type === "textarea") {
        inputEl = document.createElement("textarea");
        inputEl.rows = 2;
        inputEl.className = "w-full text-xs p-2 bg-white border border-slate-300 rounded-lg text-slate-800 placeholder-slate-400 focus:ring-2 focus:ring-blue-500 focus:outline-none resize-none transition leading-relaxed";
      } else {
        inputEl = document.createElement("input");
        inputEl.type = "text";
        inputEl.className = "w-full text-xs p-2 bg-white border border-slate-300 rounded-lg text-slate-800 placeholder-slate-400 focus:ring-2 focus:ring-blue-500 focus:outline-none transition";
      }

      inputEl.name = field.name;
      inputEl.id = `field-${field.name}`;
      inputEl.placeholder = field.placeholder || "";
      inputEl.value = initVal;

      inputEl.addEventListener("input", () => {
        updatePromptPreviewIfOpen();
      });

      container.appendChild(label);
      container.appendChild(inputEl);
      dynamicFormFields.appendChild(container);
    });
  }

  function getFormData() {
    const data = {};
    if (!dynamicFormFields) return data;
    const inputs = dynamicFormFields.querySelectorAll("input, textarea");
    inputs.forEach(el => {
      data[el.name] = el.value.trim();
    });
    return data;
  }

  function getSelectedPaletteObject() {
    if (selectedPaletteId !== "custom" && templatesData?.palettes?.[selectedPaletteId]) {
      return templatesData.palettes[selectedPaletteId];
    }
    return {
      name: "Custom Palette",
      primary: customColor || "#2563EB",
      surface: "#F8FAFC",
      accent: "#0284C7"
    };
  }

  function toggleCreationPanel(collapsed) {
    isCreationCollapsed = collapsed;
    if (collapsed) {
      creationBody.classList.add("hidden");
      creationToggleIcon.textContent = "▶ Mở rộng";
      if (templatesData?.templates?.[selectedTemplateId]) {
        creationSummaryBadge.textContent = templatesData.templates[selectedTemplateId].name;
        creationSummaryBadge.classList.remove("hidden");
      }
    } else {
      creationBody.classList.remove("hidden");
      creationToggleIcon.textContent = "▼ Thu gọn";
      creationSummaryBadge.classList.add("hidden");
    }
  }

  let promptPreviewDebounceTimer = null;
  function updatePromptPreviewIfOpen() {
    if (promptPreviewContainer && !promptPreviewContainer.classList.contains("hidden")) {
      clearTimeout(promptPreviewDebounceTimer);
      promptPreviewDebounceTimer = setTimeout(fetchPromptPreview, 300);
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
          form_data: getFormData(),
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

  async function handleCreateProject() {
    const formData = getFormData();
    // Validate required fields
    const tpl = templatesData?.templates?.[selectedTemplateId];
    if (tpl?.fields) {
      for (const f of tpl.fields) {
        if (f.required && !formData[f.name]) {
          alert(`Vui lòng điền trường bắt buộc: "${f.label}"`);
          const targetInput = document.getElementById(`field-${f.name}`);
          if (targetInput) targetInput.focus();
          return;
        }
      }
    }

    const baseApi = getApiBaseUrl();
    setGeneratingState(true, "Đang khởi tạo dự án và gửi yêu cầu sang Agent Pipeline...");
    try {
      const payload = {
        template_id: selectedTemplateId,
        form_data: formData,
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
        const err = await res.json();
        throw new Error(err.detail || "Không thể tạo dự án");
      }
      const data = await res.json();
      currentProjectId = data.project_id;
      projectIdDisplay.textContent = currentProjectId;

      // Update browser URL
      const newUrl = new URL(window.location);
      newUrl.searchParams.set("project", currentProjectId);
      window.history.pushState({}, "", newUrl);

      // Auto-collapse creation form after successful submission
      toggleCreationPanel(true);
      connectSSE(currentProjectId);
    } catch (err) {
      alert(err.message);
      setGeneratingState(false);
    }
  }

  async function handleReviseProject() {
    const feedback = feedbackInput.value.trim();
    if (!feedback) {
      alert("Vui lòng nhập nội dung góp ý chỉnh sửa");
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
      if (!res.ok) throw new Error("Gửi phản hồi thất bại");
      feedbackInput.value = "";
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

      // If project has structured form input, restore fields
      if (manifest.form_input) {
        const fi = manifest.form_input;
        if (fi.template_id) {
          selectedTemplateId = fi.template_id;
          if (templateSelect) templateSelect.value = selectedTemplateId;
          updateTemplateDescription();
        }
        if (fi.style) selectedStyle = fi.style;
        if (fi.color_palette) {
          selectedPaletteId = fi.color_palette.id || "custom";
          customColor = fi.color_palette.primary || "#2563EB";
          if (customColorPicker) customColorPicker.value = customColor;
        }
        renderFormFields(selectedTemplateId, fi.form_data || {});
        renderStyleSelector();
        renderPaletteSelector();
      }

      activeVersion = manifest.active_version;
      versionsList = manifest.versions || [];

      // Auto-collapse creation form since project exists
      toggleCreationPanel(true);

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

    eventSource.addEventListener("completed", (e) => {
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
    btnCreate.disabled = isBusy;
    btnRevise.disabled = isBusy;
    if (btnCreateSpinner) {
      if (isBusy) {
        btnCreateSpinner.classList.remove("hidden");
        btnCreateText.textContent = "Đang xử lý...";
      } else {
        btnCreateSpinner.classList.add("hidden");
        btnCreateText.textContent = "Tạo Landing Page";
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
    [btnVpDesktop, btnVpTablet, btnVpMobile].forEach(btn => btn.classList.remove("active"));
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
    const passedCount = checks.filter(c => String(c.status).toLowerCase() === "pass").length;
    qaScoreBadge.textContent = `${passedCount}/${checks.length} Passed`;
    qaScoreBadge.className = passedCount === checks.length
      ? "text-[11px] font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-2 py-0.5 rounded-full"
      : "text-[11px] font-semibold text-amber-700 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded-full";

    checks.forEach(c => {
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
    renderVersionsList();
    updatePreviewFrame();
  }

  // Run on load
  document.addEventListener("DOMContentLoaded", init);
})();
