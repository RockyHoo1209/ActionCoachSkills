import re, os, sys
book_path = sys.argv[1]
output_dir = sys.argv[2]
os.makedirs(output_dir, exist_ok=True)
with open(book_path, 'r', encoding='utf-8') as f:
    text = f.read()
chunks = re.split(r'^(## \*\*.*?\*\*)', text, flags=re.MULTILINE)
current_header = None
chapter_count = 0
for i, chunk in enumerate(chunks):
    if chunk.startswith('## **'):
        current_header = chunk.strip()
    elif current_header:
        chapter_count += 1
        clean_name = re.sub(r'\*\*', '', current_header)
        clean_name = re.sub(r'[<>:"/\\|?*]', '', clean_name)
        clean_name = clean_name.replace('## ', '').strip()
        filename = f'{chapter_count:02d}_{clean_name}.md'
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as out:
            out.write(current_header + '\n')
            out.write(chunk)
        print(f'Wrote: {filename} ({len(chunk)} chars)')
        current_header = None
print(f'\nTotal chapters extracted: {chapter_count}')
