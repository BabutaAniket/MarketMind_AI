"use strict";

const $ = (id) => document.getElementById(id);
const PRIMARY_STEPS = ["company", "campaign", "drafts", "approvals"];
let savedProfile = {};
let activeWorkflow = null;
let knowledgeSaved = false;

function el(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (key === "class") node.className = value;
    else if (key === "text") node.textContent = value;
    else if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else node.setAttribute(key, value);
  }
  for (const child of [].concat(children)) node.append(child);
  return node;
}

async function api(path, body, method) {
  const options = { method: method || (body === undefined ? "GET" : "POST"), headers: {} };
  if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const response = await fetch(path, options);
  if (response.status === 401) {
    window.location.assign("/login");
    throw new Error("Your session has ended. Please sign in again.");
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(data.detail || `Request failed (${response.status})`);
    error.status = response.status;
    throw error;
  }
  return data;
}

function show(target, content, isError = false) {
  target.replaceChildren(typeof content === "string" ? el("div", { class: "msg" + (isError ? " error" : ""), text: content }) : content);
}

const json = (value) => el("pre", { text: JSON.stringify(value, null, 2) });

async function guarded(button, target, work) {
  button.disabled = true;
  try {
    await work();
  } catch (error) {
    show(target, error.message, true);
  } finally {
    button.disabled = false;
    refreshStatus();
  }
}

