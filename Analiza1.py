"""
Analiza Płynności Banku
========================
Prosta analiza płynności na podstawie danych z yfinance.
Biblioteki: yfinance, pandas, numpy, matplotlib

Instalacja: pip install yfinance pandas numpy matplotlib
"""

import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import warnings
warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# KONFIGURACJA
# ─────────────────────────────────────────────

# Wybierz bank (ticker giełdowy)
TICKER = "PKO.WA"        # PKO BP (Warszawa); zmień np. na "JPM" dla JPMorgan
OKRES  = "5y"            # Dane historyczne: 1y, 2y, 5y, 10y

# ─────────────────────────────────────────────
# 1. POBIERANIE DANYCH
# ─────────────────────────────────────────────

print(f"\n{'='*55}")
print(f"  ANALIZA PŁYNNOŚCI BANKU: {TICKER}")
print(f"{'='*55}\n")

print("► Pobieranie danych z Yahoo Finance...")
bank = yf.Ticker(TICKER)

# Dane cenowe
hist = bank.history(period=OKRES)
if hist.empty:
    raise ValueError(f"Brak danych dla tickera: {TICKER}")

# Bilans i rachunek wyników (roczne)
balance_sheet  = bank.balance_sheet          # kolumny = daty, wiersze = pozycje
income_stmt    = bank.income_stmt
cashflow       = bank.cashflow
info           = bank.info

print(f"  Spółka : {info.get('longName', TICKER)}")
print(f"  Sektor : {info.get('sector', 'N/A')}")
print(f"  Waluta : {info.get('currency', 'N/A')}")
print(f"  Dane   : {hist.index[0].date()} → {hist.index[-1].date()}")
print(f"  Próbek : {len(hist)} dni\n")

# ─────────────────────────────────────────────
# 2. WSKAŹNIKI PŁYNNOŚCI Z BILANSU
# ─────────────────────────────────────────────

print("► Obliczanie wskaźników płynności...\n")

def pobierz_wiersz(df, mozliwe_nazwy):
    """Szuka pierwszej pasującej pozycji w DataFrame."""
    for nazwa in mozliwe_nazwy:
        if nazwa in df.index:
            return df.loc[nazwa]
    return None

# Aktywa obrotowe i zobowiązania bieżące
aktywa_obrotowe     = pobierz_wiersz(balance_sheet, ["Current Assets", "TotalCurrentAssets"])
zobowiazania_biezace = pobierz_wiersz(balance_sheet, ["Current Liabilities", "TotalCurrentLiabilities"])
gotowka             = pobierz_wiersz(balance_sheet, ["Cash And Cash Equivalents", "Cash", "CashAndCashEquivalents"])
pozyczki_krotkoterm = pobierz_wiersz(balance_sheet, ["Short Term Investments", "ShortTermInvestments"])
depozyty            = pobierz_wiersz(balance_sheet, ["Total Deposits", "Deposits"])
pozyczki            = pobierz_wiersz(balance_sheet, ["Net Loan", "NetLoans", "GrossLoans"])
aktywa_razem        = pobierz_wiersz(balance_sheet, ["Total Assets", "TotalAssets"])
kapital             = pobierz_wiersz(balance_sheet, ["Stockholders Equity", "TotalEquityGrossMinorityInterest"])

# Przepływy operacyjne
cfo = pobierz_wiersz(cashflow, ["Operating Cash Flow", "Net Cash From Operating Activities"])

wskazniki = {}

daty = balance_sheet.columns  # kolejne okresy roczne

print(f"{'Wskaźnik':<35} " + "  ".join([str(d.year) for d in daty]))
print("-" * 75)

def linia(nazwa, seria):
    if seria is not None:
        wartosci = "  ".join([f"{v/1e9:>8.2f}B" if not np.isnan(v) else "     N/A " for v in seria])
        print(f"{nazwa:<35} {wartosci}")
    else:
        print(f"{nazwa:<35} {'brak danych':>10}")

# Wyświetl kluczowe pozycje bilansowe (w miliardach)
linia("Gotówka i ekwiwalenty [mld]", gotowka)
linia("Aktywa obrotowe [mld]",       aktywa_obrotowe)
linia("Zobowiązania bieżące [mld]",  zobowiazania_biezace)
linia("Depozyty klientów [mld]",     depozyty)
linia("Kredyty netto [mld]",         pozyczki)
linia("Aktywa razem [mld]",          aktywa_razem)
linia("Przepływy operacyjne [mld]",  cfo)

print()

# ─────────────────────────────────────────────
# 3. OBLICZENIA WSKAŹNIKÓW
# ─────────────────────────────────────────────

wyniki = []

