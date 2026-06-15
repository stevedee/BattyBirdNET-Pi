# daily_plot
# modified by Steve Davis
# =============

import sqlite3
import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.colors import LogNorm
from datetime import datetime
import textwrap
import matplotlib.font_manager as font_manager
from matplotlib import rcParams
from matplotlib.ticker import MaxNLocator

config_path = "/etc/birdnet/birdnet.conf"
userDir = os.path.expanduser('~')

# ******DEBUG************************
DEBUG_NOTES = userDir + "/debug.txt"
DEBUG_MAX_SIZE = 100000  #100kb

def SaveNote2File(debugNote):

    # Create debug file if missing
    if not os.path.exists(DEBUG_NOTES):
        open(DEBUG_NOTES, 'w').close()

    # Trim oversized log
    if os.path.getsize(DEBUG_NOTES) > DEBUG_MAX_SIZE:
        os.remove(DEBUG_NOTES)
        open(DEBUG_NOTES, 'w').close()

    tStamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S: ")

    with open(DEBUG_NOTES, "a") as f:
        f.write(tStamp + debugNote + "\n")

# ******config************************

def get_night_settings(config):
    dusk_hour = int(config["BAT_DUSK"].split(":")[0])
    dawn_hour = int(config["BAT_DAWN"].split(":")[0])

    night_hours = list(range(dusk_hour, 24)) + list(range(0, dawn_hour))

    return dusk_hour, dawn_hour, night_hours
    
# *****bat night *********
def get_bat_night_date(now, dusk_hour, midday_hour=12):
    """
    Returns the canonical 'bat night date' used for filenames and grouping.

    Rule:
    - Before midday → belongs to previous night's label
    - After midday → belongs to current night's label

    This stabilises overnight-to-midday reporting.
    """
    if now.hour < midday_hour:
        return (now - pd.Timedelta(days=1)).date()
    return now.date()

# ******* MAIN ****************

config = {}

with open(config_path, "r") as f:
    for line in f:
        if "=" in line:
            key, value = line.strip().split("=", 1)
            config[key] = value.strip().strip('"')

dusk_hour, dawn_hour, night_hours = get_night_settings(config)

SaveNote2File("daily_plot running...")
#SaveNote2File("BAT_DAWN raw: " + str(config.get("BAT_DAWN"))",  BAT_DUSK raw: " + str(config.get("BAT_DUSK")))


conn = sqlite3.connect(userDir + '/BirdNET-Pi/scripts/birds.db')
df = pd.read_sql_query("SELECT * from detections", conn)

# Convert Date and Time Fields to Panda's format
df['Date'] = pd.to_datetime(df['Date'])
df['Time'] = pd.to_datetime(df['Time'], unit='ns')


# Add round hours to dataframe
df['Hour of Day'] = df['Time'].dt.hour

# Create NightDate using a fixed midday boundary

df['NightDate'] = df['Date']

df.loc[df['Hour of Day'] < 12, 'NightDate'] = (
    df.loc[df['Hour of Day'] < 12, 'NightDate']
    - pd.Timedelta(days=1)
)

# Keep only bat activity hours: Dusk -> Dawn
df = df[
    (df['Hour of Day'] >= dusk_hour)
    | (df['Hour of Day'] < dawn_hour)
]

# Create separate dataframes for separate locations
df_plt = df  # Default to use the whole Dbase

# Add every font at the specified location
font_dir = [userDir + '/BirdNET-Pi/homepage/static']
for font in font_manager.findSystemFonts(font_dir):
    font_manager.fontManager.addfont(font)

# Set font family globally
###rcParams['font.family'] = 'Roboto Flex'

# Get current bat night; runs Dusk to Dawn
now = datetime.now()

current_night = pd.Timestamp(
    get_bat_night_date(now, dusk_hour)
)

df_plt_today = df_plt[df_plt['NightDate'] == current_night]

# Set number of species to report
readings = 20 # as there are only 18 in UK

plt_top10_today = (df_plt_today['Com_Name'].value_counts()[:readings])
df_plt_top10_today = df_plt_today[df_plt_today.Com_Name.isin(plt_top10_today.index)]

# *****mod to sync nights; i.e. clear results at midday ready for current 'night'


if (now.hour >= 12 and now.hour < dusk_hour) or (now.hour >= dusk_hour and df_plt_top10_today.empty):
    SaveNote2File("No detections so far tonight")
    plt.figure(figsize=(10, 8))
    plt.text(
        0.5,
        0.5,
        "No bat detections so far tonight",
        ha='center',
        va='center',
        fontsize=22
    )

    plt.axis('off')
    #create/overwrite Nightly Chart image
    savename = (
        userDir +
        '/BirdSongs/Extracted/Charts/Combo-' +
        current_night.strftime("%Y-%m-%d") +
        '.png'
    )
    plt.savefig(savename)
    SaveNote2File("...Exit daily_plot")
    plt.close()
    exit(0)
   

