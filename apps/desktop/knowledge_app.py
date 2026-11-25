"""Desktop app: Company knowledge ingestion: build the local knowledge base from text and a profile form."""

from __future__ import annotations

import json
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, X, Y, filedialog, messagebox, ttk

from marketmind.ingestion import build_record, read_input_file
from marketmind.settings import INPUT_DIR, KNOWLEDGE_FILE, ROOT


class KnowledgeApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("MarketMind AI — Company Knowledge")
        self.geometry("1120x760")
        self.minsize(900, 620)
        self.configure(bg="#eef3f8")

        self.fields: dict[str, tk.StringVar] = {}
        self.raw_text = tk.Text(self, height=12, wrap="word", font=("Segoe UI", 10))
        self.preview_text = tk.Text(self, height=16, wrap="word", font=("Consolas", 9))
        self.status_var = tk.StringVar(value="Ready — dry-run mode only")
        self.progress = ttk.Progressbar(self, mode="indeterminate", length=140)

        self._build_style()
        self._build_header()
        self._build_body()
        self._build_footer()

    def _build_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Title.TLabel", font=("Segoe UI", 20, "bold"), foreground="#103b66")
        style.configure("Sub.TLabel", font=("Segoe UI", 10), foreground="#45627c")
        style.configure("Section.TLabelframe", padding=10)
        style.configure("Section.TLabelframe.Label", font=("Segoe UI", 11, "bold"))
        style.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), padding=(12, 7))

    def _build_header(self) -> None:
        header = tk.Frame(self, bg="#103b66", padx=18, pady=14)
        header.pack(fill=X)
        ttk.Label(header, text="MarketMind AI — Company Knowledge", style="Title.TLabel").pack(anchor="w")
        tk.Label(
            header,
            text="Front GUI • data input • basic text extraction • local JSON knowledge base",
            bg="#103b66",
            fg="#dcecff",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(3, 0))

    def _build_body(self) -> None:
        body = tk.Frame(self, bg="#eef3f8", padx=14, pady=12)
        body.pack(fill=BOTH, expand=True)

        action_bar = tk.Frame(body, bg="#dce8f3", height=64)
        action_bar.pack(side="top", fill=X, pady=(0, 10))
        action_bar.pack_propagate(False)
        tk.Button(
            action_bar,
            text="1. Extract & preview",
            command=self.extract_preview,
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
            text="2. Save knowledge base",
            command=self.save_record,
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
            text="3. Next: Content Studio",
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
            text="Clear",
            command=self.clear_all,
            font=("Segoe UI", 10),
            padx=12,
            pady=8,
        ).pack(side=LEFT, padx=(0, 8), pady=10)

        left = tk.Frame(body, bg="#eef3f8")
        left.pack(side=LEFT, fill=Y, padx=(0, 10))
        right = tk.Frame(body, bg="#eef3f8")
        right.pack(side=LEFT, fill=BOTH, expand=True)

        profile = ttk.LabelFrame(left, text="1. Company & product data", style="Section.TLabelframe")
        profile.pack(fill=Y, expand=False)

        field_specs = [
            ("company_name", "Company name"),
            ("brand_name", "Brand / product name"),
            ("products", "Products / services"),
            ("target_customer", "Target customer"),
            ("customer_problem", "Customer problem"),
            ("usp", "Unique selling point"),
            ("offer_price", "Offer / price"),
            ("location", "Location / market"),
            ("tone", "Content tone"),
            ("restrictions", "Words / claims to avoid"),
        ]

        for key, label in field_specs:
            row = tk.Frame(profile, bg="#f6f9fc")
            row.pack(fill=X, pady=3)
            tk.Label(row, text=label, width=21, anchor="w", bg="#f6f9fc", fg="#23384d").pack(side=LEFT)
            var = tk.StringVar()
            self.fields[key] = var
            ttk.Entry(row, textvariable=var, width=32).pack(side=LEFT, fill=X, expand=True)

        ttk.Separator(profile).pack(fill=X, pady=9)
        ttk.Label(
            profile, text="Tip: start with one product only for the first dry run.", style="Sub.TLabel", wraplength=360
        ).pack(anchor="w")

        source = ttk.LabelFrame(right, text="2. Data input words / notes", style="Section.TLabelframe")
        source.pack(fill=BOTH, expand=True)
        ttk.Label(
            source,
            text="Paste company/product information here, or import a local .txt/.md/.json/.csv file.",
            style="Sub.TLabel",
        ).pack(anchor="w", pady=(0, 5))
        self.raw_text.pack(in_=source, fill=BOTH, expand=True)

        buttons = tk.Frame(source, bg="#f6f9fc")
        buttons.pack(fill=X, pady=(8, 0))
        ttk.Button(buttons, text="Import input file", command=self.import_file).pack(side=LEFT, padx=(0, 7))
        ttk.Button(buttons, text="Use sample words", command=self.insert_sample).pack(side=LEFT)

        preview = ttk.LabelFrame(right, text="3. Extraction preview", style="Section.TLabelframe")
        preview.pack(fill=BOTH, expand=True, pady=(10, 0))
        self.preview_text.pack(in_=preview, fill=BOTH, expand=True)
        self.preview_text.configure(state="disabled", background="#fbfdff")

    def _build_footer(self) -> None:
        footer = tk.Frame(self, bg="#dce8f3", padx=14, pady=7)
        footer.pack(fill=X)
        tk.Label(footer, textvariable=self.status_var, bg="#dce8f3", fg="#24445f", anchor="w").pack(
            side=LEFT, fill=X, expand=True
        )
        self.progress.pack(in_=footer, side=RIGHT)

    def set_status(self, message: str) -> None:
        self.status_var.set(message)
        self.update_idletasks()

    def import_file(self) -> None:
        path_string = filedialog.askopenfilename(
            title="Choose dry-run input file",
            initialdir=str(INPUT_DIR),
            filetypes=[
                ("Text/Markdown", "*.txt *.md *.markdown *.log"),
                ("JSON", "*.json"),
                ("CSV", "*.csv"),
                ("All supported", "*.txt *.md *.markdown *.log *.json *.csv"),
            ],
        )
        if not path_string:
            return
        try:
            content = read_input_file(Path(path_string))
            self.raw_text.delete("1.0", END)
            self.raw_text.insert("1.0", content)
            self.set_status(f"Imported: {Path(path_string).name}")
        except Exception as exc:
            messagebox.showerror("Import error", str(exc))
            self.set_status("Import failed")

    def insert_sample(self) -> None:
        sample = (
            "MOSETA Solar AC\n"
            "Energy-efficient air conditioner for homes, offices and institutions.\n"
            "Key benefits: low electricity consumption, reliable cooling, green technology.\n"
            "Customer problem: high electricity bill and unreliable cooling.\n"
            "Call to action: request a product consultation.\n"
            "Avoid unsupported medical, financial or guaranteed-saving claims."
        )
        self.raw_text.delete("1.0", END)
        self.raw_text.insert("1.0", sample)
        self.set_status("Sample input inserted")

    def collect_values(self) -> dict[str, str]:
        return {key: value.get().strip() for key, value in self.fields.items()}

    def current_record(self) -> dict:
        return build_record(self.collect_values(), self.raw_text.get("1.0", END))

    def show_preview(self, record: dict) -> None:
        preview = {
            "mode": record["mode"],
            "company_profile": record["company_profile"],
            "extraction_summary": record["extraction"],
            "next_module": "content_app.py",
        }
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", END)
        self.preview_text.insert("1.0", json.dumps(preview, ensure_ascii=False, indent=2))
        self.preview_text.configure(state="disabled")

    def extract_preview(self) -> None:
        record = self.current_record()
        if not record["source_text"] and not any(record["company_profile"].values()):
            messagebox.showwarning("No input", "Please enter company data or paste/import input words first.")
            return
        self.show_preview(record)
        summary = record["extraction"]
        self.set_status(f"Extracted {summary['word_count']} words and {len(summary['keywords'])} keywords")

    def save_record(self) -> None:
        record = self.current_record()
        if not record["source_text"] and not any(record["company_profile"].values()):
            messagebox.showwarning("No input", "Please enter company data or paste/import input words first.")
            return
        try:
            KNOWLEDGE_FILE.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
            self.show_preview(record)
            self.set_status(f"Saved local knowledge base: {KNOWLEDGE_FILE}")
            messagebox.showinfo("Saved", f"Dry-run data saved to:\n{KNOWLEDGE_FILE}")
        except OSError as exc:
            messagebox.showerror("Save error", str(exc))
            self.set_status("Save failed")

    def open_next(self) -> None:
        record = self.current_record()
        if not record["source_text"] and not any(record["company_profile"].values()):
            messagebox.showwarning("No input", "Please enter company data or paste/import input words first.")
            return
        try:
            KNOWLEDGE_FILE.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
            next_file = Path(__file__).resolve().parent / "content_app.py"
            if not next_file.exists():
                raise FileNotFoundError(f"Next module not found: {next_file}")
            subprocess.Popen([sys.executable, str(next_file)], cwd=str(ROOT))
            self.set_status("Knowledge saved — Content Studio opened")
        except (OSError, subprocess.SubprocessError) as exc:
            messagebox.showerror("Next module error", str(exc))
            self.set_status("Could not open Content Studio")

    def clear_all(self) -> None:
        for value in self.fields.values():
            value.set("")
        self.raw_text.delete("1.0", END)
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", END)
        self.preview_text.configure(state="disabled")
        self.set_status("Cleared — ready for a new dry run")


if __name__ == "__main__":
    app = KnowledgeApp()
    app.mainloop()
