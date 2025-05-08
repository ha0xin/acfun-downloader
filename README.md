# AcFun 视频下载工具

一个命令行工具，用于下载 AcFun 网站的视频。

## 功能特点

- 下载单个 AcFun 视频（支持分P视频）
- 下载 UP 主的所有视频
- 支持多种视频质量（1080p, 720p, 480p, 360p）
- 并行下载视频和音频流以提高下载速度
- 使用 ffmpeg 合并视频和音频

## 安装

### 先决条件

- Python 3.8 或更高版本
- 对于视频合并功能，需要安装 [FFmpeg](https://ffmpeg.org/download.html)

### 安装方法

从源代码安装:

```bash
git clone https://github.com/yourusername/acfun-downloader.git
cd acfun-downloader
pip install -e .
```

## 使用方法

### 命令行参数

```
acfun-dl [-h] [--output OUTPUT] [--quality {1080p,720p,480p,360p}] {video,up,info} ...

选项:
  -h, --help                      显示帮助信息
  --output OUTPUT, -o OUTPUT      下载目录 (默认: ./downloads)
  --quality {1080p,720p,480p,360p}, -q {1080p,720p,480p,360p}
                                  视频质量 (默认: 720p)

命令:
  {video,up,info}
    video                         下载单个视频
    up                            下载UP主的视频
    info                          获取视频信息 (不下载)
```

### 示例

1. 下载单个视频:

```bash
acfun-dl video 12345678
```

2. 指定视频质量和输出目录:

```bash
acfun-dl video 12345678 --quality 1080p --output ~/Videos/AcFun
```

3. 下载UP主的前5个视频:

```bash
acfun-dl up 12345678 --max 5
```

4. 获取视频信息但不下载:

```bash
acfun-dl info 12345678
```

## 开发

### 安装开发依赖

```bash
pip install -e ".[dev]"
```

### 运行测试

```bash
pytest
```

### 代码结构

- `src/extractor.py`: 从 AcFun 提取视频信息
- `src/downloader.py`: 处理视频下载功能
- `src/cli.py`: 命令行界面解析和主入口
- `src/models.py`: 数据模型定义
- `tests/`: 单元测试

## 注意事项

- 本工具仅用于个人学习和研究使用
- 请遵守 AcFun 用户协议，不要滥用此工具
- 尊重内容创作者的权益，合理使用下载的视频

## 许可证

MIT