import json
import os
import shutil
import subprocess

def extract_audio_segment(input_path, output_path, start_ms, end_ms):
    """使用ffmpeg提取音频片段，避免使用pydub的audioop依赖"""
    try:
        # 构建ffmpeg命令
        cmd = [
            "ffmpeg",
            "-ss", str(start_ms / 1000),  # 开始时间（秒）
            "-to", str(end_ms / 1000),    # 结束时间（秒）
            "-i", input_path,             # 输入文件
            "-c", "copy",                 # 直接复制音频流，不重新编码
            "-y",                         # 覆盖输出文件
            output_path
        ]
        
        # 执行命令
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except Exception as e:
        print(f"提取音频失败: {e}")
        return False

def process_songs():
    # 读取原始songlist文件
    with open("songlist", "r", encoding="utf-8") as f:
        data = json.load(f)
    
    # 筛选出set为"StellarBonds"的歌曲
    stellar_songs = [song for song in data.get("songs", []) if song.get("set") == "arknights"]
    remaining_songs = [song for song in data.get("songs", []) if song.get("set") != "arknights"]
    
    # 生成新的songlist（不包含StellarBonds内容）
    new_data = data.copy()
    new_data["songs"] = remaining_songs
    with open("songlist", "w", encoding="utf-8") as f:
        json.dump(new_data, f, indent=2, ensure_ascii=False)
    
    # 为切片文件创建主目录
    os.makedirs("切片", exist_ok=True)
    
    # 为每个筛选出的歌曲创建目录并处理文件
    for song in stellar_songs:
        song_id = song["id"]
        start = song["audioPreview"]
        end = song["audioPreviewEnd"]
        
        # 创建歌曲目录
        song_dir = os.path.join("切片", "dl_" + song_id)
        os.makedirs(song_dir, exist_ok=True)
        
        # 处理音频文件
        source_dir = song_id
        base_audio = os.path.join(source_dir, "base.ogg")
        if os.path.exists(base_audio):
            # 使用ffmpeg提取音频片段
            extract_audio_segment(
                base_audio,
                os.path.join(song_dir, "preview.ogg"),
                start,
                end
            )
        
        # 复制包含base的图片文件
        for file in os.listdir(source_dir):
            if "base" in file and file.lower().endswith((".png", ".jpg", ".jpeg", ".gif")):
                shutil.copy2(os.path.join(source_dir, file), song_dir)
    
    # 创建切片目录下的songlist，设置remote_dl为true
    for song in stellar_songs:
        song["remote_dl"] = True
    
    slice_songlist = data.copy()
    slice_songlist["songs"] = stellar_songs
    with open(os.path.join("切片", "songlist"), "w", encoding="utf-8") as f:
        json.dump(slice_songlist, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    process_songs()