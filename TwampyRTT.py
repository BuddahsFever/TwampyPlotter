import re
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

logfile = 'twampy-2026-04-14_08-30-01.log'

all_data = []
current_offset = 0
last_sseq = -1

# Regex voor tijd, sseq en latency
pattern = re.compile(r"(?P<time>\d{2}:\d{2}:\d{2}).*?Reply from .*?sseq=(?P<sseq>\d+).*?outbound=(?P<out>[\d.]+)ms inbound=(?P<in>[\d.]+)ms")

print("Dubbele as genereren...")

with open(logfile, 'r') as f:
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

df = pd.DataFrame(all_data)

# Bereken gaten
full_range = set(range(df['display_seq'].min(), df['display_seq'].max() + 1))
received_range = set(df['display_seq'])
missing_seqs = sorted(list(full_range - received_range))

# Plotten
fig, ax1 = plt.subplots(figsize=(16, 8))

# 1. Packet Loss (Achtergrond)
if missing_seqs:
    ax1.vlines(missing_seqs, ymin=0, ymax=df['inbound'].max() + 50, 
               colors='gray', alpha=0.08, linewidth=0.5, zorder=1)

# 2. Latency Lijnen
ax1.plot(df['display_seq'], df['outbound'], label='Outbound Latency (Upload)', color='#3498db', lw=0.7, alpha=0.4, zorder=2)
ax1.plot(df['display_seq'], df['inbound'], label='Inbound Latency (Download)', color='#e74c3c', lw=0.8, alpha=0.9, zorder=3)

# Instellingen voor de primaire X-as (Sequence)
ax1.set_xlabel('Packet Sequence (Chronologisch)', fontsize=11)
ax1.set_ylabel('Latency (ms)', fontsize=11)
ax1.set_title('ISP Netwerk Analyse: Latency & Loss vs Tijdlijn', fontsize=14, pad=20)
ax1.grid(True, alpha=0.15)
ax1.legend(loc='upper right')

# 3. De Secundaire X-as (Tijdlijn)
ax2 = ax1.twiny() # Maak een kopie van de as die de X-as deelt
ax2.set_xlim(ax1.get_xlim()) # Zorg dat ze exact over elkaar vallen

# We kiezen een aantal punten (bijv. elke 10.000 pakketjes) om een tijdstempel te tonen
num_ticks = 8
tick_indices = [int(i) for i in (df.index.size / (num_ticks-1)) * pd.Series(range(num_ticks))]
tick_indices[-1] = df.index.size - 1 # Zorg dat de laatste ook meedoet

ax2.set_xticks(df['display_seq'].iloc[tick_indices])
ax2.set_xticklabels(df['time_str'].iloc[tick_indices], fontsize=10, color='#666')
ax2.set_xlabel('Tijdstip (HH:MM:SS)', fontsize=11, labelpad=10)

# Info box
loss_pct = (len(missing_seqs) / len(full_range)) * 100
ax1.text(0.01, 0.95, f'Totaal Packet Loss: {loss_pct:.2f}%\nMax Inbound Spike: {df["inbound"].max()}ms', 
         transform=ax1.transAxes, fontsize=11, fontweight='bold', bbox=dict(facecolor='white', alpha=0.8))

plt.tight_layout()
plt.savefig('final_isp_report.png', dpi=300)
plt.show()
