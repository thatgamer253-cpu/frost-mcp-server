#!/usr/bin/env python3
"""
South Park Episode Video Generator - Fully Animated Version
Creates actual animated movement and transitions.
"""

import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import *

def create_character_sprite(name, color, width=200, height=300):
    """Create a simple character sprite"""
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Body
    draw.ellipse([50, 100, 150, 250], fill=color, outline='black', width=3)
    
    # Head
    draw.ellipse([60, 20, 140, 100], fill='#FDB', outline='black', width=3)
    
    # Eyes
    draw.ellipse([75, 45, 90, 60], fill='white', outline='black', width=2)
    draw.ellipse([110, 45, 125, 60], fill='white', outline='black', width=2)
    draw.ellipse([80, 50, 85, 55], fill='black')
    draw.ellipse([115, 50, 120, 55], fill='black')
    
    # Mouth
    draw.arc([75, 65, 125, 85], 0, 180, fill='black', width=2)
    
    # Name
    try:
        font = ImageFont.truetype("arial.ttf", 16)
    except:
        font = ImageFont.load_default()
    draw.text((width//2 - 20, height - 25), name, fill='black', font=font)
    
    return np.array(img)

def create_background(scene_name, width=1280, height=720):
    """Create a background with scene name"""
    img = Image.new('RGB', (width, height), '#87CEEB')
    draw = ImageDraw.Draw(img)
    
    # Ground
    draw.rectangle([0, height//2, width, height], fill='#90EE90')
    
    # Mountains
    points = [(0, height//2), (200, height//2 - 100), (400, height//2), 
              (600, height//2 - 80), (800, height//2), (1000, height//2 - 120), 
              (1280, height//2)]
    draw.polygon(points, fill='#8B7355')
    
    # Scene label
    try:
        font = ImageFont.truetype("arial.ttf", 40)
    except:
        font = ImageFont.load_default()
    draw.text((50, 50), scene_name, fill='white', font=font, stroke_width=2, stroke_fill='black')
    
    return np.array(img)

def make_character_walk(char_img, start_pos, end_pos, duration):
    """Animate a character walking from start to end position"""
    def position_at_time(t):
        progress = t / duration
        x = start_pos[0] + (end_pos[0] - start_pos[0]) * progress
        y = start_pos[1] + np.sin(progress * 10) * 5  # Bobbing motion
        return (int(x), int(y))
    
    return ImageClip(char_img).set_duration(duration).set_position(position_at_time)

def make_character_bounce(char_img, pos, duration):
    """Make character bounce in place"""
    def position_at_time(t):
        bounce = abs(np.sin(t * 3)) * 20
        return (pos[0], pos[1] - int(bounce))
    
    return ImageClip(char_img).set_duration(duration).set_position(position_at_time)

def create_animated_scene(scene_name, duration, animation_type="walk"):
    """Create a fully animated scene"""
    # Create background
    bg = create_background(scene_name)
    bg_clip = ImageClip(bg).set_duration(duration)
    
    # Create characters
    stan = create_character_sprite("Stan", '#0066CC')
    kyle = create_character_sprite("Kyle", '#00AA00')
    cartman = create_character_sprite("Cartman", '#CC0000')
    kenny = create_character_sprite("Kenny", '#FF8800')
    
    char_clips = []
    
    if animation_type == "walk":
        # Characters walk across screen
        char_clips.append(make_character_walk(stan, (-200, 300), (300, 300), duration))
        char_clips.append(make_character_walk(kyle, (-100, 300), (500, 300), duration))
        char_clips.append(make_character_walk(cartman, (0, 300), (700, 300), duration))
        char_clips.append(make_character_walk(kenny, (100, 300), (900, 300), duration))
    elif animation_type == "bounce":
        # Characters bounce in place
        char_clips.append(make_character_bounce(stan, (200, 300), duration))
        char_clips.append(make_character_bounce(kyle, (400, 300), duration))
        char_clips.append(make_character_bounce(cartman, (600, 300), duration))
        char_clips.append(make_character_bounce(kenny, (800, 300), duration))
    else:  # static
        # Characters stand still
        positions = [(200, 300), (400, 300), (600, 300), (800, 300)]
        for char, pos in zip([stan, kyle, cartman, kenny], positions):
            char_clips.append(ImageClip(char).set_duration(duration).set_position(pos))
    
    return CompositeVideoClip([bg_clip] + char_clips)

def generate_episode():
    """Generate the full animated episode"""
    print("[*] Generating Animated South Park Episode...")
    
    # Define scenes with different animation types
    scenes = [
        {"name": "SOUTH PARK: The AI Takeover", "duration": 3, "type": "static"},
        {"name": "Scene 1: Elementary School", "duration": 6, "type": "bounce"},
        {"name": "Scene 2: Walking to Town", "duration": 8, "type": "walk"},
        {"name": "Scene 3: Cartman's House", "duration": 5, "type": "bounce"},
        {"name": "Scene 4: Stan's House", "duration": 5, "type": "static"},
        {"name": "Scene 5: Radio Shack Battle", "duration": 7, "type": "bounce"},
        {"name": "Scene 6: Victory!", "duration": 6, "type": "walk"},
    ]
    
    clips = []
    
    for i, scene in enumerate(scenes):
        print(f"Rendering scene {i+1}/{len(scenes)}: {scene['name']}")
        scene_clip = create_animated_scene(scene['name'], scene['duration'], scene['type'])
        clips.append(scene_clip)
    
    # Concatenate all scenes
    print("Combining scenes...")
    final_video = concatenate_videoclips(clips, method="compose")
    
    # Export
    output_path = "south_park_animated.mp4"
    print(f"Exporting video to {output_path}...")
    final_video.write_videofile(output_path, fps=24, codec='libx264')
    
    print(f"[OK] Animated episode complete! Saved to: {os.path.abspath(output_path)}")
    print(f"[INFO] Total duration: {final_video.duration:.1f} seconds")
    
    return output_path

if __name__ == "__main__":
    print("=" * 60)
    print("SOUTH PARK ANIMATED EPISODE GENERATOR")
    print("=" * 60)
    print()
    
    try:
        import moviepy
        import PIL
        print("[OK] All dependencies installed")
    except ImportError as e:
        print(f"[ERROR] Missing dependency: {e}")
        exit(1)
    
    output_file = generate_episode()
    
    print("\n" + "=" * 60)
    print(f"[SUCCESS] Your animated South Park episode is ready!")
    print(f"[FILE] Location: {output_file}")
    print("=" * 60)
