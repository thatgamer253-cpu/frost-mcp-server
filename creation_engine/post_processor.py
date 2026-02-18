#!/usr/bin/env python3
"""
==============================================================
  OVERLORD - Media Post-Processor
  Final production mixing using MoviePy 2.x.
  Combines Video + Narration + Music + Subtitles.
==============================================================
"""

import os
import sys
import logging
from typing import Optional, List, Dict, Tuple

# MoviePy 2.x specific imports
try:
    from moviepy.video.io.VideoFileClip import VideoFileClip
    from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
    from moviepy.video.VideoClip import TextClip, ColorClip
    from moviepy.audio.io.AudioFileClip import AudioFileClip
    from moviepy.audio.AudioClip import CompositeAudioClip
    from moviepy import vfx
    _HAS_MOVIEPY = True
except ImportError:
    _HAS_MOVIEPY = False

# Import shared log
try:
    from agent_brain import log
except ImportError:
    def log(tag, msg):
        from datetime import datetime
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] [{tag}]  {msg}", flush=True)

class MediaPostProcessor:
    """Handles the final assembly of media assets into a polished product."""

    def __init__(self, output_dir: str = "./output"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        if not _HAS_MOVIEPY:
            log("WARN", "MoviePy 2.x NOT FOUND. Post-processing will be limited.")

    def process_video(self, 
                      video_path: str, 
                      narration_path: Optional[str] = None,
                      music_path: Optional[str] = None,
                      subtitles: Optional[List[Dict[str, Any]]] = None,
                      output_filename: str = "final_production.mp4",
                      target_aspect_ratio: str = "16:9") -> Optional[str]:
        """
        Main production pipeline:
        1. Load & Trim Video
        2. Mix Narration + Music
        3. Burn-in Subtitles
        4. Render Final Export
        """
        if not _HAS_MOVIEPY:
            log("ERROR", "Cannot process video: moviepy not installed.")
            return None

        if not os.path.exists(video_path):
            log("ERROR", f"Source video not found: {video_path}")
            return None

        output_path = os.path.join(self.output_dir, output_filename)
        log("PRODUCER", f"🎬 Starting post-production: {output_filename}")

        try:
            # 1. Load primary clip
            main_clip = VideoFileClip(video_path)
            duration = main_clip.duration

            # 2. Audio Stage
            audio_layers = []
            
            # Original Audio (if exists)
            if main_clip.audio:
                audio_layers.append(main_clip.audio.with_volume_scaled(0.3)) # Duck original
            
            # Narration
            if narration_path and os.path.exists(narration_path):
                narr_audio = AudioFileClip(narration_path)
                # If narration is longer than video, we might want to loop video or trim narration
                # For simplicity, we'll sync narration to start and let it run
                audio_layers.append(narr_audio.with_volume_scaled(1.0))
                # Update duration if narration is longer? 
                # Better to keep video duration as master for cinematic clips
            
            # Background Music
            if music_path and os.path.exists(music_path):
                bg_music = AudioFileClip(music_path)
                if bg_music.duration < duration:
                    bg_music = bg_music.fx(vfx.loop, duration=duration)
                else:
                    bg_music = bg_music.subclipped(0, duration)
                audio_layers.append(bg_music.with_volume_scaled(0.2))

            if audio_layers:
                final_audio = CompositeAudioClip(audio_layers)
                main_clip = main_clip.with_audio(final_audio)

            # 3. Subtitle Stage (Dynamic Overlays)
            visual_layers = [main_clip]
            
            if subtitles:
                for sub in subtitles:
                    text = sub.get("text", "")
                    start = sub.get("start", 0)
                    end = sub.get("end", duration)
                    pos = sub.get("position", ("center", "bottom"))
                    
                    if text:
                        try:
                            txt_clip = TextClip(
                                text=text,
                                font_size=sub.get("font_size", 36),
                                color=sub.get("color", "white"),
                                font=sub.get("font", "Arial"),
                                stroke_color=sub.get("stroke_color", "black"),
                                stroke_width=sub.get("stroke_width", 1),
                                method='caption',
                                size=(int(main_clip.w * 0.8), None) # Cast to int
                            )
                        except Exception as font_err:
                            log("WARN", f"  Font error ({sub.get('font')}): {font_err}. Falling back to default.")
                            txt_clip = TextClip(
                                text=text,
                                font_size=sub.get("font_size", 36),
                                color=sub.get("color", "white"),
                                stroke_color=sub.get("stroke_color", "black"),
                                stroke_width=sub.get("stroke_width", 1),
                                method='caption',
                                size=(int(main_clip.w * 0.8), None)
                            )
                        
                        txt_clip = txt_clip.with_start(start).with_end(end).with_position(pos)
                        visual_layers.append(txt_clip)

            # 4. Final Assembly
            if len(visual_layers) > 1:
                final_clip = CompositeVideoClip(visual_layers)
            else:
                final_clip = main_clip

            # 5. Render
            log("PRODUCER", f"  🎥 Rendering {duration:.1f}s final export (High Quality)...")
            final_clip.write_videofile(
                output_path,
                fps=24,
                codec="libx264",
                audio_codec="aac",
                bitrate="12M",
                preset="slower",
                audio_bitrate="320k",
                logger=None # Suppress moviepy internal log
            )
            
            # Cleanup
            final_clip.close()
            main_clip.close()
            
            log("PRODUCER", f"  ✅ Production complete: {output_path}")
            return output_path

        except Exception as e:
            log("ERROR", f"Post-production failed: {e}")
            return None

    def concatenate_segments(self, segment_paths: List[str], output_filename: str) -> Optional[str]:
        """Stitches multiple video segments into a single long-form production."""
        if not _HAS_MOVIEPY:
            log("ERROR", "Cannot concatenate: moviepy not installed.")
            return None

        from moviepy.video.compositing.concatenate import concatenate_videoclips
        
        output_path = os.path.join(self.output_dir, output_filename)
        log("PRODUCER", f"🧵 Stitching {len(segment_paths)} segments into {output_filename}...")
        
        try:
            clips = [VideoFileClip(p) for p in segment_paths if os.path.exists(p)]
            if not clips:
                log("ERROR", "No valid segments found to concatenate.")
                return None
                
            final_clip = concatenate_videoclips(clips, method="compose")
            
            log("PRODUCER", f"  🎥 Rendering {final_clip.duration:.1f}s full production (High Quality)...")
            final_clip.write_videofile(
                output_path,
                fps=24,
                codec="libx264",
                audio_codec="aac",
                bitrate="12M",
                preset="slower",
                audio_bitrate="320k",
                logger=None
            )
            
            # Cleanup
            for c in clips: c.close()
            final_clip.close()
            
            return output_path
        except Exception as e:
            log("ERROR", f"Concatenation failed: {e}")
            return None

if __name__ == "__main__":
    print("✓ Media Post-Processor Module Loaded")
