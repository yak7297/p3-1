"""기상청 원본 CSV를 변경하지 않고 데이터 품질을 확인한다."""

from collections import Counter
import csv
from datetime import date, timedelta
from io import StringIO
import math
import os
from pathlib import Path
import sys

PROJECT_DIR = Path(__file__).resolve().parent
os.environ.setdefault("MPLCONFIGDIR", str(PROJECT_DIR / ".matplotlib-cache"))
os.environ.setdefault("MPLBACKEND", "Agg")

import matplotlib.pyplot as plt
import pandas as pd


def inspect_data(path: Path, start: date, end: date) -> None:
    # 기상청 CSV는 한글 인코딩과 표 앞의 검색조건 설명을 고려해 읽는다.
    lines = path.read_text(encoding="cp949").splitlines()
    header = next((i for i, line in enumerate(lines) if line.startswith("날짜,지점,")), None)
    if header is None:
        raise ValueError("CSV에서 날짜/지점 헤더를 찾지 못했습니다.")
    reader = csv.DictReader(StringIO("\n".join(lines[header:])))
    columns = ["평균기온(℃)", "최저기온(℃)", "최고기온(℃)"]
    if not set(["날짜", "지점", *columns]).issubset(reader.fieldnames or []):
        raise ValueError("필수 컬럼이 없습니다.")
    dates = []
    missing = Counter()
    invalid = Counter()
    stations = Counter()
    inconsistent = 0
    for row in reader:
        if not any(str(value or "").strip() for value in row.values()):
            continue  # 파일 끝의 빈 줄은 관측 데이터가 아니다.
        if None in row:
            raise ValueError("컬럼 개수가 맞지 않는 행이 있습니다.")
        day = date.fromisoformat((row["날짜"] or "").strip())
        dates.append(day)
        stations[(row["지점"] or "").strip()] += 1
        values = {}
        for column in columns:
            raw = (row[column] or "").strip()
            if not raw:
                missing[column] += 1
                continue
            try:
                value = float(raw)
                if not math.isfinite(value):
                    raise ValueError("유한한 수가 아님")
                values[column] = value
            except ValueError:
                invalid[column] += 1
        if len(values) == 3 and not (
            values[columns[1]] <= values[columns[0]] <= values[columns[2]]
        ):
            inconsistent += 1
    if not dates:
        raise ValueError("관측 데이터가 없습니다.")
    expected = {start + timedelta(days=i) for i in range((end - start).days + 1)}
    absent = expected - set(dates)
    duplicate = len(dates) - len(set(dates))
    outside = sum(day not in expected for day in dates)
    print(f"\n원본 파일: {path.name} (CP949)")
    print(f"컬럼: {', '.join(reader.fieldnames)}")
    print(f"실제 데이터 수: {len(dates)}개")
    print(f"실제 관측 기간: {min(dates)} ~ {max(dates)}")
    print(f"지점별 행 수: {dict(stations)}")
    print(f"빠진 날짜: {len(absent)}개")
    print(f"중복 날짜 추가 행: {duplicate}개")
    print(f"기간 밖 데이터: {outside}개")
    print(f"날짜 오름차순 정렬: {'예' if dates == sorted(dates) else '아니오'}")
    for column in columns:
        print(f"{column}: 결측치 {missing[column]}개, 숫자 오류 {invalid[column]}개")
    print(f"최저 ≤ 평균 ≤ 최고 관계 위반: {inconsistent}개")
    if absent:
        print("빠진 날짜 예시:", ", ".join(map(str, sorted(absent)[:10])))
    issues = (len(absent) + duplicate + outside + sum(missing.values())
              + sum(invalid.values()) + inconsistent
              + sum(count for station, count in stations.items() if station != "108"))
    if issues:
        raise ValueError("확인이 필요한 항목이 있습니다. 자동 삭제나 보간은 수행하지 않았습니다.")
    print("데이터 기본 점검 완료. 원본은 변경하지 않았습니다.")
    print("기본 점검 통과. 이어서 전일 대비 변화의 통계적 이상치를 검토합니다.")


def load_dataframe(path: Path) -> pd.DataFrame:
    """검색조건 설명을 건너뛰고 분석용 표를 만든다."""
    lines = path.read_text(encoding="cp949").splitlines()
    header = next(i for i, line in enumerate(lines) if line.startswith("날짜,지점,"))
    frame = pd.read_csv(path, encoding="cp949", skiprows=header, skipinitialspace=True)
    frame.columns = frame.columns.str.strip()
    frame["날짜"] = pd.to_datetime(frame["날짜"].astype(str).str.strip())
    temperature_columns = ["평균기온(℃)", "최저기온(℃)", "최고기온(℃)"]
    frame[temperature_columns] = frame[temperature_columns].apply(pd.to_numeric)
    return frame.sort_values("날짜").reset_index(drop=True)