function setupTabs() {
  const tabs = $("tabs");
  const journey = $("journey");
  const sections = [...document.querySelectorAll("main section")];
  const select = (section, updateHistory = true) => {
    if (!section) return;
    sections.forEach((s) => s.classList.toggle("active", s === section));
    [...tabs.children].forEach((b) => b.setAttribute("aria-selected", String(b.dataset.target === section.id)));
    [...journey.children].forEach((b) => {
      if (b.dataset.target === section.id) b.setAttribute("aria-current", "step");
      else b.removeAttribute("aria-current");
    });
    if (section.id === "approvals") {
      if (activeWorkflow) renderApproval(activeWorkflow);
      loadActions();
    }
    if (section.id === "leads") loadLeads();
    if (updateHistory) {
      const hash = PRIMARY_STEPS.includes(section.id) ? `#${section.id}` : `#tools-${section.id}`;
      if (window.location.hash !== hash) window.history.pushState({ section: section.id }, "", hash);
    }
  };
  sections.forEach((section) => {
    if (!PRIMARY_STEPS.includes(section.id)) {
      tabs.append(el("button", { role: "tab", "data-target": section.id, text: section.dataset.title, onclick: () => select(section) }));
    }
  });
  PRIMARY_STEPS.forEach((id, index) => {
    const section = $(id);
    journey.append(el("button", {
      type: "button",
      "data-target": id,
      text: `${index + 1}. ${section.dataset.title}`,
      onclick: () => select(section),
    }));
  });
  document.querySelectorAll("[data-next], [data-back]").forEach((button) => {
    button.addEventListener("click", () => select($(button.dataset.next || button.dataset.back)));
  });
  const fromHash = () => {
    const id = window.location.hash.replace(/^#(tools-)?/, "");
    select($(id) || sections[0], false);
  };
  window.addEventListener("popstate", fromHash);
  fromHash();
  window.openTab = (id) => select($(id));
}

async function refreshStatus() {
  const box = $("status");
  try {
    const s = await api("/api/status");
    const pill = (text, cls = "") => el("span", { class: `pill ${cls}`, text });
    box.replaceChildren(
      pill(s.llm.reachable ? (s.llm.model_installed ? `Local model ready: ${s.llm.model}` : `Model not installed: ${s.llm.model}`) : "Local model offline", s.llm.model_installed ? "ok" : "bad"),
      pill(s.knowledge_saved ? `Knowledge: ${s.company || "saved"}` : "No knowledge saved", s.knowledge_saved ? "ok" : "bad"),
      pill(`Pending approvals: ${s.pending_actions}`),
      pill(`Leads: ${s.leads}`),
      pill(`Lessons: ${s.approved_lessons}`),
    );
  } catch {
    box.replaceChildren(el("span", { class: "pill bad", text: "API unreachable" }));
  }
}

async function setupCompany() {
  const info = await api("/api/knowledge");
  const form = $("company-form");
  form.className = "grid";
  savedProfile = info.company_profile || {};
  knowledgeSaved = Boolean(info.saved);
  info.profile_fields.forEach(([key, label]) => {
    form.append(el("label", { text: label }, [el("input", { name: key, value: (info.company_profile || {})[key] || "" })]));
  });
  $("source-text").value = info.source_text || "";
  updateCampaignDefaults(savedProfile);

  const fill = (data) => {
    for (const [key, value] of Object.entries(data.company_profile || {})) {
      if (form.elements[key]) form.elements[key].value = value;
    }
    savedProfile = data.company_profile || {};
    updateCampaignDefaults(savedProfile);
    if (data.source_text !== undefined) $("source-text").value = data.source_text;
  };
  $("load-sample").onclick = async () => fill(await api("/api/sample"));
  $("import-file").onchange = async (event) => {
    const file = event.target.files[0];
    if (!file) return;
    const text = await file.text();
    if (file.name.endsWith(".json")) {
      try { fill(JSON.parse(text)); return; } catch { /* fall through to plain text */ }
    }
    $("source-text").value = text;
  };
  $("save-company").onclick = (event) => guarded(event.target, $("company-out"), async () => {
    const profile = Object.fromEntries(new FormData(form).entries());
    const result = await api("/api/knowledge", { company_profile: profile, source_text: $("source-text").value });
    savedProfile = profile;
    knowledgeSaved = true;
    updateCampaignDefaults(profile);
    const warn = result.warnings.length ? ` Warning: source text matches risk patterns (${result.warnings.join(", ")}). Review it.` : "";
    show($("campaign-out"), `Company information saved (${result.word_count} words).${warn}`, result.warnings.length > 0);
    window.openTab("campaign");
  });
}

function updateCampaignDefaults(profile) {
  const form = $("campaign-form");
  if (!form) return;
  const audience = form.elements.audience;
  const offer = form.elements.offer;
  if (audience && profile.target_customer) audience.value = profile.target_customer;
  if (offer && profile.offer_price) offer.value = profile.offer_price;
  const cta = $("cta");
  if (cta && profile.offer_price) cta.value = profile.offer_price;
  updateAudienceWarning();
}

function updateAudienceWarning() {
  const expected = String(savedProfile.target_customer || "").trim();
  const actual = String($("campaign-form").elements.audience.value || "").trim();
  const mismatch = expected && actual && expected.toLowerCase() !== actual.toLowerCase();
  $("audience-warning").hidden = !mismatch;
  $("audience-confirm-wrap").hidden = !mismatch;
  if (mismatch) {
    $("audience-warning").textContent = `Your saved profile describes "${expected}". Confirm if you intentionally want to target "${actual}" instead.`;
  } else {
    $("audience-confirm").checked = false;
  }
}

function resultCard(item, index) {
  return el("div", { class: "card" }, [
    el("h4", { text: `${index + 1}. ${item.chunk_id}` }),
    el("div", { class: "meta", text: `${item.source_ref} | ${item.source_date} | RRF ${item.rrf_score} | BM25 rank ${item.bm25_rank}, vector rank ${item.vector_rank}` }),
    el("div", { class: "text", text: item.text }),
  ]);
}

function setupSearch() {
  $("run-search").onclick = (event) => guarded(event.target, $("search-out"), async () => {
    const data = await api("/api/search", { query: $("query").value, top_k: 5, save: true });
    const list = el("div", { class: "cards" }, data.results.map(resultCard));
    show($("search-out"), data.results.length ? list : "No relevant passages found.");
  });
}

function setupCampaign() {
  $("run-plan").onclick = (event) => guarded(event.target, $("plan-out"), async () => {
    const values = Object.fromEntries(new FormData($("campaign-form")).entries());
    values.channels = values.channels.split(",").map((c) => c.trim()).filter(Boolean);
    values.use_llm = $("use-llm").checked;
    values.design = new FormData($("campaign-options")).get("design") || "team";
    $("plan-steps").replaceChildren();
    $("plan-out").replaceChildren();
    const response = await fetch("/api/plan/stream", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(values) });
    if (response.status === 401) {
      window.location.assign("/login");
      throw new Error("Your session has ended. Please sign in again.");
    }
    if (!response.ok) throw new Error((await response.json().catch(() => ({}))).detail || "Request failed");
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();
      for (const line of lines.filter(Boolean)) handlePlanEvent(JSON.parse(line));
    }
  });

  $("run-workflow").onclick = (event) => guarded(event.target, $("workflow-out"), async () => {
    updateAudienceWarning();
    if (!knowledgeSaved) throw new Error("Save company information before creating a campaign.");
    if (!$("campaign-form").elements.audience.value.trim()) throw new Error("Enter an audience for this campaign.");
    if (!$("campaign-form").elements.offer.value.trim()) throw new Error("Enter an offer or call to action.");
    if (!$("campaign-form").elements.channels.value.trim()) throw new Error("Enter at least one channel.");
    if (!$("audience-confirm-wrap").hidden && !$("audience-confirm").checked) {
      throw new Error("Confirm the audience change or use the saved customer profile.");
    }
    const campaign = Object.fromEntries(new FormData($("campaign-form")).entries());
    campaign.channels = campaign.channels.split(",").map((channel) => channel.trim()).filter(Boolean);
    campaign.design = new FormData($("campaign-options")).get("design") || "team";
    const result = await api("/api/workflow/start", { campaign });
    sessionStorage.setItem("marketmind.workflow", result.thread_id);
    renderWorkflow(result);
    if (result.plan && result.status === "awaiting_approval") window.openTab("drafts");
  });
  $("campaign-form").elements.audience.addEventListener("input", updateAudienceWarning);
}

