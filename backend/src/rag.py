import re
from pathlib import Path

import PyPDF2


def _split_code_content(content: str) -> list[str]:
    sections = []
    lines = content.split('\n')
    current_section = []

    for line in lines:
        stripped = line.strip()
        if (stripped.startswith(('def ', 'class ', 'async def ')) or
                stripped.startswith(('@', 'function ', 'public ', 'private ', 'protected '))):

            if current_section:
                sections.append('\n'.join(current_section))
                current_section = []

            current_section.append(line)
        else:
            current_section.append(line)

    if current_section:
        sections.append('\n'.join(current_section))

    return sections


def _split_markdown_content(content: str) -> list[str]:
    sections = []
    lines = content.split('\n')
    current_section = []

    for line in lines:
        if line.strip().startswith('#'):
            if current_section:
                sections.append('\n'.join(current_section))
                current_section = []

            current_section.append(line)
        else:
            current_section.append(line)

    if current_section:
        sections.append('\n'.join(current_section))

    return sections


def _split_text_content(content: str) -> list[str]:
    paragraphs = re.split(r'\n\s*\n', content)

    sections = []
    for paragraph in paragraphs:
        if re.search(r'^\s*[-*•]\s', paragraph, re.MULTILINE) or \
                re.search(r'^\s*\d+\.\s', paragraph, re.MULTILINE):
            items = re.split(r'\n(?=\s*[-*•]\s|\s*\d+\.\s)', paragraph)
            sections.extend([item.strip() for item in items if item.strip()])
        else:
            sections.append(paragraph.strip())

    return [s for s in sections if s]


def read_pdf_file(file_path: Path) -> str:
    try:
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            text = ""

            for page_num, page in enumerate(pdf_reader.pages):
                page_text = page.extract_text()
                if page_text.strip():
                    page_text = _clean_pdf_text(page_text)
                    text += f"\n=== PAGE {page_num + 1} ===\n{page_text}\n"

            return text.strip()
    except Exception as e:
        print(f"Error reading PDF {file_path}: {e}")
        return ""


def _clean_pdf_text(text: str) -> str:
    text = re.sub(r'\s+', ' ', text)
    text = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', text)
    text = re.sub(r'([.!?])\s*([A-Z])', r'\1 \2', text)
    text = re.sub(r'(\w[.!?])\s+([A-Z][a-z])', r'\1\n\n\2', text)

    return text.strip()


def split_document_into_sections(content: str, filename: str) -> list[str]:
    content = content.strip()
    if not content:
        return []

    if filename.lower().endswith('.pdf') or '=== PAGE' in content:
        return _split_any_pdf_content(content)
    elif any(filename.endswith(ext) for ext in ['.py', '.js', '.java', '.cpp', '.c']):
        return _split_code_content(content)
    elif filename.endswith('.md'):
        return _split_markdown_content(content)
    else:
        return _split_text_content(content)


def _split_any_pdf_content(content: str) -> list[str]:
    sections = []

    clean_content = re.sub(r'\n=== PAGE \d+ ===\n', '\n\n', content)

    sections = _find_section_headers(clean_content)
    if len(sections) >= 2:
        return _filter_and_clean_sections(sections)

    sections = _find_numbered_sections(clean_content)
    if len(sections) >= 2:
        return _filter_and_clean_sections(sections)

    sections = _find_formatted_sections(clean_content)
    if len(sections) >= 2:
        return _filter_and_clean_sections(sections)

    sections = _find_list_sections(clean_content)
    if len(sections) >= 2:
        return _filter_and_clean_sections(sections)

    sections = _find_topic_sections(clean_content)
    if len(sections) >= 2:
        return _filter_and_clean_sections(sections)

    return _semantic_chunking(clean_content)


def _find_section_headers(content: str) -> list[str]:
    header_patterns = [
        r'\n\s*([A-Z][A-Za-z\s]{2,50})\s*\n',
        r'\n\s*([A-Z\s]{3,50})\s*\n',
        r'\n\s*(Chapter\s+\d+[^\n]*)\s*\n',
        r'\n\s*(Section\s+\d+[^\n]*)\s*\n',
        r'\n\s*(\d+\.\s+[A-Z][^\n]{5,100})\s*\n',
        r'\n\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*\n(?=[A-Z])',
    ]

    all_matches = []
    for pattern in header_patterns:
        matches = list(re.finditer(pattern, content, re.MULTILINE))
        all_matches.extend([(m.start(), m.end(), m.group(1).strip()) for m in matches])

    if len(all_matches) < 2:
        return []

    all_matches.sort(key=lambda x: x[0])

    sections = []
    for i, (start, end, header) in enumerate(all_matches):
        section_start = start
        section_end = all_matches[i + 1][0] if i + 1 < len(all_matches) else len(content)

        section_content = content[section_start:section_end].strip()
        if len(section_content) > 50:
            sections.append(section_content)

    return sections


