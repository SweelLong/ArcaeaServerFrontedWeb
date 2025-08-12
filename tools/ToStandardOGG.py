import os
import subprocess
import sys
import tempfile
import uuid

def main():
    # 设置工作区为脚本所在的父目录
    script_path = os.path.abspath(__file__)
    workspace = os.path.dirname(script_path)
    print(f"工作区: {workspace}")

    # 检查ffmpeg是否安装及是否支持libvorbis编码器
    try:
        # 检查ffmpeg是否存在
        subprocess.run(['ffmpeg', '-version'], capture_output=True, check=True)
        # 检查是否支持libvorbis编码器
        encoders = subprocess.run(
            ['ffmpeg', '-encoders'], 
            capture_output=True, 
            text=True, 
            check=True
        ).stdout
        if 'libvorbis' not in encoders:
            print("错误: ffmpeg未安装libvorbis编码器，无法处理OGG文件。")
            sys.exit(1)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("错误: 未找到ffmpeg。请先安装ffmpeg并确保它在系统PATH中。")
        sys.exit(1)

    # 统计变量
    total = 0
    success = 0
    failed = []

    # 遍历工作区所有文件
    for root, _, files in os.walk(workspace):
        for file in files:
            if file.lower().endswith('.ogg'):
                total += 1
                input_path = os.path.join(root, file)
                
                # 显示当前处理的文件
                print(f"处理: {input_path}...", end=" ")
                
                try:
                    # 关键修复：在同一目录创建临时文件，避免跨磁盘移动
                    # 使用UUID生成唯一临时文件名，避免冲突
                    temp_filename = f".temp_{uuid.uuid4().hex}.ogg"
                    temp_path = os.path.join(root, temp_filename)
                    
                    # 执行优化压缩
                    result = subprocess.run([
                        'ffmpeg', '-hide_banner', '-loglevel', 'warning',
                        '-y', '-i', input_path,
                        '-vn', '-c:a', 'libvorbis',
                        '-q:a', '5',           # 音质级别(0-10)
                        '-ac', '2',            # 确保立体声
                        '-compression_level', '10',
                        temp_path
                    ], capture_output=True, text=True, check=True)
                    
                    # 先删除原文件再重命名临时文件（解决Windows文件占用问题）
                    if os.path.exists(input_path):
                        os.remove(input_path)
                    os.rename(temp_path, input_path)
                    
                    success += 1
                    print("成功")
                    
                except subprocess.CalledProcessError as e:
                    print(f"失败 (ffmpeg错误: {e.stderr.strip()})")
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    failed.append(f"{input_path} (ffmpeg错误: {e.stderr.strip()[:100]})")
                except Exception as e:
                    print(f"失败 (系统错误: {str(e)})")
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                    failed.append(f"{input_path} (系统错误: {str(e)})")

    # 显示结果
    print("\n处理完成!")
    print(f"总文件数: {total}")
    print(f"成功: {success}")
    print(f"失败: {len(failed)}")
    
    if failed:
        print("\n失败的文件及原因:")
        for f in failed:
            print(f"- {f}")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n程序被中断")
    except Exception as e:
        print(f"发生错误: {str(e)}")
    