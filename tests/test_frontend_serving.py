import json
import subprocess
import pytest
from fastapi.testclient import TestClient
from pathlib import Path
from web.server import create_app
from form_schemas import get_templates_metadata


@pytest.fixture
def client(tmp_path: Path):
    app = create_app(base_dir=tmp_path)
    return TestClient(app)


def test_frontend_static_serving(client: TestClient):
    res = client.get("/")
    assert res.status_code == 200
    assert "Landing Page Studio" in res.text
    assert "iframe" in res.text

    js_res = client.get("/app.js")
    assert js_res.status_code == 200
    assert "EventSource" in js_res.text or "createProject" in js_res.text


def test_studio_serves_modular_property_builder_hooks(client: TestClient):
    html_res = client.get("/")
    assert html_res.status_code == 200
    html = html_res.text
    assert 'id="section-picker-bar"' in html
    assert 'id="btn-new-project"' in html

    js_res = client.get("/app.js")
    assert js_res.status_code == 200
    js = js_res.text
    assert "section-picker-bar" in js
    assert "custom_properties" in js
    assert "version_form_inputs" in js
    assert "Cập nhật theo Properties" in js


def test_app_js_uid_collision_custom_prop_grid_reset_and_legacy_hydration(tmp_path: Path):
    app_js_path = Path(__file__).resolve().parent.parent / "web" / "static" / "app.js"
    tpl_file = tmp_path / "templates.json"
    tpl_file.write_text(json.dumps(get_templates_metadata(), ensure_ascii=False), encoding="utf-8")

    harness_file = tmp_path / "harness.js"
    harness_file.write_text(
        r"""
const fs = require("fs");
const appCode = fs.readFileSync(process.argv[2], "utf8");
const templatesMeta = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));

const elementsById = new Map();
function makeEl(tag, id = "") {
  const listeners = {};
  const classSet = new Set();
  const el = {
    tagName: tag.toUpperCase(),
    id: id,
    name: "",
    type: "",
    value: "",
    textContent: "",
    _html: "",
    get innerHTML() { return this._html; },
    set innerHTML(v) { this._html = String(v || ""); el.children = []; },
    disabled: false,
    style: {},
    children: [],
    onclick: null,
    onmousedown: null,
    get className() { return Array.from(classSet).join(" "); },
    set className(v) {
      classSet.clear();
      String(v || "").split(/\s+/).filter(Boolean).forEach(c => classSet.add(c));
    },
    classList: {
      add: (...cs) => cs.forEach(c => classSet.add(c)),
      remove: (...cs) => cs.forEach(c => classSet.delete(c)),
      contains: (c) => classSet.has(c),
    },
    appendChild(child) {
      el.children.push(child);
      if (child && child.id) elementsById.set(child.id, child);
      return child;
    },
    addEventListener(ev, fn) {
      listeners[ev] = listeners[ev] || [];
      listeners[ev].push(fn);
    },
    dispatch(ev, payload = {}) {
      (listeners[ev] || []).forEach(fn => fn(payload));
      if (ev === "click" && typeof el.onclick === "function") {
        el.onclick({ stopPropagation() {}, preventDefault() {}, ...payload });
      }
    },
    focus() {},
    scrollIntoView() {},
    querySelectorAll() { return []; },
  };
  if (id) elementsById.set(id, el);
  return el;
}

function registerTreeIds(node) {
  if (!node) return;
  if (node.id) elementsById.set(node.id, node);
  (node.children || []).forEach(registerTreeIds);
}

function findButtonsByText(root, substr) {
  const out = [];
  function walk(node) {
    if (!node) return;
    if (node.tagName === "BUTTON" && String(node.textContent || "").includes(substr)) out.push(node);
    (node.children || []).forEach(walk);
  }
  walk(root);
  return out;
}

function findInputs(root) {
  const out = [];
  function walk(node) {
    if (!node) return;
    if (node.tagName === "INPUT" || node.tagName === "TEXTAREA") out.push(node);
    (node.children || []).forEach(walk);
  }
  walk(root);
  return out;
}

const knownIds = [
  "project-id-display", "btn-new-project", "task-status-badge", "format-select",
  "creation-header", "creation-body", "creation-summary-badge", "creation-toggle-icon", "btn-toggle-creation",
  "template-select", "template-desc", "style-selector", "color-palette-selector", "custom-color-picker",
  "section-picker-bar", "dynamic-form-fields",
  "btn-toggle-prompt-preview", "prompt-preview-icon", "prompt-preview-container", "prompt-preview-text",
  "btn-create", "btn-create-text", "btn-create-spinner",
  "activity-box", "activity-text", "versions-container", "active-version-pill",
  "qa-score-badge", "qa-list", "feedback-input", "btn-revise", "btn-approve", "btn-rollback", "btn-export",
  "preview-iframe", "preview-placeholder", "preview-url-display", "link-external", "btn-reload-preview",
  "code-inspector", "code-display", "viewport-frame-wrapper",
  "btn-vp-desktop", "btn-vp-tablet", "btn-vp-mobile", "btn-tab-preview", "btn-tab-code",
  "btn-settings", "settings-modal", "btn-close-settings", "btn-save-settings",
  "cfg-backend-url", "cfg-provider", "cfg-api-key"
];
knownIds.forEach(id => makeEl("div", id));
elementsById.get("btn-create-spinner").className = "hidden";

let domReadyHandler = null;
let lastRevisePayload = null;
let alerts = [];
let currentProjectMock = {
  project_id: "lp_1",
  manifest: {
    output_format: "html_css",
    active_version: 1,
    versions: [1],
    form_input: {
      template_id: "personal_portfolio",
      style: "modern_clean",
      form_data: {
        sections: {
          about_me: { enabled: true, values: { full_name: "Minh", title: "AI Dev", bio: "Bio" } },
          projects: {
            enabled: true,
            items: [
              { id: "item_1", values: { name: "Proj 1" } },
              { id: "item_2", values: { name: "Proj 2" } }
            ]
          }
        }
      }
    }
  },
  version_form_inputs: {},
  qa_report: {}
};

let hangNextCreate = false;
global.window = {
  location: new URL("http://localhost/?project=lp_1"),
  history: { pushState() {} },
  ENV_CONFIG: {}
};
global.localStorage = { getItem() { return ""; }, setItem() {} };
global.alert = (msg) => alerts.push(msg);
global.EventSource = class { addEventListener() {} close() {} };
global.document = {
  getElementById(id) {
    registerTreeIds(elementsById.get("dynamic-form-fields"));
    return elementsById.get(id) || null;
  },
  createElement(tag) { return makeEl(tag); },
  querySelectorAll() { return []; },
  addEventListener(ev, fn) { if (ev === "DOMContentLoaded") domReadyHandler = fn; }
};
global.fetch = async (url, opts) => {
  if (url.endsWith("/api/templates")) {
    return { ok: true, json: async () => templatesMeta };
  }
  if (url.includes("/api/projects/lp_")) {
    if (opts && opts.method === "POST" && url.endsWith("/revise")) {
      lastRevisePayload = JSON.parse(opts.body);
      return { ok: true, json: async () => ({ status: "queued" }) };
    }
    return { ok: true, json: async () => currentProjectMock };
  }
  if (url.endsWith("/api/projects") && opts && opts.method === "POST") {
    if (hangNextCreate) return new Promise(() => {});
    return { ok: true, json: async () => ({ project_id: "lp_new", status: "queued" }) };
  }
  return { ok: true, json: async () => ({ prompt: "ok" }) };
};

eval(appCode);

(async () => {
  await domReadyHandler();
  const dynFields = elementsById.get("dynamic-form-fields");

  // 1. Critical #1: After hydrating item_1 and item_2, clicking "+ Thêm dự án" must NOT collide with item_1
  const addProjBtn = findButtonsByText(dynFields, "+ Thêm dự án")[0];
  if (!addProjBtn) throw new Error("Missing + Thêm dự án button");
  addProjBtn.dispatch("click");
  registerTreeIds(dynFields);

  const projInputs = findInputs(dynFields).filter(i => i.id.startsWith("sec-projects-") && i.id.endsWith("-name"));
  const newInput = projInputs[projInputs.length - 1];
  if (!newInput || newInput.id === "sec-projects-item_1-name" || newInput.id === "sec-projects-item_2-name") {
    throw new Error("Item ID collided after hydration: " + (newInput && newInput.id));
  }

  // 2. Important #1: "+ Thuộc tính tùy chỉnh" inputs must have w-full and min-w-0
  const addCustomBtn = findButtonsByText(dynFields, "+ Thuộc tính tùy chỉnh")[0];
  addCustomBtn.dispatch("click");
  const customKeyInp = findInputs(dynFields).find(i => i.placeholder === "Thuộc tính...");
  if (!customKeyInp.className.includes("w-full") || !customKeyInp.className.includes("min-w-0")) {
    throw new Error("Custom prop input missing w-full min-w-0: " + customKeyInp.className);
  }

  // 3. Important #2: Legacy flat hydration for course_workshop (tuition), saas_product (pricing), business_service (testimonials)
  const legacyCases = [
    {
      template_id: "course_workshop",
      form_data: { course_title: "AI Course", instructor: "Minh", tuition: "2.500.000đ", cta_text: "Đăng ký" },
      check(payload) {
        if (payload.sections.tuition.values.price !== "2.500.000đ") {
          throw new Error("Lost legacy course_workshop.tuition: " + JSON.stringify(payload.sections.tuition));
        }
      }
    },
    {
      template_id: "saas_product",
      form_data: { product_name: "FastSaaS", tagline: "Fast", cta_text: "Dùng thử", pricing: "Pro: 29$/tháng" },
      check(payload) {
        const p0 = payload.sections.pricing.items[0];
        if (!p0 || !p0.values.plan_name || !p0.values.price) {
          throw new Error("Incomplete legacy saas_product.pricing: " + JSON.stringify(p0));
        }
      }
    },
    {
      template_id: "business_service",
      form_data: { company_name: "Nexus", headline: "Top Agency", cta_text: "Liên hệ", testimonials: "“Dịch vụ xuất sắc” - CEO Alpha" },
      check(payload) {
        const t0 = payload.sections.testimonials.items[0];
        if (!t0 || !t0.values.author || !t0.values.quote) {
          throw new Error("Incomplete legacy business_service.testimonials: " + JSON.stringify(t0));
        }
      }
    }
  ];

  let lastSse = null;
  global.EventSource = class {
    constructor() { this.handlers = {}; lastSse = this; }
    addEventListener(ev, fn) { this.handlers[ev] = fn; }
    close() {}
  };

  for (const lc of legacyCases) {
    alerts = [];
    lastRevisePayload = null;
    currentProjectMock = {
      project_id: "lp_1",
      manifest: {
        output_format: "html_css",
        active_version: 1,
        versions: [1],
        form_input: { template_id: lc.template_id, style: "modern_clean", form_data: lc.form_data }
      },
      version_form_inputs: {},
      qa_report: {}
    };
    // Trigger loadProject("lp_1") cleanly via SSE completed listener or re-init
    global.window.location = new URL("http://localhost/?project=lp_1");
    // Re-trigger load via rollback/approve or SSE completed
    if (lastSse && lastSse.handlers.completed) {
      lastSse.handlers.completed({});
      await new Promise(r => setTimeout(r, 15));
    } else {
      // First iteration: connectSSE ran during domReadyHandler with old EventSource, trigger via approve!
      await elementsById.get("btn-approve").dispatch("click");
      await new Promise(r => setTimeout(r, 15));
    }
    elementsById.get("feedback-input").value = "Upgrade check";
    elementsById.get("btn-create").dispatch("click");
    await new Promise(r => setTimeout(r, 15));
    if (alerts.some(a => a.includes("Vui lòng điền"))) {
      throw new Error(`Unexpected validation alert on ${lc.template_id}: ${alerts.join("; ")}`);
    }
    lc.check(lastRevisePayload.form_data);
  }

  // 4. Important #3: Clicking + Dự án mới while generation is in-flight must re-enable btn-create and hide spinner
  elementsById.get("btn-new-project").dispatch("click");
  registerTreeIds(dynFields);
  elementsById.get("sec-company_overview-company_name").value = "New Biz";
  elementsById.get("sec-company_overview-company_name").dispatch("input");
  elementsById.get("sec-company_overview-headline").value = "Great Headline";
  elementsById.get("sec-company_overview-headline").dispatch("input");
  elementsById.get("sec-company_overview-cta_text").value = "Contact";
  elementsById.get("sec-company_overview-cta_text").dispatch("input");

  hangNextCreate = true;
  elementsById.get("btn-create").dispatch("click");
  if (!elementsById.get("btn-create").disabled) {
    throw new Error("Expected btn-create to be disabled while create is in-flight");
  }
  elementsById.get("btn-new-project").dispatch("click");
  if (elementsById.get("btn-create").disabled) {
    throw new Error("btn-create remained disabled after clicking + Dự án mới!");
  }
  if (!elementsById.get("btn-create-spinner").classList.contains("hidden")) {
    throw new Error("btn-create-spinner remained visible after clicking + Dự án mới!");
  }

  console.log("ALL_FRONTEND_CHECKS_PASSED");
})().catch(err => {
  console.error(err);
  process.exit(1);
});
""",
        encoding="utf-8",
    )

    proc = subprocess.run(
        ["node", str(harness_file), str(app_js_path), str(tpl_file)],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert proc.returncode == 0, f"Node check failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"
    assert "ALL_FRONTEND_CHECKS_PASSED" in proc.stdout
