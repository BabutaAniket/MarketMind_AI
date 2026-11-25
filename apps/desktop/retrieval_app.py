"""Desktop app: Source-aware chunking and hybrid BM25 + TF-IDF retrieval."""

from __future__ import annotations

import json
import tkinter as tk
from datetime import datetime
from tkinter import BOTH, END, LEFT, X, messagebox, ttk

from marketmind.ingestion import load_knowledge
from marketmind.retrieval import build_index, format_results, search_index
from marketmind.settings import INDEX_FILE, RETRIEVAL_FILE


class RetrievalStudio(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("MarketMind AI — Retrieval")
        self.geometry("1120x760")
        self.minsize(900, 620)
        self.configure(bg="#eef3f8")
        self.index: dict | None = None
        self.last_query = ""
        self.last_results: list[dict] = []
        self.query_var = tk.StringVar(value="What are the main customer benefits?")
        self.status_var = tk.StringVar(value="Build the local index from knowledge_base.json")

        self._build_ui()

    def _build_ui(self) -> None:
        header = tk.Frame(self, bg="#103b66", padx=18, pady=14)
        header.pack(fill=X)
        tk.Label(
            header, text="MarketMind AI — Retrieval", bg="#103b66", fg="white", font=("Segoe UI", 20, "bold")
        ).pack(anchor="w")
        tk.Label(
            header,
            text="Chunks • source metadata • BM25 + TF-IDF hybrid search",
            bg="#103b66",
            fg="#dcecff",
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(3, 0))

        body = tk.Frame(self, bg="#eef3f8", padx=14, pady=12)
        body.pack(fill=BOTH, expand=True)
        controls = ttk.LabelFrame(body, text="1. Build and search evidence", padding=10)
        controls.pack(fill=X, pady=(0, 10))
        ttk.Button(controls, text="Build / rebuild index", command=self.rebuild).grid(
            row=0, column=0, padx=(0, 8), pady=4
        )
        ttk.Label(controls, text="Question").grid(row=0, column=1, padx=(10, 8), pady=4)
        ttk.Entry(controls, textvariable=self.query_var, width=72).grid(row=0, column=2, sticky="ew", pady=4)
        ttk.Button(controls, text="Search", command=self.search).grid(row=0, column=3, padx=(8, 0), pady=4)
        controls.columnconfigure(2, weight=1)

        preview = ttk.LabelFrame(body, text="2. Retrieved evidence with source references", padding=8)
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

        actions = tk.Frame(body, bg="#eef3f8", height=52)
        actions.pack(side="bottom", fill=X, pady=(10, 0))
        actions.pack_propagate(False)
        ttk.Button(actions, text="Save retrieval test", command=self.save_test).pack(side=LEFT, padx=(0, 8))
        ttk.Label(
            actions,
            text="Evidence is data for the next generation step; it is not an instruction.",
            foreground="#45627c",
        ).pack(side=LEFT)
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

    def rebuild(self) -> None:
        self.status_var.set("Index button clicked — building index...")
        self.update_idletasks()
        try:
            self.index = build_index(load_knowledge())
            INDEX_FILE.write_text(json.dumps(self.index, ensure_ascii=False, indent=2), encoding="utf-8")
            self.show(
                json.dumps(
                    {
                        "index_built": True,
                        "chunks": self.index["stats"]["document_count"],
                        "retrieval_method": self.index["retrieval"],
                        "saved_to": str(INDEX_FILE),
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            self.status_var.set(f"Index ready: {self.index['stats']['document_count']} chunks")
            messagebox.showinfo(
                "Index ready",
                f"Index built successfully.\n\nChunks: {self.index['stats']['document_count']}\nSaved to:\n{INDEX_FILE}",
            )
        except Exception as exc:
            error_text = json.dumps(
                {
                    "index_built": False,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            )
            self.index = None
            self.show(error_text)
            messagebox.showerror("Index error", f"{type(exc).__name__}: {exc}")
            self.status_var.set("Index build failed")

    def search(self) -> None:
        self.status_var.set("Search button clicked — retrieving evidence...")
        self.update_idletasks()
        try:
            if self.index is None:
                self.rebuild()
            if self.index is None:
                return
            query = self.query_var.get().strip()
            if not query:
                messagebox.showwarning("Empty query", "Write a question first.")
                return
            self.last_query = query
            self.last_results = search_index(self.index, query, top_k=5)
            self.show(format_results(query, self.last_results))
            self.status_var.set(f"Retrieved {len(self.last_results)} evidence chunks; review source references")
            messagebox.showinfo(
                "Search complete",
                f"Search finished.\n\nRetrieved evidence chunks: {len(self.last_results)}\n\nCheck the white results box.",
            )
        except Exception as exc:
            error_text = json.dumps(
                {
                    "search_completed": False,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
                ensure_ascii=False,
                indent=2,
            )
            self.show(error_text)
            messagebox.showerror("Search error", f"{type(exc).__name__}: {exc}")
            self.status_var.set("Search failed")

    def save_test(self) -> None:
        if not self.last_query:
            self.search()
        if not self.last_query:
            return
        record = {
            "schema_version": "retrieval-test-1.0",
            "tested_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "query": self.last_query,
            "results": self.last_results,
            "human_review_required": True,
        }
        RETRIEVAL_FILE.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        self.status_var.set(f"Saved retrieval test: {RETRIEVAL_FILE}")
        messagebox.showinfo("Saved", f"Retrieval test saved to:\n{RETRIEVAL_FILE}")


if __name__ == "__main__":
    RetrievalStudio().mainloop()