async function restoreWorkflow() {
  const threadId = sessionStorage.getItem("marketmind.workflow");
  if (!threadId) return;
  try {
    const result = await api(`/api/workflow/${encodeURIComponent(threadId)}`);
    activeWorkflow = result;
    renderWorkflow(result);
    if (result.status === "awaiting_approval") window.openTab("approvals");
  } catch (error) {
    if (error.status === 404) sessionStorage.removeItem("marketmind.workflow");
    else show($("approval-out"), `Could not restore the pending review: ${error.message}`, true);
  }
}

function renderWorkflow(result) {
  activeWorkflow = result;
  const out = $("workflow-out");
  out.replaceChildren();
  if (result.errors?.length && !result.plan) {
    show(out, result.errors.join(" "), true);
    return;
  }
  out.append(el("div", {
    class: `msg ${result.review?.passed ? "safe-banner" : ""}`,
    text: result.review?.passed
      ? "Draft checks completed. These are template-generated suggestions based on your saved company profile."
      : "The workflow prepared a draft for human review.",
  }));
  const draftList = Object.entries(result.drafts || {}).map(([channel, draft]) => {
    const card = el("article", { class: "card" }, [
      el("h4", { text: channel }),
      el("p", { class: "text", text: draft.text || "" }),
    ]);
    if (draft.subject) card.append(el("div", { class: "meta", text: `Email subject: ${draft.subject}` }));
    return card;
  });
  const sourceDetails = el("details", {}, [
    el("summary", { text: "Company facts used as evidence" }),
    el("ul", {}, (result.plan?.source_references || []).map((source) => el("li", {
      text: `${source.source_ref} (${source.source_date}): ${source.evidence_text}`,
    }))),
  ]);
  $("drafts-out").replaceChildren(...draftList, sourceDetails);
  const technical = el("details", {}, [
    el("summary", { text: "Workflow details" }),
    el("div", { class: "meta", text: `Checkpoint thread: ${result.thread_id}` }),
    el("ol", { class: "steps" }, (result.events || []).map((item) => el("li", { text: item.node.replaceAll("_", " ") }))),
  ]);
  if (result.errors?.length) technical.append(el("div", { class: "msg error", text: result.errors.join("; ") }));
  out.append(technical);
  renderApproval(result);
}