for data in daty:
    row = {"Rok": data.year}

    try:
        ao  = float(aktywa_obrotowe[data])  if aktywa_obrotowe  is not None else np.nan
        zb  = float(zobowiazania_biezace[data]) if zobowiazania_biezace is not None else np.nan
        got = float(gotowka[data])          if gotowka          is not None else np.nan
        dep = float(depozyty[data])         if depozyty         is not None else np.nan
        kred= float(pozyczki[data])         if pozyczki         is not None else np.nan
        at  = float(aktywa_razem[data])     if aktywa_razem     is not None else np.nan
        cap = float(kapital[data])          if kapital          is not None else np.nan
        cf  = float(cfo[data])              if cfo              is not None else np.nan

        # Wskaźnik bieżący (Current Ratio)
        row["Current Ratio"]         = ao / zb   if not np.isnan(ao)  and not np.isnan(zb)  and zb  != 0 else np.nan

        # Wskaźnik szybki (Quick Ratio) — uproszczony dla banku: gotówka / zobowiązania bieżące
        row["Quick Ratio (Cash/CL)"] = got / zb  if not np.isnan(got) and not np.isnan(zb)  and zb  != 0 else np.nan

        # Wskaźnik kredyty/depozyty (Loan-to-Deposit Ratio) — kluczowy dla banków
        row["Loan-to-Deposit Ratio"] = kred / dep if not np.isnan(kred) and not np.isnan(dep) and dep != 0 else np.nan

        # Udział gotówki w aktywach
        row["Cash / Total Assets"]   = got / at  if not np.isnan(got) and not np.isnan(at)  and at  != 0 else np.nan

        # Dźwignia (Assets / Equity)
        row["Leverage (Assets/Eq)"]  = at / cap  if not np.isnan(at)  and not np.isnan(cap) and cap != 0 else np.nan

        # Gotówka / Zobowiązania (pokrycie gotówkowe)
        row["Cash Flow Ratio"]       = cf / zb   if not np.isnan(cf)  and not np.isnan(zb)  and zb  != 0 else np.nan

    except Exception:
        pass  # Brak danych dla danego okresu

    wyniki.append(row)

df_wskazniki = pd.DataFrame(wyniki).set_index("Rok")

print("\n" + "=" * 55)
print("  WSKAŹNIKI PŁYNNOŚCI")
print("=" * 55)
print(df_wskazniki.round(3).to_string())

# ─────────────────────────────────────────────
# 4. INTERPRETACJA
# ─────────────────────────────────────────────

print("\n" + "=" * 55)
print("  INTERPRETACJA (ostatni dostępny rok)")
print("=" * 55)

ostatni = df_wskazniki.dropna(how="all").iloc[-1] if not df_wskazniki.empty else None

if ostatni is not None:
    cr  = ostatni.get("Current Ratio")
    ldr = ostatni.get("Loan-to-Deposit Ratio")
    ca  = ostatni.get("Cash / Total Assets")
    lev = ostatni.get("Leverage (Assets/Eq)")

    if not np.isnan(cr if cr is not None else np.nan):
        ocena = "✅ DOBRA" if cr >= 1.0 else "⚠️  SŁABA"
        print(f"\n  Current Ratio = {cr:.2f}  →  {ocena}  (norma: ≥ 1.0)")
        print(f"    Bank ma {'więcej' if cr >= 1 else 'mniej'} aktywów obrotowych niż zobowiązań bieżących.")

    if ldr is not None and not np.isnan(ldr):
        ocena = "✅ BEZPIECZNY" if 0.7 <= ldr <= 0.9 else ("⚠️  WYSOKI" if ldr > 0.9 else "🔵 NISKI")
        print(f"\n  Loan-to-Deposit = {ldr:.2%}  →  {ocena}  (norma: 70–90%)")
        print(f"    {'Wysoki LDR może sygnalizować ryzyko płynności.' if ldr > 0.9 else 'Niski LDR — bank ma duży bufor płynności.'}")

    if ca is not None and not np.isnan(ca):
        print(f"\n  Gotówka / Aktywa = {ca:.2%}")
        print(f"    {ca*100:.1f}% aktywów banku trzymane jest w gotówce lub ekwiwalentach.")

    if lev is not None and not np.isnan(lev):
        ocena = "⚠️  WYSOKA DŹWIGNIA" if lev > 15 else "✅ UMIARKOWANA"
        print(f"\n  Dźwignia (Aktywa/KW) = {lev:.1f}x  →  {ocena}")
        print(f"    Typowo banki mają dźwignię 10–20x ze względu na naturę działalności.")

# ─────────────────────────────────────────────
# 5. ANALIZA CENY / WOLUMENU (historyczna)
# ─────────────────────────────────────────────

print("\n► Obliczanie zmienności i wolumenu...")

