import os
import re
import subprocess
import argparse
from pathlib import Path
from tqdm import tqdm
from src.extractor import AcFunExtractor
from src.models import Vid


def sanitize_filename(filename):
    """移除文件名中不允许的字符"""
    # 替换Windows文件系统不允许的字符
    return re.sub(r'[<>:"/\\|?*]', '_', filename)


def download_video(video_url, output_path, title=None):
    """使用yt-dlp下载单个视频"""
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "-o", output_path,
        video_url
    ]
    
    print(f"正在下载: {title or video_url}")
    # 使用subprocess.Popen代替run，以实时显示输出
    process = subprocess.Popen(
        cmd, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True
    )
    
    # 实时读取并打印输出
    for line in process.stdout:
        print(line, end='')
    
    process.wait()
    
    if process.returncode != 0:
        print(f"下载失败，返回码: {process.returncode}")
        return False
    return True


def download_videos_from_up(uid, output_dir="./downloads", max_videos=None):
    """批量下载某UP主的所有视频"""
    extractor = AcFunExtractor(use_random_ua=False)
    
    print(f"正在获取UP主(UID:{uid})的视频列表...")
    videos = extractor.get_up_videos(uid, fetch_all_pages=True)
    
    if not videos:
        print("未找到视频或获取视频列表失败")
        return
    
    # 创建基本下载目录
    downloads_dir = Path(output_dir)
    downloads_dir.mkdir(exist_ok=True, parents=True)
    
    # 限制下载数量
    if max_videos is not None:
        videos = videos[:max_videos]
    
    print(f"找到 {len(videos)} 个视频，准备下载")
    
    # 使用tqdm创建总进度条
    with tqdm(total=len(videos), desc="总进度", unit="视频") as pbar:
        for idx, video in enumerate(videos):
            vid = video['vid'].value
            title = video['title']
            safe_title = sanitize_filename(title)
            
            print(f"\n[{idx+1}/{len(videos)}] 处理视频: {title}")
            
            # 获取视频分P信息
            multi_part_info = extractor.get_multi_p_info(vid)
            
            if multi_part_info.has_multi_part and len(multi_part_info.part_list) > 0:
                # 多P视频处理
                print(f"视频 {title} 有 {len(multi_part_info.part_list)} 个分P")
                
                # 为多P视频创建单独文件夹
                video_dir = downloads_dir / safe_title
                video_dir.mkdir(exist_ok=True)
                
                # 下载每个分P
                for part_idx, part in enumerate(multi_part_info.part_list):
                    part_title = part.title
                    part_vid = part.vid.value
                    safe_part_title = sanitize_filename(part_title)
                    
                    # 构建输出路径
                    output_path = str(video_dir / f"{safe_part_title}.%(ext)s")
                    
                    # 构建分P视频URL
                    video_url = f"https://www.acfun.cn/v/ac{part_vid}"
                    
                    print(f"  下载分P {part_idx+1}/{len(multi_part_info.part_list)}: {part_title}")
                    success = download_video(video_url, output_path, title=part_title)
                    
                    if not success:
                        print(f"  分P {part_title} 下载失败，跳过")
            else:
                # 单P视频处理
                print(f"视频 {title} 是单P视频")
                
                # 构建输出路径
                output_path = str(downloads_dir / f"{safe_title}.%(ext)s")
                
                # 构建视频URL
                video_url = f"https://www.acfun.cn/v/ac{vid}"
                
                success = download_video(video_url, output_path, title=title)
                
                if not success:
                    print(f"视频 {title} 下载失败，跳过")
            
            pbar.update(1)
    
    print("\n下载完成!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="批量下载AcFun UP主视频")
    parser.add_argument("uid", type=str, help="UP主的UID")
    parser.add_argument("--output", "-o", type=str, default="./downloads", 
                        help="下载目录 (默认: ./downloads)")
    parser.add_argument("--max", "-m", type=int, default=None,
                        help="最大下载视频数 (默认: 全部)")
    
    args = parser.parse_args()
    
    download_videos_from_up(args.uid, args.output, args.max)