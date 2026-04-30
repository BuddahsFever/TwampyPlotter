import re
import sys
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.legend_handler import HandlerBase
from matplotlib.patches import Rectangle
import numpy as np


class BarcodeHandler(HandlerBase):
    def create_artists(self, legend, orig_handle, xdescent, ydescent, width, height, fontsize, trans):
        rng = np.random.default_rng(42)
        stripes = sorted(rng.uniform(0, width, 14))
        artists = []
        for x in stripes:
            lw = rng.uniform(0.8, 2.5)
            rect = Rectangle((x - lw / 2 + xdescent, ydescent), lw, height,
                              transform=trans, facecolor='gray', edgecolor='none',
                              alpha=rng.uniform(0.3, 0.85))
            artists.append(rect)
        return artists


logfile = 'twampy-2026-04-30_08-30-01.log'

# DOEL: Packet loss meten is de kern van dit script.
#
# Packet loss wordt berekend door Sent en Reply regels te correleren op sseq.
# Een sseq die wel in Sent voorkomt maar niet in Reply is een verloren pakket.
#
# BELANGRIJK: Dit script gaat uit van één doorlopende twampy sessie met een
# unieke oplopende sseq. Als het bash script meerdere sessies start reset
# twampy de sseq naar 0, waardoor sseq nummers hergebruikt worden. In dat
# geval worden verloren packets aan het einde van sessie N onzichtbaar omdat
# de sseq aan het begin van sessie N+1 hetzelfde nummer heeft. De oplossing
# is het bash script zo te configureren dat er altijd één sessie draait
# (COUNT hoog genoeg voor de gewenste meetduur).

all_data = []
pattern_sent  = re.compile(r"(?P<time>\d{2}:\d{2}:\d{2}).*?Sent to .*?\[sseq=(?P<sseq>\d+)\]")
pattern_reply = re.compile(r"(?P<time>\d{2}:\d{2}:\d{2}).*?Reply from .*?sseq=(?P<sseq>\d+).*?rtt=(?P<rtt>[\d.]+)ms.*?outbound=(?P<out>[\d.]+)ms inbound=(?P<in>[\d.]+)ms")

sent_times = {}

print("Logfile inlezen...")

try:
    f = open(logfile, 'r')
except FileNotFoundError:
    print(f"Error: logfile '{logfile}' not found.")
    sys.exit(1)

with f:
    for line in f:
        m = pattern_sent.search(line)
        if m:
            sent_times[int(m.group('sseq'))] = m.group('time')
            continue

        m = pattern_reply.search(line)
        if m:
            all_data.append({
                'sseq':    int(m.group('sseq')),
                'rtt':     float(m.group('rtt')),
                'inbound': float(m.group('in')),
                'outbound': float(m.group('out'))
            })

if not all_data:
    print("Error: no matching data found in logfile. Check the log format.")
    sys.exit(1)

df = pd.DataFrame(all_data)

# Packet loss: verschil tussen verzonden en ontvangen sseq nummers
all_sent_seqs = set(sent_times.keys())
received_seqs = set(df['sseq'])
missing_seqs  = sorted(list(all_sent_seqs - received_seqs))

total_sent = len(all_sent_seqs)
loss_pct   = (len(missing_seqs) / total_sent * 100) if total_sent > 0 else 0.0

print(f"Verzonden: {total_sent}, Ontvangen: {len(df)}, Verloren: {len(missing_seqs)} ({loss_pct:.2f}%)")

# Plotten
fig, ax1 = plt.subplots(figsize=(16, 8))
ymax = max(df['inbound'].max(), df['outbound'].max(), df['rtt'].max())

# 1. Packet Loss (achtergrond)
if missing_seqs:
    ax1.vlines(missing_seqs, ymin=0, ymax=ymax + 2,
               colors='gray', alpha=0.08, linewidth=0.5, zorder=1)

# 2. Latency lijnen
ax1.plot(df['sseq'], df['outbound'], label='Outbound Latency', color='#3498db', lw=0.7, alpha=0.4, zorder=2)
ax1.plot(df['sseq'], df['inbound'],  label='Inbound Latency',  color='#e74c3c', lw=0.8, alpha=0.9, zorder=3)

# RTT gemiddeld over 100 packets (10 seconden)
df['rtt_smooth'] = df['rtt'].rolling(window=100, center=True).mean()
ax1.plot(df['sseq'], df['rtt_smooth'], label='RTT (gemiddeld)', color='#2ecc71', lw=1.0, alpha=0.8, zorder=2)

ax1.set_xlabel('Packet Sequence (Chronologisch)', fontsize=11)
ax1.set_ylabel('Latency (ms)', fontsize=11)
ax1.set_title('ISP Netwerk Analyse: Latency & Loss vs Tijdlijn', fontsize=14, pad=20)
ax1.grid(True, alpha=0.15)

loss_handle = ax1.vlines([], [], [], colors='gray', alpha=0.5, linewidth=1, label='Packet Loss')
ax1.legend(loc='upper right', handler_map={loss_handle: BarcodeHandler()})

# 3. Secundaire X-as op basis van Sent tijden
ax2 = ax1.twiny()
ax2.set_xlim(ax1.get_xlim())

num_ticks = 8
seq_min = min(all_sent_seqs)
seq_max = max(all_sent_seqs)
tick_seqs = [int(round(seq_min + i * (seq_max - seq_min) / (num_ticks - 1))) for i in range(num_ticks)]

available = sorted(all_sent_seqs)
tick_positions = []
tick_labels = []
for ts in tick_seqs:
    closest = min(available, key=lambda s: abs(s - ts))
    tick_positions.append(closest)
    tick_labels.append(sent_times[closest])

ax2.set_xticks(tick_positions)
ax2.set_xticklabels(tick_labels, fontsize=10, color='#666')
ax2.set_xlabel('Tijdstip (HH:MM:SS)', fontsize=11, labelpad=10)

# Info box
ax1.text(0.01, 0.881,
         f'Totaal Packet Loss: {loss_pct:.2f}%\n'
         f'Max Inbound Spike: {df["inbound"].max():.2f}ms\n'
         f'Max Outbound Spike: {df["outbound"].max():.2f}ms\n'
         f'Max RTT Spike: {df["rtt"].max():.2f}ms',
         transform=ax1.transAxes, fontsize=11, fontweight='bold',
         bbox=dict(facecolor='white', alpha=0.8))

plt.tight_layout()
plt.savefig('final_isp_report.png', dpi=300)
plt.show()
print("Grafiek opgeslagen als final_isp_report.png")