function handlePlanEvent(event) {
  if (event.step === "done") {
    const plan = event.plan;
    const generation = plan.generation || { status: "template_generated", message: "Template-generated plan." };
    const summary = el("div", { class: "card" }, [
      el("h4", { text: "Campaign plan" }),
      el("div", { class: `msg ${generation.status === "ai_generated" ? "safe-banner" : generation.status === "template_fallback" ? "warning" : ""}`, text: `${generation.message}${generation.model ? ` Model: ${generation.model}.` : ""}` }),
      el("p", { class: "text", text: `Audience: ${plan.inputs.audience}\nOffer: ${plan.inputs.offer}\nChannels: ${plan.inputs.channels.join(", ")}` }),
    ]);
    const technical = el("details", {}, [el("summary", { text: "Sources and plan details" })]);
    technical.append(json({ sources: plan.source_references, generation }));
    const result = el("div", {}, [summary]);
    if (generation.status === "ai_generated" && plan.qwen3_output) {
      result.append(modelSuggestionCards(plan.qwen3_output));
    }
    result.append(technical);
    show($("plan-out"), result);
    return;
  }
  if (event.step === "blocked") {
    show($("plan-out"), event.error, true);
    return;
  }
  const label = { input_guardrail: "Safety check", retrieval: "Finding company evidence", plan: "Preparing campaign plan", llm: "Optional model generation" }[event.step] || event.step;
  const detail = event.error || (event.step === "llm" && event.status === "failed" ? "failed; template fallback will be shown" : event.status === "done" ? "complete" : event.passages !== undefined ? `${event.passages} passages found` : event.allowed === false ? "blocked" : "complete");
  $("plan-steps").append(el("li", { text: `${label}: ${detail}` }));
}

function modelSuggestionCards(output) {
  const cards = el("div", { class: "cards" });
  const entries = output && typeof output === "object" && !Array.isArray(output) ? Object.entries(output) : [["Suggestions", output]];
  entries.forEach(([key, value]) => {
    const text = typeof value === "string" ? value : Array.isArray(value) ? value.join("\n") : JSON.stringify(value, null, 2);
    cards.append(el("article", { class: "card" }, [
      el("h4", { text: key.replaceAll("_", " ") }),
      el("p", { class: "text", text: String(text || "") }),
    ]));
  });
  return cards;
}

function renderApproval(result) {
  const out = $("approval-out");
  const approval = result.interrupts?.[0];
  if (result.status === "approved_mock") {
    show(out, "Campaign approved for the demo. This recorded a mock action only; nothing was sent or published.");
    return;
  }
  if (result.status === "rejected") {
    show(out, "Campaign rejected. No external action was taken.");
    return;
  }
  if (!approval) {
    if (result.errors?.length) show(out, result.errors.join(" "), true);
    else show(out, "Create campaign drafts before reviewing an approval.");
    return;
  }
  const payload = approval.payload;
  const summary = payload.campaign_summary || {};
  const card = el("div", { class: "card" }, [
    el("h4", { text: "Campaign summary" }),
    el("p", { class: "text", text: `Company: ${summary.company_name || "Not specified"}\nProduct: ${summary.brand_name || "Not specified"}\nObjective: ${summary.objective || "Not specified"}\nAudience: ${summary.audience || "Not specified"}\nOffer: ${summary.offer || "Not specified"}\nChannels: ${(summary.channels || []).join(", ")}\nTone: ${summary.tone || "Not specified"}\nBudget: ${summary.budget || "Not specified"}` }),
    el("h4", { text: "Drafts included in this approval" }),
  ]);
  const draftEntries = Object.entries(payload.drafts || {});
  draftEntries.forEach(([channel, draft]) => {
    card.append(
      el("h4", { text: channel }),
      el("p", { class: "text", text: (typeof draft === "string" ? draft : draft.text) || "" }),
    );
    if (draft.subject) card.append(el("div", { class: "meta", text: `Subject: ${draft.subject}` }));
  });
  if (payload.sources?.length) {
    card.append(el("details", {}, [
      el("summary", { text: "Evidence used" }),
      el("ul", {}, payload.sources.map((source) => el("li", {
        text: `${source.source_ref}: ${source.evidence_text}`,
      }))),
    ]));
  }
  const editorLabel = el("label", { text: "Edit one channel draft" });
  const channelSelect = el("select", { class: "review-channel" }, draftEntries.map(([channel]) => el("option", { value: channel, text: channel })));
  const editor = el("textarea", { class: "review-copy", rows: "6" });
  const syncEditor = () => {
    const item = (payload.drafts || {})[channelSelect.value];
    editor.value = typeof item === "string" ? item : item?.text || "";
  };
  channelSelect.addEventListener("change", syncEditor);
  syncEditor();
  editorLabel.append(channelSelect);
  card.append(
    el("div", { class: "msg safe-banner", text: "This action is a demo only. Approval will not publish, email, message, or contact anyone." }),
    editorLabel,
    editor,
  );
  const controls = el("div", { class: "row" });
  const send = async (button, decision, editedPayload) => {
    button.disabled = true;
    try {
      const next = await api(`/api/workflow/${encodeURIComponent(result.thread_id)}/resume`, {
        decision,
        payload_hash: approval.payload_hash,
        ...(editedPayload ? { edited_payload: editedPayload } : {}),
      });
      renderWorkflow(next);
      renderApproval(next);
    } catch (error) {
      show(out, error.message, true);
    } finally {
      button.disabled = false;
    }
  };
  controls.append(
    el("button", { text: "Approve this campaign", onclick: (event) => send(event.currentTarget, "approve") }),
    el("button", { class: "secondary", text: "Save edit for re-approval", onclick: (event) => {
      const edited = JSON.parse(JSON.stringify(payload));
      const draft = edited.drafts[channelSelect.value];
      if (typeof draft === "string") edited.drafts[channelSelect.value] = editor.value;
      else draft.text = editor.value;
      return send(event.currentTarget, "edit", edited);
    } }),
    el("button", { class: "secondary", text: "Reject campaign", onclick: (event) => send(event.currentTarget, "reject") }),
  );
  const integrity = el("details", {}, [
    el("summary", { text: "Technical approval details" }),
    el("div", { class: "meta", text: `Thread ${result.thread_id}; payload hash ${approval.payload_hash}` }),
  ]);
  card.append(controls, integrity);
  if (result.errors?.length) card.append(el("div", { class: "msg error", text: result.errors.join("; ") }));
  out.replaceChildren(card);
}

