# RTMP STREAMING
# GET https://ingest.twitch.tv/ingests
# rtmp://<ingest-server>/app/<stream-key>[?bandwidthtest=true]
# https://trac.ffmpeg.org/wiki/EncodingForStreamingSites

# Pygame Video Data To Flie

from configparser import ConfigParser

import av
import numpy as np
import pygame

filepath = "Config.ini"
config = ConfigParser()
config.read(filepath)

WIDTH, HEIGHT = 1280, 720
FPS = 60
STREAM_KEY = config["TWITCH_STREAM"]["STREAM_KEY"]
TWITCH_URL = config["TWITCH_STREAM"]["TWITCH_URL"]

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

pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()

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

        pygame.display.flip()
        clock.tick(FPS)

except KeyboardInterrupt:
    pass

finally:
    for packet in video_stream.encode():
        output.mux(packet)

    output.close()
    pygame.quit()
