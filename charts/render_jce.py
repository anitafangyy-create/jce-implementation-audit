"""Render the audited Markdown paper as offline, accessible HTML.
Requires mistune (Markdown tables and fenced-code support).
"""
from pathlib import Path
import argparse
import base64
import html
import re
import mistune

OUT = Path(__file__).resolve().parents[1]

def render(from_markdown=False):
    target = OUT / "paper" / "paper_jce.html"
    if target.exists() and not from_markdown:
        current = target.read_text(encoding="utf-8")
        ids = re.findall(r'\bid="([^"]+)"', current)
        links = re.findall(r'href="#([^"]+)"', current)
        assert len(ids) == len(set(ids)), "Duplicate document identifiers"
        assert not set(links) - set(ids), "Unresolved internal links"
        assert "<h1>" in current and current.count("<table>") == 20
        print("Validated current HTML; preserved direct edits. Use --from-markdown only to explicitly rebuild from Markdown.")
        return
    md = (OUT / 'paper' / 'paper_jce.md').read_text(encoding='utf-8')
    body = (mistune.create_markdown(escape=False, plugins=['table'])(md)
            if hasattr(mistune, 'create_markdown') else mistune.markdown(md, escape=False))
    toc = []
    def heading(match):
        level, text = match.groups()
        plain = re.sub('<[^>]*>', '', text)
        slug = re.sub(r'[^a-z0-9]+', '-', plain.lower()).strip('-')
        if level == '2':
            toc.append(f'<li><a href="#{slug}">{text}</a></li>')
        return f'<h{level} id="{slug}">{text}</h{level}>'
    body = re.sub(r'<h([23])>(.*?)</h\1>', heading, body)
    def figure(match):
        path, alt = match.groups()
        encoded = base64.b64encode((OUT / "paper" / html.unescape(path)).read_bytes()).decode()
        return (f'<figure><img src="data:image/png;base64,{encoded}" alt="{alt}" '
                f'width="1620" height="900"><figcaption>{alt}</figcaption></figure>')
    body = re.sub(r'<p><img src="([^"]+)" alt="([^"]*)"\s*/?></p>', figure, body)
    body = body.replace('<table>', '<div class="table-wrap" tabindex="0" role="region" aria-label="Research data table"><table>')
    body = body.replace('</table>', '</table></div>')
    body = re.sub(r'<p>(Table \d+\..*?)</p>',r'<p class="caption">\1</p>',body)
    body = body.replace('<th>', '<th scope="col">')
    body = re.sub(r'<p>\[(\d+)\]', lambda m: '<p id="ref-'+m.group(1)+'">['+m.group(1)+']', body)
    before, separator, after = body.partition('<h2 id="references">')
    before = re.sub(r'\[(\d+(?:,\s*\d+)*)\]', lambda m: '['+', '.join('<a href="#ref-'+n.strip()+'">'+n.strip()+'</a>' for n in m.group(1).split(','))+']', before)
    body = before + separator + after
    eq_count = [0]
    def number_equation(match):
        eq_count[0] += 1
        return '<div class="equation" id="eq-%d">%s <span class="eq-number">(%d)</span></div>' % (eq_count[0], match.group(1), eq_count[0])
    body = re.sub(r'<div class="equation">(.*?)</div>', number_equation, body, flags=re.S)
    title = html.escape(md.splitlines()[0][2:])
    style = '''
:root{--ink:#202e38;--muted:#5c6a73;--accent:#17685d;--line:#dbe3e1;--paper:#fff;--canvas:#f3f5f3}
*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:30px}
body{margin:0;background:var(--canvas);color:var(--ink);font:17px/1.8 Georgia,"Times New Roman",serif}
a{color:var(--accent);text-underline-offset:3px}a:hover{color:#0b433b}a:focus-visible,button:focus-visible,[tabindex]:focus-visible{outline:3px solid #b17138;outline-offset:4px}
.skip{position:absolute;top:-80px;left:20px;background:white;padding:8px}.skip:focus{top:10px}
.top{max-width:1320px;margin:auto;padding:28px 36px 20px;display:flex;justify-content:space-between;align-items:center;gap:18px;font:12px/1.5 system-ui,sans-serif;letter-spacing:.1em;color:var(--accent)}
.top strong{letter-spacing:.16em}.top button{background:white;border:1px solid var(--line);padding:9px 15px;border-radius:5px;color:var(--ink);cursor:pointer;font:12px system-ui,sans-serif}
.layout{max-width:1320px;margin:auto;padding:0 36px 64px;display:grid;grid-template-columns:230px minmax(0,1fr);gap:30px}
nav{position:sticky;top:28px;align-self:start;max-height:calc(100vh - 56px);overflow:auto;font:12px/1.55 system-ui,sans-serif;padding:12px 0}
nav .label{font-size:10px;letter-spacing:.18em;color:var(--muted);margin:0 0 15px}nav ol{list-style:none;margin:0;padding:0}nav li{margin:0 0 3px}nav a{display:block;padding:7px 10px;border-left:2px solid transparent;text-decoration:none;color:var(--muted)}nav a:hover{background:#e8efeb;border-color:var(--accent)}
article{min-width:0;background:var(--paper);padding:48px 56px 60px;border:1px solid var(--line);border-top:4px solid var(--accent);box-shadow:0 8px 30px #183b2b05}
.kicker{font:11px/1.5 system-ui,sans-serif;letter-spacing:.16em;color:var(--accent);text-transform:uppercase;margin-bottom:18px}
h1{font-size:clamp(28px,3vw,40px);line-height:1.2;letter-spacing:-.025em;font-weight:normal;margin:0 0 20px}h1+p{font:16px/1.65 system-ui,sans-serif;color:var(--muted);margin-bottom:30px}h1+p strong{font-weight:400}
h2{font-size:24px;line-height:1.4;font-weight:normal;padding-top:30px;margin:28px 0 18px;border-top:1px solid var(--line);color:#174e45}h3{font:600 16px/1.5 system-ui,sans-serif;margin:26px 0 12px}p{margin:13px 0}strong{font-weight:700}
.table-wrap{max-width:100%;overflow:auto;margin:22px 0 8px}table{border-collapse:collapse;width:100%;font:12px/1.6 system-ui,sans-serif;font-variant-numeric:tabular-nums}th,td{padding:10px 10px;border-bottom:1px solid var(--line);vertical-align:top}th{background:#edf4f0;text-align:left;color:#174e45;font-weight:600}tbody tr:nth-child(even){background:#fafbf9}table code{font-size:11px;overflow-wrap:anywhere;white-space:normal}
.caption,figcaption{font:12px/1.65 system-ui,sans-serif;color:var(--muted)}.caption{margin:8px 0 22px}figure{margin:28px 0}figure img{display:block;width:100%;height:auto}figcaption{margin-top:10px}
code{font:12px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace;background:#f0f4f2;padding:2px 4px;border-radius:3px;overflow-wrap:anywhere}pre{background:#f1f5f3;padding:18px 20px;overflow:auto;border-left:3px solid #81a89d;font:12px/1.7 ui-monospace,monospace}pre code{background:none;padding:0;overflow-wrap:normal;white-space:pre}
.equation{font:18px/1.9 Georgia,serif;text-align:center;padding:20px 12px;margin:22px 0;background:#f5f8f5;border:1px solid #e1e9e3;overflow:auto}ol,ul{padding-left:24px}li{margin:9px 0}.endnote{font:12px/1.7 system-ui,sans-serif;color:var(--muted);border-top:1px solid var(--line);margin-top:36px;padding-top:16px}
@media(max-width:1000px){.layout{grid-template-columns:180px minmax(0,1fr);gap:20px;padding:0 20px 40px}article{padding:35px 30px}.top{padding:20px}}
@media(max-width:740px){body{font-size:16px}.layout{display:block;padding:0 12px 24px}nav{position:static;max-height:none;margin-bottom:18px;padding:8px 10px}nav ol{display:grid;grid-template-columns:1fr 1fr;gap:0 8px}nav a{padding:5px 0}article{padding:28px 20px}.top{padding:16px;letter-spacing:0;font-size:10px}.top span{max-width:60%}h2{font-size:22px}.equation{font-size:16px}table{min-width:530px}}
@media print{@page{size:A4;margin:18mm 16mm}body{background:white;font-size:10.5pt;line-height:1.6}.skip,.top,nav{display:none}.layout{display:block;padding:0;max-width:none}article{border:0;box-shadow:none;padding:0}h1{font-size:25pt}h2{font-size:17pt;break-after:avoid}h3{font-size:12pt;break-after:avoid}a{color:inherit;text-decoration:none}figure,tr,.equation{break-inside:avoid}table{font-size:8pt;min-width:0}.table-wrap{overflow:visible}pre{white-space:pre-wrap;overflow:visible}pre code{white-space:pre-wrap}nav{display:none}thead{display:table-header-group}figure img{max-height:115mm;object-fit:contain}.caption,figcaption{font-size:8.5pt}}
'''
    result = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="An audited engineering study of Winternitz signatures, payload accounting, and signer-state recovery."><title>{title}</title><style>{style}</style></head>
