import streamlit as st
import pandas as pd
from datetime import datetime, time
from pathlib import Path

# =========================
# 설정
# =========================
WAKE_TARGET = time(5, 0)          # 05:00
FASTING_TARGET_HOURS = 16.0       # 16시간
DATA_FILE = Path("routine_log.csv")

MONTH_FMT = "%Y-%m-%d"

st.set_page_config(page_title="하루 루틴 체크", page_icon="✅", layout="centered")

# =========================
# 유틸
# =========================
def load_df() -> pd.DataFrame:
    if DATA_FILE.exists():
        df = pd.read_csv(DATA_FILE)
        return df
    cols = [
        "date",
        "wake_time", "wake_on_time",
        "cold_shower", "yoga", "warm_water",
        "last_meal", "first_meal", "fasting_hours", "fasting_ok",
        "score", "note"
    ]
    return pd.DataFrame(columns=cols)

def save_df(df: pd.DataFrame) -> None:
    df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")

def minutes(t: time) -> int:
    return t.hour * 60 + t.minute

def calc_fasting_hours(last_meal: time, first_meal: time) -> float:
    a = minutes(last_meal)
    b = minutes(first_meal)
    diff = b - a
    if diff <= 0:  # 다음날로 넘어감
        diff += 24 * 60
    return diff / 60.0

def bool_to_int(x: bool) -> int:
    return 1 if x else 0

# =========================
# UI
# =========================
st.title("✅ 하루 루틴 체크")
st.caption("목표: 기상 05:00 이내 / 공복 16시간 이상")

df = load_df()

with st.container():
    st.subheader("오늘 체크 입력")

    c1, c2 = st.columns(2)
    with c1:
        selected_date = st.date_input("날짜", value=datetime.now().date())
    with c2:
        wake_time = st.time_input("기상시간", value=time(5, 0))

    st.divider()

    colA, colB, colC = st.columns(3)
    with colA:
        cold_shower = st.checkbox("냉수샤워")
    with colB:
        yoga = st.checkbox("요가")
    with colC:
        warm_water = st.checkbox("따뜻한 물 마시기")

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        last_meal = st.time_input("마지막 식사 시간", value=time(19, 0))
    with col2:
        first_meal = st.time_input("첫 식사 시간", value=time(11, 0))

    fasting_hours = calc_fasting_hours(last_meal, first_meal)
    fasting_ok = fasting_hours >= FASTING_TARGET_HOURS
    wake_on_time = minutes(wake_time) <= minutes(WAKE_TARGET)

    st.info(
        f"🕒 공복시간: **{fasting_hours:.2f}시간**  → "
        f"{'✅ 목표 달성(16h)' if fasting_ok else '❌ 목표 미달(16h)'}"
    )

    note = st.text_input("메모(선택)", value="")

    # 점수(5점 만점)
    score = (
        bool_to_int(wake_on_time)
        + bool_to_int(cold_shower)
        + bool_to_int(yoga)
        + bool_to_int(warm_water)
        + bool_to_int(fasting_ok)
    )

    st.write(f"⭐ 오늘 점수: **{score}/5**")

    save_clicked = st.button("💾 저장", use_container_width=True)

    if save_clicked:
        date_str = selected_date.strftime(MONTH_FMT)

        row = {
            "date": date_str,
            "wake_time": wake_time.strftime("%H:%M"),
            "wake_on_time": int(wake_on_time),
            "cold_shower": int(cold_shower),
            "yoga": int(yoga),
            "warm_water": int(warm_water),
            "last_meal": last_meal.strftime("%H:%M"),
            "first_meal": first_meal.strftime("%H:%M"),
            "fasting_hours": round(fasting_hours, 2),
            "fasting_ok": int(fasting_ok),
            "score": int(score),
            "note": note.strip(),
        }

        # 같은 날짜는 덮어쓰기
        df2 = df[df["date"] != date_str].copy()
        df2 = pd.concat([df2, pd.DataFrame([row])], ignore_index=True)
        df2 = df2.sort_values("date").reset_index(drop=True)
        save_df(df2)
        df = df2  # 화면 업데이트
        st.success("저장 완료! ✅")

st.divider()

# =========================
# 기록 조회/통계
# =========================
st.subheader("기록 보기")

if df.empty:
    st.warning("아직 저장된 기록이 없습니다.")
else:
    # 보기 편하게 변환
    view = df.copy()
    view["wake_on_time"] = view["wake_on_time"].map({1:"✅", 0:"❌"})
    view["cold_shower"] = view["cold_shower"].map({1:"✅", 0:"❌"})
    view["yoga"] = view["yoga"].map({1:"✅", 0:"❌"})
    view["warm_water"] = view["warm_water"].map({1:"✅", 0:"❌"})
    view["fasting_ok"] = view["fasting_ok"].map({1:"✅", 0:"❌"})

    st.dataframe(
        view[["date","wake_time","wake_on_time","cold_shower","yoga","warm_water","last_meal","first_meal","fasting_hours","fasting_ok","score","note"]],
        use_container_width=True,
        hide_index=True
    )

    st.subheader("최근 통계")
    days = st.slider("최근 며칠?", min_value=3, max_value=60, value=7, step=1)

    dfx = df.copy()
    dfx["date_dt"] = pd.to_datetime(dfx["date"])
    cutoff = dfx["date_dt"].max() - pd.Timedelta(days=days-1)
    recent = dfx[dfx["date_dt"] >= cutoff].copy()

    if recent.empty:
        st.info("해당 기간 기록이 없습니다.")
    else:
        rates = {
            "기상(05:00 이내)": round(recent["wake_on_time"].mean()*100, 1),
            "냉수샤워": round(recent["cold_shower"].mean()*100, 1),
            "요가": round(recent["yoga"].mean()*100, 1),
            "따뜻한 물": round(recent["warm_water"].mean()*100, 1),
            "공복(16h)": round(recent["fasting_ok"].mean()*100, 1),
        }
        st.table(pd.DataFrame.from_dict(rates, orient="index", columns=["준수율(%)"]))

    st.download_button(
        "⬇️ CSV 다운로드",
        data=DATA_FILE.read_bytes(),
        file_name="routine_log.csv",
        mime="text/csv",
        use_container_width=True
    )

st.caption("※ 같은 날짜는 저장 시 자동으로 덮어씁니다.")