# Set Palette for graphics
#batBarChartColours = "Reds"
batBarChartColours = "Greys"

# generate y-axis order for all figures based on frequency
freq_order = df_plt_top10_today['Com_Name'].value_counts().iloc[:readings].index
num_species = len(freq_order)
row_height = 0.5
top_bottom_margin = 1.0
fig_height = top_bottom_margin + (num_species * row_height)

# Set up plot axes and titles
f, axs = plt.subplots(
    1, 2,
    figsize=(10, fig_height),
    gridspec_kw=dict(width_ratios=[1, 4]),
    facecolor='#f02080'
)

f.set_constrained_layout(False)

plt.subplots_adjust(
    left=0.25,
    bottom=0.28,
    right=None,
    top=0.85,
    wspace=0,
    hspace=0
)

SaveNote2File("...Hello!")


# make color for max confidence --> this groups by name and calculates max conf
confmax = df_plt_top10_today.groupby('Com_Name')['Confidence'].max()
# reorder confmax to detection frequency order
confmax = confmax.reindex(freq_order)

# norm values for color palette
if confmax.empty:
    SaveNote2File("Empty confmax - using fallback colour scale")
    confmax = pd.Series([1], index=["No data"])

norm = plt.Normalize(confmax.values.min(), confmax.values.max())
colors = plt.cm.Reds(norm(confmax))

# Generate frequency plot
plot = sns.countplot(y='Com_Name', data=df_plt_top10_today, palette=colors, order=freq_order, ax=axs[0])

# Try plot grid lines between bars - problem at the moment plots grid lines on bars - want between bars
z = plot.get_ymajorticklabels()
plot.set_yticklabels(['\n'.join(textwrap.wrap(ticklabel.get_text(), 20)) for ticklabel in plot.get_yticklabels()], fontsize=16)
plot.set(ylabel=None)   
plot.set(xlabel=None)
axs[0].set_xticklabels([])
axs[0].tick_params(axis='x', length=0)
#axs[0].xaxis.set_major_locator(MaxNLocator(integer=True))

# Generate crosstab matrix for heatmap plot
night_hours = list(range(dusk_hour, 24)) + list(range(0, dawn_hour))


heat = pd.crosstab(
    df_plt_top10_today['Com_Name'],
    df_plt_top10_today['Hour of Day']
).reindex(columns=night_hours, fill_value=0)

# Order heatmap Birds by frequency of occurrance
heat.index = pd.CategoricalIndex(heat.index, categories=freq_order)
heat.sort_index(level=0, inplace=True)

# Get current hour
current_hour = now.hour

if heat.empty or heat.values.size == 0 or heat.values.sum() == 0:
    SaveNote2File("Empty heatmap detected - inserting fallback")

    heat = pd.DataFrame(
        [[0]],
        index=["No detections"],
        columns=["0"]
    )

# Generate heatmap plot
plot = sns.heatmap(
    heat,
    norm=LogNorm(),
    annot=True,
    annot_kws={'size': 10, 'rotation': 45},
    fmt="g",
    cmap=batBarChartColours,
    square=False,
    cbar=False,
    linewidths=0.5,
    linecolor="Grey",
    ax=axs[1],
    yticklabels=False
)

# Set color and weight of tick label for current hour
for label in axs[1].get_xticklabels():
    try:
        if int(label.get_text()) == current_hour:
            label.set_color('yellow')
    except:
        pass


# Set heatmap border
for _, spine in plot.spines.items():
    spine.set_visible(True)

plot.set(ylabel=None)
plot.set_xlabel(
    "Hour of Night",
    fontsize=16,
    labelpad=12
)
axs[1].tick_params(axis='x', labelsize=12)
# Set combined plot layout and titles



plt.suptitle(
    "Species for the night of " +
    current_night.strftime("%d-%b-%Y") +
    " ...last updated: " +
    str(now.strftime("%H:%M")),
    fontsize=14,
    fontweight='bold',
    y=0.97
)

# Save combined plot
savename = userDir + '/BirdSongs/Extracted/Charts/Combo-' + current_night.strftime("%Y-%m-%d") + '.png'
plt.savefig(savename)
SaveNote2File("...save combined plot & close")
plt.show()
plt.close()

# Bottom 10 chart now deleted!
