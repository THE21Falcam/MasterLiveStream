# RTMP STREAMING
# GET https://ingest.twitch.tv/ingests
# rtmp://<ingest-server>/app/<stream-key>[?bandwidthtest=true]
# https://trac.ffmpeg.org/wiki/EncodingForStreamingSites

# Pygame Video Data To Flie

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

# Load sound once
sound = pygame.mixer.Sound("music.wav")
raw = pygame.sndarray.array(sound)  # int16, shape (N, 2)
raw_float = raw.astype(np.float32) / 32768.0  # normalize to float32
raw_float = np.ascontiguousarray(raw_float.T)  # shape (2, N), C-contiguous

SAMPLE_RATE = 44100
FRAME_SAMPLES = 1024
AUDIO_PTS = 0
VIDEO_PTS = 0
audio_pos = 0

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
        end_pos = audio_pos + FRAME_SAMPLES
        if end_pos > raw_float.shape[1]:
            audio_pos = 0
            end_pos = FRAME_SAMPLES

        chunk = np.ascontiguousarray(raw_float[:, audio_pos:end_pos])
        audio_frame = av.AudioFrame.from_ndarray(chunk, format="fltp", layout="stereo")
        audio_frame.sample_rate = SAMPLE_RATE
        audio_frame.pts = AUDIO_PTS
        AUDIO_PTS += chunk.shape[1]
        audio_pos = end_pos

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
