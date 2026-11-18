import glob
import json
import os
import re
import sqlite3
from datetime import datetime
from urllib.parse import unquote

PROJECT_KEY = "ackopulse"  # Matches D:\5 sem\ackopulse regardless of slash/URI encoding
OUTPUT_MD = os.path.join(os.getcwd(), "antigravity_ackopulse_prompts.md")

# Antigravity IDE & CLI storage locations on Windows (including D: drive junctions)
USER_HOME = os.path.expanduser("~")
SEARCH_ROOTS = [
    os.path.join(USER_HOME, ".gemini", "antigravity"),
    os.path.join(USER_HOME, ".gemini", "antigravity-ide"),
    os.path.join(USER_HOME, ".gemini", "antigravity-cli"),
    r"D:\.gemini\antigravity",
    r"D:\.gemini\antigravity-ide",
    r"D:\.gemini\antigravity-cli",
]


def extract_user_prompts_from_jsonl(jsonl_path):
    """Extracts clean user prompts from Antigravity's .system_generated/logs/transcript*.jsonl."""
    prompts = []
    with open(jsonl_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                source = str(entry.get("source", "")).upper()
                role = str(entry.get("role", "")).lower()
                msg_type = str(entry.get("type", "")).upper()
                if source == "USER" or role == "user" or "USER_INPUT" in msg_type:
                    content = entry.get("content") or entry.get("text") or ""
                    if isinstance(content, list):
                        content = "\n".join(
                            c.get("text", "") for c in content if isinstance(c, dict)
                        )
                    if str(content).strip():
                        prompts.append(str(content).strip())
            except json.JSONDecodeError:
                continue
    return prompts


def read_sqlite_text(db_path):
    """Reads all text and protobuf-encoded string blobs from an Antigravity .db file safely."""
    chunks = []
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    cur = conn.cursor()
    tables = [
        r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
    ]
    for table in tables:
        for row in cur.execute(f"SELECT * FROM [{table}]"):
            for col in row:
                if isinstance(col, bytes):
                    chunks.append(col.decode("utf-8", errors="ignore"))
                elif isinstance(col, str):
                    chunks.append(col)
    conn.close()
    return "\n".join(chunks)


def extract_user_prompts_from_blob(raw_blob):
    """Filters printable prompt segments from raw SQLite/Protobuf dumps while skipping AI/system noise."""
    # Check if JSON-structured user messages exist inside the DB text
    json_prompts = re.findall(
        r'"(?:source|role)"\s*:\s*"(?:USER|user)"[^}]*?"(?:content|text)"\s*:\s*"((?:[^"\\]|\\.)+)"',
        raw_blob,
    )
    if json_prompts:
        cleaned = []
        for p in json_prompts:
            try:
                cleaned.append(json.loads(f'"{p}"').strip())
            except Exception:
                cleaned.append(p.strip())
        return [p for p in cleaned if p]

    # Fallback for pure binary protobuf blobs: extract readable human sentences
    noise_prefixes = (
        "file://",
        "http://",
        "https://",
        "PLANNER_",
        "MODEL",
        "TOOL_",
        "step_index",
        "created_at",
        "implementation_plan.md",
        "walkthrough.md",
        "task.md",
    )
    candidates = []
    for match in re.findall(r"[ -~\r\n\t]{12,}", raw_blob):
        s = match.strip()
        if any(s.startswith(pfx) for pfx in noise_prefixes):
            continue
        # Skip single-token hashes, base64, and protobuf field keys
        if " " not in s and len(s) > 30:
            continue
        if s not in candidates:
            candidates.append(s)
    return candidates


def main():
    sessions_found = []
    seen_ids = set()

    for root in SEARCH_ROOTS:
        if not os.path.exists(root):
            continue

        # 1. Check structured brain/<conversation-id>/.system_generated/logs/ first
        brain_dir = os.path.join(root, "brain")
        if os.path.isdir(brain_dir):
            for conv_id in os.listdir(brain_dir):
                conv_path = os.path.join(brain_dir, conv_id)
                if not os.path.isdir(conv_path) or conv_id in seen_ids:
                    continue

                # Scan all files in this conversation folder to verify it belongs to ackopulse
                folder_text = ""
                jsonl_files = []
                for fpath in glob.glob(os.path.join(conv_path, "**", "*"), recursive=True):
                    if os.path.isfile(fpath):
                        if fpath.endswith(".jsonl"):
                            jsonl_files.append(fpath)
                        try:
                            with open(fpath, "rb") as f:
                                folder_text += f.read().decode("utf-8", errors="ignore")
                        except Exception:
                            pass

                if PROJECT_KEY not in unquote(folder_text).lower():
                    continue

                prompts = []
                for jf in sorted(jsonl_files):
                    prompts.extend(extract_user_prompts_from_jsonl(jf))

                if prompts:
                    seen_ids.add(conv_id)
                    sessions_found.append((conv_id, prompts))

        # 2. Check conversations/*.db and conversations/*.pb
        conv_dir = os.path.join(root, "conversations")
        if os.path.isdir(conv_dir):
            for fpath in glob.glob(os.path.join(conv_dir, "*")):
                if not os.path.isfile(fpath):
                    continue
                conv_id = os.path.splitext(os.path.basename(fpath))[0]
                if conv_id in seen_ids:
                    continue

                ext = os.path.splitext(fpath)[1].lower()
                try:
                    if ext in (".db", ".sqlite"):
                        blob = read_sqlite_text(fpath)
                    elif ext == ".pb":
                        with open(fpath, "rb") as f:
                            blob = f.read().decode("utf-8", errors="ignore")
                    else:
                        continue
                except Exception:
                    continue

                if PROJECT_KEY not in unquote(blob).lower():
                    continue

                prompts = extract_user_prompts_from_blob(blob)
                if prompts:
                    seen_ids.add(conv_id)
                    sessions_found.append((conv_id, prompts))

    # Write output Markdown file inside D:\5 sem\ackopulse
    with open(OUTPUT_MD, "w", encoding="utf-8") as out:
        out.write(f"# Antigravity Prompt History — `D:\\5 sem\\ackopulse`\n")
        out.write(f"_Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_\n\n")

        if not sessions_found:
            out.write("No matching Antigravity sessions found for `ackopulse`.\n")
        else:
            for conv_id, prompts in sessions_found:
                out.write(f"---\n## Conversation ID: `{conv_id}`\n\n")
                for i, p in enumerate(prompts, 1):
                    out.write(f"**Prompt {i}:**\n> {p.replace(chr(10), chr(10) + '> ')}\n\n")

    print(f"Extracted {len(sessions_found)} Antigravity session(s) -> {OUTPUT_MD}")


if __name__ == "__main__":
    main()