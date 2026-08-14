# CPUC NetGent Experiment Results — Lab VM
**Generated on the lab VM** (`docker-vm-1` at `128.111.5.230:2204`)
**Platform**: NetGent standalone Docker container (native x86_64)
**Apps tested**: YouTube, Twitch, Vimeo
**Bandwidth levels**: 1, 3, 6, 10, 25 Mbps

## Phase 1: Solo Baselines

| App | Rate | Resolution | Avg Buffer (s) | Min Buffer (s) | Dropped Frames | Drop Rate (%) |
|-----|------|-----------|---------------|---------------|---------------|---------------|
| Youtube | 1 Mbps | 854x480 | 70.9 | 40.4 | 9 | 0.44 |
| Youtube | 3 Mbps | 854x480 | 71.4 | 41.7 | 6 | 0.29 |
| Youtube | 6 Mbps | 854x480 | 71.4 | 40.3 | 16 | 0.78 |
| Youtube | 10 Mbps | 854x480 | 71.9 | 42.1 | 10 | 0.49 |
| Youtube | 25 Mbps | 854x480 | 70.9 | 40.6 | 9 | 0.43 |
| Twitch | 1 Mbps | ? | 0.0 | 0 | 0 | 0 |
| Twitch | 3 Mbps | ? | 0.0 | 0 | 0 | 0 |
| Twitch | 6 Mbps | ? | 0.0 | 0 | 0 | 0 |
| Twitch | 10 Mbps | ? | 0.0 | 0 | 0 | 0 |
| Twitch | 25 Mbps | ? | 0.0 | 0 | 0 | 0 |
| Vimeo | 1 Mbps | 1280x720 | 22.5 | 0.7 | 2 | 0.13 |
| Vimeo | 3 Mbps | 1280x720 | 23.1 | 0.6 | 1 | 0.06 |
| Vimeo | 6 Mbps | 1280x720 | 22.9 | 0.7 | 3 | 0.19 |
| Vimeo | 10 Mbps | 1280x720 | 23.1 | 0.7 | 1 | 0.06 |
| Vimeo | 25 Mbps | 1280x720 | 23.1 | 0.6 | 1 | 0.06 |

### Key Findings — Phase 1

- **Youtube**: Lowest buffer at 1 Mbps (70.9s), highest drop rate at 6 Mbps (0.78%)
- **Twitch**: Lowest buffer at 1 Mbps (0.0s), highest drop rate at 1 Mbps (0%)
- **Vimeo**: Lowest buffer at 1 Mbps (22.5s), highest drop rate at 6 Mbps (0.19%)

### Phase 1 Plots

#### Youtube

- QoE comparison: `plots/phase1/youtube_qoe_comparison.png`
- 1 Mbps: `plots/phase1/youtube_1mbps_throughput.png`, `plots/phase1/youtube_1mbps_pktsize.png`
- 3 Mbps: `plots/phase1/youtube_3mbps_throughput.png`, `plots/phase1/youtube_3mbps_pktsize.png`
- 6 Mbps: `plots/phase1/youtube_6mbps_throughput.png`, `plots/phase1/youtube_6mbps_pktsize.png`
- 10 Mbps: `plots/phase1/youtube_10mbps_throughput.png`, `plots/phase1/youtube_10mbps_pktsize.png`
- 25 Mbps: `plots/phase1/youtube_25mbps_throughput.png`, `plots/phase1/youtube_25mbps_pktsize.png`

#### Twitch

- QoE comparison: `plots/phase1/twitch_qoe_comparison.png`
- 1 Mbps: `plots/phase1/twitch_1mbps_throughput.png`, `plots/phase1/twitch_1mbps_pktsize.png`
- 3 Mbps: `plots/phase1/twitch_3mbps_throughput.png`, `plots/phase1/twitch_3mbps_pktsize.png`
- 6 Mbps: `plots/phase1/twitch_6mbps_throughput.png`, `plots/phase1/twitch_6mbps_pktsize.png`
- 10 Mbps: `plots/phase1/twitch_10mbps_throughput.png`, `plots/phase1/twitch_10mbps_pktsize.png`
- 25 Mbps: `plots/phase1/twitch_25mbps_throughput.png`, `plots/phase1/twitch_25mbps_pktsize.png`

#### Vimeo

- QoE comparison: `plots/phase1/vimeo_qoe_comparison.png`
- 1 Mbps: `plots/phase1/vimeo_1mbps_throughput.png`, `plots/phase1/vimeo_1mbps_pktsize.png`
- 3 Mbps: `plots/phase1/vimeo_3mbps_throughput.png`, `plots/phase1/vimeo_3mbps_pktsize.png`
- 6 Mbps: `plots/phase1/vimeo_6mbps_throughput.png`, `plots/phase1/vimeo_6mbps_pktsize.png`
- 10 Mbps: `plots/phase1/vimeo_10mbps_throughput.png`, `plots/phase1/vimeo_10mbps_pktsize.png`
- 25 Mbps: `plots/phase1/vimeo_25mbps_throughput.png`, `plots/phase1/vimeo_25mbps_pktsize.png`

