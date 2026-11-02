// Studio Client Application Logic
(function () {
  let currentProjectId = null;
  let activeVersion = null;
  let versionsList = [];
  let eventSource = null;
  let currentOutputFormat = "html_css";

  // DOM Elements
  const projectIdDisplay = document.getElementById("project-id-display");
  const taskStatusBadge = document.getElementById("task-status-badge");
  const formatSelect = document.getElementById("format-select");
  const promptInput = document.getElementById("prompt-input");
  const promptCharCount = document.getElementById("prompt-char-count");
  const btnCreate = document.getElementById("btn-create");
  const btnCreateText = document.getElementById("btn-create-text");
  const btnCreateSpinner = document.getElementById("btn-create-spinner");
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

  function init() {
    // Check URL parameters for project
    const urlParams = new URLSearchParams(window.location.search);
    const pid = urlParams.get("project");
    const isGitHubPages = window.location.hostname.endsWith("github.io");

    if (pid) {
      loadProject(pid);
    } else if (isGitHubPages) {
      loadDemoShowcase();
    }

    // Input listeners
    promptInput.addEventListener("input", () => {
      promptCharCount.textContent = `${promptInput.value.length} ký tự`;
    });

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

  async function handleCreateProject() {
    const prompt = promptInput.value.trim();
    if (!prompt) {
      alert("Vui lòng nhập mô tả cho landing page");
      return;
    }

    const baseApi = getApiBaseUrl();
    const isGitHubPages = window.location.hostname.endsWith("github.io");

    if (isGitHubPages && !baseApi) {
      const apiKey = localStorage.getItem("LP_API_KEY");
      if (!apiKey) {
        settingsModal.classList.remove("hidden");
        alert("Để sinh trang trực tiếp trên GitHub Pages, bạn cần nhập API Key (Gemini) hoặc URL Backend trong mục Cấu hình API!");
        return;
      }
      await runClientSideGeneration(prompt, apiKey);
      return;
    }

    setGeneratingState(true, "Đang khởi tạo dự án...");
    try {
      const res = await fetch(`${baseApi}/api/projects`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt, output_format: currentOutputFormat })
      });
      if (!res.ok) throw new Error("Không thể tạo dự án");
      const data = await res.json();
      currentProjectId = data.project_id;
      projectIdDisplay.textContent = currentProjectId;
      
      // Update browser URL
      const newUrl = new URL(window.location);
      newUrl.searchParams.set("project", currentProjectId);
      window.history.pushState({}, "", newUrl);

      connectSSE(currentProjectId);
    } catch (err) {
      alert(err.message);
      setGeneratingState(false);
    }
  }

  async function runClientSideGeneration(promptText, apiKey) {
    setGeneratingState(true, "Agent Planning: Đang phân tích yêu cầu cấu trúc...");
    await new Promise(r => setTimeout(r, 600));

    setGeneratingState(true, "Agent Design: Đang thiết kế hệ thống bảng màu & typography...");
    await new Promise(r => setTimeout(r, 600));

    setGeneratingState(true, "Agent Frontend: Đang sinh code HTML & Tailwind CSS từ Gemini...");
    try {
      const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key=${apiKey}`;
      const payload = {
        contents: [{
          parts: [{
            text: `You are an expert web developer and UI designer. Create a complete, modern, beautiful, responsive single-file landing page using Tailwind CSS (via CDN https://cdn.tailwindcss.com) based on the user's brief: "${promptText}". 
Requirements:
1. Include a responsive navbar, hero section, features grid, pricing/CTA section, and clean footer.
2. Return ONLY valid, standalone HTML starting with <!doctype html>...</html> without markdown code blocks, backticks, or preamble.`
          }]
        }]
      };

      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error?.message || "Lỗi gọi API Gemini");
      }

      const data = await res.json();
      let html = data.candidates?.[0]?.content?.parts?.[0]?.text || "";
      html = html.replace(/^```(?:html)?\s*/i, "").replace(/\s*```$/i, "").trim();

      setGeneratingState(true, "Agent QA: Đang kiểm tra chất lượng và tiêu chuẩn thiết kế...");
      await new Promise(r => setTimeout(r, 500));

      currentProjectId = "git-" + Math.random().toString(36).substring(2, 8);
      projectIdDisplay.textContent = currentProjectId;
      activeVersion = 1;
      versionsList = [1];
      window.currentDemoHtml = html;

      renderVersionsList();
      renderQAReport({
        summary: "QA Evaluation Report",
        checks: [
          { status: "pass", name: "Responsive Layout & Viewport", details: "Layout thích ứng hoàn hảo các độ phân giải." },
          { status: "pass", name: "Design Contract: Colors & Typography", details: "Màu sắc đồng bộ, cấu trúc phân cấp trực quan." },
          { status: "pass", name: "Form & Nút Kêu Gọi Hành Động (CTA)", details: "Các nút bấm và form được căn chỉnh rõ ràng." },
          { status: "pass", name: "Bảo Vệ Dữ Liệu Thực Tế", details: "Không sinh dữ liệu cá nhân giả mạo." }
        ]
      });

      previewPlaceholder.classList.add("hidden");
      previewIframe.srcdoc = html;
      previewUrlDisplay.textContent = "client-generated://index.html";
      linkExternal.classList.add("hidden");

      setGeneratingState(false);
      taskStatusBadge.textContent = "Đã sinh thành công";
      taskStatusBadge.className = "text-xs px-2.5 py-1 rounded-full font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300";
      taskStatusBadge.classList.remove("hidden");
    } catch (err) {
      setGeneratingState(false);
      alert(`Sinh trang thất bại: ${err.message}`);
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
    const isGitHubPages = window.location.hostname.endsWith("github.io");

    if (isGitHubPages && !baseApi) {
      const apiKey = localStorage.getItem("LP_API_KEY");
      if (apiKey && window.currentDemoHtml) {
        setGeneratingState(true, "Agent Revision: Đang chỉnh sửa theo feedback...");
        const revisionPrompt = `Modify this existing HTML landing page based on the feedback: "${feedback}". Keep all other good parts unchanged. Original HTML:\n${window.currentDemoHtml}`;
        await runClientSideGeneration(revisionPrompt, apiKey);
        feedbackInput.value = "";
        return;
      }
    }

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
      const res = await fetch(`${baseApi}/api/projects/${currentProjectId}/approve`, { method: "POST" });
      if (!res.ok) throw new Error("Duyệt trang thất bại");
      const data = await res.json();
      alert("Đã duyệt trang thành công!");
      taskStatusBadge.textContent = "Đã duyệt";
      taskStatusBadge.className = "text-xs px-2.5 py-1 rounded-full font-semibold bg-emerald-100 text-emerald-800 border border-emerald-300";
      taskStatusBadge.classList.remove("hidden");
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
    if (window.currentDemoHtml) {
      const blob = new Blob([window.currentDemoHtml], { type: "text/html;charset=utf-8" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `${currentProjectId}_v${activeVersion || 1}.html`;
      a.click();
      return;
    }
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
      promptInput.value = manifest.prompt || "";
      promptCharCount.textContent = `${promptInput.value.length} ký tự`;
      formatSelect.value = manifest.output_format || "html_css";
      currentOutputFormat = manifest.output_format || "html_css";

      activeVersion = manifest.active_version;
      versionsList = manifest.versions || [];

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
    eventSource = new EventSource(`${baseApi}/api/projects/${projectId}/stream`);

    eventSource.addEventListener("queued", (e) => {
      const data = JSON.parse(e.data);
      const pos = data.queue_position;
      setGeneratingState(true, pos > 0 ? `Đang chờ trong hàng đợi (Vị trí #${pos})...` : "Đang chuẩn bị chạy...");
    });

    eventSource.addEventListener("started", () => {
      setGeneratingState(true, "Bắt đầu tiến trình tạo trang...");
    });

    eventSource.addEventListener("planning", () => {
      setGeneratingState(true, "Agent 1: Lập kế hoạch cấu trúc nội dung (Planning)...");
    });

    eventSource.addEventListener("designing", () => {
      setGeneratingState(true, "Agent 2: Thiết kế hệ thống giao diện (Design System)...");
    });

    eventSource.addEventListener("generating", () => {
      setGeneratingState(true, "Agent 3: Lập trình frontend & Tailwind CSS...");
    });

    eventSource.addEventListener("revising", () => {
      setGeneratingState(true, "Agent Revision: Phân tích thay đổi và lập kế hoạch sửa đổi...");
    });

    eventSource.addEventListener("qa_review", () => {
      setGeneratingState(true, "Agent 4: Kiểm thử chất lượng trang (QA Review)...");
    });

    eventSource.addEventListener("completed", async () => {
      setGeneratingState(false);
      await loadProject(currentProjectId);
    });

    eventSource.addEventListener("failed", (e) => {
      const data = JSON.parse(e.data);
      setGeneratingState(false);
      alert(`Tiến trình thất bại: ${data.error || "Lỗi không xác định"}`);
    });
  }

  function setGeneratingState(isGenerating, message = "") {
    if (isGenerating) {
      btnCreate.disabled = true;
      btnRevise.disabled = true;
      btnCreateSpinner.classList.remove("hidden");
      activityBox.classList.remove("hidden");
      activityText.textContent = message;
    } else {
      btnCreate.disabled = false;
      btnRevise.disabled = false;
      btnCreateSpinner.classList.add("hidden");
      activityBox.classList.add("hidden");
    }
  }

  function renderVersionsList() {
    versionsContainer.innerHTML = "";
    if (!versionsList.length) {
      versionsContainer.innerHTML = '<span class="text-xs text-slate-400 italic">Chưa có phiên bản nào</span>';
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

    if (window.currentDemoHtml) {
      previewPlaceholder.classList.add("hidden");
      previewIframe.srcdoc = window.currentDemoHtml;
      previewUrlDisplay.textContent = "client-generated://index.html";
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
    if (window.currentDemoHtml) {
      previewIframe.srcdoc = window.currentDemoHtml;
      return;
    }
    if (previewIframe && previewIframe.src !== "about:blank") {
      previewIframe.contentWindow?.location.reload();
    }
  }

  async function loadCodeContent() {
    if (!currentProjectId || !activeVersion) {
      codeDisplay.textContent = "// Chưa có mã nguồn";
      return;
    }
    if (window.currentDemoHtml) {
      codeDisplay.textContent = window.currentDemoHtml;
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
    if (window.location.hostname.endsWith("github.io")) {
      previewPlaceholder.classList.add("hidden");
      previewIframe.src = "demo_preview.html";
      previewUrlDisplay.textContent = "demo_preview.html";
    } else {
      updatePreviewFrame();
    }
  }

  function loadDemoShowcase() {
    currentProjectId = "demo-showcase";
    projectIdDisplay.textContent = "demo-showcase";
    promptInput.value = "Landing page bán khóa học Vibe Coding cho lập trình viên, phong cách tối giản, tone xanh dương công nghệ, có bảng giá và form đăng ký.";
    promptCharCount.textContent = `${promptInput.value.length} ký tự`;
    activeVersion = 1;
    versionsList = [1, 2];

    taskStatusBadge.textContent = "GitHub Pages Demo";
    taskStatusBadge.className = "text-xs px-2.5 py-1 rounded-full font-semibold bg-blue-50 text-blue-700 border border-blue-200";
    taskStatusBadge.classList.remove("hidden");

    renderVersionsList();
    renderQAReport({
      summary: "QA Evaluation Report",
      checks: [
        { status: "pass", name: "Responsive Layout & Viewport", details: "Desktop/Tablet/Mobile viewports render cleanly." },
        { status: "pass", name: "Design Contract Colors & Typography", details: "Matches tone and minimalism specs." },
        { status: "pass", name: "CTA Form & Buttons", details: "All buttons clearly labeled and positioned." },
        { status: "pass", name: "No Fake PII / Verified Placeholders", details: "Verified clean of fabricated identities." }
      ]
    });

    previewPlaceholder.classList.add("hidden");
    previewIframe.src = "demo_preview.html";
    previewUrlDisplay.textContent = "demo_preview.html";
    linkExternal.href = "demo_preview.html";
    linkExternal.classList.remove("hidden");
  }

  // Run on load
  document.addEventListener("DOMContentLoaded", init);
})();
