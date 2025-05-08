"""
AcFun video downloader module.
Handles downloading videos from AcFun.
"""
import os
import re
import json
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple
import requests
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor
from .models import Vid
from .extractor import AcFunExtractor

class AcFunDownloader:
    """Downloads videos from AcFun."""
    
    def __init__(self, output_dir: str = "./downloads", max_workers: int = 4):
        """Initialize the downloader.
        
        Args:
            output_dir: Directory to save downloaded videos.
            max_workers: Maximum number of concurrent download workers.
        """
        self.output_dir = output_dir
        self.max_workers = max_workers
        self.extractor = AcFunExtractor()
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
    
    def download_video(self, vid: Union[str, Vid], quality: str = "720p") -> bool:
        """Download a video by its ID.
        
        Args:
            vid: The video ID (without 'ac' prefix).
            quality: Video quality, one of "1080p", "720p", "480p", "360p".
            
        Returns:
            True if download was successful, False otherwise.
        """
        if isinstance(vid, Vid):
            vid_str = vid.value
        else:
            vid_str = str(vid)
        
        # Get video info
        video_info = self.extractor.get_video_info(vid_str)
        if not video_info:
            print(f"无法获取视频信息: ac{vid_str}")
            return False
        
        # Check if video has multiple parts
        if video_info["has_multi_p"]:
            print(f"视频 {video_info['title']} 包含多个分P, 正在下载所有分P...")
            part_list = self.extractor.get_multi_p_info(vid_str)
            
            # Download each part
            success = True
            for i, part in enumerate(part_list):
                print(f"正在下载第 {i+1}/{len(part_list)} P: {part['title']}")
                part_url = part["url"]
                part_vid_match = re.search(r"ac(\d+)", part_url)
                if part_vid_match:
                    part_vid = part_vid_match.group(1)
                    # Create part title based on video title and part index
                    part_filename = f"{video_info['title']}_p{i+1}_{part['title']}"
                    part_success = self._download_single_video(part_vid, part_filename, quality)
                    success = success and part_success
                else:
                    print(f"无法从URL {part_url} 解析视频ID")
                    success = False
            
            return success
        else:
            # Single video download
            return self._download_single_video(vid_str, video_info["title"], quality)
    
    def _download_single_video(self, vid: str, title: str, quality: str = "720p") -> bool:
        """Download a single video.
        
        Args:
            vid: The video ID (without 'ac' prefix).
            title: Video title used for filename.
            quality: Video quality, one of "1080p", "720p", "480p", "360p".
            
        Returns:
            True if download was successful, False otherwise.
        """
        # Get video streams
        streams = self._get_video_streams(vid)
        if not streams:
            print(f"无法获取视频流信息: ac{vid}")
            return False
        
        # Select quality
        selected_stream = None
        qualities = ["1080p", "720p", "480p", "360p"]
        
        # Try to find the requested quality or fallback to the nearest available quality
        quality_idx = qualities.index(quality) if quality in qualities else 1  # Default to 720p index
        
        # Try to find the requested quality or fall back to lower qualities
        for q_idx in range(quality_idx, len(qualities)):
            q = qualities[q_idx]
            if q in streams:
                selected_stream = streams[q]
                if q != quality:
                    print(f"请求的质量 {quality} 不可用，使用 {q} 替代")
                break
        
        # If not found, try higher qualities
        if not selected_stream and quality_idx > 0:
            for q_idx in range(quality_idx - 1, -1, -1):
                q = qualities[q_idx]
                if q in streams:
                    selected_stream = streams[q]
                    print(f"请求的质量 {quality} 不可用，使用 {q} 替代")
                    break
        
        if not selected_stream:
            print(f"没有可用的视频流")
            return False
        
        # Sanitize title for filename
        safe_title = re.sub(r'[<>:"/\\|?*]', '_', title)
        output_filename = os.path.join(self.output_dir, f"{safe_title}.mp4")
        
        # Download video and audio in parallel and merge them
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            video_future = executor.submit(self._download_stream, selected_stream["video"], "video")
            audio_future = executor.submit(self._download_stream, selected_stream["audio"], "audio")
            
            video_path = video_future.result()
            audio_path = audio_future.result()
            
            if not video_path or not audio_path:
                print("下载视频或音频流失败")
                return False
            
            # Merge video and audio
            try:
                # Check if ffmpeg is available
                try:
                    subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True)
                except (subprocess.SubprocessError, FileNotFoundError):
                    print("警告: ffmpeg 未安装，无法合并视频和音频。保存分离的文件。")
                    video_output = os.path.join(self.output_dir, f"{safe_title}_video.mp4")
                    audio_output = os.path.join(self.output_dir, f"{safe_title}_audio.m4a")
                    os.rename(video_path, video_output)
                    os.rename(audio_path, audio_output)
                    print(f"视频保存至: {video_output}")
                    print(f"音频保存至: {audio_output}")
                    return True
                
                print("正在合并视频和音频...")
                cmd = [
                    "ffmpeg", "-i", video_path, "-i", audio_path,
                    "-c:v", "copy", "-c:a", "aac", "-strict", "experimental",
                    output_filename
                ]
                subprocess.run(cmd, check=True, capture_output=True)
                
                # Remove temporary files
                os.remove(video_path)
                os.remove(audio_path)
                
                print(f"下载完成: {output_filename}")
                return True
                
            except Exception as e:
                print(f"合并视频和音频失败: {e}")
                return False
    
    def _get_video_streams(self, vid: str) -> Optional[Dict]:
        """Get video streams by video ID.
        
        Args:
            vid: The video ID (without 'ac' prefix).
            
        Returns:
            Dictionary of available video streams by quality.
        """
        # This is a simplified implementation
        # In a real implementation, you would need to extract the actual m3u8 URLs
        # from the AcFun website, which might require additional reverse engineering
        
        video_url = f"https://www.acfun.cn/v/ac{vid}"
        headers = {
            "Referer": "https://www.acfun.cn/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0",
        }
        
        try:
            response = requests.get(video_url, headers=headers)
            response.raise_for_status()
            html_content = response.text
            
            # Look for the videoInfo JSON in the HTML
            # This is a simplified approach and might need adjustment based on actual site structure
            video_info_match = re.search(r'window.videoInfo\s*=\s*({.+?});', html_content, re.DOTALL)
            if not video_info_match:
                print("无法在页面中找到视频信息")
                return None
            
            video_info_str = video_info_match.group(1)
            video_info = json.loads(video_info_str)
            
            # Process video streams
            # This is a placeholder - actual implementation would depend on AcFun's structure
            streams = {
                # Example structure, actual implementation would extract real URLs
                "720p": {
                    "video": f"https://example.com/video/{vid}_720p.m3u8",
                    "audio": f"https://example.com/audio/{vid}.m3u8"
                },
                "480p": {
                    "video": f"https://example.com/video/{vid}_480p.m3u8",
                    "audio": f"https://example.com/audio/{vid}.m3u8"
                }
            }
            
            return streams
            
        except Exception as e:
            print(f"获取视频流失败: {e}")
            return None
    
    def _download_stream(self, url: str, stream_type: str) -> Optional[str]:
        """Download a video or audio stream.
        
        Args:
            url: The stream URL.
            stream_type: "video" or "audio".
            
        Returns:
            Path to the downloaded file or None if download failed.
        """
        # This is a simplified implementation
        # In a real implementation, you would need to handle m3u8 playlists
        # and download all segments
        
        try:
            temp_file = os.path.join(self.output_dir, f"temp_{stream_type}_{os.urandom(4).hex()}")
            
            with requests.get(url, stream=True) as response:
                response.raise_for_status()
                total_size = int(response.headers.get("content-length", 0))
                block_size = 8192
                
                with open(temp_file, "wb") as f, tqdm(
                    desc=f"下载{stream_type}",
                    total=total_size,
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                ) as progress:
                    for chunk in response.iter_content(chunk_size=block_size):
                        if chunk:
                            f.write(chunk)
                            progress.update(len(chunk))
            
            return temp_file
            
        except Exception as e:
            print(f"下载{stream_type}流失败: {e}")
            return None
    
    def download_up_videos(self, uid: Union[str, Vid], max_videos: int = None, quality: str = "720p") -> int:
        """Download videos from an UP user.
        
        Args:
            uid: The UP user ID.
            max_videos: Maximum number of videos to download (None for all).
            quality: Video quality, one of "1080p", "720p", "480p", "360p".
            
        Returns:
            Number of successfully downloaded videos.
        """
        # Get UP videos
        user_info = self.extractor.get_up_videos(uid, fetch_all_pages=True)
        if not user_info:
            print(f"获取UP主 {uid} 的视频列表失败")
            return 0
        
        videos = user_info["videos"]
        if max_videos:
            videos = videos[:max_videos]
        
        print(f"UP主: {user_info['user']}, 准备下载 {len(videos)} 个视频")
        
        # Download each video
        successful = 0
        for i, video in enumerate(videos):
            print(f"\n[{i+1}/{len(videos)}] 下载视频: {video['title']}")
            if self.download_video(video["vid"], quality):
                successful += 1
            
            # Small delay between downloads
            if i < len(videos) - 1:
                print("短暂休息...")
                import time
                time.sleep(1)
        
        print(f"\n下载完成! 成功: {successful}/{len(videos)}")
        return successful