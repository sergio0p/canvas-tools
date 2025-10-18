import json
import os
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import platform
import subprocess

# === Globals ===
upload_list_path = None
current_files = set()
file_buttons_frame = None

# === GUI Setup ===
root = tk.Tk()
root.title("📤 Add to upload_list.json")
root.geometry("500x500")
root.configure(bg="#f0f0f0")

status = tk.StringVar()

# === Functions ===

def open_folder():
    if not upload_list_path:
        return
    folder = str(upload_list_path.parent)
    if platform.system() == "Darwin":
        subprocess.run(["open", folder])
    elif platform.system() == "Windows":
        subprocess.run(["explorer", folder])
    else:
        subprocess.run(["xdg-open", folder])

def refresh_display():
    for widget in file_buttons_frame.winfo_children():
        widget.destroy()

    for fname in sorted(current_files):
        row = tk.Frame(file_buttons_frame, bg="#f0f0f0")
        row.pack(fill="x", pady=2)

        label = tk.Label(row, text=fname, anchor="w", bg="#f0f0f0")
        label.pack(side="left", fill="x", expand=True)

        del_btn = tk.Button(row, text="🗑️ Delete", command=lambda f=fname: delete_file(f))
        del_btn.pack(side="right")

def delete_file(filename):
    global current_files
    if filename in current_files:
        current_files.remove(filename)
        save_list()
        refresh_display()
        status.set(f"🗑️ Removed: {filename}")

def save_list():
    with open(upload_list_path, "w") as f:
        json.dump(sorted(current_files), f, indent=2)

def load_list(path):
    global current_files
    if path.exists():
        try:
            with open(path, "r") as f:
                current_files = set(json.load(f))
        except Exception:
            current_files = set()
    else:
        current_files = set()

def handle_drop(files):
    global upload_list_path

    if not files:
        return

    parents = {Path(f).parent.resolve() for f in files}
    if len(parents) != 1:
        messagebox.showerror("Invalid Drop", "❌ All files must be from the same folder.")
        return

    folder = next(iter(parents))
    upload_list_path = folder / "upload_list.json"
    load_list(upload_list_path)

    added = 0
    for f in files:
        fname = Path(f).name
        if fname not in current_files:
            current_files.add(fname)
            added += 1

    save_list()
    refresh_display()

    if added:
        status.set(f"✅ Added {added} file(s) to {upload_list_path.name}")
    else:
        status.set("⏩ No new files added.")

def browse_files():
    filepaths = filedialog.askopenfilenames(title="Select files to add")
    handle_drop(filepaths)

def drop_event(event):
    files = root.tk.splitlist(event.data)
    handle_drop(files)

# === GUI Widgets ===

frame = tk.Label(root, text="\n📁 Drag & drop files here\nor click below to browse",
                 bg="#f0f0f0", fg="black", font=("Helvetica", 14), width=40, height=6, relief="ridge")
frame.pack(pady=10)

browse_btn = tk.Button(root, text="📂 Browse Files", command=browse_files)
browse_btn.pack(pady=(0, 10))

open_btn = tk.Button(root, text="🗂 Open Folder", command=open_folder)
open_btn.pack(pady=(0, 10))

status_label = tk.Label(root, textvariable=status, bg="#f0f0f0", fg="green")
status_label.pack(pady=(0, 10))

canvas = tk.Canvas(root, bg="#ffffff", height=250)
scrollbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
file_buttons_frame = tk.Frame(canvas, bg="#ffffff")

file_buttons_frame.bind(
    "<Configure>",
    lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
)

canvas.create_window((0, 0), window=file_buttons_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)

canvas.pack(fill="both", expand=True, side="left", padx=(20, 0))
scrollbar.pack(fill="y", side="right", padx=(0, 20))

# === Drag & Drop Support ===
try:
    import tkinterdnd2
    root = tkinterdnd2.TkinterDnD.Tk()
    frame.drop_target_register(tkinterdnd2.DND_FILES)
    frame.dnd_bind("<<Drop>>", drop_event)
except ImportError:
    frame.config(text="\n📂 Drag & drop unavailable\n(install tkinterdnd2)\nUse Browse instead")

root.mainloop()