def _find_numbered_sections(content: str) -> list[str]:
    numbered_patterns = [
        r'\n\s*(\d+\.\s+[^\n]{5,})',
        r'\n\s*(\d+\.\d+\s+[^\n]{5,})',
        r'\n\s*([IVX]+\.\s+[^\n]{5,})',
        r'\n\s*([A-Z]\.\s+[^\n]{5,})',
    ]

    best_pattern = None
    best_matches = []

    for pattern in numbered_patterns:
        matches = list(re.finditer(pattern, content, re.MULTILINE))
        if len(matches) > len(best_matches):
            best_matches = matches
            best_pattern = pattern

    if len(best_matches) < 2:
        return []

    sections = []
    for i, match in enumerate(best_matches):
        section_start = match.start()
        section_end = best_matches[i + 1].start() if i + 1 < len(best_matches) else len(content)

        section_content = content[section_start:section_end].strip()
        if len(section_content) > 50:
            sections.append(section_content)

    return sections


def _find_formatted_sections(content: str) -> list[str]:
    caps_pattern = r'\n\s*([A-Z]{3,}(?:\s+[A-Z]{3,})*)\s*\n'
    caps_matches = list(re.finditer(caps_pattern, content))

    header_matches = []
    for match in caps_matches:
        header_text = match.group(1).strip()
        words = header_text.split()
        if len(words) >= 3 or (len(words) == 1 and len(words[0]) > 5):
            header_matches.append(match)

    if len(header_matches) < 2:
        return []

    sections = []
    for i, match in enumerate(header_matches):
        section_start = match.start()
        section_end = header_matches[i + 1].start() if i + 1 < len(header_matches) else len(content)

        section_content = content[section_start:section_end].strip()
        if len(section_content) > 50:
            sections.append(section_content)

    return sections


def _find_list_sections(content: str) -> list[str]:
    list_patterns = [
        r'\n\s*•\s+[^\n]+',
        r'\n\s*[-*]\s+[^\n]+',
        r'\n\s*\d+\)\s+[^\n]+',
        r'\n\s*\([a-z]\)\s+[^\n]+',
    ]

    sections = []
    current_section = ""
    lines = content.split('\n')

    for line in lines:
        is_list_item = any(re.match(pattern.replace(r'\n\s*', r'^\s*'), line) for pattern in list_patterns)

        if is_list_item:
            if not current_section or len(current_section) > 1000:
                if current_section.strip():
                    sections.append(current_section.strip())
                current_section = line + '\n'
            else:
                current_section += line + '\n'
        else:
            current_section += line + '\n'

    if current_section.strip():
        sections.append(current_section.strip())

    return sections


def _find_topic_sections(content: str) -> list[str]:
    paragraphs = re.split(r'\n\s*\n\s*', content)

    sections = []
    current_section = []
    current_topic_words = set()

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph or len(paragraph) < 30:
            current_section.append(paragraph)
            continue

        paragraph_words = set(re.findall(r'\b[A-Za-z]{4,}\b', paragraph.lower()))

        if (current_topic_words and
                len(paragraph_words & current_topic_words) / max(len(current_topic_words), 1) < 0.3 and
                len(' '.join(current_section)) > 300):

            sections.append('\n\n'.join(current_section))
            current_section = [paragraph]
            current_topic_words = paragraph_words
        else:
            current_section.append(paragraph)
            current_topic_words.update(paragraph_words)

    if current_section:
        sections.append('\n\n'.join(current_section))

    return sections


def _semantic_chunking(content: str) -> list[str]:
    sentences = re.split(r'(?<=[.!?])\s+', content)

    sections = []
    current_section = ""
    target_section_size = 800
    min_section_size = 400

    for sentence in sentences:
        if len(current_section) + len(sentence) > target_section_size and len(current_section) > min_section_size:
            sections.append(current_section.strip())
            overlap_sentences = current_section.split('.')[-2:]
            current_section = '. '.join(overlap_sentences) + '. ' + sentence
        else:
            current_section += sentence + ' '

    if current_section.strip():
        sections.append(current_section.strip())

    return sections


def _filter_and_clean_sections(sections: list[str]) -> list[str]:
    filtered_sections = []

    for section in sections:
        section = section.strip()

        if len(section) < 50:
            continue

        if len(section.split()) < 10:
            continue

        alpha_ratio = len(re.findall(r'[a-zA-Z]', section)) / len(section)
        if alpha_ratio < 0.5:
            continue

        section = _clean_section_content(section)

        if section:
            filtered_sections.append(section)

    return filtered_sections


def _clean_section_content(content: str) -> str:
    content = re.sub(r'Page \d+ of \d+', '', content)
    content = re.sub(r'=== PAGE \d+ ===', '', content)
    content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
    content = re.sub(r'[ \t]+', ' ', content)
    content = content.strip()

    return content
