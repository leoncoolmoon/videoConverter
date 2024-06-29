import os
import sys
import subprocess
import json
import re
#import time
from datetime import timedelta

def format_duration_explicit(seconds):
    hours, remainder = divmod(int(seconds), 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"

def get_video_duration(input_file):
    try:
        command = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            input_file
        ]
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
        duration = float(result.stdout)
        return duration
    except:
        print("警告: 无法获取视频时长")
        return None

def get_video_info(input_file):
    try:
        command = [
            'ffprobe',
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            '-show_streams',
            input_file
        ]
        result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', errors='replace')
        
        if not result.stdout:
            print("警告: ffprobe 没有返回任何输出")
            return None, None

        info = json.loads(result.stdout)
        video_stream = next((stream for stream in info['streams'] if stream['codec_type'] == 'video'), None)
        if video_stream:
            width = int(video_stream['width'])
            height = int(video_stream['height'])
            return width, height
        else:
            print("警告: 未找到视频流信息")
    except Exception as e:
        print(f"获取视频信息时发生错误: {e}")
    return None, None

def convert_rmvb_to_mpg(input_file):
    if not os.path.exists(input_file):
        print(f"错误: 输入文件 '{input_file}' 不存在。")
        return

    input_dir, input_filename = os.path.split(input_file)
    output_filename = os.path.splitext(input_filename)[0] + '.mpg'
    output_file = os.path.join(input_dir, output_filename)

    width, height = get_video_info(input_file)
    print(f"video wxh: {width} x {height}")
    if width is None or height is None:
        print("无法获取视频信息，将使用默认设置。")
        width, height = 720, 480  # 默认分辨率
    
    aspect_ratio = f"{width}:{height}"
    duration = get_video_duration(input_file)
    if duration is not None:
        formatted_duration = format_duration_explicit(duration)
        print(f"video duration: {formatted_duration}")


    try:
        command = [
            'ffmpeg',
            '-i', input_file,
            '-c:v', 'mpeg2video',
            '-q:v', '3',
            '-c:a', 'mp2',
            '-b:a', '192k',
            '-aspect', aspect_ratio,
            '-vf', f'scale={width}:{height}',
            '-f', 'mpegts',
            '-progress', 'pipe:1',
            output_file
        ]
        print("开始转换...\n")
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                   universal_newlines=True, encoding='utf-8', errors='replace')
        #start_time = time.time()
        pattern = re.compile(r"out_time_ms=(\d+)")
        try:
            while True:
                line = process.stdout.readline()
                if not line:
                    break
                matches = pattern.search(line)
                if matches:
                    time_ms = int(matches.group(1))
                    if duration:
                        progress = min(time_ms / (duration * 1000000) * 100, 100)
                        print(f"\r转换进度: {progress:.2f}%", end='', flush=True)
                    else:
                        current_time = str(timedelta(microseconds=time_ms))
                        print(f"\r当前转换时间: {current_time}", end='', flush=True)
        finally:
            #elapsed_time = time.time() - start_time
            #print(f"\r转换用时: {timedelta(seconds=int(elapsed_time))}")
            process.stdout.close()
            process.wait()

        print()  # 换行
        
        if process.returncode != 0:
            print(f"转换失败。FFmpeg 返回非零退出码: {process.returncode}")
        else:
            print(f"转换成功: '{input_file}' 已转换为 '{output_file}'")
    except FileNotFoundError:
        print("错误: FFmpeg 未安装或未在系统路径中。请安装 FFmpeg 并确保它在系统路径中。")
    except Exception as e:
        print(f"转换过程中发生未知错误: {e}")
        print("错误详情:")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("使用方法: python script.py <input_rmvb_file>")
        sys.exit(1)
    
    # 确保命令行参数使用正确的编码
    if sys.platform == 'win32':
        sys.argv = [arg.encode('utf-8').decode(sys.getfilesystemencoding()) for arg in sys.argv]
    
    input_file = sys.argv[1]
    convert_rmvb_to_mpg(input_file)
