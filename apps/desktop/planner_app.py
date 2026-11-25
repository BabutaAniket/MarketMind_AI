"""Desktop app: Campaign planner: baseline plan and optional local Qwen3 drafts."""

from __future__ import annotations

import json
import threading
import tkinter as tk
from tkinter import BOTH, END, LEFT, X, messagebox, ttk

from marketmind.memory_store import read_json
from marketmind.planner import OLLAMA_MODEL, OLLAMA_URL, ask_local_qwen, build_campaign_plan
from marketmind.settings import KNOWLEDGE_FILE, PLAN_FILE, RETRIEVAL_FILE


class CampaignPlanner(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("MarketMind AI — Campaign Planner")
        self.geometry("1180x800")
        self.minsize(920, 650)
        self.configure(bg="#eef3f8")
        self.knowledge: dict | None = None
        self.retrieval: dict | None = None
        self.plan: dict | None = None
        self._save_when_ready = False
        self.status_var = tk.StringVar(value="Load saved data, then generate a campaign plan")
        self.objective_var = tk.StringVar(value="Generate qualified B2B leads")
        self.audience_var = tk.StringVar(value="B2B decision-makers and procurement teams in India")
        self.offer_var = tk.StringVar(value="Book a product consultation")
        self.channels_var = tk.StringVar(value="Instagram, Facebook, WhatsApp, Email")
        self.tone_var = tk.StringVar(value="Professional, clear, trustworthy")
        self.budget_var = tk.StringVar(value="Small test budget")
        self._build_ui()

    def _build_ui(self) -> None:
        header = tk.Frame(self, bg="#103b66", padx=18, pady=14)
        header.pack(fill=X)
        tk.Label(
            header, text="MarketMind AI — Campaign Planner", bg="#103b66", fg="white", font=("Segoe UI", 20, "bold")
        ).pack(anchor="w")
        tk.Label(
            header,
            text="Strategy • content • leads • measurement • human approval gate",
            bg="#103b66",
            fg="#dcecff",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(3, 0))

        body = tk.Frame(self, bg="#eef3f8", padx=14, pady=12)
        body.pack(fill=BOTH, expand=True)
        inputs = ttk.LabelFrame(body, text="1. Campaign inputs", padding=10)
        inputs.pack(fill=X, pady=(0, 10))
        fields = [
            ("Objective", self.objective_var),
            ("Audience", self.audience_var),
            ("Offer / CTA", self.offer_var),
            ("Channels (comma separated)", self.channels_var),
            ("Tone", self.tone_var),
            ("Budget", self.budget_var),
        ]
        for row, (label, variable) in enumerate(fields):
            ttk.Label(inputs, text=label).grid(row=row // 2, column=(row % 2) * 2, sticky="w", padx=(0, 8), pady=4)
            ttk.Entry(inputs, textvariable=variable, width=55).grid(
                row=row // 2, column=(row % 2) * 2 + 1, sticky="ew", padx=(0, 18), pady=4
            )
        inputs.columnconfigure(1, weight=1)
        inputs.columnconfigure(3, weight=1)

        actions = tk.Frame(body, bg="#eef3f8")
        actions.pack(fill=X, pady=(0, 10))
        ttk.Button(actions, text="1. Load saved data", command=self.load_data).pack(side=LEFT, padx=(0, 8))
        self.qwen_button = ttk.Button(actions, text="2. Generate with Qwen3", command=self.generate_with_qwen)
        self.qwen_button.pack(side=LEFT, padx=(0, 8))
        ttk.Button(actions, text="Generate baseline", command=self.generate_baseline).pack(side=LEFT, padx=(0, 8))
        ttk.Button(actions, text="3. Save campaign_plan.json", command=self.save_plan).pack(side=LEFT, padx=(0, 8))

        preview = ttk.LabelFrame(body, text="2. Inspectable plan output", padding=8)
        preview.pack(fill=BOTH, expand=True)
        self.output_text = tk.Text(
            preview,
            wrap="word",
            font=("Consolas", 9),
            state="disabled",
            background="#ffffff",
            foreground="#111111",
            insertbackground="#111111",
        )
        self.output_text.pack(fill=BOTH, expand=True)

        footer = tk.Frame(self, bg="#dce8f3", padx=14, pady=7)
        footer.pack(fill=X)
        tk.Label(footer, textvariable=self.status_var, bg="#dce8f3", fg="#24445f", anchor="w").pack(fill=X)

    def show(self, text: str) -> None:
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", END)
        self.output_text.insert("1.0", text)
        self.output_text.configure(state="disabled")
        self.output_text.see("1.0")
        self.update_idletasks()

    def load_data(self) -> None:
        self.status_var.set("Loading knowledge_base.json and retrieval_test_results.json...")
        self.update_idletasks()
        try:
            self.knowledge = read_json(KNOWLEDGE_FILE)
            self.retrieval = read_json(RETRIEVAL_FILE) if RETRIEVAL_FILE.exists() else None
            profile = self.knowledge.get("company_profile", self.knowledge.get("profile", {}))
            company = (
                profile.get("company_name", profile.get("brand_name", "Company"))
                if isinstance(profile, dict)
                else "Company"
            )
            retrieval_state = "loaded" if self.retrieval else "not found; profile evidence will be used"
            self.show(
                json.dumps({"data_loaded": True, "company": company, "retrieval_test": retrieval_state}, indent=2)
            )
            self.status_var.set("Project data loaded")
            messagebox.showinfo("Data loaded", f"Knowledge loaded.\nRetrieval test: {retrieval_state}")
        except Exception as exc:
            self.show(json.dumps({"data_loaded": False, "error_type": type(exc).__name__, "error": str(exc)}, indent=2))
            self.status_var.set("Data loading failed")
            messagebox.showerror("Load error", f"{type(exc).__name__}: {exc}")

    def ensure_data(self) -> bool:
        if self.knowledge is None:
            self.load_data()
        return self.knowledge is not None

    def make_baseline(self) -> dict:
        return build_campaign_plan(
            self.knowledge or {},
            self.retrieval,
            self.objective_var.get().strip(),
            self.audience_var.get().strip(),
            self.offer_var.get().strip(),
            self.channels_var.get().strip(),
            self.tone_var.get().strip(),
            self.budget_var.get().strip(),
        )

    def generate_baseline(self) -> None:
        self.status_var.set("Preparing transparent baseline plan...")
        self.update_idletasks()
        try:
            if not self.ensure_data():
                return
            self.plan = self.make_baseline()
            self.show(json.dumps(self.plan, ensure_ascii=False, indent=2))
            self.status_var.set("Baseline plan generated; human approval is required")
            messagebox.showinfo(
                "Baseline generated", "Baseline campaign plan generated.\n\nNo post or message was published."
            )
        except Exception as exc:
            self.show(
                json.dumps({"plan_generated": False, "error_type": type(exc).__name__, "error": str(exc)}, indent=2)
            )
            self.status_var.set("Plan generation failed")
            messagebox.showerror("Generation error", f"{type(exc).__name__}: {exc}")

    def generate_with_qwen(self) -> None:
        self.status_var.set("Qwen3 is generating in the background; the window should remain responsive...")
        self.update_idletasks()
        try:
            if not self.ensure_data():
                return
            baseline_plan = self.make_baseline()
            baseline_plan["local_llm"] = {
                "provider": "Ollama",
                "model": OLLAMA_MODEL,
                "endpoint": OLLAMA_URL,
                "generation_mode": "local_only",
            }
        except Exception as exc:
            self.show(
                json.dumps({"qwen3_generation": False, "error_type": type(exc).__name__, "error": str(exc)}, indent=2)
            )
            self.status_var.set("Qwen3 generation failed")
            messagebox.showerror("Qwen3 error", f"{type(exc).__name__}: {exc}")
            return

        self.qwen_button.configure(state="disabled")
        worker = threading.Thread(target=self._qwen_worker, args=(baseline_plan,), daemon=True)
        worker.start()

    def _qwen_worker(self, plan: dict) -> None:
        try:
            qwen_output = ask_local_qwen(plan)
            self.after(0, self._qwen_success, plan, qwen_output)
        except Exception as exc:
            self.after(0, self._qwen_failure, exc)

    def _qwen_success(self, plan: dict, qwen_output: dict | str) -> None:
        self.plan = plan
        self.plan["qwen3_output"] = qwen_output
        self.show(json.dumps(self.plan, ensure_ascii=False, indent=2))
        self.status_var.set("Qwen3 campaign drafts generated locally; human approval is required")
        self.qwen_button.configure(state="normal")
        if self._save_when_ready:
            self._save_when_ready = False
            self._write_plan("Qwen3 drafts generated and campaign plan saved to:")
            return
        messagebox.showinfo("Qwen3 complete", "Local Qwen3 drafts generated.\n\nNo post or message was published.")

    def _qwen_failure(self, exc: Exception) -> None:
        self._save_when_ready = False
        self.show(
            json.dumps({"qwen3_generation": False, "error_type": type(exc).__name__, "error": str(exc)}, indent=2)
        )
        self.status_var.set("Qwen3 generation failed")
        self.qwen_button.configure(state="normal")
        messagebox.showerror("Qwen3 error", f"{type(exc).__name__}: {exc}")

    def save_plan(self) -> None:
        if self.plan is not None:
            self._write_plan("Campaign plan saved to:")
            return
        self._save_when_ready = True
        if str(self.qwen_button["state"]) != "disabled":
            self.generate_with_qwen()
        if str(self.qwen_button["state"]) == "disabled":
            self.status_var.set("Qwen3 is generating; the plan will be saved automatically when it finishes")
        else:
            self._save_when_ready = False

    def _write_plan(self, message: str) -> None:
        PLAN_FILE.write_text(json.dumps(self.plan, ensure_ascii=False, indent=2), encoding="utf-8")
        self.status_var.set(f"Saved campaign plan: {PLAN_FILE}")
        messagebox.showinfo("Saved", f"{message}\n{PLAN_FILE}\n\nNo post or message was published.")


if __name__ == "__main__":
    CampaignPlanner().mainloop()
