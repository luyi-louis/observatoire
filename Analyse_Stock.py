# ---------------------------------------------
# ----- INFORMATIONS -----
#   Author          : louis tomczyk + ChatGPT + Grok
#   Institution     : 
#   Profile         : https://github.com/luyi-louis
#   Version         : 1.1.1
#   Date            : 2025-10-23
#   License         : Creative Commons Attribution-ShareAlike 4.0 International
#                       (CC BY-SA 4.0)
#                       CAN:    commercial use - modify - distribute
#                       CANNOT: apply legal terms or technological measures
#                               that restrict others from doing anything the
#                               license permits
#                       MUST:   give appropriate credit - provide a link to the
#                               license
#                               indicate if changes were made - share alike
#                               (same license)
#                       NO:     warranty - liability
#
# ----- CHANGELOG -----
#   1.0.0 (2025-10-21) - Creation
#   1.1.0 (2025-10-23) - merged from Analyse_Stock_Or, Analyse_Stock_Argent,
#                           and Analyse_Ratio_Or_Argent
#   1.1.1 (2025-10-23) - brent added
#   1.1.2 (2026-02-02) - copper added
#
# ----- MAIN IDEA -----
#   Unified tools for studying gold, silver, or gold/silver ratio with
#   technical indicators and visualisations.
#
# ----- DEPENDENCES -----
#   pandas, numpy, matplotlib, scipy, statsmodels
#   pip install pandas numpy matplotlib scipy statsmodels
#
# ----- BIBLIOGRAPHY -----
#   Articles/Books:
#   [A1] Authors         :
#        Title           :
#        Journal/Editor  :
#        Volume - N°     :
#        Date            :
#        DOI/ISBN        :
#        Pages           :
#  ----------------------
#   CODE
#   [C1] Author          : louis tomczyk + ChatGPT
#        Contact         : https://github.com/luyi-louis
#        Laboratory/team :
#        Institution     :
#        Date            : 2025-10-23
#        Program Title   : Analyse_Metals
#        Code Version    : 1.0.0
#        Type            : Python script
#        Web Address     :
# ---------------------------------------------

#%% ===========================================================================
# --- LIBRARIES ---
# =============================================================================
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
from scipy import stats
from statsmodels.tsa.stattools import adfuller

#%% ===========================================================================
# --- PARAMETERS ---
# =============================================================================
START_DATE  = "2020-01"
END_DATE    = "2026-01"
SMA_WINDOWS = [12, 24]  # Simple Moving Average periods (months)
EMA_WINDOWS = [12, 26]  # EMA for MACD (fast: 12, slow: 26)
MACD_SIGNAL = 9         # MACD signal line period
RSI_PERIOD  = 14        # RSI period (months)
BB_WINDOW   = 20        # Bollinger Bands period
ROLL_WINDOW = 12        # Rolling volatility window (months)

