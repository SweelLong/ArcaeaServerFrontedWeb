import json
import pandas as pd

def process_songlist(input_file, output_file):
    try:
        # 读取songlist文件
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # 检查是否包含"songs"键
        if "songs" not in data:
            print("错误：文件中不包含'songs'键")
            return
        
        # 提取符合条件的数据
        result = []
        for song in data["songs"]:
            # 检查是否包含必要的键
            if "id" in song and "set" in song and song["set"] == "single":
                result.append({
                    "item_id": song["id"],
                    "purchase_name": 'single_' + song["id"]
                })
        
        # 将结果保存到Excel表格
        df = pd.DataFrame(result)
        df.to_excel(output_file, index=False)
        print(f"成功提取 {len(result)} 条数据并保存到 {output_file}")
        
    except FileNotFoundError:
        print(f"错误：找不到文件 {input_file}")
    except json.JSONDecodeError:
        print(f"错误：文件 {input_file} 不是有效的JSON格式")
    except Exception as e:
        print(f"处理过程中发生错误：{str(e)}")

if __name__ == "__main__":
    # 输入文件路径（songlist文件）
    input_filename = "songlist"  # 请替换为实际的文件路径
    # 输出Excel文件路径
    output_filename = "single_songs_ai.xlsx"
    
    process_songlist(input_filename, output_filename)
    