<body><a class="skip" href="#paper">Skip to paper</a>
<header class="top"><span><strong>PQC RESEARCH</strong> &nbsp; / &nbsp; ENGINEERING MANUSCRIPT</span><button type="button" onclick="window.print()">Print / Save PDF</button></header>
<div class="layout"><nav aria-label="Table of contents"><p class="label">CONTENTS</p><ol>{''.join(toc)}</ol></nav>
<main id="paper"><article><div class="kicker">Research revision · 28 September 2026</div>{body}
<footer class="endnote">Evidence: preserved benchmark aggregates, executable source audit, and bounded state-model checks. Figures and styles are embedded; this document requires no network connection.</footer></article></main></div></body></html>'''
    if target.exists():
        existing = target.read_text(encoding='utf-8')
        new_article = re.search(r'<article>(.*?)</article>', result, re.S).group(0)
        new_nav = re.search(r'<nav[^>]*>.*?</nav>', result, re.S).group(0)
        result = re.sub(r'<article>.*?</article>', lambda _: new_article, existing, count=1, flags=re.S)
        result = re.sub(r'<nav[^>]*>.*?</nav>', lambda _: new_nav, result, count=1, flags=re.S)
        result = re.sub(r'<title>.*?</title>', lambda _: '<title>'+title+'</title>', result, count=1)
    target.write_text(result, encoding='utf-8')
    print(f'Rendered {len(toc)} sections; {len(result.encode()):,} bytes, fully offline.')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from-markdown', action='store_true', help='Explicitly rebuild content from Markdown; preserve current HTML styles')
    render(parser.parse_args().from_markdown)
