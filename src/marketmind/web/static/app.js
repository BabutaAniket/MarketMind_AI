"use strict";

const $ = (id) => document.getElementById(id);

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
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || `Request failed (${response.status})`);
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
  const sections = [...document.querySelectorAll("main section")];
  const select = (section) => {
    sections.forEach((s) => s.classList.toggle("active", s === section));
    [...tabs.children].forEach((b) => b.setAttribute("aria-selected", String(b.dataset.target === section.id)));
    if (section.id === "approvals") loadActions();
    if (section.id === "leads") loadLeads();
  };
  sections.forEach((section) => {
    tabs.append(el("button", { role: "tab", "data-target": section.id, text: section.dataset.title, onclick: () => select(section) }));
  });
  select(sections[0]);
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
  info.profile_fields.forEach(([key, label]) => {
    form.append(el("label", { text: label }, [el("input", { name: key, value: (info.company_profile || {})[key] || "" })]));
  });
  $("source-text").value = info.source_text || "";

  const fill = (data) => {
    for (const [key, value] of Object.entries(data.company_profile || {})) {
      if (form.elements[key]) form.elements[key].value = value;
    }
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
    const warn = result.warnings.length ? ` Warning: source text matches risk patterns (${result.warnings.join(", ")}). Review it.` : "";
    show($("company-out"), `Saved (${result.word_count} words).${warn}`, result.warnings.length > 0);
  });
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
    $("plan-steps").replaceChildren();
    $("plan-out").replaceChildren();
    const response = await fetch("/api/plan/stream", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(values) });
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
    const campaign = Object.fromEntries(new FormData($("campaign-form")).entries());
    campaign.channels = campaign.channels.split(",").map((channel) => channel.trim()).filter(Boolean);
    const result = await api("/api/workflow/start", { campaign });
    renderWorkflow(result);
  });
}

function renderWorkflow(result) {
  const out = $("workflow-out");
  const card = el("div", { class: "card" }, [
    el("h4", { text: `LangGraph workflow: ${result.status}` }),
    el("div", { class: "meta", text: `Thread ${result.thread_id} | checkpointed in SQLite` }),
    el("ol", { class: "steps" }, (result.events || []).map((item) => el("li", {
      text: `${item.node}: ${item.status || item.result || item.passages || (item.passed === undefined ? "complete" : item.passed ? "passed" : "review required")}`,
    }))),
  ]);
  if (result.errors?.length) card.append(el("div", { class: "msg error", text: result.errors.join("; ") }));
  if (result.plan) card.append(el("details", {}, [
    el("summary", { text: "View plan" }),
    json(result.plan),
  ]));
  if (result.review) card.append(el("div", { class: "msg", text: result.review.passed ? "Draft checks passed." : "Draft checks require review." }));

  const approval = result.interrupts?.[0];
  if (approval) {
    const editor = el("textarea", { rows: "10" });
    editor.value = JSON.stringify(approval.payload, null, 2);
    const notice = el("div", { class: "msg", text: `Review the exact payload. Hash: ${approval.payload_hash}` });
    const controls = el("div", { class: "row" });
    const send = async (button, decision, extra = {}) => {
      button.disabled = true;
      try {
        const next = await api(`/api/workflow/${encodeURIComponent(result.thread_id)}/resume`, {
          decision,
          payload_hash: approval.payload_hash,
          reviewer: "web user",
          ...extra,
        });
        renderWorkflow(next);
      } catch (error) {
        show(out, error.message, true);
      } finally {
        button.disabled = false;
      }
    };
    controls.append(
      el("button", { text: "Approve exact payload", onclick: (event) => send(event.currentTarget, "approve") }),
      el("button", { class: "secondary", text: "Save edit (new approval required)", onclick: (event) => {
        let edited;
        try { edited = JSON.parse(editor.value); } catch { return show(out, "Edited payload must be valid JSON.", true); }
        return send(event.currentTarget, "edit", { edited_payload: edited });
      } }),
      el("button", { class: "secondary", text: "Reject", onclick: (event) => send(event.currentTarget, "reject") }),
    );
    card.append(notice, editor, controls);
  }
  if (result.action) card.append(el("div", { class: "meta", text: `Action ${result.action.action_id}: ${result.action.status}; external side effects are disabled.` }));
  out.replaceChildren(card);
}

function handlePlanEvent(event) {
  if (event.step === "done") {
    show($("plan-out"), json(event.plan));
    return;
  }
  if (event.step === "blocked") {
    show($("plan-out"), event.error, true);
    return;
  }
  const detail = event.error || event.status || (event.passages !== undefined ? `${event.passages} passages` : event.allowed === false ? "blocked" : "ok");
  $("plan-steps").append(el("li", { text: `${event.step}: ${detail}` }));
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
  $("run-drafts").onclick = (event) => guarded(event.target, $("drafts-out"), async () => {
    const record = await api("/api/drafts", { campaign_goal: $("goal").value, call_to_action: $("cta").value });
    $("drafts-out").replaceChildren(...Object.entries(record.drafts).map(([channel, draft]) => draftCard(channel, draft)));
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
setupCompany().catch((error) => show($("company-out"), error.message, true));
refreshStatus();