function draftCard(channel, draft) {
  const ok = draft.compliance.allowed;
  return el("div", { class: "card" }, [
    el("h4", { text: `${channel} ` }, [el("span", { class: `tag ${ok ? "ok" : "bad"}`, text: ok ? "claims check passed" : `flagged: ${draft.compliance.claim_or_safety_hits.join(", ")}` })]),
    draft.subject ? el("div", { class: "meta", text: `Subject: ${draft.subject}` }) : "",
    el("div", { class: "text", text: draft.text }),
    el("div", { class: "meta", text: `Visual brief: ${draft.visual_brief}` }),
    el("button", { class: "secondary", text: "Send to approval (mock publish)", onclick: async (event) => {
      await guarded(event.target, $("drafts-out"), async () => {
        await api("/api/actions/prepare", { action_type: "publish_draft", payload: { channel, text: draft.text, subject: draft.subject || null } });
        window.openTab("approvals");
      });
    } }),
  ]);
}

function setupDrafts() {
  $("run-drafts").onclick = (event) => guarded(event.target, $("extra-drafts-out"), async () => {
    const record = await api("/api/drafts", { campaign_goal: $("goal").value, call_to_action: $("cta").value });
    $("extra-drafts-out").replaceChildren(...Object.entries(record.drafts).map(([channel, draft]) => draftCard(channel, draft)));
  });
}

const LEAD_FIELDS = [["name", "Name"], ["company", "Company"], ["contact", "Phone or email"], ["location", "Location"], ["requirement", "Requirement"], ["timeline", "Timeline"]];

function leadValues() {
  return Object.fromEntries(new FormData($("lead-form")).entries());
}

async function loadLeads() {
  const data = await api("/api/leads");
  $("lead-list").replaceChildren(data.leads.length ? json(data.leads) : el("div", { class: "msg", text: "No saved leads." }));
}

function setupLeads() {
  LEAD_FIELDS.forEach(([key, label]) => $("lead-form").append(el("label", { text: label }, [el("input", { name: key })])));
  $("score-lead").onclick = (event) => guarded(event.target, $("lead-out"), async () => show($("lead-out"), json(await api("/api/leads/score", leadValues()))));
  $("prepare-lead").onclick = (event) => guarded(event.target, $("lead-out"), async () => {
    const lead = leadValues();
    if (!lead.name || !lead.contact) throw new Error("Name and phone or email are required.");
    await api("/api/actions/prepare", { action_type: "write_lead", payload: lead });
    window.openTab("approvals");
  });
}

