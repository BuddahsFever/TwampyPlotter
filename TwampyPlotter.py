import re
import sys
import pandas as pd
import matplotlib.pyplot as plt

logfile = 'twampy-2026-04-20_09-08-39.log'

all_data = []
current_offset = 0
last_sseq = -1

pattern = re.compile(r"(?P<time>\d{2}:\d{2}:\d{2}).*?Reply from .*?sseq=(?P<sseq>\d+).*?outbound=(?P<out>[\d.]+)ms inbound=(?P<in>[\d.]+)ms")

print("Dubbele as genereren...")

try:
    f = open(logfile, 'r')
except FileNotFoundError:
    print(f"Error: logfile '{logfile}' not found.")
    sys.exit(1)

with f:
    for line in f:
        match = pattern.search(line)
        if match:
            sseq = int(match.group('sseq'))
            if sseq < last_sseq:
                current_offset += last_sseq + 1

            all_data.append({
                'time_str': match.group('time'),
                'display_seq': sseq + current_offset,
                'inbound': float(match.group('in')),
                'outbound': float(match.group('out'))
            })
            last_sseq = sseq

if not all_data:
    print("Error: no matching data found in logfile. Check the log format.")
    sys.exit(1)

df = pd.DataFrame(all_data)

# Bereken gaten
full_range = set(range(df['display_seq'].min(), df['display_seq'].max() + 1))
received_range = set(df['display_seq'])
missing_seqs = sorted(list(full_range - received_range))

# Plotten
fig, ax1 = plt.subplots(figsize=(16, 8))

# 1. Packet Loss (Achtergrond)
if missing_seqs:
    ymax = max(df['inbound'].max(), df['outbound'].max()) + 50
    ax1.vlines(missing_seqs, ymin=0, ymax=ymax,
               colors='gray', alpha=0.08, linewidth=0.5, zorder=1)

# 2. Latency Lijnen
ax1.plot(df['display_seq'], df['outbound'], label='Outbound Latency', color='#3498db', lw=0.7, alpha=0.4, zorder=2)
ax1.plot(df['display_seq'], df['inbound'], label='Inbound Latency', color='#e74c3c', lw=0.8, alpha=0.9, zorder=3)

# Instellingen voor de primaire X-as (Sequence)
ax1.set_xlabel('Packet Sequence (Chronologisch)', fontsize=11)
ax1.set_ylabel('Latency (ms)', fontsize=11)
ax1.set_title('ISP Netwerk Analyse: Latency & Loss vs Tijdlijn', fontsize=14, pad=20)
ax1.grid(True, alpha=0.15)
ax1.legend(loc='upper right')

# 3. De Secundaire X-as (Tijdlijn)
ax2 = ax1.twiny()
ax2.set_xlim(ax1.get_xlim())

num_ticks = max(2, min(8, df.index.size))
tick_indices = [int(round(i * (df.index.size - 1) / (num_ticks - 1))) for i in range(num_ticks)]

ax2.set_xticks(df['display_seq'].iloc[tick_indices])
ax2.set_xticklabels(df['time_str'].iloc[tick_indices], fontsize=10, color='#666')
ax2.set_xlabel('Tijdstip (HH:MM:SS)', fontsize=11, labelpad=10)

# Info box
loss_pct = (len(missing_seqs) / len(full_range)) * 100
ax1.text(0.01, 0.90, f'Totaal Packet Loss: {loss_pct:.2f}%\nMax Inbound Spike: {df["inbound"].max()}ms\nMax Outbound Spike: {df["outbound"].max()}ms',
         transform=ax1.transAxes, fontsize=11, fontweight='bold', bbox=dict(facecolor='white', alpha=0.8))

plt.tight_layout()
plt.savefig('final_isp_report.png', dpi=300)
plt.show()
