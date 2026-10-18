"""Figures for the audited paper; legacy data remain unchanged."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
OUT = Path(__file__).resolve().parents[1]
rows = json.loads((OUT / 'experiments' / 'results_jce.json').read_text())
audit = json.loads((OUT / 'audit' / 'audit_jce.json').read_text())['rows']
plt.rcParams.update({'font.size': 11, 'axes.spines.top': False,
                     'axes.spines.right': False, 'savefig.facecolor':'white'})
sizes = [r['explicit_pk_payload_bytes'] for r in audit]
fig, ax = plt.subplots(figsize=(9, 5))
for key, label, color, marker in [('sign','Signing','#17685d','o'),('verify','Verification','#b17138','s')]:
    ax.errorbar(sizes,[r[f'{key}_ms_mean'] for r in rows],
        yerr=[r[f'{key}_ms_std'] for r in rows],fmt=marker+'-',color=color,
        label=label,capsize=5,lw=1.6)
for x,r in zip(sizes,rows):
    ax.annotate(f"w = {r['w']}",(x,r['sign_ms_mean']),xytext=(0,16),
                textcoords='offset points',ha='center',fontsize=10)
ax.set(xlabel='Explicit-public-key payload (bytes; index / framing excluded)',
       ylabel='Historical latency (ms)',ylim=(-.05,3.65),xlim=(1600,9200))
ax.grid(axis='y',alpha=.2); ax.legend(frameon=False)
fig.text(.1,.98,'Recorded timings · legacy prototype with checksum defect',va='top',fontsize=12,fontweight='bold')
fig.tight_layout(rect=[0,0,1,.94]); fig.savefig(OUT/'figures'/'fig_jce_wtradeoff.png',dpi=180);plt.close(fig)
fig, ax = plt.subplots(figsize=(9,5))
xs=list(range(3)); width=.34
ax.bar([x-width/2 for x in xs],[r['sign_steps'] for r in audit],width,label='Signing',color='#17685d')
ax.bar([x+width/2 for x in xs],[r['verify_steps'] for r in audit],width,label='Verification',color='#b17138')
for x,r in zip(xs,audit):
 for off,key in [(-width/2,'sign_steps'),(width/2,'verify_steps')]:
  ax.text(x+off,r[key]*1.12,f"{r[key]:,}",ha='center',fontsize=10)
ax.set(xticks=xs,xticklabels=[f"w = {r['w']}" for r in audit],ylabel='Chain hash calls (log scale)',yscale='log',ylim=(100,10000))
ax.grid(axis='y',alpha=.15);ax.set_axisbelow(True);ax.legend(frameon=False)
fig.text(.1,.98,'Exact chain work · fixed benchmark message',va='top',fontsize=12,fontweight='bold')
fig.tight_layout(rect=[0,0,1,.94]);fig.savefig(OUT/'figures'/'fig_jce_costmodel.png',dpi=180);plt.close(fig)
print('Regenerated both JCE figures from preserved timing data and audit evidence.')
