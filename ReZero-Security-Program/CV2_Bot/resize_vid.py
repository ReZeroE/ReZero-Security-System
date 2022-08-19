from moviepy.editor import *
import os

def resize_video(video_full_path, target_size_mb=7.5):
    starting_width = 300
    starting_height = 300

    file_size = os.path.getsize(video_full_path)
    if float(file_size / (1024 * 1024)) < target_size_mb:
        return video_full_path

    print(f"size: {float(file_size / (1024 * 1024))}mb, resizing")
    clip = VideoFileClip(video_full_path)
    print(f"trimming to: {starting_width}")
    final = clip.fx(vfx.resize, width = starting_width, height = starting_height)

    out_filename = os.path.join(os.path.dirname(os.path.dirname(__file__)), "recordings\\out.mp4")
    final.write_videofile(out_filename, verbose=False, logger=None)
    return out_filename
            

if __name__ == '__main__':
    file_name = resize_video('********.mp4', 2)
    print(file_name)
