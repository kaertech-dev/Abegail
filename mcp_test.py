# mcp_test.py
import tkinter as tk
import requests

def start_machine():
    requests.post("http://localhost:8000/start")
    status_label.config(text="Machine Running", fg="green")

def stop_machine():
    requests.post("http://localhost:8000/stop")
    status_label.config(text="Machine Stopped", fg="red")

root = tk.Tk()
root.title("Manufacturing Control Panel")

status_label = tk.Label(root, text="Machine Stopped", font=("Arial", 16), fg="red")
status_label.pack(pady=10)

tk.Button(root, text="Start", command=start_machine, bg="lightgreen", width=10).pack(pady=5)
tk.Button(root, text="Stop", command=stop_machine, bg="salmon", width=10).pack(pady=5)

root.mainloop()
