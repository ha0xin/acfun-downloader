"""
Tests for the AcFun downloader module.
"""
import unittest
from unittest.mock import patch, MagicMock, mock_open
import os
import json
from datetime import datetime
import requests
import subprocess
from io import BytesIO
from tqdm import tqdm

from src.downloader import AcFunDownloader
from src.models import Vid, Uid, Uploader, VideoMetadata

class TestAcFunDownloader(unittest.TestCase):
    """Test cases for AcFunDownloader."""
    
    def setUp(self):
        """Set up test environment."""
        # Create downloader with a test directory
        self.test_output_dir = "./test_downloads"
        self.downloader = AcFunDownloader(output_dir=self.test_output_dir)
        
        # Ensure test directory exists
        os.makedirs(self.test_output_dir, exist_ok=True)
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove test directory if it exists
        if os.path.exists(self.test_output_dir):
            # In a real implementation, we would remove files and directory
            # Here we'll just skip this to avoid file system operations in tests
            pass
    
    @patch("src.downloader.AcFunDownloader._download_single_video")
    @patch("src.downloader.AcFunExtractor.get_video_info")
    def test_download_video_single_part(self, mock_get_info, mock_download_single):
        """Test downloading a single-part video."""
        # Mock video info
        mock_video_info = VideoMetadata(
            vid=Vid("12345"),
            title="测试视频",
            cover_url="https://example.com/cover.jpg",
            uploader=Uploader(uid=Uid("9876"), name="测试UP主"),
            upload_date=datetime.now(),
            has_multi_p=False,
            multi_p=[]
        )
        mock_get_info.return_value = mock_video_info
        
        # Mock successful download
        mock_download_single.return_value = True
        
        # Call the method
        result = self.downloader.download_video("12345")
        
        # Check results
        self.assertTrue(result)
        mock_get_info.assert_called_once_with("12345")
        mock_download_single.assert_called_once_with("12345", "测试视频", "720p")
    
    @patch("src.downloader.AcFunDownloader._download_single_video")
    @patch("src.downloader.AcFunExtractor.get_multi_p_info")
    @patch("src.downloader.AcFunExtractor.get_video_info")
    def test_download_video_multi_part(self, mock_get_info, mock_get_multi_p, mock_download_single):
        """Test downloading a multi-part video."""
        # Mock video info
        mock_video_info = VideoMetadata(
            vid=Vid("12345"),
            title="测试多P视频",
            cover_url="https://example.com/cover.jpg",
            uploader=Uploader(uid=Uid("9876"), name="测试UP主"),
            upload_date=datetime.now(),
            has_multi_p=True,
            multi_p=[Vid("12345_1"), Vid("12345_2")]
        )
        mock_get_info.return_value = mock_video_info
        
        # Mock multi-part info
        mock_get_multi_p.return_value = [
            {"title": "第一集", "url": "https://www.acfun.cn/v/ac12345_1"},
            {"title": "第二集", "url": "https://www.acfun.cn/v/ac12345_2"}
        ]
        
        # Mock successful downloads
        mock_download_single.return_value = True
        
        # Call the method
        result = self.downloader.download_video("12345")
        
        # Check results
        self.assertTrue(result)
        mock_get_info.assert_called_once_with("12345")
        mock_get_multi_p.assert_called_once_with("12345")
        
        # Should be called twice, once for each part
        self.assertEqual(mock_download_single.call_count, 2)
        mock_download_single.assert_any_call("12345_1", "测试多P视频_p1_第一集", "720p")
        mock_download_single.assert_any_call("12345_2", "测试多P视频_p2_第二集", "720p")
    
    @patch("src.downloader.subprocess.run")
    @patch("src.downloader.os.remove")
    @patch("src.downloader.AcFunDownloader._download_stream")
    @patch("src.downloader.AcFunDownloader._get_video_streams")
    def test_download_single_video(self, mock_get_streams, mock_download_stream, 
                               mock_remove, mock_subprocess_run):
        """Test _download_single_video method."""
        # Mock stream info
        mock_get_streams.return_value = {
            "720p": {
                "video": "https://example.com/video_720p.m3u8",
                "audio": "https://example.com/audio.m3u8"
            },
            "480p": {
                "video": "https://example.com/video_480p.m3u8",
                "audio": "https://example.com/audio.m3u8"
            }
        }
        
        # Mock successful downloads
        mock_download_stream.side_effect = [
            os.path.join(self.test_output_dir, "temp_video"),
            os.path.join(self.test_output_dir, "temp_audio")
        ]
        
        # Mock subprocess run
        mock_subprocess_run.return_value.returncode = 0
        
        # Call the method
        result = self.downloader._download_single_video("12345", "测试视频", "720p")
        
        # Check results
        self.assertTrue(result)
        mock_get_streams.assert_called_once_with("12345")
        mock_download_stream.assert_any_call("https://example.com/video_720p.m3u8", "video")
        mock_download_stream.assert_any_call("https://example.com/audio.m3u8", "audio")
        
        # Check ffmpeg command
        mock_subprocess_run.assert_called_once()
        args = mock_subprocess_run.call_args[0][0]
        self.assertEqual(args[0], "ffmpeg")
        
        # Temporary files should be removed
        mock_remove.assert_any_call(os.path.join(self.test_output_dir, "temp_video"))
        mock_remove.assert_any_call(os.path.join(self.test_output_dir, "temp_audio"))
    
    @patch("src.downloader.requests.get")
    def test_get_video_streams(self, mock_get):
        """Test _get_video_streams method."""
        # Mock response with videoInfo
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <script>
                window.videoInfo = {
                    "title": "测试视频",
                    "videoList": [
                        {
                            "id": "1",
                            "quality": "720p",
                            "url": "https://example.com/video_720p.m3u8"
                        },
                        {
                            "id": "2",
                            "quality": "480p",
                            "url": "https://example.com/video_480p.m3u8"
                        }
                    ],
                    "audioUrl": "https://example.com/audio.m3u8"
                };
            </script>
        </html>
        """
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        # Call the method
        result = self.downloader._get_video_streams("12345")
        
        # Check results - this is a placeholder implementation
        self.assertIsNotNone(result)
        self.assertIn("720p", result)
        self.assertIn("480p", result)
    
    @patch("builtins.open", new_callable=mock_open)
    @patch("src.downloader.requests.get")
    def test_download_stream(self, mock_get, mock_file_open):
        """Test _download_stream method."""
        # Mock response
        mock_response = MagicMock()
        mock_response.headers = {"content-length": "1024"}
        mock_response.iter_content.return_value = [b"chunk1", b"chunk2"]
        mock_response.__enter__.return_value = mock_response
        mock_get.return_value = mock_response
        
        # Mock tqdm to avoid visual progress bar
        with patch("src.downloader.tqdm", autospec=True) as mock_tqdm:
            mock_progress = MagicMock()
            mock_tqdm.return_value.__enter__.return_value = mock_progress
            
            # Call the method
            result = self.downloader._download_stream("https://example.com/stream.m3u8", "video")
            
            # Check results
            self.assertIsNotNone(result)
            mock_get.assert_called_once_with("https://example.com/stream.m3u8", stream=True)
            
            # File should be opened for writing
            mock_file_open.assert_called_once()
            self.assertEqual(mock_file_open.call_args[0][1], "wb")
            
            # Content should be written
            mock_file = mock_file_open()
            mock_file.write.assert_any_call(b"chunk1")
            mock_file.write.assert_any_call(b"chunk2")
            
            # Progress should be updated
            mock_progress.update.assert_any_call(len(b"chunk1"))
            mock_progress.update.assert_any_call(len(b"chunk2"))
    
    @patch("src.downloader.AcFunDownloader.download_video")
    @patch("src.downloader.AcFunExtractor.get_up_videos")
    def test_download_up_videos(self, mock_get_up_videos, mock_download_video):
        """Test download_up_videos method."""
        # Mock UP videos
        mock_get_up_videos.return_value = {
            "user": "测试UP主",
            "profile_url": "https://www.acfun.cn/u/9876",
            "videos": [
                {
                    "title": "视频1",
                    "cover": "https://example.com/cover1.jpg",
                    "url": "https://www.acfun.cn/v/ac11111",
                    "pub_date": "2023-05-01",
                    "vid": "11111"
                },
                {
                    "title": "视频2",
                    "cover": "https://example.com/cover2.jpg",
                    "url": "https://www.acfun.cn/v/ac22222",
                    "pub_date": "2023-05-02",
                    "vid": "22222"
                }
            ]
        }
        
        # Mock successful downloads
        mock_download_video.return_value = True
        
        # Call the method with max_videos=1
        result = self.downloader.download_up_videos("9876", max_videos=1, quality="1080p")
        
        # Check results
        self.assertEqual(result, 1)  # Should have 1 successful download
        mock_get_up_videos.assert_called_once_with("9876", fetch_all_pages=True)
        
        # Should only download the first video
        mock_download_video.assert_called_once_with("11111", "1080p")
    
    @patch("time.sleep")
    @patch("src.downloader.AcFunDownloader.download_video")
    @patch("src.downloader.AcFunExtractor.get_up_videos")
    def test_download_up_videos_all(self, mock_get_up_videos, mock_download_video, mock_sleep):
        """Test download_up_videos method with all videos."""
        # Mock UP videos
        mock_get_up_videos.return_value = {
            "user": "测试UP主",
            "profile_url": "https://www.acfun.cn/u/9876",
            "videos": [
                {
                    "title": "视频1",
                    "cover": "https://example.com/cover1.jpg",
                    "url": "https://www.acfun.cn/v/ac11111",
                    "pub_date": "2023-05-01",
                    "vid": "11111"
                },
                {
                    "title": "视频2",
                    "cover": "https://example.com/cover2.jpg",
                    "url": "https://www.acfun.cn/v/ac22222",
                    "pub_date": "2023-05-02",
                    "vid": "22222"
                }
            ]
        }
        
        # Mock mixed success downloads
        mock_download_video.side_effect = [True, False]
        
        # Call the method without max_videos (download all)
        result = self.downloader.download_up_videos("9876", quality="720p")
        
        # Check results
        self.assertEqual(result, 1)  # Should have 1 successful download out of 2
        mock_get_up_videos.assert_called_once_with("9876", fetch_all_pages=True)
        
        # Should download both videos
        self.assertEqual(mock_download_video.call_count, 2)
        mock_download_video.assert_any_call("11111", "720p")
        mock_download_video.assert_any_call("22222", "720p")
        
        # Should have a sleep between downloads
        mock_sleep.assert_called_once()
        
if __name__ == "__main__":
    unittest.main()