#%% ===========================================================================
# --- MAIN ANALYSIS FUNCTION ---
# =============================================================================
def analyse(what):
    """
    Parameters:
        what (str): 'or' for gold, 'argent' for silver, 'ratio_oa' for gold/silver ratio.
    """
    # Validate input
    valid_inputs = ["or", "argent", "ratio_oa","brent","cuivre"]
    if what not in valid_inputs:
        raise ValueError(f"Invalid input for 'what'. Must be one of {valid_inputs}")

    #%% =======================================================================
    # --- LOAD DATA ---
    # =========================================================================
    
    data_dir    = "data"
    fig_dir     = "figs"
    
    # Create figs folder if it doesn't exist
    os.makedirs(fig_dir, exist_ok=True)
    
    if what in ["or", "ratio_oa"]:
        or_file = os.path.join(data_dir, "valeurs_mensuelles_or.csv")
        if not os.path.exists(or_file):
            raise FileNotFoundError(f"Le fichier '{or_file}' est introuvable.")
        df_or = pd.read_csv(or_file, sep=",", header=0,
                            names=["date", "prix"], dtype={"date": str, "prix": float})
        df_or["date"] = pd.to_datetime(df_or["date"], format="%Y-%m")
        df_or = df_or.set_index("date").sort_index().asfreq("MS")
        df_or = df_or.loc[START_DATE:END_DATE]
    
    if what in ["argent", "ratio_oa"]:
        arg_file = os.path.join(data_dir, "valeurs_mensuelles_argent.csv")
        if not os.path.exists(arg_file):
            raise FileNotFoundError(f"Le fichier '{arg_file}' est introuvable.")
        df_arg = pd.read_csv(arg_file, sep=",", header=0,
                             names=["date", "prix"], dtype={"date": str, "prix": float})
        df_arg["date"] = pd.to_datetime(df_arg["date"], format="%Y-%m")
        df_arg = df_arg.set_index("date").sort_index().asfreq("MS")
        df_arg = df_arg.loc[START_DATE:END_DATE]

    if what in ["brent"]:
        arg_file = os.path.join(data_dir, "valeurs_mensuelles_brent.csv")
        if not os.path.exists(arg_file):
            raise FileNotFoundError(f"Le fichier '{arg_file}' est introuvable.")
        df_arg = pd.read_csv(arg_file, sep = ",", header=0,
                             names=["date", "prix"], dtype={"date": str, "prix": float})
        df_arg["date"] = pd.to_datetime(df_arg["date"], format="%Y-%m")
        df_arg = df_arg.set_index("date").sort_index().asfreq("MS")
        df_arg = df_arg.loc[START_DATE:END_DATE]
        
    if what in ["cuivre"]:
        arg_file = os.path.join(data_dir, "valeurs_mensuelles_cuivre.csv")
        if not os.path.exists(arg_file):
            raise FileNotFoundError(f"Le fichier '{arg_file}' est introuvable.")
        df_arg = pd.read_csv(arg_file, sep = ",", header=0,
                             names=["date", "prix"], dtype={"date": str, "prix": float})
        df_arg["date"] = pd.to_datetime(df_arg["date"], format="%Y-%m")
        df_arg = df_arg.set_index("date").sort_index().asfreq("MS")
        df_arg = df_arg.loc[START_DATE:END_DATE]


    # Create main DataFrame
    if what == "ratio_oa":
        df          = pd.DataFrame(index=df_or.index)
        df["Or"]    = df_or["prix"]
        df["Arg"]   = df_arg["prix"]
        df["prix"]  = df["Or"] / df["Arg"]  # Gold/Silver ratio
    else:
        df = df_or if what == "or" else df_arg
        df = df.rename(columns={"prix": "prix"})  # Ensure consistent column name

    if len(df) < 12:
        raise ValueError("Pas assez de données (minimum 12 mois requis).")

    #%% =======================================================================
    # --- RETURNS & TRANSFORMATIONS ---
    # =========================================================================
    df["ret_simple"] = df["prix"].pct_change()
    df["ret_log"] = np.log(df["prix"]).diff()

    # Annualized mean (approximation)
    mean_monthly = df["ret_simple"].mean().round(3)
    annualised_mean_simple = (((1 + mean_monthly)**12 - 1)*100).round(1) if pd.notna(mean_monthly) else np.nan
    print(f"\nRendement simple moyen mensuel ({what}): {(mean_monthly*100):.2f}%")
    print(f"Rendement annualisé approx ({what}): {annualised_mean_simple:.2f}%")

    #%% =======================================================================
    # --- MOVING AVERAGES & EMA ---
    # =========================================================================
    for w in SMA_WINDOWS:
        df[f"SMA_{w}"] = df["prix"].rolling(window=w, min_periods=1).mean()

    df[f"EMA_{EMA_WINDOWS[0]}"] = df["prix"].ewm(span=EMA_WINDOWS[0], adjust=False).mean()
    df[f"EMA_{EMA_WINDOWS[1]}"] = df["prix"].ewm(span=EMA_WINDOWS[1], adjust=False).mean()

    #%% =======================================================================
    # --- MACD & RSI ---
    # =========================================================================
    # MACD
    df["MACD"] = df[f"EMA_{EMA_WINDOWS[0]}"] - df[f"EMA_{EMA_WINDOWS[1]}"]
    df["MACD_signal"] = df["MACD"].ewm(span=MACD_SIGNAL, adjust=False).mean()
    df["MACD_hist"] = df["MACD"] - df["MACD_signal"]

    # RSI
    def compute_RSI(series, period=RSI_PERIOD):
        delta = series.diff()
        up = delta.clip(lower=0.0)
        down = -1 * delta.clip(upper=0.0)
        roll_up = up.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
        roll_down = down.ewm(alpha=1/period, adjust=False, min_periods=period).mean()
        rs = roll_up / roll_down
        rsi = 100 - (100 / (1 + rs))
        return rsi

    df[f"RSI_{RSI_PERIOD}"] = compute_RSI(df["prix"])

    #%% =======================================================================
    # --- BOLLINGER BANDS ---
    # =========================================================================
    df["BB_mid"] = df["prix"].rolling(window=BB_WINDOW, min_periods=1).mean()
    df["BB_std"] = df["prix"].rolling(window=BB_WINDOW, min_periods=1).std()
    df["BB_upper"] = df["BB_mid"] + 2 * df["BB_std"]
    df["BB_lower"] = df["BB_mid"] - 2 * df["BB_std"]

    #%% =======================================================================
    # --- ROLLING VOLATILITY ---
    # =========================================================================
    df["vol_roll"] = df["ret_log"].rolling(window=ROLL_WINDOW, min_periods=1).std()
    df["vol_annualised"] = df["vol_roll"] * np.sqrt(12)
    vol_low = df["vol_annualised"].quantile(0.25)
    vol_high = df["vol_annualised"].quantile(0.75)

    #%% =======================================================================
    # --- CAGR & MAX DRAWDOWN ---
    # =========================================================================
    def CAGR(price_series):
        price_series = price_series.dropna()
        if len(price_series) < 2:
            return np.nan
        start = price_series.iloc[0]
        end = price_series.iloc[-1]
        n_years = (price_series.index[-1] - price_series.index[0]).days / 365.25
        return (end / start)**(1.0 / n_years) - 1

    cagr = (CAGR(df["prix"])*100).round(2)
    print(f"\nCAGR (annual, {what}): {cagr:.2f}%")

    def max_drawdown(series):
        roll_max = series.cummax()
        drawdown = series / roll_max - 1.0
        return drawdown.min()

    mdd = (max_drawdown(df["prix"].dropna())*100).round(2)
    print(f"Max drawdown ({what}): {mdd:.2f}%")

    vol_hist = ((df["ret_log"].std() * np.sqrt(12))*100).round(2)
    print(f"Volatilité historique annualisée ({what}): {vol_hist:.2f}%")

    #%% =======================================================================
    # --- STATIONARITY TEST ---
    # =========================================================================
    adf_results = {}
    try:
        adf_log = adfuller(np.log(df["prix"].dropna()), autolag="AIC")
        adf_results["log_price"] = {
            "adf_stat": adf_log[0],
            "p_value": adf_log[1],
            "used_lag": adf_log[2],
            "nobs": adf_log[3]
        }
    except Exception as e:
        adf_results["log_price"] = {"error": str(e)}

    try:
        adf_ret = adfuller(df["ret_log"].dropna(), autolag="AIC")
        adf_results["log_return"] = {
            "adf_stat": adf_ret[0],
            "p_value": adf_ret[1],
            "used_lag": adf_ret[2],
            "nobs": adf_ret[3]
        }
    except Exception as e:
        adf_results["log_return"] = {"error": str(e)}

    #%% =======================================================================
    # --- VISUALIZATIONS ---
    # =========================================================================
    plt.close("all")
    plt.style.use("default")

    # -------------------------------------------------------------------------
    # Figure 1: Price/Ratio with SMA and Bollinger Bands
    title = {"or": "Prix de l'or", "argent": "Prix de l'argent", "ratio_oa": "Ratio Or/Argent", "brent": "Prix du baril de brent", "cuivre": "Prix de la tonne de cuivre"}
    ylabel = {"or": "Prix (USD)", "argent": "Prix (USD)", "ratio_oa": "Or / Argent", "brent": "Prix (USD)", "cuivre": "Prix (USD)"}
    filename_prefix = {"or": "gold", "argent": "silver", "ratio_oa": "ratio_oa","brent": "brent","cuivre": "cuivre"}

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.plot(df.index, df["prix"], label="Prix (spot)" if what in ["or", "argent"] else "Ratio Or/Argent",
            linewidth=2, color="black")
    colors = ["blue", "green"]
    for i, w in enumerate(SMA_WINDOWS):
        ax.plot(df.index, df[f"SMA_{w}"], label=f"SMA {w}M", linewidth=1, color=colors[i])
    ax.plot(df.index, df["BB_upper"], linestyle="--", label="BB upper", linewidth=0.8, color="gray")
    ax.plot(df.index, df["BB_lower"], linestyle="--", label="BB lower", linewidth=0.8, color="gray")
    ax.set_title(f"{title[what]} avec SMA et Bollinger Bands")
    ax.set_xlabel("Date")
    ax.set_ylabel(ylabel[what])
    ax.grid(True)
    ax.legend()
    fig.tight_layout()
    plt.show()

    # -------------------------------------------------------------------------
    # Figure 2: Log-price or Log-ratio
    fig2, ax2 = plt.subplots(figsize=(10, 4))
    ax2.plot(df.index, np.log(df["prix"]), label="ln(prix [USD])" if what in ["or", "argent"] else "ln(ratio)")
    ax2.set_title(f"ln({title[what]})")
    ax2.set_xlabel("Date")
    ax2.set_ylabel("ln(prix [USD])" if what in ["or", "argent"] else "ln(ratio)")
    ax2.legend()
    ax2.grid(True)
    fig2.tight_layout()
    plt.show()

    # -------------------------------------------------------------------------
    # Figure 3: MACD
    fig3, ax3 = plt.subplots(figsize=(10, 5))
    ax3.plot(df.index, df["MACD"], label="MACD", color="blue", linewidth=1.2, linestyle="dashed")
    ax3.plot(df.index, df["MACD_signal"], label="Signal", color="black", linewidth=1.0)
    ax3.bar(df.index, df["MACD_hist"], label="Histogramme", color="black", alpha=0.4, width=50)
    ax3.set_ylabel("MACD / Signal / Histogramme")
    ax3.legend(loc="upper left")
    ax3.grid(True)
    ax_price = ax3.twinx()
    ax_price.plot(df.index, df["prix"], label=title[what], color="green", linewidth=1.2)
    ax_price.set_ylabel(ylabel[what], color="green")
    ax_price.tick_params(axis='y', colors='green')
    ax_price.legend(loc="upper right")
    ax3.set_title(f"MACD et {title[what]}")
    fig3.tight_layout()
    plt.show()

    # -------------------------------------------------------------------------
    # Figure 4: RSI with overbought/oversold zones
    rsi_labels = {
        "or": {"overbought": "Surachat", "oversold": "Survente"},
        "argent": {"overbought": "Surachat", "oversold": "Survente"},
        "ratio_oa": {"overbought": "Or cher", "oversold": "Or bon marché"},
        "brent": {"overbought": "Surachat", "oversold": "Survente"},
        "cuivre": {"overbought": "Surachat", "oversold": "Survente"},
    }
    fig4, ax4 = plt.subplots(figsize=(10, 3))
    ax4.plot(df.index, df[f"RSI_{RSI_PERIOD}"], label=f"RSI {RSI_PERIOD} M", color="blue", linewidth=1.2)
    ax4.fill_between(df.index, 70, 100, color="red", alpha=0.2, label=rsi_labels[what]["overbought"])
    ax4.fill_between(df.index, 0, 30, color="green", alpha=0.2, label=rsi_labels[what]["oversold"])
    ax4.set_ylim(0, 100)
    ax4.grid(True)
    ax4.legend(loc="upper left")
    ax4.set_title(f"RSI {title[what]} ({RSI_PERIOD} mois)")
    fig4.tight_layout()
    plt.show()

    # -------------------------------------------------------------------------
    # Figure 5: Rolling annualized volatility with zones
    fig5, ax5 = plt.subplots(figsize=(10, 3))
    ax5.plot(df.index, df["vol_annualised"], label="Vol annualisée roulante", color="blue", linewidth=1.2)
    ax5.fill_between(df.index, vol_low, df["vol_annualised"].max(),
                     where=(df["vol_annualised"] >= vol_high), color="red", alpha=0.2, label="Turbulences")
    ax5.fill_between(df.index, 0, vol_low, color="green", alpha=0.2, label="Calme")
    ax5.set_title(f"Volatilité annualisée (rolling {ROLL_WINDOW} mois, {title[what]})")
    ax5.set_ylabel("Volatilité (%)")
    ax5.set_ylim(0, df["vol_annualised"].max()*1.1)
    ax5.grid(True)
    ax5.legend(loc="upper left")
    fig5.tight_layout()
    plt.show()


    # Save figures in figs folder
    fig.savefig(os.path.join(fig_dir, f"{filename_prefix[what]}_price_sma_bb.png"), dpi=150)
    fig2.savefig(os.path.join(fig_dir, f"{filename_prefix[what]}_log_trend.png"), dpi=150)
    fig3.savefig(os.path.join(fig_dir, f"{filename_prefix[what]}_macd_doubly_axis_colored.png"), dpi=150)
    fig4.savefig(os.path.join(fig_dir, f"{filename_prefix[what]}_rsi_zones.png"), dpi=150)
    fig5.savefig(os.path.join(fig_dir, f"{filename_prefix[what]}_volatility_zones.png"), dpi=150)


    #%% =======================================================================
    # --- SUMMARY ---
    # =========================================================================
    print(f"\n--- Synthèse ({what}) ---")
    print(f"Période analysée : {df.index.min().date()} --> {df.index.max().date()}")
    print(f"Nombre de points : {len(df.dropna(subset=['prix']))}")
    print(f"Rendement moyen annualisé (CAGR) : {cagr:.2f}%")
    print(f"Volatilité historique annualisée : {vol_hist:.2f}%")
    print(f"Perte maximale historique (Max Drawdown) : {mdd:.2f}%")

    if f"RSI_{RSI_PERIOD}" in df.columns:
        last_rsi = df[f"RSI_{RSI_PERIOD}"].iloc[-1]
        rsi_status = rsi_labels[what]["overbought"] if last_rsi > 70 else rsi_labels[what]["oversold"] if last_rsi < 30 else "neutre"
        print(f"Dernier RSI ({RSI_PERIOD} périodes) : {last_rsi:.2f} ({rsi_status})")
    if "MACD" in df.columns:
        last_macd = df["MACD"].iloc[-1]
        print(f"Dernier MACD : {last_macd:.2f} ({'momentum haussier' if last_macd > 0 else 'momentum baissier'})")

    print("\nTests de stationnarité (ADF) :")
    for k, v in adf_results.items():
        if "error" in v:
            print(f"{k} : erreur lors du calcul -> {v['error']}")
        else:
            adf_stat = v["adf_stat"]
            p_val = v["p_value"]
            if k == "log_price":
                print(f"- {k} : adf_stat={adf_stat:.2f}, p_value={p_val:.3f} -> "
                      f"{'non-stationnaire (ne pas différencier)' if p_val > 0.05 else 'stationnaire'}")
            else:
                print(f"- {k} : adf_stat={adf_stat:.2f}, p_value={p_val:.3f} -> "
                      f"{'stationnaire' if p_val <= 0.05 else 'non-stationnaire'}")

#%% ===========================================================================
# --- EXAMPLE USAGE ---
# =============================================================================
if __name__ == "__main__":
    analyse("or")       # or, argent, ratio_oa, brent

