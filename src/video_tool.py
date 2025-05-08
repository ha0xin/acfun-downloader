import json
import re
import os
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from fake_useragent import UserAgent


def get_multi_p_info(vid):
    # 发请求获取页面数据

    # 构造请求URL和随机User-Agent
    video_url = f"https://www.acfun.cn/v/ac{vid}"
    headers = {
        # 'Referer': 'https://www.acfun.cn/',
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.0.0",
    }

    response = requests.get(url=video_url, headers=headers)
    response_html = response.text
    with open("response.html", "w", encoding="utf-8") as f:
        f.write(response_html)

    soup = BeautifulSoup(response_html, "html.parser")
    # <div id="pagelet_rightrecommend"></div><div class='part'><div class='part-title'><h3>分段列表</h3><p>共3P, 当前正在播放<span class='current-priority'>1</span>P</p></div><div class='fl part-wrap'><ul class='scroll-div'><li class='single-p active' data-href='/v/ac41502955_1' title="好汉歌" data-id='31124282'>好汉歌</li><li class='single-p' data-href='/v/ac41502955_2' title="好汉歌2" data-id='31491321'>好汉歌2</li><li class='single-p' data-href='/v/ac41502955_3' title="好汉歌3" data-id='31491348'>好汉歌3</li></ul></div></div>

    part_list = []

    # 解析HTML，找到分段列表的部分
    part_list_div = soup.find("div", class_="part")
    if not part_list_div:
        print("分段列表未找到")
        return part_list

    part_li_elems = part_list_div.find_all("li", class_="single-p")
    for li_elem in part_li_elems:
        # 获取分段的标题和ID
        title = li_elem.get("title")
        url = "https://www.acfun.cn" + li_elem.get("data-href")
        part_list.append(
            {
                "title": title,
                "url": url,
            }
        )
    
    return part_list


if __name__ == "__main__":
    # 测试函数
    vid = "41789850"  # 替换为实际的vid
    # https://www.acfun.cn/v/ac41789850
    part_list = get_multi_p_info(vid)
    for part in part_list:
        print(f"标题: {part['title']}, URL: {part['url']}")
