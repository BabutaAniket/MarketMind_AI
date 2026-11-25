"""Desktop app: Human feedback records and approved lessons."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import BOTH, END, LEFT, X, messagebox, ttk

from marketmind.feedback import build_feedback_record, extract_draft, save_feedback
from marketmind.memory_store import read_json
from marketmind.settings import PLAN_FILE


class FeedbackStudio(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("MarketMind AI — Human Feedback")
        self.geometry("1180x820")
        self.minsize(920, 680)
        self.configure(bg="#eef3f8")
        self.current_plan: dict | None = None
        self.status_var = tk.StringVar(value="Load the latest campaign plan")
        self.raw_var = tk.StringVar()
        self.corrected_var = tk.StringVar()
        self._build_ui()

    def _build_ui(self) -> None:
        header = tk.Frame(self, bg="#103b66", padx=18, pady=14)
        header.pack(fill=X)
        tk.Label(
            header,
            text="MarketMind AI — Human Feedback",
            bg="#103b66",
            fg="white",
            font=("Segoe UI", 20, "bold"),
        ).pack(anchor="w")
        tk.Label(
            header,
            text="Human approval • corrected intent • approved lessons for future Qwen3 prompts",
            bg="#103b66",
            fg="#dcecff",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(3, 0))

        body = tk.Frame(self, bg="#eef3f8", padx=14, pady=12)
        body.pack(fill=BOTH, expand=True)
        actions = tk.Frame(body, bg="#eef3f8")
        actions.pack(fill=X, pady=(0, 10))
        ttk.Button(actions, text="1. Load latest campaign plan", command=self.load_plan).pack(side=LEFT, padx=(0, 8))
        ttk.Button(actions, text="2. Approve + save lesson", command=self.approve).pack(side=LEFT, padx=(0, 8))
        ttk.Button(actions, text="Reject + save audit only", command=self.reject).pack(side=LEFT, padx=(0, 8))

        form = ttk.LabelFrame(body, text="Feedback input", padding=10)
        form.pack(fill=X, pady=(0, 10))
        ttk.Label(form, text="Raw user request / fast typing").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(form, textvariable=self.raw_var, width=105).grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Label(form, text="Corrected meaning").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(form, textvariable=self.corrected_var, width=105).grid(row=1, column=1, sticky="ew", pady=4)
        form.columnconfigure(1, weight=1)

        notes = ttk.LabelFrame(body, text="Human correction / lesson", padding=8)
        notes.pack(fill=X, pady=(0, 10))
        self.lesson_text = tk.Text(
            notes, height=4, wrap="word", font=("Segoe UI", 10), background="#ffffff", foreground="#111111"
        )
        self.lesson_text.pack(fill=X, expand=True)
        self.lesson_text.insert(
            "1.0", "Example: Keep a professional tone. Do not claim a percentage saving unless the source verifies it."
        )

        preview = ttk.LabelFrame(body, text="Latest draft under review", padding=8)
        preview.pack(fill=BOTH, expand=True)
        self.draft_text = tk.Text(
            preview, wrap="word", font=("Consolas", 9), state="disabled", background="#ffffff", foreground="#111111"
        )
        self.draft_text.pack(fill=BOTH, expand=True)

        footer = tk.Frame(self, bg="#dce8f3", padx=14, pady=7)
        footer.pack(fill=X)
        tk.Label(footer, textvariable=self.status_var, bg="#dce8f3", fg="#24445f", anchor="w").pack(fill=X)

    def show_draft(self, text: str) -> None:
        self.draft_text.configure(state="normal")
        self.draft_text.delete("1.0", END)
        self.draft_text.insert("1.0", text)
        self.draft_text.configure(state="disabled")
        self.draft_text.see("1.0")
        self.update_idletasks()

    def load_plan(self) -> None:
        try:
            self.current_plan = read_json(PLAN_FILE)
            self.show_draft(extract_draft(self.current_plan))
            inputs = self.current_plan.get("inputs", {})
            self.raw_var.set(str(inputs.get("objective", "")))
            self.corrected_var.set(str(inputs.get("objective", "")))
            self.status_var.set("Draft loaded; review it and approve, correct, or reject it")
            messagebox.showinfo("Draft loaded", "Review the draft carefully. Nothing will be published.")
        except Exception as exc:
            self.show_draft(json.dumps({"load_error": type(exc).__name__, "error": str(exc)}, indent=2))
            self.status_var.set("Draft loading failed")
            messagebox.showerror("Load error", f"{type(exc).__name__}: {exc}")

    def build_record(self, decision: str) -> dict:
        if self.current_plan is None:
            raise RuntimeError("Load a campaign plan first.")
        return build_feedback_record(
            self.current_plan,
            decision,
            self.raw_var.get(),
            self.corrected_var.get(),
            self.lesson_text.get("1.0", END),
        )

    def approve(self) -> None:
        try:
            save_feedback(self.build_record("approved"))
            self.status_var.set("Approved lesson saved and will guide future Qwen3 prompts")
            messagebox.showinfo("Approved", "Approved lesson saved. It will be used in the next Qwen3 generation.")
        except Exception as exc:
            messagebox.showerror("Save error", f"{type(exc).__name__}: {exc}")

    def reject(self) -> None:
        try:
            save_feedback(self.build_record("rejected"))
            self.status_var.set("Rejected draft saved for audit only; it will not guide Qwen3")
            messagebox.showinfo("Rejected", "Rejected draft saved for audit only. It will not be used as a lesson.")
        except Exception as exc:
            messagebox.showerror("Save error", f"{type(exc).__name__}: {exc}")


if __name__ == "__main__":
    FeedbackStudio().mainloop()
