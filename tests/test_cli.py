"""
Tests for the AcFun downloader CLI module.
"""
import unittest
from unittest.mock import patch, MagicMock
import sys
import argparse
from io import StringIO

from src.cli import parse_arguments, main

class TestAcFunCLI(unittest.TestCase):
    """Test cases for AcFun downloader CLI."""
    
    def test_parse_arguments_video_command(self):
        """Test argument parsing for video command."""
        test_args = ["video", "12345", "--quality", "1080p", "--output", "/test/path"]
        args = parse_arguments(test_args)
        
        self.assertEqual(args.command, "video")
        self.assertEqual(args.vid, "12345")
        self.assertEqual(args.quality, "1080p")
        self.assertEqual(args.output, "/test/path")
    
    def test_parse_arguments_up_command(self):
        """Test argument parsing for up command."""
        test_args = ["up", "9876", "--max", "5", "--all-pages", "--quality", "480p"]
        args = parse_arguments(test_args)
        
        self.assertEqual(args.command, "up")
        self.assertEqual(args.uid, "9876")
        self.assertEqual(args.max, 5)
        self.assertTrue(args.all_pages)
        self.assertEqual(args.quality, "480p")
    
    def test_parse_arguments_info_command(self):
        """Test argument parsing for info command."""
        test_args = ["info", "12345"]
        args = parse_arguments(test_args)
        
        self.assertEqual(args.command, "info")
        self.assertEqual(args.vid, "12345")
    
    def test_parse_arguments_defaults(self):
        """Test default argument values."""
        test_args = ["video", "12345"]
        args = parse_arguments(test_args)
        
        self.assertEqual(args.quality, "720p")
        self.assertEqual(args.output, "./downloads")
    
    @patch("src.cli.AcFunDownloader")
    @patch("src.cli.os.makedirs")
    def test_main_video_command(self, mock_makedirs, mock_downloader_class):
        """Test main function with video command."""
        # Setup mock
        mock_downloader = MagicMock()
        mock_downloader.download_video.return_value = True
        mock_downloader_class.return_value = mock_downloader
        
        # Call main with video command
        test_args = ["video", "12345", "--quality", "720p"]
        result = main(test_args)
        
        # Check results
        self.assertEqual(result, 0)  # Success
        mock_makedirs.assert_called_once()
        mock_downloader_class.assert_called_once()
        mock_downloader.download_video.assert_called_once_with("12345", quality="720p")
    
    @patch("src.cli.AcFunDownloader")
    @patch("src.cli.os.makedirs")
    def test_main_up_command(self, mock_makedirs, mock_downloader_class):
        """Test main function with up command."""
        # Setup mock
        mock_downloader = MagicMock()
        mock_downloader.download_up_videos.return_value = 3  # 3 successful downloads
        mock_downloader_class.return_value = mock_downloader
        
        # Call main with up command
        test_args = ["up", "9876", "--max", "5"]
        result = main(test_args)
        
        # Check results
        self.assertEqual(result, 0)  # Success
        mock_makedirs.assert_called_once()
        mock_downloader_class.assert_called_once()
        mock_downloader.download_up_videos.assert_called_once_with("9876", max_videos=5, quality="720p")
    
    @patch("src.cli.AcFunExtractor")
    @patch("sys.stdout", new_callable=StringIO)
    @patch("src.cli.os.makedirs")
    def test_main_info_command(self, mock_makedirs, mock_stdout, mock_extractor_class):
        """Test main function with info command."""
        from datetime import datetime
        from src.models import Vid, Uid, Uploader, VideoMetadata
        
        # Setup mock
        mock_extractor = MagicMock()
        # Create a mock video info return value
        mock_video_info = VideoMetadata(
            vid=Vid("12345"),
            title="测试视频",
            cover_url="https://example.com/cover.jpg",
            uploader=Uploader(uid=Uid("9876"), name="测试UP主"),
            upload_date=datetime(2023, 5, 1, 12, 34, 56),
            has_multi_p=False,
            multi_p=[]
        )
        mock_extractor.get_video_info.return_value = mock_video_info
        mock_extractor_class.return_value = mock_extractor
        
        # Call main with info command
        test_args = ["info", "12345"]
        result = main(test_args)
        
        # Check results
        self.assertEqual(result, 0)  # Success
        mock_makedirs.assert_called_once()
        mock_extractor_class.assert_called_once()
        mock_extractor.get_video_info.assert_called_once_with("12345")
        
        # Check output
        output = mock_stdout.getvalue()
        self.assertIn("标题: 测试视频", output)
        self.assertIn("UP主: 测试UP主", output)
        self.assertIn("单P视频", output)
    
    @patch("src.cli.AcFunDownloader")
    @patch("src.cli.os.makedirs")
    def test_main_video_command_failure(self, mock_makedirs, mock_downloader_class):
        """Test main function with video command that fails."""
        # Setup mock
        mock_downloader = MagicMock()
        mock_downloader.download_video.return_value = False  # Download fails
        mock_downloader_class.return_value = mock_downloader
        
        # Call main with video command
        test_args = ["video", "12345"]
        result = main(test_args)
        
        # Check results
        self.assertEqual(result, 1)  # Failure
        mock_downloader.download_video.assert_called_once()
        
if __name__ == "__main__":
    unittest.main()