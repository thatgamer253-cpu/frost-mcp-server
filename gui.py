# gui.py

import tkinter as tk
from tkinter import messagebox

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("Example GUI")
        self.label = tk.Label(root, text="Hello, World!")
        self.label.pack()
        self.button = tk.Button(root, text="Click Me", command=self.on_button_click)
        self.button.pack()

    def on_button_click(self):
        messagebox.showinfo("Message", "Button Clicked")

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()