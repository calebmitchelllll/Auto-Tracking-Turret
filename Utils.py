import time

def print_fps(prev_time):
    now = time.time()
    fps = 1.0 / (now - prev_time)

    print("\033[2K\r" + f"[FPS] {fps:6.1f}")

    return now