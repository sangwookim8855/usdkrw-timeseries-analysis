# 원/달러 환율 시계열 분석

## 실행 방법
```bash
pip install pandas numpy matplotlib
python analysis.py                  # FRED에서 자동 다운로드 후 분석
# 또는 직접 받은 CSV 사용: python analysis.py data/usdkrw.csv
```

## 데이터 수집 방법
- 출처: FRED `DEXKOUS` https://fred.stlouisfed.org/series/DEXKOUS
- `analysis.py`가 `https://fred.stlouisfed.org/graph/fredgraph.csv?id=DEXKOUS&cosd=2021-11-15&coed=2026-11-13` 을 내려받아 `data/usdkrw.csv`로 저장
- 분석 기간: 2021-11-15 ~ 2026-11-13 (1,305개 일별 데이터)
- 이 저장소의 `data/usdkrw.csv`는 위 시리즈 페이지의 DOWNLOAD → CSV로 받은 파일이며, `python analysis.py data/usdkrw.csv`로 바로 재현할 수 있다

## 구성
- `analysis.py` 분석 코드
- `REPORT.md` 리포트
- `figures/` 시각화 이미지, `output/summary.txt` 수치 요약, `data/` 원본 데이터