function actionCard(action) {
  const pending = action.status === "waiting_for_human_approval";
  const editor = el("textarea", { rows: "5" });
  editor.value = JSON.stringify(action.exact_payload, null, 2);
  const out = el("div");
  const decide = (decision, extra = {}) => async (event) => {
    await guarded(event.target, out, async () => {
      await api("/api/actions/decide", { action_id: action.action_id, decision, payload_hash: action.payload_hash, reviewer: "web user", ...extra });
      await loadActions();
    });
  };
  const controls = pending
    ? [editor, el("div", { class: "row" }, [
        el("button", { text: "Approve exact payload", onclick: decide("approve") }),
        el("button", { class: "secondary", text: "Save edit (needs new approval)", onclick: async (event) => {
          let edited;
          try { edited = JSON.parse(editor.value); } catch { return show(out, "Edited payload must be valid JSON.", true); }
          await decide("edit", { edited_payload: edited })(event);
        } }),
        el("button", { class: "secondary", text: "Reject", onclick: decide("reject") }),
      ])]
    : [el("pre", { text: JSON.stringify(action.exact_payload, null, 2) })];
  const tagClass = action.status === "executed" ? "ok" : action.status === "rejected" ? "bad" : "";
  return el("div", { class: "card" }, [
    el("h4", { text: `${action.action_type} ` }, [el("span", { class: `tag ${tagClass}`, text: action.status.replaceAll("_", " ") })]),
    el("div", { class: "meta", text: `${action.action_id} | payload hash ${action.payload_hash.slice(0, 12)} | external side effect: none (mock)` }),
    ...controls,
    out,
  ]);
}

async function loadActions() {
  const data = await api("/api/actions");
  const items = [...data.actions].reverse();
  $("actions-out").replaceChildren(...(items.length ? items.map(actionCard) : [el("div", { class: "msg", text: "No actions yet. Prepare one from Drafts or Leads." })]));
}

function setupFeedback() {
  const send = (decision) => (event) => guarded(event.target, $("fb-out"), async () => {
    const result = await api("/api/feedback", { decision, raw_input: $("fb-raw").value, corrected_meaning: $("fb-corrected").value, lesson: $("fb-lesson").value });
    show($("fb-out"), result.used_for_future_prompts ? "Approved lesson saved; it will guide the next local-model generation." : "Rejected draft saved for audit only.");
  });
  $("fb-approve").onclick = send("approved");
  $("fb-reject").onclick = send("rejected");
  $("refresh-actions").onclick = loadActions;
}

function setupEvaluation() {
  $("run-eval").onclick = (event) => guarded(event.target, $("eval-out"), async () => {
    const r = await api("/api/evaluation/run", {});
    const summary = el("div", { class: "card" }, [
      el("h4", { text: "Result " }, [el("span", { class: `tag ${r.passed ? "ok" : "bad"}`, text: r.passed ? "passed" : "below threshold" })]),
      el("div", { text: `Red-team: ${r.red_team_blocked}/${r.red_team_cases} blocked (${r.red_team_block_rate}). Legitimate requests allowed: ${r.golden_allowed_rate}. Required: ${r.minimum_pass_rate}.` }),
      el("div", { class: "meta", text: r.scope }),
    ]);
    show($("eval-out"), el("div", {}, [summary, json(r)]));
  });
  $("run-retrieval-eval").onclick = (event) => guarded(event.target, $("retrieval-eval-out"), async () => {
    const r = await api("/api/evaluation/retrieval", {});
    const summary = el("div", { class: "card" }, [
      el("h4", { text: `Recall@5: ${r.before.recall} → ${r.after.recall}` }),
      el("div", { text: `${r.query_count} labeled queries; ${r.labeled_passages} relevant passages; change ${r.change >= 0 ? "+" : ""}${r.change}.` }),
      el("div", { class: "meta", text: "Synthetic company development set; do not treat as held-out results." }),
    ]);
    show($("retrieval-eval-out"), el("div", {}, [summary, json(r)]));
  });
}

setupTabs();
setupSearch();
setupCampaign();
setupDrafts();
setupLeads();
setupFeedback();
setupEvaluation();
setupCompany()
  .then(restoreWorkflow)
  .catch((error) => show($("company-out"), error.message, true));
refreshStatus();
$("sign-out").onclick = async () => {
  const response = await fetch("/api/auth/logout", { method: "POST" });
  if (!response.ok) {
    window.alert("Could not sign out. Please try again.");
    return;
  }
  sessionStorage.removeItem("marketmind.workflow");
  window.location.assign("/login");
};
