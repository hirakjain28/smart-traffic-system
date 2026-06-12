# rl_engine/utils/plotter.py

"""
PLOTTER — Visualizes training progress

WHAT WE PLOT:
  1. Reward curve       — is the AI getting better over time?
  2. Wait time curve    — is traffic flowing better?
  3. Epsilon decay      — is exploration decreasing properly?
  4. Switches per ep    — is agent becoming more decisive?

A GOOD TRAINING RUN looks like:
  Reward:    starts very negative → gradually rises → plateaus near 0
  Wait time: starts high → gradually drops → plateaus at low value
  Epsilon:   starts at 1.0 → decays to 0.05 → stays flat

A BAD TRAINING RUN looks like:
  Reward:   completely flat (not learning) or oscillating wildly
  → Try adjusting learning_rate or network size
"""

import os
import csv
import matplotlib
matplotlib.use('Agg')           # Non-interactive backend (works without display)
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np


def moving_average(data, window=10):
    """
    Smooths a noisy curve by averaging over a sliding window.
    
    Raw reward curve is very noisy (up/down every episode).
    Smoothed curve shows the TREND clearly.
    
    Example:
    Raw:      [-8, -2, -10, -3, -9, -1] (noisy)
    Smoothed: [-5, -4, -5, -4]          (trend visible)
    """
    if len(data) < window:
        return data
    return np.convolve(data, np.ones(window)/window, mode='valid')


def plot_training_results(log_path, save_dir="data/logs"):
    """
    Reads the training log CSV and produces a 4-panel plot.
    
    Parameters:
        log_path  - path to the CSV log file from TrafficLogger
        save_dir  - where to save the plot image
    
    Returns:
        plot_path  - path to the saved plot image
    """

    # ── READ LOG FILE ─────────────────────────────────────────────────────────
    episodes, rewards, waits, epsilons, switches = [], [], [], [], []

    with open(log_path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            episodes.append(int(row["episode"]))
            rewards.append(float(row["total_reward"]))
            waits.append(float(row["avg_wait_time"]))
            epsilons.append(float(row["epsilon"]))
            switches.append(int(row["num_switches"]))

    if not episodes:
        print("⚠️  No data to plot yet.")
        return None

    # ── CREATE FIGURE ─────────────────────────────────────────────────────────
    fig = plt.figure(figsize=(14, 10))
    fig.suptitle("DQN Training Progress — Smart Traffic Management",
                 fontsize=14, fontweight='bold', y=0.98)

    gs = gridspec.GridSpec(2, 2, hspace=0.4, wspace=0.35)

    # ── PANEL 1: Reward Curve ─────────────────────────────────────────────────
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.plot(episodes, rewards, alpha=0.3, color='steelblue', linewidth=0.8,
             label='Raw reward')
    if len(rewards) >= 10:
        smooth = moving_average(rewards, window=10)
        smooth_ep = episodes[len(episodes)-len(smooth):]
        ax1.plot(smooth_ep, smooth, color='steelblue', linewidth=2,
                 label='10-ep average')
    ax1.axhline(y=0, color='green', linestyle='--', alpha=0.5, label='Target (0)')
    ax1.set_xlabel("Episode")
    ax1.set_ylabel("Total Reward")
    ax1.set_title("📈 Reward per Episode")
    ax1.legend(fontsize=8)
    ax1.grid(True, alpha=0.3)

    # Add annotation showing improvement
    if len(rewards) > 20:
        early_avg = np.mean(rewards[:10])
        late_avg  = np.mean(rewards[-10:])
        improvement = ((late_avg - early_avg) / abs(early_avg)) * 100 if early_avg != 0 else 0
        ax1.annotate(f"Δ {improvement:+.1f}%",
                     xy=(episodes[-1], late_avg),
                     fontsize=9, color='green' if improvement > 0 else 'red')

    # ── PANEL 2: Wait Time Curve ───────────────────────────────────────────────
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.plot(episodes, waits, alpha=0.3, color='tomato', linewidth=0.8,
             label='Raw wait time')
    if len(waits) >= 10:
        smooth_w = moving_average(waits, window=10)
        smooth_ep = episodes[len(episodes)-len(smooth_w):]
        ax2.plot(smooth_ep, smooth_w, color='tomato', linewidth=2,
                 label='10-ep average')
    ax2.set_xlabel("Episode")
    ax2.set_ylabel("Avg Wait Time (seconds)")
    ax2.set_title("⏱️  Average Wait Time per Episode")
    ax2.legend(fontsize=8)
    ax2.grid(True, alpha=0.3)

    # ── PANEL 3: Epsilon Decay ────────────────────────────────────────────────
    ax3 = fig.add_subplot(gs[1, 0])
    ax3.plot(episodes, epsilons, color='purple', linewidth=2)
    ax3.fill_between(episodes, epsilons, alpha=0.2, color='purple')
    ax3.axhline(y=0.05, color='gray', linestyle='--', alpha=0.7,
                label='Min epsilon (0.05)')
    ax3.set_xlabel("Episode")
    ax3.set_ylabel("Epsilon (ε)")
    ax3.set_title("🎲 Exploration Rate (Epsilon) Decay")
    ax3.set_ylim(0, 1.1)
    ax3.legend(fontsize=8)
    ax3.grid(True, alpha=0.3)

    # Shade regions
    ax3.axvspan(episodes[0], episodes[len(episodes)//2],
                alpha=0.05, color='red', label='Exploring')
    ax3.axvspan(episodes[len(episodes)//2], episodes[-1],
                alpha=0.05, color='green', label='Exploiting')

    # ── PANEL 4: Switches per Episode ─────────────────────────────────────────
    ax4 = fig.add_subplot(gs[1, 1])
    ax4.bar(episodes, switches, alpha=0.6, color='orange', width=0.8)
    if len(switches) >= 10:
        smooth_s = moving_average(switches, window=10)
        smooth_ep = episodes[len(episodes)-len(smooth_s):]
        ax4.plot(smooth_ep, smooth_s, color='darkorange', linewidth=2,
                 label='10-ep average')
    ax4.set_xlabel("Episode")
    ax4.set_ylabel("Number of Phase Switches")
    ax4.set_title("🔄 Phase Switches per Episode")
    ax4.legend(fontsize=8)
    ax4.grid(True, alpha=0.3)

    # ── SAVE PLOT ─────────────────────────────────────────────────────────────
    os.makedirs(save_dir, exist_ok=True)
    plot_name = os.path.basename(log_path).replace(".csv", "_plot.png")
    plot_path = os.path.join(save_dir, plot_name)
    plt.savefig(plot_path, dpi=150, bbox_inches='tight')
    plt.close()

    print(f"📊 Plot saved to: {plot_path}")
    return plot_path