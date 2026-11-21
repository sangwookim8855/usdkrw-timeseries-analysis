"""USD/KRW 환율 시계열 분석 (FRED DEXKOUS, 일별).

사용법:
    python analysis.py                  # FRED에서 데이터를 내려받아 분석
    python analysis.py data/usdkrw.csv  # 이미 받은 CSV로 분석

필요 패키지: pandas, numpy, matplotlib
산출물: data/usdkrw.csv, figures/*.png, output/summary.txt
"""
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT_DIR = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT
DATA = ROOT / "data" / "usdkrw.csv"
FIG = OUT_DIR / "figures"
OUT = OUT_DIR / "output"
URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXKOUS&cosd=2021-11-15&coed=2026-11-13"

from matplotlib import font_manager

_have = {f.name for f in font_manager.fontManager.ttflist}
_kr = next((f for f in ["Malgun Gothic", "AppleGothic", "NanumGothic", "Noto Sans CJK KR"] if f in _have), "sans-serif")
plt.rcParams["font.family"] = _kr
plt.rcParams["axes.unicode_minus"] = False
BLUE, ORANGE, GRAY, RED = "#2a6fdb", "#e8833a", "#8a8f98", "#d64545"


def load() -> pd.DataFrame:
    """CSV를 읽는다. 경로 인자가 없으면 FRED에서 내려받아 data/에 저장한다."""
    if len(sys.argv) > 1:
        src = sys.argv[1]
    else:
        src = URL
    raw = pd.read_csv(src, na_values=[".", ""])
    date_col, val_col = raw.columns[0], raw.columns[1]
    df = raw.rename(columns={date_col: "date", val_col: "krw"})
    df["date"] = pd.to_datetime(df["date"])
    df["krw"] = pd.to_numeric(df["krw"], errors="coerce")
    DATA.parent.mkdir(exist_ok=True)
    if src == URL:
        df.to_csv(DATA, index=False)
    return df.set_index("date").sort_index()


def main():
    FIG.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    df = load()
    lines = []
    log = lambda s="": (lines.append(s), print(s))

    # ---------- 1. 기본 정보 / 결측치 ----------
    log("## 기본 정보")
    log(f"기간: {df.index.min().date()} ~ {df.index.max().date()}")
    log(f"전체 행 수: {len(df)}, 결측치: {int(df['krw'].isna().sum())} "
        f"({df['krw'].isna().mean():.1%})")
    # 결측 = 미국 공휴일 등 비거래일. 직전 값으로 채움(ffill): 환율은 휴장일에도 직전 값이 유지된다고 가정
    df["krw"] = df["krw"].ffill()
    df = df.dropna()
    log(f"처리 후 데이터 포인트: {len(df)}")
    log(f"최저 {df['krw'].min():.1f} ({df['krw'].idxmin().date()}), "
        f"최고 {df['krw'].max():.1f} ({df['krw'].idxmax().date()}), 평균 {df['krw'].mean():.1f}")

    # ---------- 2. 시계열 기법 ----------
    df["ma30"] = df["krw"].rolling(30).mean()
    df["ma90"] = df["krw"].rolling(90).mean()
    df["ret"] = df["krw"].pct_change() * 100          # 일간 변화율(%)
    df["vol30"] = df["ret"].rolling(30).std()          # 30일 변동성(일간 변화율 표준편차)

    # 이상치: 일간 변화율의 |z| > 3 (삭제하지 않고 표시만 함 - 실제 시장 충격일 가능성)
    z = (df["ret"] - df["ret"].mean()) / df["ret"].std()
    outliers = df[z.abs() > 3]
    log("\n## 이상치(일간 변화율 |z|>3)")
    log(f"개수: {len(outliers)}")
    for d, r in outliers["ret"].sort_values(key=abs, ascending=False).head(8).items():
        log(f"  {d.date()}  {r:+.2f}%  (환율 {df.loc[d, 'krw']:.1f})")

    # 연도별 통계
    yearly = df.groupby(df.index.year)["krw"].agg(["mean", "min", "max"]).round(1)
    yearly["연간 변화율(%)"] = (df.groupby(df.index.year)["krw"].last().pct_change() * 100).round(1)
    log("\n## 연도별 환율 통계")
    log(yearly.to_string())

    # 월별 평균 (연도 x 월)
    monthly = df["krw"].resample("MS").mean()
    pivot = monthly.to_frame("krw").assign(y=monthly.index.year, m=monthly.index.month)\
        .pivot(index="y", columns="m", values="krw")

    # 변동성 구간
    vol = df["vol30"].dropna()
    log("\n## 30일 변동성")
    log(f"평균 {vol.mean():.2f}%p, 최대 {vol.max():.2f}%p ({vol.idxmax().date()}), "
        f"최소 {vol.min():.2f}%p ({vol.idxmin().date()})")

    # 요일별 평균 변화율 (참고용)
    wd = df["ret"].groupby(df.index.dayofweek).mean().round(3)
    log("\n## 요일별 평균 일간 변화율(%) (0=월 ... 4=금)")
    log(wd.to_string())

    # ---------- 3. 시각화 ----------
    # (1) 환율 + 이동평균 + 이상치
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(df.index, df["krw"], color=GRAY, lw=0.8, alpha=0.7, label="일별 환율")
    ax.plot(df.index, df["ma30"], color=BLUE, lw=1.8, label="30일 이동평균")
    ax.plot(df.index, df["ma90"], color=ORANGE, lw=1.8, label="90일 이동평균")
    ax.scatter(outliers.index, outliers["krw"], color=RED, s=22, zorder=5, label="이상치(|z|>3)")
    ax.set_title("원/달러 환율 추이와 이동평균")
    ax.set_ylabel("원 / 1달러")
    ax.legend(frameon=False, ncol=4, loc="upper left")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIG / "01_trend_ma.png", dpi=150)
    plt.close(fig)

    # (2) 일간 변화율 + 30일 변동성
    fig, axes = plt.subplots(2, 1, figsize=(11, 6), sharex=True)
    axes[0].bar(df.index, df["ret"], color=GRAY, width=1.0)
    axes[0].set_ylabel("일간 변화율 (%)")
    axes[0].set_title("일간 변화율과 30일 변동성")
    axes[0].grid(alpha=0.25)
    axes[1].plot(df.index, df["vol30"], color=BLUE, lw=1.6)
    axes[1].set_ylabel("30일 변동성 (%p)")
    axes[1].grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(FIG / "02_returns_volatility.png", dpi=150)
    plt.close(fig)

    # (3) 연도 x 월 평균 환율 히트맵
    fig, ax = plt.subplots(figsize=(10, 4.5))
    im = ax.imshow(pivot.values, cmap="Blues", aspect="auto")
    ax.set_xticks(range(12), [f"{m}월" for m in range(1, 13)])
    ax.set_yticks(range(len(pivot.index)), pivot.index)
    for i in range(pivot.shape[0]):
        for j in range(pivot.shape[1]):
            v = pivot.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.0f}", ha="center", va="center", fontsize=8,
                        color="white" if v > np.nanmean(pivot.values) else "black")
    ax.set_title("연도·월별 평균 환율 (원/달러)")
    fig.colorbar(im, ax=ax, label="원 / 1달러")
    fig.tight_layout()
    fig.savefig(FIG / "03_monthly_heatmap.png", dpi=150)
    plt.close(fig)

    (OUT / "summary.txt").write_text("\n".join(lines), encoding="utf-8")
    print(f"\n저장 완료: {FIG}, {OUT / 'summary.txt'}")


if __name__ == "__main__":
    main()