- Cross-app comparison @ 1 Mbps: `plots/phase1/comparison_1mbps_throughput.png`
- Cross-app comparison @ 3 Mbps: `plots/phase1/comparison_3mbps_throughput.png`
- Cross-app comparison @ 6 Mbps: `plots/phase1/comparison_6mbps_throughput.png`
- Cross-app comparison @ 10 Mbps: `plots/phase1/comparison_10mbps_throughput.png`
- Cross-app comparison @ 25 Mbps: `plots/phase1/comparison_25mbps_throughput.png`

## Phase 2: Concurrent Multi-App Testing

Concurrent tests share a single `tc` bandwidth cap and `tcpdump` capture across all browsers.

| Combo | Rate | Shared PCAP Size |
|-------|------|------------------|
| yt_tw | 6 Mbps | 168 MB |
| yt_tw | 10 Mbps | 209 MB |
| yt_vm | 6 Mbps | 183 MB |
| yt_vm | 10 Mbps | 177 MB |
| yt_tw_vm | 6 Mbps | 250 MB |
| yt_tw_vm | 10 Mbps | 264 MB |

### Phase 2 Plots

- yt_tw @ 6 Mbps: `plots/phase2/yt_tw_6mbps_throughput.png`, `plots/phase2/yt_tw_6mbps_pktsize.png`
- yt_tw @ 10 Mbps: `plots/phase2/yt_tw_10mbps_throughput.png`, `plots/phase2/yt_tw_10mbps_pktsize.png`
- yt_vm @ 6 Mbps: `plots/phase2/yt_vm_6mbps_throughput.png`, `plots/phase2/yt_vm_6mbps_pktsize.png`
- yt_vm @ 10 Mbps: `plots/phase2/yt_vm_10mbps_throughput.png`, `plots/phase2/yt_vm_10mbps_pktsize.png`
- yt_tw_vm @ 6 Mbps: `plots/phase2/yt_tw_vm_6mbps_throughput.png`, `plots/phase2/yt_tw_vm_6mbps_pktsize.png`
- yt_tw_vm @ 10 Mbps: `plots/phase2/yt_tw_vm_10mbps_throughput.png`, `plots/phase2/yt_tw_vm_10mbps_pktsize.png`
- Solo vs Concurrent @ 6 Mbps: `plots/phase2/solo_vs_concurrent_6mbps.png`
- Solo vs Concurrent @ 10 Mbps: `plots/phase2/solo_vs_concurrent_10mbps.png`

## Phase 3: AQM Comparison (pfifo vs fq_codel)

All AQM tests run at 6 Mbps. pfifo uses a 50-packet queue limit.

| Combo | Qdisc | PCAP Size |
|-------|-------|-----------|
| yt_tw_6mbps_fq_codel | — | 176 MB |
| yt_tw_6mbps_pfifo | — | 212 MB |
| yt_tw_vm_6mbps_fq_codel | — | 260 MB |
| yt_tw_vm_6mbps_pfifo | — | 243 MB |

### Phase 3 Plots

- yt_tw AQM comparison: `plots/phase3/yt_tw_6mbps_aqm_comparison.png`
- yt_tw_vm AQM comparison: `plots/phase3/yt_tw_vm_6mbps_aqm_comparison.png`
- yt_tw_6mbps_fq_codel: `plots/phase3/yt_tw_6mbps_fq_codel_throughput.png`, `plots/phase3/yt_tw_6mbps_fq_codel_pktsize.png`
- yt_tw_6mbps_pfifo: `plots/phase3/yt_tw_6mbps_pfifo_throughput.png`, `plots/phase3/yt_tw_6mbps_pfifo_pktsize.png`
- yt_tw_vm_6mbps_fq_codel: `plots/phase3/yt_tw_vm_6mbps_fq_codel_throughput.png`, `plots/phase3/yt_tw_vm_6mbps_fq_codel_pktsize.png`
- yt_tw_vm_6mbps_pfifo: `plots/phase3/yt_tw_vm_6mbps_pfifo_throughput.png`, `plots/phase3/yt_tw_vm_6mbps_pfifo_pktsize.png`

---

## Experiment Setup

- **VM**: docker-vm-1 (128.111.5.230:2204), x86_64, 5.8 GB RAM
- **Docker image**: `netgent-standalone:latest` (built from NetGent codebase)
- **Traffic shaping**: `tc` htb + netem inside Docker (--cap-add=NET_ADMIN)
- **Packet capture**: `tcpdump` inside Docker container
- **QoE stats**: NetGent `VideoStatsLogger` (2s interval, 60s per run)
- **Solo runs**: 1 browser per container, per-workflow throttle + capture
- **Concurrent runs**: shared `tc` cap + shared `tcpdump`, N browsers in same container
- **AQM**: pfifo (limit=50) and fq_codel as leaf qdiscs under htb
