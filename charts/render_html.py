"""Render paper.md into a standalone, self-contained HTML file with
all figures embedded as base64 data URIs."""
import base64
from pathlib import Path
import re

OUT = Path(__file__).resolve().parents[1]

# Read markdown
md = (OUT / "paper" / "paper.md").read_text()

# --- Convert markdown to HTML (simple, sufficient for this paper) ---
# We use a minimal hand-rolled converter to avoid python-markdown dependency.
def md_to_html(text: str) -> str:
    lines = text.split("\n")
    out = []
    in_table = False
    table_rows = []
    in_list = False

    def flush_table():
        nonlocal table_rows, in_table
        if not table_rows:
            return
        # First row = header, second = separator, rest = body
        header = table_rows[0]
        body = table_rows[2:]
        out.append('<table class="data">')
        out.append("<thead><tr>")
        for c in header:
            out.append(f"<th>{c.strip()}</th>")
        out.append("</tr></thead><tbody>")
        for row in body:
            out.append("<tr>")
            for c in row:
                out.append(f"<td>{c.strip()}</td>")
            out.append("</tr>")
        out.append("</tbody></table>")
        table_rows = []
        in_table = False

    i = 0
    while i < len(lines):
        line = lines[i]
        # Table detection
        if line.strip().startswith("|") and line.strip().endswith("|"):
            cells = [c for c in line.strip().strip("|").split("|")]
            table_rows.append(cells)
            in_table = True
            i += 1
            continue
        else:
            if in_table:
                flush_table()

        # Headings
        if line.startswith("# "):
            out.append(f"<h1>{inline(line[2:])}</h1>")
        elif line.startswith("## "):
            out.append(f"<h2>{inline(line[3:])}</h2>")
        elif line.startswith("### "):
            out.append(f"<h3>{inline(line[4:])}</h3>")
        elif line.startswith("---"):
            out.append("<hr>")
        elif line.startswith("!["):
            # ![alt](path)
            m = re.match(r"!\[(.*?)\]\((.*?)\)", line)
            if m:
                alt, path = m.group(1), m.group(2)
                img_path = OUT / "paper" / path
                if img_path.exists():
                    b64 = base64.b64encode(img_path.read_bytes()).decode()
                    out.append(
                        f'<figure><img src="data:image/png;base64,{b64}" '
                        f'alt="{alt}"/><figcaption>{alt}</figcaption></figure>')
        elif line.startswith("- "):
            out.append(f"<ul><li>{inline(line[2:])}</li></ul>")
        elif line.strip() == "":
            out.append("")
        else:
            out.append(f"<p>{inline(line)}</p>")
        i += 1
    if in_table:
        flush_table()
    return "\n".join(out)


def inline(text: str) -> str:
    # bold **x**
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # italic *x*
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
    # inline code `x`
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    # math-ish: $...$ -> keep as-is (unicode)
    return text


body_html = md_to_html(md)

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>A Compact Hash-Based Post-Quantum Signature Scheme</title>
<style>
  :root {{
    --text: #1a1a1a;
    --muted: #555;
    --accent: #2c5282;
    --border: #e2e8f0;
    --bg: #ffffff;
    --code-bg: #f7fafc;
  }}
  body {{
    font-family: "Georgia", "Times New Roman", serif;
    font-size: 16px;
    line-height: 1.65;
    color: var(--text);
    max-width: 820px;
    margin: 40px auto;
    padding: 0 28px;
    background: var(--bg);
  }}
  h1 {{
    font-size: 26px;
    line-height: 1.3;
    color: var(--accent);
    border-bottom: 2px solid var(--accent);
    padding-bottom: 10px;
  }}
  h2 {{
    font-size: 20px;
    margin-top: 32px;
    color: var(--accent);
    border-bottom: 1px solid var(--border);
    padding-bottom: 6px;
  }}
  h3 {{ font-size: 17px; margin-top: 22px; color: #2d3748; }}
  p {{ margin: 10px 0; text-align: justify; }}
  table.data {{
    border-collapse: collapse;
    width: 100%;
    margin: 18px 0;
    font-size: 14px;
    font-family: "Helvetica Neue", Arial, sans-serif;
  }}
  table.data th, table.data td {{
    border: 1px solid var(--border);
    padding: 8px 10px;
    text-align: left;
  }}
  table.data th {{
    background: #edf2f7;
    font-weight: 600;
  }}
  table.data tbody tr:nth-child(even) {{ background: #f9fafb; }}
  figure {{
    margin: 24px 0;
    text-align: center;
  }}
  figure img {{
    max-width: 100%;
    border: 1px solid var(--border);
    border-radius: 4px;
  }}
  figcaption {{
    font-size: 13px;
    color: var(--muted);
    margin-top: 8px;
    font-style: italic;
  }}
  code {{
    background: var(--code-bg);
    padding: 2px 5px;
    border-radius: 3px;
    font-family: "Menlo", monospace;
    font-size: 13px;
  }}
  hr {{ border: none; border-top: 1px solid var(--border); margin: 28px 0; }}
  ul {{ margin: 8px 0; }}
  li {{ margin: 4px 0; }}
  strong {{ color: #1a202c; }}
  .meta {{
    color: var(--muted);
    font-size: 14px;
    margin-bottom: 20px;
  }}
</style>
</head>
<body>
{body_html}
</body>
</html>
"""

(OUT / "paper" / "paper.html").write_text(html)
print(f"[written] {OUT/'paper'/'paper.html'} ({len(html)/1024:.0f} KB)")