def create_charts(frame: pd.DataFrame, image_dir: Path) -> None:
    """이동평균, 월평균, 전일 대비 기온 차이 그래프를 저장한다."""
    image_dir.mkdir(exist_ok=True)
    plt.rcParams["font.family"] = "Apple SD Gothic Neo"
    plt.rcParams["axes.unicode_minus"] = False

    frame = frame.copy()
    frame["7일 이동평균(℃)"] = frame["평균기온(℃)"].rolling(window=7, min_periods=7).mean()

    fig, axis = plt.subplots(figsize=(13, 6))
    axis.plot(frame["날짜"], frame["평균기온(℃)"], color="#9ecae1", linewidth=0.8,
              label="일평균기온")
    axis.plot(frame["날짜"], frame["7일 이동평균(℃)"], color="#d62728", linewidth=2,
              label="7일 이동평균")
    axis.axhline(0, color="#666666", linewidth=0.7, alpha=0.7)
    axis.set(title="서울 일평균기온과 7일 이동평균", xlabel="날짜", ylabel="기온(℃)")
    axis.grid(alpha=0.25)
    axis.legend()
    fig.tight_layout()
    fig.savefig(image_dir / "01_daily_temperature_moving_average.png", dpi=150)
    plt.close(fig)

    frame["연도"] = frame["날짜"].dt.year
    frame["월"] = frame["날짜"].dt.month
    monthly = frame.groupby(["연도", "월"], as_index=False)["평균기온(℃)"].mean()
    monthly_table = monthly.pivot(index="월", columns="연도", values="평균기온(℃)")

    fig, axis = plt.subplots(figsize=(11, 6))
    for year in monthly_table.columns:
        axis.plot(monthly_table.index, monthly_table[year], marker="o", linewidth=2,
                  label=f"{year}년")
    axis.set(title="2023년과 2024년 서울 월평균기온 비교",
             xlabel="월", ylabel="월평균기온(℃)", xticks=range(1, 13))
    axis.grid(alpha=0.25)
    axis.legend()
    fig.tight_layout()
    fig.savefig(image_dir / "02_monthly_average_comparison.png", dpi=150)
    plt.close(fig)

    frame["전일 대비 차이(℃)"] = frame["평균기온(℃)"].diff()
    changes = frame["전일 대비 차이(℃)"].dropna()
    q1 = changes.quantile(0.25)
    q3 = changes.quantile(0.75)
    iqr = q3 - q1
    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    unusual = frame[
        (frame["전일 대비 차이(℃)"] < lower_bound)
        | (frame["전일 대비 차이(℃)"] > upper_bound)
    ]
    largest_rise = frame.loc[frame["전일 대비 차이(℃)"].idxmax()]
    largest_fall = frame.loc[frame["전일 대비 차이(℃)"].idxmin()]

    fig, axis = plt.subplots(figsize=(13, 6))
    axis.plot(frame["날짜"], frame["전일 대비 차이(℃)"], color="#4c78a8",
              linewidth=0.9, label="전일 대비 차이")
    axis.axhline(0, color="#333333", linewidth=0.8)
    axis.axhline(upper_bound, color="#e45756", linestyle="--", linewidth=1,
                 label=f"IQR 상한 {upper_bound:.1f}℃")
    axis.axhline(lower_bound, color="#e45756", linestyle="--", linewidth=1,
                 label=f"IQR 하한 {lower_bound:.1f}℃")
    axis.scatter(unusual["날짜"], unusual["전일 대비 차이(℃)"], color="#e45756",
                 s=22, zorder=3, label="통계적으로 큰 변화")
    axis.set(title="서울 일평균기온의 전일 대비 변화",
             xlabel="날짜", ylabel="전일 대비 차이(℃)")
    axis.grid(alpha=0.25)
    axis.legend(ncol=2)
    fig.tight_layout()
    fig.savefig(image_dir / "03_daily_temperature_change.png", dpi=150)
    plt.close(fig)

    # 집계 단위에 따라 큰 변화의 기준과 결과가 달라지는지 확인한다.
    weekly = (
        frame.set_index("날짜")["평균기온(℃)"]
        .resample("W-SUN")
        .agg(["mean", "count"])
    )
    weekly = weekly[weekly["count"] == 7].copy()  # 시작·종료의 불완전한 주 제외
    weekly["전주 대비 차이(℃)"] = weekly["mean"].diff()
    weekly_changes = weekly["전주 대비 차이(℃)"].dropna()
    weekly_q1 = weekly_changes.quantile(0.25)
    weekly_q3 = weekly_changes.quantile(0.75)
    weekly_iqr = weekly_q3 - weekly_q1
    weekly_lower = weekly_q1 - 1.5 * weekly_iqr
    weekly_upper = weekly_q3 + 1.5 * weekly_iqr
    weekly_unusual = weekly[
        (weekly["전주 대비 차이(℃)"] < weekly_lower)
        | (weekly["전주 대비 차이(℃)"] > weekly_upper)
    ]

    fig, axis = plt.subplots(figsize=(13, 6))
    axis.plot(weekly.index, weekly["전주 대비 차이(℃)"], color="#59a14f",
              linewidth=1.2, label="전주 대비 주평균 차이")
    axis.axhline(0, color="#333333", linewidth=0.8)
    axis.axhline(weekly_upper, color="#e45756", linestyle="--", linewidth=1,
                 label=f"IQR 상한 {weekly_upper:.1f}℃")
    axis.axhline(weekly_lower, color="#e45756", linestyle="--", linewidth=1,
                 label=f"IQR 하한 {weekly_lower:.1f}℃")
    axis.scatter(weekly_unusual.index, weekly_unusual["전주 대비 차이(℃)"],
                 color="#e45756", s=35, zorder=3, label="통계적으로 큰 변화")
    axis.set(title="서울 주평균기온의 전주 대비 변화",
             xlabel="주 종료일(일요일)", ylabel="전주 대비 주평균 차이(℃)")
    axis.grid(alpha=0.25)
    axis.legend(ncol=2)
    fig.tight_layout()
    fig.savefig(image_dir / "04_weekly_temperature_change.png", dpi=150)
    plt.close(fig)

    print("\n시계열 분석 결과")
    print("7일 이동평균: 첫 6일을 제외한 725개 값 계산")
    print("연도별 월평균: 2023년 12개 월, 2024년 12개 월 계산")
    print("그래프 저장: images/01_daily_temperature_moving_average.png")
    print("그래프 저장: images/02_monthly_average_comparison.png")
    print(f"가장 큰 상승: {largest_rise['날짜']:%Y-%m-%d}, "
          f"{largest_rise['전일 대비 차이(℃)']:+.1f}℃")
    print(f"가장 큰 하락: {largest_fall['날짜']:%Y-%m-%d}, "
          f"{largest_fall['전일 대비 차이(℃)']:+.1f}℃")
    print(f"IQR 기준: {lower_bound:.1f}℃ 미만 또는 {upper_bound:.1f}℃ 초과, "
          f"해당 {len(unusual)}일")
    print("통계적으로 큰 변화는 관측 오류로 단정하거나 삭제하지 않았습니다.")
    print("그래프 저장: images/03_daily_temperature_change.png")
    print("\n집계 단위 변경에 따른 민감도 확인")
    print(f"완전한 7일로 구성된 주: {len(weekly)}개, 전주 대비 변화: "
          f"{weekly_changes.count()}개")
    print(f"주 단위 IQR 기준: {weekly_lower:.1f}℃ 미만 또는 "
          f"{weekly_upper:.1f}℃ 초과, 해당 {len(weekly_unusual)}주")
    print(f"주 단위 큰 변화 방향: 상승 "
          f"{(weekly_unusual['전주 대비 차이(℃)'] > 0).sum()}주, 하락 "
          f"{(weekly_unusual['전주 대비 차이(℃)'] < 0).sum()}주")
    print("그래프 저장: images/04_weekly_temperature_change.png")


def main() -> None:
    if sys.version_info < (3, 10):
        raise SystemExit("Python 3.10 이상이 필요합니다.")

    project_dir = PROJECT_DIR
    start = date(2023, 1, 1)
    end = date(2024, 12, 31)
    print("서울의 2023~2024년 일별 기온 변화 분석")
    print(f"Python 버전: {sys.version.split()[0]}")
    print(f"분석 대상 기간: {start} ~ {end}")
    print(f"기간 내 전체 날짜 수: {(end - start).days + 1}일")
    data_path = project_dir / "data" / "seoul_2023_2024.csv"
    inspect_data(data_path, start, end)
    frame = load_dataframe(data_path)
    create_charts(frame, project_dir / "images")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as error:
        raise SystemExit(f"데이터 확인 중 오류: {error}") from error
