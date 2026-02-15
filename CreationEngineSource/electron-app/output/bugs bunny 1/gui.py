import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from scene import Scene
from actions import CharacterActions
from sound import SoundManager
from export import AnimationExporter

class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Animation Studio")
        self.geometry("800x600")
        
        self.scene = None
        self.character_actions = None
        self.sound_manager = None
        
        self.create_widgets()

    def create_widgets(self):
        # Scene Setup
        scene_frame = ttk.LabelFrame(self, text="Scene Setup")
        scene_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(scene_frame, text="Load Background", command=self.load_background).pack(side="left", padx=5, pady=5)
        ttk.Button(scene_frame, text="Clear Props", command=self.clear_props).pack(side="left", padx=5, pady=5)
        
        # Character Customization
        character_frame = ttk.LabelFrame(self, text="Character Customization")
        character_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(character_frame, text="Load Character Sprites", command=self.load_character_sprites).pack(side="left", padx=5, pady=5)
        
        # Action Scripting
        action_frame = ttk.LabelFrame(self, text="Action Scripting")
        action_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(action_frame, text="Move Left", command=lambda: self.perform_action('left')).pack(side="left", padx=5, pady=5)
        ttk.Button(action_frame, text="Move Right", command=lambda: self.perform_action('right')).pack(side="left", padx=5, pady=5)
        ttk.Button(action_frame, text="Jump", command=lambda: self.perform_action('jump')).pack(side="left", padx=5, pady=5)
        ttk.Button(action_frame, text="Attack", command=lambda: self.perform_action('attack')).pack(side="left", padx=5, pady=5)
        
        # Sound Management
        sound_frame = ttk.LabelFrame(self, text="Sound Management")
        sound_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(sound_frame, text="Load Sounds", command=self.load_sounds).pack(side="left", padx=5, pady=5)
        ttk.Button(sound_frame, text="Play Sound", command=self.play_sound).pack(side="left", padx=5, pady=5)
        
        # Export
        export_frame = ttk.LabelFrame(self, text="Export")
        export_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(export_frame, text="Export to Video", command=self.export_to_video).pack(side="left", padx=5, pady=5)

    def load_background(self):
        file_path = filedialog.askopenfilename(title="Select Background Image", filetypes=[("Image Files", "*.png;*.jpg;*.jpeg")])
        if file_path:
            try:
                self.scene = Scene(self, file_path)
                messagebox.showinfo("Success", "Background loaded successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load background: {e}")

    def clear_props(self):
        if self.scene:
            self.scene.clear_props()
            messagebox.showinfo("Success", "Props cleared successfully.")
        else:
            messagebox.showwarning("Warning", "No scene loaded.")

    def load_character_sprites(self):
        folder_path = filedialog.askdirectory(title="Select Character Sprites Folder")
        if folder_path:
            try:
                self.character_actions = CharacterActions(self, folder_path)
                messagebox.showinfo("Success", "Character sprites loaded successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load character sprites: {e}")

    def perform_action(self, action):
        if self.character_actions:
            try:
                self.character_actions.perform_action(action)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to perform action: {e}")
        else:
            messagebox.showwarning("Warning", "No character loaded.")

    def load_sounds(self):
        folder_path = filedialog.askdirectory(title="Select Sound Directory")
        if folder_path:
            try:
                self.sound_manager = SoundManager(folder_path)
                messagebox.showinfo("Success", "Sounds loaded successfully.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load sounds: {e}")

    def play_sound(self):
        if self.sound_manager:
            sound_name = filedialog.askstring("Play Sound", "Enter sound name:")
            if sound_name:
                try:
                    self.sound_manager.play_sound(sound_name)
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to play sound: {e}")
        else:
            messagebox.showwarning("Warning", "No sounds loaded.")

    def export_to_video(self):
        if self.character_actions:
            output_file = filedialog.asksaveasfilename(title="Export to Video", defaultextension=".mp4", filetypes=[("MP4 Files", "*.mp4")])
            if output_file:
                try:
                    exporter = AnimationExporter(self.character_actions.character_animation.character_sprites_path, output_file)
                    exporter.export_to_video()
                    messagebox.showinfo("Success", "Video exported successfully.")
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to export video: {e}")
        else:
            messagebox.showwarning("Warning", "No character actions to export.")