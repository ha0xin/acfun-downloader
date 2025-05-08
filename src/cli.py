"""
Command-line interface for AcFun video downloader.
"""
import argparse
import sys
import os
from typing import List, Optional
from .extractor import AcFunExtractor
from .downloader import AcFunDownloader
from .models import Vid, Uid

def parse_arguments(args: Optional[List[str]] = None) -> argparse.Namespace:
    """Parse command line arguments.
    
    Args:
        args: Command line arguments (uses sys.argv if None).
        
    Returns:
        Parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="AcFun视频下载工具",
        epilog="示例：\n"
               "下载单个视频: acfun-dl video 12345678\n"
               "下载UP主的视频: acfun-dl up 12345678 --max 5\n"
               "设置视频质量: acfun-dl video 12345678 --quality 1080p",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Set common arguments
    parser.add_argument("--output", "-o", type=str, default="./downloads",
                        help="下载目录 (默认: ./downloads)")
    parser.add_argument("--quality", "-q", type=str, choices=["1080p", "720p", "480p", "360p"],
                        default="720p", help="视频质量 (默认: 720p)")
    
    # Set subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # Video download command
    video_parser = subparsers.add_parser("video", help="下载单个视频")
    video_parser.add_argument("vid", type=str, help="视频ID (不含ac前缀)")
    
    # UP videos download command
    up_parser = subparsers.add_parser("up", help="下载UP主的视频")
    up_parser.add_argument("uid", type=str, help="UP主用户ID")
    up_parser.add_argument("--max", type=int, default=None, 
                          help="最多下载的视频数量 (默认: 全部)")
    up_parser.add_argument("--all-pages", action="store_true",
                          help="获取所有页面的视频 (可能较慢)")
    
    # Info command (just displays info without downloading)
    info_parser = subparsers.add_parser("info", help="获取视频信息 (不下载)")
    info_parser.add_argument("vid", type=str, help="视频ID (不含ac前缀)")
    
    # Parse arguments
    parsed_args = parser.parse_args(args)
    
    # Validate that a command was provided
    if not parsed_args.command:
        parser.print_help()
        sys.exit(1)
    
    return parsed_args

def main(args: Optional[List[str]] = None) -> int:
    """Main entry point for CLI.
    
    Args:
        args: Command line arguments (uses sys.argv if None).
        
    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parsed_args = parse_arguments(args)
    
    # Create output directory if it doesn't exist
    os.makedirs(parsed_args.output, exist_ok=True)
    
    # Create downloader
    downloader = AcFunDownloader(output_dir=parsed_args.output)
    
    # Execute command
    if parsed_args.command == "video":
        print(f"下载视频 ac{parsed_args.vid} (质量: {parsed_args.quality})...")
        success = downloader.download_video(parsed_args.vid, quality=parsed_args.quality)
        return 0 if success else 1
    
    elif parsed_args.command == "up":
        print(f"下载UP主 {parsed_args.uid} 的视频 (质量: {parsed_args.quality})...")
        successful_count = downloader.download_up_videos(
            parsed_args.uid,
            max_videos=parsed_args.max,
            quality=parsed_args.quality
        )
        return 0 if successful_count > 0 else 1
    
    elif parsed_args.command == "info":
        extractor = AcFunExtractor()
        video_info = extractor.get_video_info(parsed_args.vid)
        
        if not video_info:
            print(f"无法获取视频信息: ac{parsed_args.vid}")
            return 1
        
        print(f"标题: {video_info['title']}")
        print(f"UP主: {video_info['uploader'].name} (UID: {video_info['uploader'].uid})")
        print(f"上传时间: {video_info['upload_date'].strftime('%Y-%m-%d %H:%M:%S')}")
        
        if video_info["has_multi_p"]:
            print(f"分P视频，共 {len(video_info['multi_p'])} P")
            part_list = extractor.get_multi_p_info(parsed_args.vid)
            for i, part in enumerate(part_list):
                print(f"  P{i+1}: {part['title']}")
        else:
            print("单P视频")
        
        return 0
    
    return 0

if __name__ == "__main__":
    sys.exit(main())