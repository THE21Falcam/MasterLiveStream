import os.path
from configparser import ConfigParser

import av
import numpy as np
import pygame

filepath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../Config.ini")
config = ConfigParser()
config.read(filepath)

WIDTH, HEIGHT = 1280, 720
FPS = 60
STREAM_KEY = config["STREAM"]["STREAM_KEY"]
TWITCH_URL = config["STREAM"]["TWITCH_URL"]

output = av.open(f"{TWITCH_URL}{STREAM_KEY}", mode="w", format="flv")

video_stream = output.add_stream("libx264", rate=FPS)
video_stream.width = WIDTH
video_stream.height = HEIGHT
video_stream.pix_fmt = "yuv420p"
video_stream.options = {
    "preset": "veryfast",
    "tune": "zerolatency",
    "profile": "baseline",
    "g": str(FPS * 2),
}

audio_stream = output.add_stream("aac", rate=44100)
audio_stream.layout = "stereo"

pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=1024)
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

SAMPLE_RATE = 44100
FRAME_SAMPLES = 1024


def load_audio(filepath):
    """Load a WAV file and return a normalized float32 planar array (2, N)."""
    sound = pygame.mixer.Sound(filepath)
    raw = pygame.sndarray.array(sound)  # int16, shape (N, 2)
    raw_float = raw.astype(np.float32) / 32768.0  # normalize
    return np.ascontiguousarray(raw_float.T)  # shape (2, N)


def mix_tracks(tracks, positions, num_samples):
    """
    Mix multiple audio tracks together at their current positions.
    Loops each track when it reaches the end.
    Returns a mixed C-contiguous float32 array of shape (2, num_samples).
    """
    mixed = np.zeros((2, num_samples), dtype=np.float32)

    for i, track in enumerate(tracks):
        track_len = track.shape[1]
        pos = positions[i]
        end = pos + num_samples

        if end <= track_len:
            chunk = track[:, pos:end]
        else:
            # Loop: take what's left, then wrap from the beginning
            first_part = track[:, pos:]
            remaining = num_samples - first_part.shape[1]
            second_part = track[:, :remaining]
            chunk = np.concatenate([first_part, second_part], axis=1)
            positions[i] = remaining  # update wrapped position

        if end <= track_len:
            positions[i] = end

        mixed += chunk

    # Clamp to [-1, 1] to prevent clipping from mixing
    np.clip(mixed, -1.0, 1.0, out=mixed)
    return np.ascontiguousarray(mixed)


# --- Load your audio tracks here ---
AUDIO_FILES = [
    "music.wav",
    "sfx.wav",
    "ambience.wav",
    # Add as many as you need
]

tracks = [load_audio(f) for f in AUDIO_FILES]
positions = [0] * len(tracks)  # playback position per track

# Per-track volume controls (0.0 to 1.0)
volumes = [1.0, 0.8, 0.5]  # adjust to match number of tracks

# Apply volumes
tracks = [track * vol for track, vol in zip(tracks, volumes)]

AUDIO_PTS = 0
VIDEO_PTS = 0

try:
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                raise KeyboardInterrupt

        # --- DRAW ---
        screen.fill((20, 20, 30))
        pygame.draw.rect(screen, (0, 200, 255), (400, 300, 480, 120))

        # --- VIDEO ---
        frame = pygame.surfarray.array3d(screen)
        frame = np.ascontiguousarray(np.transpose(frame, (1, 0, 2)))
        video_frame = av.VideoFrame.from_ndarray(frame, format="rgb24")
        video_frame = video_frame.reformat(WIDTH, HEIGHT, format="yuv420p")
        video_frame.pts = VIDEO_PTS
        VIDEO_PTS += 1
        for packet in video_stream.encode(video_frame):
            output.mux(packet)

        # --- AUDIO ---
        mixed_chunk = mix_tracks(tracks, positions, FRAME_SAMPLES)
        audio_frame = av.AudioFrame.from_ndarray(
            mixed_chunk, format="fltp", layout="stereo"
        )
        audio_frame.sample_rate = SAMPLE_RATE
        audio_frame.pts = AUDIO_PTS
        AUDIO_PTS += FRAME_SAMPLES

        for packet in audio_stream.encode(audio_frame):
            output.mux(packet)

        pygame.display.flip()
        clock.tick(FPS)

except KeyboardInterrupt:
    pass

finally:
    for packet in video_stream.encode():
        output.mux(packet)
    for packet in audio_stream.encode():
        output.mux(packet)
    output.close()
    pygame.quit()
