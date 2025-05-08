"""
AcFun video extractor module.
Handles extracting video information from AcFun.
"""
import json
import re
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from typing import Dict, List, Optional, Union
from .models import Vid, Uid, Uploader, VideoMetadata, MultiPartInfo, PartVideoMetadata

class AcFunExtractor:
    """Extracts video information from AcFun."""
    
    def __init__(self, use_random_ua: bool = True):
        """Initialize the extractor.
        
        Args:
            use_random_ua: Whether to use a random User-Agent for requests.
        """
        self.use_random_ua = use_random_ua
        self._ua = UserAgent() if use_random_ua else None
        self.base_url = "https://www.acfun.cn"
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with User-Agent."""
        if self.use_random_ua:
            return {
                "Referer": "https://www.acfun.cn/",
                "User-Agent": self._ua.random,
            }
        else:
            return {
                "Referer": "https://www.acfun.cn/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0",
            }
    
    def get_video_info(self, vid: Union[str, Vid]) -> Optional[VideoMetadata]:
        """Get video information by video ID.
        
        Args:
            vid: The video ID (without 'ac' prefix).
            
        Returns:
            Video metadata or None if extraction failed.
        """
        if isinstance(vid, Vid):
            vid_str = vid.value
        else:
            vid_str = str(vid)
            
        video_url = f"{self.base_url}/v/ac{vid_str}"
        headers = self._get_headers()
        
        try:
            response = requests.get(url=video_url, headers=headers)
            response.raise_for_status()
            html_content = response.text
            
            # Parse HTML content
            soup = BeautifulSoup(html_content, "html.parser")
            
            # Extract video title
            title_elem = soup.select_one("h1.title")
            title = title_elem.text.strip() if title_elem else "Unknown Title"
            
            # Extract uploader information
            up_info_elem = soup.select_one(".up-info")
            uploader_name = "Unknown"
            uploader_uid = "0"
            
            if up_info_elem:
                up_name_elem = up_info_elem.select_one(".up-name")
                if up_name_elem:
                    uploader_name = up_name_elem.text.strip()
                    # Extract UID from href (e.g., /u/12345)
                    href = up_name_elem.get("href", "")
                    uid_match = re.search(r"/u/(\d+)", href)
                    if uid_match:
                        uploader_uid = uid_match.group(1)
            
            # Extract upload date
            upload_date = datetime.now()  # Default to now
            date_elem = soup.select_one(".video-info-main time")
            if date_elem:
                date_str = date_elem.text.strip()
                try:
                    upload_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                except ValueError:
                    pass
            
            # Extract cover URL
            cover_url = ""
            cover_elem = soup.select_one(".video-cover img")
            if cover_elem and cover_elem.has_attr("src"):
                cover_url = cover_elem["src"]
            
            # Check if video has multiple parts
            has_multi_p = False
            multi_p = []
            part_list = self.get_multi_p_info(vid_str)
            if part_list and len(part_list) > 1:
                has_multi_p = True
                for part in part_list:
                    # Extract part vid from URL
                    part_url = part["url"]
                    part_vid_match = re.search(r"ac(\d+)", part_url)
                    if part_vid_match:
                        multi_p.append(Vid(part_vid_match.group(1)))
            
            return VideoMetadata(
                vid=Vid(vid_str),
                title=title,
                cover_url=cover_url,
                uploader=Uploader(uid=Uid(uploader_uid), name=uploader_name),
                upload_date=upload_date,
                has_multi_p=has_multi_p,
                multi_p=multi_p
            )
            
        except Exception as e:
            print(f"Error extracting video info: {e}")
            return None

    def get_multi_p_info(self, vid: Union[str, Vid]) -> MultiPartInfo:
        """Get multi-part video information.
        
        Args:
            vid: The video ID (without 'ac' prefix).
            
        Returns:
            List of video parts with title and URL.
        """
        if isinstance(vid, Vid):
            vid_str = vid.value
        else:
            vid_str = str(vid)
            
        video_url = f"{self.base_url}/v/ac{vid_str}"
        headers = self._get_headers()
        
        try:
            response = requests.get(url=video_url, headers=headers)
            response.raise_for_status()
            html_content = response.text
            
            soup = BeautifulSoup(html_content, "html.parser")
            part_list = []
            
            # Find the multi-part section
            part_list_div = soup.find("div", class_="part")
            if not part_list_div:
                # No multi-part section found, return single part info
                return MultiPartInfo(
                    has_multi_part=False,
                    part_list=[]
                )
            
            # Extract part information
            part_li_elems = part_list_div.find_all("li", class_="single-p")
            for li_elem in part_li_elems:
                title = li_elem.get("title", "未知标题")
                # /v/ac41502955_2 -> 41502955_2
                part_vid_match = re.search(r"ac(\d+_\d+)", li_elem.get("data-href", ""))
                if part_vid_match:
                    part_vid = part_vid_match.group(1)
                else:
                    part_vid = ""
                part_list.append(
                    PartVideoMetadata(
                        vid=Vid(part_vid),
                        title=title
                    )
                )
            return MultiPartInfo(
                has_multi_part=True,
                part_list=part_list
            )
            
        except Exception as e:
            print(f"Error extracting multi-part info: {e}")
            return []
    
    def get_up_videos(self, uid: Union[str, Uid], fetch_all_pages: bool = False) -> List[VideoMetadata]:
        """Get videos from an UP user.
        
        Args:
            uid: The UP user ID.
            fetch_all_pages: Whether to fetch all pages of videos (default: False).
            
        Returns:
            List of video metadata dictionaries.
        """
        if isinstance(uid, Uid):
            uid_str = uid.value
        else:
            uid_str = str(uid)
            
        base_url = f"{self.base_url}/u/{uid_str}"
        headers = self._get_headers()
        
        try:
            response = requests.get(base_url, headers=headers)
            response.raise_for_status()
            response_text = response.text
            
            soup = BeautifulSoup(response_text, "html.parser")

            uploader_elem = soup.select_one("span.name > span.text-overflow")
            uploader_name = uploader_elem["title"] if uploader_elem else "Unknown"

            uploader_profile = Uploader(
                uid=Uid(uid_str),
                name=uploader_name
            )
            
            video_count_elem = soup.select_one("div.wp > div.tab > ul > li.active > span")
            video_count = int(video_count_elem.text) if video_count_elem else 0
            
            print(f"UP主: {uploader_name}, 视频总数: {video_count}")
            
            # Extract video list
            video_list = []
            
            # Parse first page videos
            first_page_videos = self._parse_video_page(soup, uploader=uploader_profile)
            video_list.extend(first_page_videos)
            
            # If we need to fetch all pages and there are multiple pages
            if fetch_all_pages and video_count > 20:  # Assuming 20 videos per page
                # Calculate total pages
                total_pages = (video_count // 20) + (1 if video_count % 20 > 0 else 0)
                
                # Get remaining pages
                for page in range(2, total_pages + 1):
                    print(f"正在获取第 {page}/{total_pages} 页...")
                    # Get current timestamp
                    timestamp = int(time.time() * 1000)
                    
                    params = {
                        "quickViewId": "ac-space-video-list",
                        "reqID": page,
                        "ajaxpipe": 1,
                        "type": "video",
                        "order": "newest",
                        "page": page,
                        "pageSize": 20,
                        "t": timestamp
                    }
                    
                    try:
                        response = requests.get(base_url, headers=headers, params=params)
                        response.raise_for_status()
                        
                        response_text = response.text
                        json_text = response_text.split("/*<!-- fetch-stream -->*/")[0]
                        json_obj = json.loads(json_text)
                        html_content = json_obj.get("html", "")
                        
                        # Parse HTML content
                        soup = BeautifulSoup(html_content, "html.parser")
                        
                        this_page_videos = self._parse_video_page(soup, uploader=uploader_profile)
                        video_list.extend(this_page_videos)
                        
                        # Avoid too frequent requests
                        time.sleep(0.5)
                        
                    except Exception as e:
                        print(f"获取第 {page} 页失败: {e}")
            
            return video_list
            
        except requests.exceptions.RequestException as e:
            print(f"请求失败: {e}")
            return None
    
    def _parse_video_page(self, soup: BeautifulSoup, uploader: Uploader) -> List[VideoMetadata]:
        """Parse video information from a BeautifulSoup object.
        
        Args:
            soup: BeautifulSoup object of the page.
            
        Returns:
            List of video metadata dictionaries.
        """
        video_list = []
        a_elems = soup.select("a.ac-space-video")
        
        for item in a_elems:
            # Extract video title
            title_elem = item.select_one("p.title")
            title_text = title_elem.get_text(strip=True) if title_elem else ""
            
            # Extract cover image
            image_elem = item.select_one("figure img")
            image_url = image_elem["src"].split("?")[0] if image_elem and image_elem.has_attr("src") else ""
            
            # Extract video link
            href = item.get("href", "")
            
            # Extract publish date
            date_elem = item.select_one(".date")
            if date_elem:
                date_str = date_elem.get_text(strip=True)
                try:
                    pub_date = datetime.strptime(date_str, "%Y/%m/%d")
                except ValueError:
                    pub_date = None
            else:
                pub_date = None
            
            # Extract video ID from the URL
            vid = ""
            vid_match = re.search(r"ac(\d+)", href)
            if vid_match:
                vid = vid_match.group(1)
            
            metadata = VideoMetadata(
                vid=Vid(vid),
                title=title_text,
                cover_url=image_url,
                uploader=uploader,
                upload_date=pub_date,
                multi_p=None
            )
            video_list.append(metadata)
        
        return video_list