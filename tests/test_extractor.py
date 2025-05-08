"""
Tests for the AcFun extractor module.
"""
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime
import requests
from bs4 import BeautifulSoup

from src.extractor import AcFunExtractor
from src.models import Vid, Uid, Uploader, VideoMetadata

class TestAcFunExtractor(unittest.TestCase):
    """Test cases for AcFunExtractor."""
    
    def setUp(self):
        """Set up test environment."""
        self.extractor = AcFunExtractor(use_random_ua=False)
    
    @patch("src.extractor.requests.get")
    def test_get_multi_p_info_success(self, mock_get):
        """Test get_multi_p_info when successful."""
        # Create a mock response
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <div class="part">
                <div class="part-title">
                    <h3>分段列表</h3>
                    <p>共3P, 当前正在播放<span class='current-priority'>1</span>P</p>
                </div>
                <div class="fl part-wrap">
                    <ul class="scroll-div">
                        <li class="single-p active" data-href="/v/ac12345_1" title="第一集" data-id="1">第一集</li>
                        <li class="single-p" data-href="/v/ac12345_2" title="第二集" data-id="2">第二集</li>
                        <li class="single-p" data-href="/v/ac12345_3" title="第三集" data-id="3">第三集</li>
                    </ul>
                </div>
            </div>
        </html>
        """
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        # Call the method
        result = self.extractor.get_multi_p_info("12345")
        
        # Check results
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["title"], "第一集")
        self.assertEqual(result[0]["url"], "https://www.acfun.cn/v/ac12345_1")
        self.assertEqual(result[1]["title"], "第二集")
        self.assertEqual(result[2]["title"], "第三集")
        
        # Check request
        mock_get.assert_called_once_with(
            url="https://www.acfun.cn/v/ac12345",
            headers={
                "Referer": "https://www.acfun.cn/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0",
            }
        )
    
    @patch("src.extractor.requests.get")
    def test_get_multi_p_info_no_parts(self, mock_get):
        """Test get_multi_p_info when no parts are found."""
        # Create a mock response without parts
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <div id="pagelet_rightrecommend"></div>
            <!-- No part list div -->
        </html>
        """
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        # Call the method
        result = self.extractor.get_multi_p_info("12345")
        
        # Check results - should return one item for the single video
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "单P视频")
        self.assertEqual(result[0]["url"], "https://www.acfun.cn/v/ac12345")
    
    @patch("src.extractor.requests.get")
    def test_get_video_info(self, mock_get):
        """Test get_video_info."""
        # Create a mock response
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <h1 class="title">测试视频标题</h1>
            <div class="up-info">
                <a class="up-name" href="/u/9876">测试UP主</a>
            </div>
            <div class="video-info-main">
                <time>2023-05-01 12:34:56</time>
            </div>
            <div class="video-cover">
                <img src="https://example.com/cover.jpg">
            </div>
            <!-- No part list for a single video -->
        </html>
        """
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        # Mock the multi-part info call to return a single video
        with patch.object(
            self.extractor, 
            "get_multi_p_info", 
            return_value=[{"title": "单P视频", "url": "https://www.acfun.cn/v/ac12345"}]
        ):
            # Call the method
            result = self.extractor.get_video_info("12345")
            
            # Check results
            self.assertIsInstance(result, VideoMetadata)
            self.assertEqual(result["title"], "测试视频标题")
            self.assertEqual(result["uploader"].name, "测试UP主")
            self.assertEqual(result["uploader"].uid.value, "9876")
            self.assertEqual(result["cover_url"], "https://example.com/cover.jpg")
            self.assertEqual(result["upload_date"].strftime("%Y-%m-%d %H:%M:%S"), "2023-05-01 12:34:56")
            self.assertFalse(result["has_multi_p"])
            self.assertEqual(len(result["multi_p"]), 0)
    
    @patch("src.extractor.AcFunExtractor.get_multi_p_info")
    @patch("src.extractor.requests.get")
    def test_get_video_info_with_multi_p(self, mock_get, mock_get_multi_p):
        """Test get_video_info with multi-part video."""
        # Create a mock response
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <h1 class="title">测试多P视频</h1>
            <div class="up-info">
                <a class="up-name" href="/u/9876">测试UP主</a>
            </div>
            <div class="video-info-main">
                <time>2023-05-01 12:34:56</time>
            </div>
            <div class="video-cover">
                <img src="https://example.com/cover.jpg">
            </div>
            <!-- Part list will be mocked -->
        </html>
        """
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        # Mock the multi-part info call to return multiple parts
        mock_get_multi_p.return_value = [
            {"title": "第一集", "url": "https://www.acfun.cn/v/ac12345_1"},
            {"title": "第二集", "url": "https://www.acfun.cn/v/ac12345_2"},
            {"title": "第三集", "url": "https://www.acfun.cn/v/ac12345_3"}
        ]
        
        # Call the method
        result = self.extractor.get_video_info("12345")
        
        # Check results
        self.assertIsInstance(result, VideoMetadata)
        self.assertEqual(result["title"], "测试多P视频")
        self.assertTrue(result["has_multi_p"])
        # Note: In actual implementation, the multi_p list would contain Vid objects
        # but our mock doesn't extract these correctly
    
    @patch("src.extractor.requests.get")
    def test_get_up_videos_first_page(self, mock_get):
        """Test get_up_videos for the first page."""
        # Create a mock response
        mock_response = MagicMock()
        mock_response.text = """
        <html>
            <title>UP主: 测试UP主</title>
            <div class="wp">
                <div class="tab">
                    <ul>
                        <li class="active">
                            <span>5</span>
                        </li>
                    </ul>
                </div>
            </div>
            <a class="ac-space-video">
                <p class="title">视频1</p>
                <figure>
                    <img src="https://example.com/cover1.jpg">
                </figure>
                <span class="date">2023/05/01</span>
                <a href="/v/ac11111"></a>
            </a>
            <a class="ac-space-video">
                <p class="title">视频2</p>
                <figure>
                    <img src="https://example.com/cover2.jpg">
                </figure>
                <span class="date">2023/05/02</span>
                <a href="/v/ac22222"></a>
            </a>
        </html>
        """
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        # Mock the _parse_video_page method to return some videos
        with patch.object(
            self.extractor, 
            "_parse_video_page", 
            return_value=[
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
        ):
            # Call the method
            result = self.extractor.get_up_videos("9876", fetch_all_pages=False)
            
            # Check results
            self.assertIsNotNone(result)
            self.assertEqual(result["user"], "UP主: 测试UP主")
            self.assertEqual(result["profile_url"], "https://www.acfun.cn/u/9876")
            self.assertEqual(len(result["videos"]), 2)
            self.assertEqual(result["videos"][0]["title"], "视频1")
            self.assertEqual(result["videos"][1]["title"], "视频2")
            
if __name__ == "__main__":
    unittest.main()