hist["MA_50"]  = hist["Close"].rolling(50).mean()
hist["MA_200"] = hist["Close"].rolling(200).mean()
hist["Zwrot"]  = hist["Close"].pct_change()
hist["Vol_30"] = hist["Zwrot"].rolling(30).std() * np.sqrt(252) * 100  # annualizowana [%]

print(f"\n  Bieżąca cena       : {hist['Close'].iloc[-1]:.2f}")
print(f"  Średnia MA50       : {hist['MA_50'].iloc[-1]:.2f}")
print(f"  Średnia MA200      : {hist['MA_200'].iloc[-1]:.2f}")
print(f"  Zmienność 30d (ann): {hist['Vol_30'].iloc[-1]:.1f}%")
print(f"  Max cena (5 lat)   : {hist['Close'].max():.2f}")
print(f"  Min cena (5 lat)   : {hist['Close'].min():.2f}")

# ─────────────────────────────────────────────
# 6. WYKRESY
# ─────────────────────────────────────────────

print("\n► Rysowanie wykresów...\n")

fig = plt.figure(figsize=(16, 12))
fig.suptitle(f"Analiza Płynności — {info.get('longName', TICKER)}", fontsize=15, fontweight="bold", y=0.98)
gs = gridspec.GridSpec(3, 2, figure=fig, hspace=0.45, wspace=0.35)

# --- Wykres 1: Cena + MA ---
ax1 = fig.add_subplot(gs[0, :])
ax1.plot(hist.index, hist["Close"],  label="Cena zamknięcia", color="#1f77b4", linewidth=1.2)
ax1.plot(hist.index, hist["MA_50"],  label="MA 50",           color="#ff7f0e", linewidth=1.0, linestyle="--")
ax1.plot(hist.index, hist["MA_200"], label="MA 200",          color="#d62728", linewidth=1.0, linestyle="--")
ax1.set_title("Cena akcji z średnimi kroczącymi")
ax1.set_ylabel("Cena")
ax1.legend(fontsize=9)
ax1.grid(True, alpha=0.3)

# --- Wykres 2: Zmienność ---
ax2 = fig.add_subplot(gs[1, 0])
ax2.plot(hist.index, hist["Vol_30"], color="#9467bd", linewidth=1.0)
ax2.axhline(hist["Vol_30"].mean(), color="gray", linestyle="--", linewidth=0.8, label=f"Średnia: {hist['Vol_30'].mean():.1f}%")
ax2.set_title("Zmienność 30-dniowa (annualizowana)")
ax2.set_ylabel("Zmienność [%]")
ax2.legend(fontsize=9)
ax2.grid(True, alpha=0.3)

# --- Wykres 3: Wolumen ---
ax3 = fig.add_subplot(gs[1, 1])
ax3.bar(hist.index, hist["Volume"] / 1e6, color="#8c564b", alpha=0.6, width=1)
ax3.set_title("Wolumen obrotu")
ax3.set_ylabel("Wolumen [mln]")
ax3.grid(True, alpha=0.3)

# --- Wykres 4: Wskaźniki płynności ---
ax4 = fig.add_subplot(gs[2, 0])
kolumny_plot = [c for c in ["Current Ratio", "Quick Ratio (Cash/CL)", "Cash / Total Assets"] if c in df_wskazniki.columns]
if kolumny_plot:
    df_wskazniki[kolumny_plot].plot(ax=ax4, marker="o", linewidth=1.5)
    ax4.axhline(1.0, color="red", linestyle="--", linewidth=0.8, alpha=0.5, label="Próg = 1.0")
    ax4.set_title("Wskaźniki płynności (historyczne)")
    ax4.set_ylabel("Wartość")
    ax4.legend(fontsize=8)
    ax4.grid(True, alpha=0.3)

# --- Wykres 5: LDR i Dźwignia ---
ax5 = fig.add_subplot(gs[2, 1])
kolumny_plot2 = [c for c in ["Loan-to-Deposit Ratio", "Leverage (Assets/Eq)"] if c in df_wskazniki.columns]
if kolumny_plot2:
    df_wskazniki[kolumny_plot2].plot(ax=ax5, marker="s", linewidth=1.5, secondary_y="Leverage (Assets/Eq)" if "Leverage (Assets/Eq)" in kolumny_plot2 else False)
    ax5.set_title("LDR i Dźwignia")
    ax5.set_ylabel("Loan-to-Deposit Ratio")
    ax5.grid(True, alpha=0.3)

plt.savefig("/mnt/user-data/outputs/analiza_plynnosci_banku.png", dpi=130, bbox_inches="tight")
print("  Wykresy zapisane → analiza_plynnosci_banku.png")

plt.show()
print("\n✅ Analiza zakończona.\n")