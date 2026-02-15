from manim import FadeIn, FadeOut, AnimationGroup

class Animation:
    def __init__(self, scenes):
        self.scenes = scenes

    def generate_animation(self):
        try:
            animations = []
            for scene in self.scenes:
                animations.append(self.create_scene_animation(scene))
            return animations
        except Exception as e:
            print(f"Error generating animation: {str(e)}")
            return []

    def create_scene_animation(self, scene):
        try:
            animation_group = AnimationGroup(
                FadeIn(scene),
                FadeOut(scene)
            )
            return animation_group
        except Exception as e:
            print(f"Error creating scene animation: {str(e)}")
            return None