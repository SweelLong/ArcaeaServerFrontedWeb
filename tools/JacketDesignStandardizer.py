import os 
from PIL import Image

base_dir = os.path.dirname(os.path.abspath(__file__))
exclude_dirs = ['pack', 'random', 'tutorial']

lst_768 = ['base.jpg', '1080_base.jpg', '1080_0.jpg', '1080_1.jpg', '1080_2.jpg', '1080_3.jpg', '1080_4.jpg', '0.jpg', '1.jpg', '2.jpg', '3.jpg', '4.jpg']
lst_384 = ['base_256.jpg', '1080_base_256.jpg', '1080_0_256.jpg', '1080_1_256.jpg', '1080_2_256.jpg', '1080_3_256.jpg', '1080_4_256.jpg', '0_256.jpg', '1_256.jpg', '2_256.jpg', '3_256.jpg', '4_256.jpg']

def convert_image_mode(i):
    if i.mode in ("RGBA", "P", "LA"):
        if i.mode == "RGBA":
            b = Image.new("RGB", i.size, (255,255,255))
            b.paste(i, mask=i.split()[3])
            return b
        elif i.mode == "P": 
            return i.convert("RGB")
        elif i.mode == "LA":
            b = Image.new("L", i.size, 255)
            b.paste(i, mask=i.split()[1])
            return b
    return i

for f in os.listdir(base_dir):
    p = os.path.join(base_dir, f)
    if os.path.isdir(p) and f not in exclude_dirs:
        print(f'Processing {f}...')
        for fl in os.listdir(p):
            fp = os.path.join(p, fl)
            if os.path.isfile(fp):
                try:
                    # 确定需要调整的尺寸
                    s = (768,768) if fl in lst_768 else (384,384) if fl in lst_384 else None
                    
                    if s:
                        # 检查文件名是否需要添加1080_前缀
                        if not fl.startswith("1080_"):
                            new_fl = f"1080_{fl}"
                            new_fp = os.path.join(p, new_fl)
                        else:
                            new_fl = fl
                            new_fp = fp
                            
                        with Image.open(fp) as img:
                            # 调整尺寸并转换模式
                            processed_img = convert_image_mode(img.resize(s, Image.LANCZOS))
                            # 保存到新文件
                            processed_img.save(new_fp, "JPEG", quality=95, optimize=True)
                            
                            # 如果文件名有变化，删除原文件
                            if new_fl != fl:
                                os.remove(fp)
                                
                            print(f"Processed {fl} -> {new_fl} in {f} - {s[0]}x{s[1]}")
                except Exception as e:
                    print(f"Error processing {fl} in {f}: {e}")
