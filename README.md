# 서울의 2023~2024년 일별 기온 변화 분석

Python으로 일별 기온 데이터를 정제하고, 그래프와 근거를 바탕으로 인사이트를 작성하는 학습 프로젝트입니다. 보너스 과제는 포함하지 않습니다.

완성된 분석 내용과 그래프는 [REPORT.md](REPORT.md)에서 확인할 수 있습니다.

## 현재 진행 상태

1. 분석 주제와 질문 확정 — 완료
2. 프로젝트 기본 파일과 실행 환경 준비 — 완료 (Python 3.14.6, 가상환경 실행 확인)
3. 실제 데이터 수집 및 기본 점검 — 완료 (731개, 결측치·누락 날짜·중복 없음)
4. 정제, 분석, 그래프 3개 작성 — 완료
5. 리포트 작성 — 완료, 최종 검토 예정
6. GitHub 제출 준비 — 예정

실제 데이터를 수집하고 분석하여 그래프 3개와 인사이트 3개를 REPORT.md에 작성했습니다.

## 분석 계획

- 대상: 서울의 2023-01-01~2024-12-31 일별 기온
- 수집 자료: 기상청 서울(108) 관측소의 일별 기온 관측 자료
- 실제 관측 수: 731개. 누락 날짜, 중복 날짜, 기온 결측치 모두 0개입니다.
- 기법: 7일 이동평균, 월별 평균, 전일 대비 기온 차이(℃)
- 그래프: 일별 기온과 이동평균 / 연도별 월평균 비교 / 전일 대비 기온 차이
- 기온은 0℃와 음수가 가능하므로 백분율 변화율 대신 ℃ 차이를 사용합니다.

## 파일 구성

```text
seoul-temperature-analysis/
├── data/README.md
├── images/01_daily_temperature_moving_average.png
├── images/02_monthly_average_comparison.png
├── images/03_daily_temperature_change.png
├── analysis.py
├── REPORT.md
├── README.md
├── requirements.txt
└── .gitignore
```

## 기본 실행 환경

Python 3.10 이상을 사용합니다. analysis.py는 원본 CSV를 CP949로 읽어 기본 품질을 확인하고, 세 가지 분석과 그래프 생성을 한 번에 수행합니다.

macOS에서 이 폴더를 열고 실행:

```bash
/opt/homebrew/bin/python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python analysis.py
```

실행이 끝나면 터미널에 데이터 점검과 주요 계산 결과가 표시되고, `images` 폴더의 PNG 3개가 갱신됩니다. 사용한 라이브러리 버전은 requirements.txt에 고정했습니다.

## 데이터 준비

원본 CSV는 저작권 정책의 개별 표시를 확인하지 못해 GitHub에 포함하지 않습니다. 실행 전에 [기상청 기온분석](https://data.kma.go.kr/stcs/grnd/grndTaList.do?pgmNo=70)에서 일 / 기본 / 서울(108) / 20230101~20241231 조건으로 내려받아 `data/seoul_2023_2024.csv`로 저장합니다. 자세한 내용은 `data/README.md`에 있습니다.

이 컴퓨터에서는 기본 `python3`가 실행 환경에 따라 3.9.6을 가리킬 수 있어, `/opt/homebrew/bin/python3`(3.14.6)으로 가상환경을 만들었습니다. 이미 준비된 환경은 `.venv/bin/python analysis.py`로 바로 확인할 수 있습니다.
