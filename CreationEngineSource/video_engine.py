import os
import json
import time
import requests
from typing import List, Dict, Any
from moviepy.editor import ImageClip, concatenate_videoclips, CompositeVideoClip
from openai import OpenAI

class FrostVideoEngine:
    """
    Transforms text prompts into cinematic video sequences autonomously.
    """
    def __init__(self, output_dir: str, api_key: str = None):
        self.output_dir = output_dir
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        os.makedirs(output_dir, exist_ok=True)

    def generate_scene_descriptions(self, prompt: str) -> List[Dict[str, str]]:
        """
        Calls LLM to expand the prompt into a sequence of 3 visual scenes.
        """
        if not self.client:
            raise ValueError("OpenAI API Key required for scene generation.")

        response = self.client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "system", 
                "content": "You are a cinematic director. Break the prompt into exactly 3 visual scenes. Return ONLY a JSON array of objects with 'title' and 'visual_description' (for DALL-E) fields."
            }, {"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        
        data = json.loads(response.choices[0].message.content)
        # Handle different potential JSON structures from the model
        if "scenes" in data: return data["scenes"]
        if isinstance(data, list): return data
        return [data]

    def generate_images_for_scenes(self, scenes: List[Dict[str, str]]) -> List[str]:
        """
        Calls DALL-E to generate images for each scene.
        """
        if not self.client:
            raise ValueError("OpenAI API Key required for image generation.")

        image_paths = []
        for i, scene in enumerate(scenes):
            print(f"[FROST] Generating image for scene {i+1}: {scene['title']}...")
            response = self.client.images.generate(
                model="dall-e-3",
                prompt=f"{scene['visual_description']} Cinematic, high-quality, 16:9 aspect ratio.",
                size="1024x1792", # DALL-E 3 Vertical for mobile or 1792x1024 for horizontal
                quality="hd",
                n=1,
            )
            
            image_url = response.data[0].url
            img_data = requests.get(image_url).content
            path = os.path.join(self.output_dir, f"scene_{i+1}.png")
            with open(path, 'wb') as f:
                f.write(img_data)
            image_paths.append(path)
            
        return image_paths

    def create_motion_clip(self, image_path: str, duration: float = 4.0, motion_type: str = "zoom_in") -> Any:
        """
        Applies cinematic motion (zoom/pan) to a static image.
        Uses a sliding crop window to simulate camera movement.
        """
        clip = ImageClip(image_path).set_duration(duration)
        w, h = clip.size
        
        if motion_type == "zoom_in":
            # Start at 1.0x, end at 1.2x
            return clip.resize(lambda t: 1.0 + 0.2 * (t/duration)).set_position('center')
            
        elif motion_type == "pan_right":
            # Subtle pan from left to right
            # We need a slightly larger canvas or just shift the position
            return clip.set_position(lambda t: (int(-50 + 100 * (t/duration)), 'center'))

        elif motion_type == "zoom_out":
            # Start at 1.2x, end at 1.0x
            return clip.resize(lambda t: 1.2 - 0.2 * (t/duration)).set_position('center')
            
        return clip

    def assemble_video(self, scene_images: List[str], output_filename: str = "frost_render.mp4"):
        """
        Combines multiple motion clips into a final video.
        """
        clips = []
        motions = ["zoom_in", "pan_right", "zoom_out"]
        
        for i, img_path in enumerate(scene_images):
            motion = motions[i % len(motions)]
            clips.append(self.create_motion_clip(img_path, motion_type=motion))
            
        final_video = concatenate_videoclips(clips, method="compose")
        target_path = os.path.join(self.output_dir, output_filename)
        final_video.write_videofile(target_path, fps=24, codec='libx264')
        return target_path

if __name__ == "__main__":
    engine = FrostVideoEngine("./test_outputs")
    print("Engine initialized.")
