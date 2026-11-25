"""Desktop app: Lead capture, scoring and recommendation."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import BOTH, END, LEFT, X, messagebox, ttk

from marketmind.leads import score_lead
from marketmind.settings import LEADS_FILE
from marketmind.tools.actions import decide_action, prepare_action


class LeadStudio(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("MarketMind AI — Lead Capture")
        self.geometry("980x700")
        self.configure(bg="#eef3f8")
        self.vars = {
            key: tk.StringVar() for key in ["name", "company", "contact", "location", "requirement", "timeline"]
        }
        self.score_var = tk.StringVar(value="Not scored")
        self._build_ui()

    def _build_ui(self) -> None:
        header = tk.Frame(self, bg="#103b66", padx=18, pady=14)
        header.pack(fill=X)
        tk.Label(
            header,
            text="MarketMind AI — Lead Capture",
            bg="#103b66",
            fg="white",
            font=("Segoe UI", 19, "bold"),
        ).pack(anchor="w")
        tk.Label(
            header, text="Capture • qualify • recommend • human approval before CRM write", bg="#103b66", fg="#dcecff"
        ).pack(anchor="w")
        body = tk.Frame(self, bg="#eef3f8", padx=14, pady=12)
        body.pack(fill=BOTH, expand=True)
        form = ttk.LabelFrame(body, text="Lead information", padding=10)
        form.pack(fill=X, pady=(0, 10))
        labels = [
            ("Name", "name"),
            ("Company", "company"),
            ("Phone or email", "contact"),
            ("Location", "location"),
            ("Requirement", "requirement"),
            ("Timeline", "timeline"),
        ]
        for row, (label, key) in enumerate(labels):
            ttk.Label(form, text=label).grid(row=row // 2, column=(row % 2) * 2, sticky="w", padx=(0, 8), pady=4)
            ttk.Entry(form, textvariable=self.vars[key], width=48).grid(
                row=row // 2, column=(row % 2) * 2 + 1, sticky="ew", padx=(0, 18), pady=4
            )
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)
        actions = tk.Frame(body, bg="#eef3f8")
        actions.pack(fill=X, pady=(0, 10))
        ttk.Button(actions, text="Score + recommend", command=self.score).pack(side=LEFT, padx=(0, 8))
        ttk.Button(actions, text="Prepare approval payload", command=self.prepare).pack(side=LEFT, padx=(0, 8))
        ttk.Button(actions, text="Save approved lead", command=self.save).pack(side=LEFT, padx=(0, 8))
        ttk.Label(actions, textvariable=self.score_var, foreground="#24445f").pack(side=LEFT, padx=8)
        preview = ttk.LabelFrame(body, text="Recommendation and approval payload", padding=8)
        preview.pack(fill=BOTH, expand=True)
        self.output = tk.Text(
            preview, wrap="word", font=("Consolas", 9), state="disabled", background="#ffffff", foreground="#111111"
        )
        self.output.pack(fill=BOTH, expand=True)
        footer = tk.Frame(self, bg="#dce8f3", padx=14, pady=7)
        footer.pack(fill=X)
        tk.Label(
            footer, text="Run writes only after a human clicks Save approved lead.", bg="#dce8f3", fg="#24445f"
        ).pack(anchor="w")

    def show(self, value: dict) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", END)
        self.output.insert("1.0", json.dumps(value, ensure_ascii=False, indent=2))
        self.output.configure(state="disabled")

    def lead(self) -> dict:
        return {key: value.get().strip() for key, value in self.vars.items()}

    def score(self) -> None:
        result = score_lead(self.lead())
        self.score_var.set(f"Qualification score: {result['qualification_score']}/100")
        self.show(result)

    def prepare(self) -> None:
        self.action = prepare_action("write_lead", self.lead())
        self.show(self.action)

    def save(self) -> None:
        lead = self.lead()
        if not lead["name"] or not lead["contact"]:
            messagebox.showwarning("Missing information", "Name and phone/email are required.")
            return
        if getattr(self, "action", None) is None or self.action.get("exact_payload") != lead:
            self.prepare()
        result = decide_action(
            self.action["action_id"], "approve", self.action["payload_hash"], reviewer="desktop user"
        )
        if not result["ok"]:
            messagebox.showerror("Not saved", result["error"])
            return
        self.action = None
        messagebox.showinfo("Saved", f"Approved lead saved to:\n{LEADS_FILE}")


if __name__ == "__main__":
    LeadStudio().mainloop()
