import tkinter as tk
from tkinter import ttk

class CreatorWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Creator Window')
        self.geometry('400x300')

        # Corrected attribute name from 'council_timer' to 'council_view'
        self.council_view = ttk.Label(self, text='Council Timer', font=('Helvetica', 16))
        self.council_view.pack(pady=20)

if __name__ == '__main__':
    app = CreatorWindow()
    app.mainloop()