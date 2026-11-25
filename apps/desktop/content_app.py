"""Desktop app: Template-based channel drafts grounded in the saved company profile."""

from __future__ import annotations

import json
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import BOTH, END, LEFT, X, filedialog, messagebox, ttk

from marketmind.content import build_drafts
from marketmind.ingestion import load_knowledge
from marketmind.settings import DRAFTS_FILE, KNOWLEDGE_FILE, OUTPUT_DIR, ROOT


class ContentStudio(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("MarketMind AI — Content Studio")
        self.geometry("1120x760")
        self.minsize(900, 620)
        self.configure(bg="#eef3f8")
        self.current_output: dict | None = None
        self.loaded_knowledge: dict | None = None
        self.loaded_knowledge_path: Path | None = None

        self.goal_var = tk.StringVar(value="Create awareness and invite a product consultation.")
        self.cta_var = tk.StringVar(value="Contact us for a suitable model recommendation.")
        self.status_var = tk.StringVar(value="Ready — save the company knowledge first")
        self.output_text = tk.Text(self, wrap="word", font=("Consolas", 9), state="disabled")
        self.output_text.configure(
            background="#ffffff",
            foreground="#111111",
        )

        self._build_style()
        self._build_ui()

    def _build_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Title.TLabel", font=("Segoe UI", 20, "bold"), foreground="#103b66")
        style.configure("Sub.TLabel", font=("Segoe UI", 10), foreground="#45627c")
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=(12, 7))

    def _build_ui(self) -> None:
        header = tk.Frame(self, bg="#103b66", padx=18, pady=14)
        header.pack(fill=X)
        tk.Label(
            header, text="MarketMind AI — Content Studio", bg="#103b66", fg="white", font=("Segoe UI", 20, "bold")
        ).pack(anchor="w")
        tk.Label(
            header,
            text="Knowledge base → grounded channel drafts → human review",
            bg="#103b66",
            fg="#dcecff",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(3, 0))

        body = tk.Frame(self, bg="#eef3f8", padx=14, pady=12)
        body.pack(fill=BOTH, expand=True)

        action_bar = tk.Frame(body, bg="#dce8f3", height=62)
        action_bar.pack(side="top", fill=X, pady=(0, 10))
        action_bar.pack_propagate(False)
        tk.Button(
            action_bar,
            text="1. Load file + Generate drafts",
            command=self.load_knowledge_file,
            font=("Segoe UI", 10, "bold"),
            bg="#1f6aa5",
            fg="white",
            activebackground="#174e7b",
            activeforeground="white",
            padx=12,
            pady=8,
        ).pack(side=LEFT, padx=(8, 8), pady=10)
        tk.Button(
            action_bar,
            text="2. Generate drafts",
            command=self.generate,
            font=("Segoe UI", 10, "bold"),
            bg="#287a4b",
            fg="white",
            activebackground="#1d5a37",
            activeforeground="white",
            padx=12,
            pady=8,
        ).pack(side=LEFT, padx=(0, 8), pady=10)
        tk.Button(
            action_bar,
            text="3. Save content drafts",
            command=self.save,
            font=("Segoe UI", 10, "bold"),
            bg="#5b3f8c",
            fg="white",
            activebackground="#422c68",
            activeforeground="white",
            padx=12,
            pady=8,
        ).pack(side=LEFT, padx=(0, 8), pady=10)
        tk.Button(
            action_bar,
            text="4. Next: Retrieval",
            command=self.open_next,
            font=("Segoe UI", 10, "bold"),
            bg="#8a5a12",
            fg="white",
            activebackground="#68430d",
            activeforeground="white",
            padx=12,
            pady=8,
        ).pack(side=LEFT, padx=(0, 8), pady=10)
        tk.Button(
            action_bar,
            text="Choose file + generate",
            command=self.choose_and_generate,
            font=("Segoe UI", 10),
            padx=10,
            pady=8,
        ).pack(side=LEFT, padx=(0, 8), pady=10)

        controls = ttk.LabelFrame(body, text="1. Campaign brief", padding=10)
        controls.pack(fill=X, pady=(0, 10))
        ttk.Label(controls, text="Campaign goal").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(controls, textvariable=self.goal_var, width=90).grid(row=0, column=1, sticky="ew", pady=4)
        ttk.Label(controls, text="Call to action").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        ttk.Entry(controls, textvariable=self.cta_var, width=90).grid(row=1, column=1, sticky="ew", pady=4)
        controls.columnconfigure(1, weight=1)

        preview = ttk.LabelFrame(body, text="2. Generated drafts and grounding record", padding=8)
        preview.pack(fill=BOTH, expand=True)
        self.output_text.pack(in_=preview, fill=BOTH, expand=True)

        footer = tk.Frame(self, bg="#dce8f3", padx=14, pady=7)
        footer.pack(fill=X)
        tk.Label(footer, textvariable=self.status_var, bg="#dce8f3", fg="#24445f", anchor="w").pack(fill=X)

    def show(self, data: dict) -> None:
        self.output_text.configure(state="normal")
        self.output_text.delete("1.0", END)
        self.output_text.insert("1.0", json.dumps(data, ensure_ascii=False, indent=2))
        self.output_text.configure(state="disabled")

    def generate(self) -> None:
        self.status_var.set("Generate button clicked — preparing drafts...")
        self.update_idletasks()
        try:
            if self.loaded_knowledge is not None:
                knowledge = self.loaded_knowledge
                knowledge_path = self.loaded_knowledge_path or KNOWLEDGE_FILE
            else:
                knowledge_path = KNOWLEDGE_FILE
                if not knowledge_path.exists():
                    self.status_var.set("First click 'Load knowledge file'")
                    messagebox.showinfo(
                        "Load knowledge first",
                        "Please click '1. Load knowledge file' and select knowledge_base.json first.",
                    )
                    return
                knowledge = load_knowledge(knowledge_path)
            self.current_output = build_drafts(knowledge, self.goal_var.get(), self.cta_var.get())
            self.show(self.current_output)
            DRAFTS_FILE.write_text(
                json.dumps(self.current_output, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            self.status_var.set(f"Generated 4 drafts from {knowledge_path.name}; auto-saved content_drafts.json")
            self.update_idletasks()
            messagebox.showinfo(
                "Draft generation complete",
                "Four drafts were generated and saved:\n\n"
                "Instagram • Facebook • WhatsApp • Email\n\n"
                f"File: {DRAFTS_FILE}",
            )
        except Exception as exc:
            self.show(
                {
                    "generation_complete": False,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "next_step": "Check the selected JSON file and try again",
                }
            )
            messagebox.showerror("Generation error", str(exc))
            self.status_var.set("Generation failed")

    def load_knowledge_file(self) -> None:
        selected = filedialog.askopenfilename(
            title="Choose knowledge_base.json",
            initialdir=str(OUTPUT_DIR),
            filetypes=[("Knowledge base", "knowledge_base.json"), ("JSON", "*.json")],
        )
        if not selected:
            self.status_var.set("No knowledge file selected")
            return
        try:
            self.loaded_knowledge_path = Path(selected)
            self.loaded_knowledge = load_knowledge(self.loaded_knowledge_path)
            profile = self.loaded_knowledge.get("company_profile", {})
            self.show(
                {
                    "knowledge_loaded": True,
                    "file": str(self.loaded_knowledge_path),
                    "company_profile": profile,
                    "source_words": self.loaded_knowledge.get("extraction", {}).get("word_count", 0),
                    "next_step": "Drafts will be generated automatically",
                }
            )
            self.status_var.set(f"Knowledge loaded: {self.loaded_knowledge_path.name}")
            self.generate()
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            self.loaded_knowledge = None
            self.loaded_knowledge_path = None
            messagebox.showerror("Load error", str(exc))
            self.status_var.set("Could not load knowledge file")

    def choose_and_generate(self) -> None:
        selected = filedialog.askopenfilename(
            title="Choose knowledge_base.json",
            initialdir=str(OUTPUT_DIR),
            filetypes=[("Knowledge base", "knowledge_base.json"), ("JSON", "*.json")],
        )
        if not selected:
            self.status_var.set("No knowledge file selected")
            return
        try:
            knowledge_path = Path(selected)
            self.loaded_knowledge_path = knowledge_path
            self.loaded_knowledge = load_knowledge(knowledge_path)
            self.generate()
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            messagebox.showerror("Load error", str(exc))
            self.status_var.set("Could not load knowledge file")

    def save(self) -> None:
        if self.current_output is None:
            self.generate()
        if self.current_output is None:
            return
        DRAFTS_FILE.write_text(json.dumps(self.current_output, ensure_ascii=False, indent=2), encoding="utf-8")
        self.status_var.set(f"Saved dry-run drafts: {DRAFTS_FILE}")
        messagebox.showinfo("Saved", f"Drafts saved to:\n{DRAFTS_FILE}")

    def open_next(self) -> None:
        if self.current_output is None:
            self.generate()
        if self.current_output is None:
            return
        try:
            DRAFTS_FILE.write_text(
                json.dumps(self.current_output, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            next_file = Path(__file__).resolve().parent / "retrieval_app.py"
            if not next_file.exists():
                raise FileNotFoundError(f"Next module not found: {next_file}")
            subprocess.Popen([sys.executable, str(next_file)], cwd=str(ROOT))
            self.status_var.set("Drafts saved — Retrieval opened")
        except (OSError, subprocess.SubprocessError) as exc:
            messagebox.showerror("Next module error", str(exc))
            self.status_var.set("Could not open Retrieval")

    def open_file(self) -> None:
        if KNOWLEDGE_FILE.exists():
            filedialog.askopenfilename(initialdir=str(OUTPUT_DIR), initialfile=KNOWLEDGE_FILE.name)
        else:
            messagebox.showinfo("Not found", "Save the company knowledge first.")


if __name__ == "__main__":
    ContentStudio().mainloop()
