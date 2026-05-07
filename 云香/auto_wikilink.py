#!/usr/bin/env python3
"""
auto_wikilink.py —— 自动为Markdown摘要添加Obsidian双链

用法:
    python auto_wikilink.py <文件或目录>          # 直接覆盖处理
    python auto_wikilink.py --dry-run <文件>       # 预览改动，不写入
    python auto_wikilink.py <输入文件> <输出文件>  # 输出到新文件

词库位置（与脚本同目录）:
    ./双链词库/人物.txt
    ./双链词库/地点.txt
    ./双链词库/事件.txt
    ./双链词库/时间.txt
    ./双链词库/官职.txt
"""

import re
import sys
from pathlib import Path


def load_keywords(lib_dir: Path) -> list:
    """从词库目录加载所有关键词，按长度降序排列（避免短词覆盖长词）"""
    keywords = []
    files = ['人物.txt', '地点.txt', '事件.txt', '时间.txt', '官职.txt']
    
    for fname in files:
        fpath = lib_dir / fname
        if fpath.exists():
            with open(fpath, 'r', encoding='utf-8') as f:
                for line in f:
                    word = line.strip()
                    if word and not word.startswith('#'):
                        keywords.append(word)
    
    # 按长度降序排列，确保先匹配"沈砚之"再匹配"沈砚"
    keywords.sort(key=len, reverse=True)
    
    # 去重，保持顺序
    seen = set()
    unique = []
    for w in keywords:
        if w not in seen:
            seen.add(w)
            unique.append(w)
    
    return unique


def add_wikilinks(text: str, keywords: list) -> str:
    """
    为文本添加Obsidian双链。
    
    核心逻辑：从左到右线性扫描，优先匹配最长关键词。
    已存在于 [[ ]] 内部的文本、代码块、URL 不会被重复处理。
    """
    # 记录已被保护的字符位置（已有双链、代码块等）
    protected = set()
    
    # 保护已有的 Obsidian 双链 [[...]]
    for m in re.finditer(r'\[\[.*?\]\]', text):
        for i in range(m.start(), m.end()):
            protected.add(i)
    
    # 保护 Markdown 代码块 ```...```
    for m in re.finditer(r'```[\s\S]*?```', text):
        for i in range(m.start(), m.end()):
            protected.add(i)
    
    # 保护 Markdown 行内代码 `...`
    for m in re.finditer(r'`[^`]+`', text):
        for i in range(m.start(), m.end()):
            protected.add(i)
    
    # 保护 URL 和 Markdown 链接
    for m in re.finditer(r'!?\[([^\]]*)\]\([^)]*\)', text):
        for i in range(m.start(), m.end()):
            protected.add(i)
    
    result = []
    i = 0
    n = len(text)
    
    while i < n:
        matched = False
        
        # 按长度降序尝试匹配关键词
        for word in keywords:
            word_len = len(word)
            end = i + word_len
            
            if end > n:
                continue
            
            # 检查当前位置是否以该词开头
            if text[i:end] != word:
                continue
            
            # 检查该词的每个字符是否被保护
            if any(pos in protected for pos in range(i, end)):
                continue
            
            # 替换为双链格式
            result.append(f'[[{word}]]')
            
            # 标记这些位置为已占用（防止后续短词再次匹配同一位置）
            for pos in range(i, end):
                protected.add(pos)
            
            i = end
            matched = True
            break
        
        if not matched:
            result.append(text[i])
            i += 1
    
    return ''.join(result)


def process_file(input_path: Path, output_path: Path, keywords: list, dry_run: bool = False):
    """处理单个文件"""
    with open(input_path, 'r', encoding='utf-8') as f:
        original = f.read()
    
    modified = add_wikilinks(original, keywords)
    
    if original == modified:
        print(f"  [无改动] {input_path.name}")
        return False
    
    if dry_run:
        print(f"  [预览] {input_path.name}（未写入）")
        # 显示前3处改动
        for i, (a, b) in enumerate(zip(original, modified)):
            if a != b:
                start = max(0, i - 20)
                end = min(len(modified), i + 60)
                print(f"      ...{modified[start:end]}...")
                break
    else:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(modified)
        print(f"  [已更新] {output_path.name}")
    
    return True


def main():
    # 词库目录：脚本所在目录下的 双链词库/
    script_dir = Path(__file__).parent.resolve()
    lib_dir = script_dir / '双链词库'
    
    if not lib_dir.exists():
        print(f"错误：词库目录不存在: {lib_dir}")
        print("请确保脚本所在目录下有 '双链词库/' 文件夹")
        sys.exit(1)
    
    keywords = load_keywords(lib_dir)
    print(f"已加载 {len(keywords)} 个关键词")
    
    # 解析参数
    dry_run = False
    args = sys.argv[1:]
    
    if '--dry-run' in args:
        dry_run = True
        args.remove('--dry-run')
    
    if len(args) < 1:
        print(__doc__)
        sys.exit(1)
    
    input_path = Path(args[0]).resolve()
    output_path = Path(args[1]).resolve() if len(args) > 1 else input_path
    
    if input_path.is_file():
        process_file(input_path, output_path, keywords, dry_run)
    elif input_path.is_dir():
        md_files = sorted(input_path.glob('*.md'))
        print(f"发现 {len(md_files)} 个 Markdown 文件\n")
        changed = 0
        for md_file in md_files:
            if process_file(md_file, md_file, keywords, dry_run):
                changed += 1
        print(f"\n完成: {changed}/{len(md_files)} 个文件有改动")
    else:
        print(f"错误：目标不存在: {input_path}")
        sys.exit(1)


if __name__ == '__main__':
    main()
