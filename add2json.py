import os
import json
from pathlib import Path

# Constants
UPLOAD_JSON = "upload_list.json"

# Function to load or initialize JSON data
def load_json_data(directory):
    json_path = directory / UPLOAD_JSON
    if json_path.exists():
        with open(json_path, 'r') as file:
            return json.load(file)
    return []

# Function to save JSON data
def save_json_data(directory, data):
    json_path = directory / UPLOAD_JSON
    with open(json_path, 'w') as file:
        json.dump(data, file, indent=4)

# Function to add file to JSON
def add_file_to_json(filepath):
    filepath = Path(filepath).resolve()
    directory = filepath.parent
    json_data = load_json_data(directory)

    if filepath.name not in json_data:
        json_data.append(filepath.name)
        save_json_data(directory, json_data)
        print(f"✅ Added '{filepath.name}' to '{UPLOAD_JSON}' in '{directory}'.")
    else:
        print(f"⚠️ '{filepath.name}' is already in '{UPLOAD_JSON}' in '{directory}'.")

if __name__ == "__main__":
    file_input = input("Type or paste the full path to the file to add: ").strip()

    if not file_input:
        print("No file provided.")
    elif not os.path.isfile(file_input):
        print(f"Error: '{file_input}' does not exist or is not a file.")
    else:
        add_file_to_json(file_input)

# Note: Drag-and-drop functionality is temporarily disabled due to installation issues.
# from tkinterdnd2 import TkinterDnD, DND_FILES
# import tkinter as tk

# def on_drop(event):
#     file_path = event.data.strip('{}')
#     add_file_to_json(file_path)

# # TkinterDnD setup
# app = TkinterDnD.Tk()
# app.title("Drag and Drop JSON Adder")
# app.geometry("400x200")

# drop_label = tk.Label(app, text="Drag and drop files here", bg="lightgray")
# drop_label.pack(expand=True, fill='both', padx=10, pady=10)
# drop_label.drop_target_register(DND_FILES)
# drop_label.dnd_bind('<<Drop>>', on_drop)

# app.mainloop()