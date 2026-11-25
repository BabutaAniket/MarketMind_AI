"""Desktop app: Golden-set and red-team evaluation of the guardrails."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import BOTH, END, LEFT, X, messagebox, ttk

from marketmind.evaluation import run_evaluation, save_report
from marketmind.settings import EVAL_DIR, REPORT_FILE, ROOT


class EvaluationStudio(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("MarketMind AI — Evaluation and Security")
        self.geometry("1100x760")
        self.configure(bg="#eef3f8")
        self._build_ui()

    def _build_ui(self) -> None:
        header = tk.Frame(self, bg="#103b66", padx=18, pady=14)
        header.pack(fill=X)
        tk.Label(
            header,
            text="MarketMind AI — Evaluation and Security",
            bg="#103b66",
            fg="white",
            font=("Segoe UI", 20, "bold"),
        ).pack(anchor="w")
        tk.Label(header, text="Golden set • red team • output checks • approval gate", bg="#103b66", fg="#dcecff").pack(
            anchor="w"
        )
        body = tk.Frame(self, bg="#eef3f8", padx=14, pady=12)
        body.pack(fill=BOTH, expand=True)
        actions = tk.Frame(body, bg="#eef3f8")
        actions.pack(fill=X, pady=(0, 10))
        ttk.Button(actions, text="Generate test sets", command=self.generate_sets).pack(side=LEFT, padx=(0, 8))
        ttk.Button(actions, text="Run evaluation checks", command=self.run_checks).pack(side=LEFT, padx=(0, 8))
        ttk.Button(actions, text="Save report", command=self.save_report).pack(side=LEFT, padx=(0, 8))
        preview = ttk.LabelFrame(body, text="Evaluation report", padding=8)
        preview.pack(fill=BOTH, expand=True)
        self.output = tk.Text(
            preview, wrap="word", font=("Consolas", 9), state="disabled", background="#ffffff", foreground="#111111"
        )
        self.output.pack(fill=BOTH, expand=True)
        self.report: dict = {}

    def show(self, value: dict) -> None:
        self.output.configure(state="normal")
        self.output.delete("1.0", END)
        self.output.insert("1.0", json.dumps(value, ensure_ascii=False, indent=2))
        self.output.configure(state="disabled")

    def log(self, line: str) -> None:
        self.output.configure(state="normal")
        self.output.insert(END, line)
        self.output.see(END)
        self.output.configure(state="disabled")

    def generate_sets(self) -> None:
        import queue
        import subprocess
        import sys
        import threading

        generator = EVAL_DIR / "generate_sets.py"
        if not generator.exists():
            messagebox.showerror("Generator missing", f"File not found:\n{generator}")
            return
        if getattr(self, "_generating", False):
            messagebox.showinfo("Already running", "Test-set generation is already running.")
            return

        self._generating = True
        self.output.configure(state="normal")
        self.output.delete("1.0", END)
        self.output.configure(state="disabled")
        self.log(
            f"Starting {generator}\nThis can take a long time with a local model. "
            "Progress is saved after every batch, so you can close and resume.\n\n"
        )
        lines: queue.Queue = queue.Queue()

        def worker() -> None:
            process = subprocess.Popen(
                [sys.executable, "-u", str(generator)],
                cwd=str(ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            for line in process.stdout:
                lines.put(line)
            lines.put(("DONE", process.wait()))

        def poll() -> None:
            while not lines.empty():
                item = lines.get()
                if isinstance(item, tuple):
                    self._generating = False
                    if item[1] == 0:
                        messagebox.showinfo("Test sets saved", "Golden and red-team sets were generated.")
                    else:
                        messagebox.showerror("Generation stopped", "See the log in the window. Run again to resume.")
                    return
                self.log(item)
            self.after(300, poll)

        threading.Thread(target=worker, daemon=True).start()
        self.after(300, poll)

    def run_checks(self) -> None:
        try:
            self.report = run_evaluation()
        except FileNotFoundError as exc:
            messagebox.showinfo("No test sets", str(exc))
            return
        self.show(self.report)

    def save_report(self) -> None:
        if not self.report:
            self.run_checks()
        save_report(self.report)
        messagebox.showinfo("Saved", f"Evaluation report saved to:\n{REPORT_FILE}")


if __name__ == "__main__":
    EvaluationStudio().mainloop()
