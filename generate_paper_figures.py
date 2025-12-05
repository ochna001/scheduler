import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# Set style
sns.set_style("whitegrid")
plt.rcParams.update({'font.size': 12, 'font.family': 'serif'})

def generate_solver_time_chart():
    """Generate Figure 1: Solve Time Comparison"""
    # Updated with actual test results (5 test cases)
    data = {
        'Configuration': [
            'Seq\n(CP-SAT)', 
            'Seq\n(HiGHS)', 
            'Seq\n(CBC)', 
            'Global\n(CP-SAT)', 
            'Global\n(HiGHS)'
        ],
        'Time (seconds)': [34.9, 57.5, 67.9, 37.0, 600],
        'Status': ['Optimal', 'Optimal', 'Optimal', 'Optimal', 'Timeout']
    }
    df = pd.DataFrame(data)

    plt.figure(figsize=(10, 6))
    # Green for Seq, Blue for Global-Opt, Red for Timeout
    colors = ['#55a868', '#55a868', '#55a868', '#4c72b0', '#c44e52']
    ax = sns.barplot(x='Configuration', y='Time (seconds)', data=df, palette=colors)
    
    # Add value labels on top of bars
    labels = ['35s', '58s', '68s', '37s', '>600s\n(Timeout)']
    for i, (v, label) in enumerate(zip(df['Time (seconds)'], labels)):
        ax.text(i, v + 15, label, ha='center', va='bottom', fontweight='bold')
        
    plt.title('Solve Time Comparison (18 blocks, 50 courses)', pad=20)
    plt.ylim(0, 700)
    plt.ylabel('Solve Time (seconds)')
    plt.xlabel('Solver Configuration')
    
    # Add optimal indicator
    for i in range(4):
        plt.text(i, 100, 'Optimal', ha='center', va='bottom', fontsize=9, color='white', weight='bold')

    plt.tight_layout()
    plt.savefig('fig_solver_time.png', dpi=300)
    print("Generated fig_solver_time.png")

def generate_utilization_chart():
    """Generate Figure 2: Room Utilization Comparison"""
    # Calculated weighted average: (64.1% * 11 lec + 52.5% * 6 lab) / 17 total = 60.0%
    data = {
        'Source': ['Cornell Target', 'Seq Strategy\n(Weighted Avg)', 'Austero et al.', 'Schininà'],
        'Utilization (%)': [59.0, 60.0, 75.8, 72.0],
        'Category': ['Benchmark', 'Our Result', 'Benchmark', 'Benchmark']
    }
    df = pd.DataFrame(data)

    plt.figure(figsize=(8, 6))
    colors = {'Benchmark': '#dd8452', 'Our Result': '#55a868'}
    ax = sns.barplot(x='Source', y='Utilization (%)', data=df, 
                     palette=[colors[x] for x in df['Category']], hue='Source', legend=False)
    
    # Add value labels
    for i, v in enumerate(df['Utilization (%)']):
        ax.text(i, v + 1, f"{v}%", ha='center', va='bottom', fontweight='bold')

    # Add target range shading
    plt.axhspan(75, 85, color='red', alpha=0.1, label='Target Range (75-85%)')
    plt.axhline(y=75, color='red', linestyle='--', alpha=0.5)
    plt.axhline(y=85, color='red', linestyle='--', alpha=0.5)
    
    plt.text(0, 80, 'Target Efficiency Zone (75-85%)', color='red', va='center', fontsize=10)

    plt.title('Room Utilization Comparison vs Benchmarks', pad=20)
    plt.ylim(0, 100)
    plt.xticks(rotation=15)
    plt.ylabel('Average Room Utilization (%)')
    plt.xlabel('')
    
    plt.tight_layout()
    plt.savefig('fig_utilization.png', dpi=300)
    print("Generated fig_utilization.png")

if __name__ == "__main__":
    generate_solver_time_chart()
    generate_utilization_chart()
