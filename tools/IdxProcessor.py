import json, os

f = os.path.join(os.path.dirname(os.path.abspath(__file__)), "songlist")
os.chdir(os.path.dirname(f) or ".")

with open(f, "r", encoding="utf-8") as f_r:
    data = json.load(f_r)
songs = data["songs"]

ids = [s["idx"] for s in songs if "idx" in s]
current = 0
while current in ids:
    current += 1

for i, s in enumerate(songs):
    if "idx" not in s:
        songs[i] = {"idx": current, **s}
        ids.append(current)
        current += 1

with open(f, "w", encoding="utf-8") as f_w:
    json.dump(data, f_w, ensure_ascii=False, indent=2)