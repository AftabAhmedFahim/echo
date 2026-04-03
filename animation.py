import pygame


class AnimationClip:
    def __init__(self, frames: list[pygame.Surface], fps: float = 8.0, loop: bool = True):
        self.frames = frames
        self.fps = fps
        self.loop = loop

    def get_frame(self, time_seconds: float) -> pygame.Surface:
        if not self.frames:
            raise ValueError("AnimationClip must contain at least one frame.")

        frame_count = len(self.frames)
        if frame_count == 1 or self.fps <= 0:
            return self.frames[0]

        frame_index = int(time_seconds * self.fps)
        if self.loop:
            frame_index %= frame_count
        else:
            frame_index = min(frame_count - 1, frame_index)
        return self.frames[frame_index]


class Animator:
    def __init__(self, clips: dict[str, AnimationClip], initial_state: str = "idle"):
        if not clips:
            raise ValueError("Animator requires at least one animation clip.")

        self.clips = clips
        self.state = initial_state if initial_state in clips else next(iter(clips))
        self.time_in_state = 0.0

    def set_state(self, state: str, restart: bool = False) -> None:
        if state not in self.clips:
            return
        if state != self.state:
            self.state = state
            self.time_in_state = 0.0
        elif restart:
            self.time_in_state = 0.0

    def update(self, dt: float) -> None:
        self.time_in_state += dt

    def get_frame(self) -> pygame.Surface:
        return self.clips[self.state].get_frame(self.time_in_state)
