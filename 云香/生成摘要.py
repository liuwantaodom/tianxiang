#!/usr/bin/env python3
"""
小说章节摘要生成工具
用法: python 生成摘要.py [章节文件路径1] [章节文件路径2] ...
或: python 生成摘要.py --batch 目录路径  (批量处理目录下所有.md文件)
"""

import os
import re
import sys
import json
from pathlib import Path

# ============ LLM调用 (MiniMax API) ============
def call_llm(text: str, system: str = "") -> str:
    """调用MiniMax API生成摘要"""
    import urllib.request
    
    url = "https://api.minimaxi.com/v1/text/chatcompletion_pro?GroupId=__GROUP_ID__"
    
    payload = {
        "model": "MiniMax-Text-01",
        "tokens_to_generate": 600,
        "temperature": 0.3,
        "top_p": 0.95,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": text}
        ]
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.environ.get('MINIMAX_CN_API_KEY', '')}"
        },
        method="POST"
    )
    
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["text"]

# ============ 核心摘要生成Prompt ============
SUMMARY_SYSTEM = """你是一个网络小说摘要生成专家。
要求：
1. 提炼章节核心事件，叙事简洁有力
2. 为所有人物名、地名、事件名加上[[双链]]格式（如：[[苏锦婳]]）
3. 只基于原文内容，不要自行添加未提及的信息
4. 输出格式：
## 第X章
（正文摘要，200-300字）
## 本章要点
- 要点1
- 要点2
- 要点3（可选）
"""

def extract_chapter_num(filename: str) -> int:
    """从文件名提取章节号"""
    match = re.search(r'第([零一二三四五六七八九十百千0-9]+)章', filename)
    if match:
        chinese = match.group(1)
        # 转换中文数字
        if chinese.isdigit():
            return int(chinese)
        # 中文数字转换表
        cn_map = {'零':0,'一':1,'二':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9,
                  '十':10,'百':100,'千':1000}
        result = 0
        for c in chinese:
            if c in cn_map:
                result = result * 10 + cn_map[c] if result < 10 else result + cn_map[c]
        return result if result > 0 else 0
    return 0

def generate_summary(chapter_text: str, chapter_num: int) -> str:
    """生成章节摘要"""
    prompt = f"""请为以下小说章节生成摘要：

{SUMMARY_SYSTEM}

## 章节内容
{chapter_text}"""
    
    try:
        result = call_llm(prompt, SUMMARY_SYSTEM)
        # 确保标题正确
        if not result.startswith(f"## 第{chapter_num}章"):
            result = f"## 第{chapter_num}章\n\n{result}"
        return result
    except Exception as e:
        print(f"  [ERROR] LLM调用失败: {e}")
        return None

def process_chapter(file_path: str, output_dir: str) -> bool:
    """处理单个章节文件"""
    file_path = Path(file_path)
    
    # 读取章节内容
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read().strip()
    
    if not content:
        print(f"  [SKIP] {file_path.name} - 文件为空")
        return False
    
    # 提取章节号
    chapter_num = extract_chapter_num(file_path.name)
    if not chapter_num:
        print(f"  [SKIP] {file_path.name} - 无法识别章节号")
        return False
    
    print(f"  处理: 第{chapter_num}章 ({file_path.name})")
    
    # 生成摘要
    summary = generate_summary(content, chapter_num)
    if not summary:
        return False
    
    # 检查字数（不含标题）
    body = re.sub(r'^## .*\n', '', summary, count=1)
    main_text = re.sub(r'^## 本章要点.*', '', body, flags=re.DOTALL).strip()
    total_chars = len(main_text) + len(re.findall(r'\[\[[^\]]+\]\]', summary)) * 4
    
    # 简单估算：双链格式会把字符数撑大，按实际输出
    print(f"    摘要生成完成，约{len(summary)}字符")
    
    # 保存到输出目录
    output_path = Path(output_dir) / f"第{chapter_num}章.md"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(summary)
    
    print(f"    -> 已保存: {output_path.name}")
    return True

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    output_dir = "/home/agentuser/xiaoshuo_tianxian/云香/已发布摘要"
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)
    
    if sys.argv[1] == "--batch" and len(sys.argv) >= 3:
        # 批量处理
        batch_dir = sys.argv[2]
        files = sorted(Path(batch_dir).glob("*.md"))
        print(f"批量处理: {batch_dir}")
        print(f"找到 {len(files)} 个文件\n")
        
        success = 0
        for f in files:
            if process_chapter(str(f), output_dir):
                success += 1
        
        print(f"\n完成: 成功 {success}/{len(files)}")
    
    else:
        # 单个或多个文件处理
        files = sys.argv[1:]
        print(f"处理 {len(files)} 个文件\n")
        
        success = 0
        for f in files:
            if process_chapter(f, output_dir):
                success += 1
        
        print(f"\n完成: 成功 {success}/{len(files)}")

if __name__ == "__main__":
    main()
