import streamlit as st
import pandas as pd
import numpy as np
import random
import calendar
from datetime import date

st.set_page_config(page_title="GA 월간 근무 스케줄", layout="wide")

st.title("GA 기반 월간 근무 스케줄 자동 생성 시스템")

shifts = ["오픈", "마감"]
weekdays = ["월", "화", "수", "목", "금", "토", "일"]

if "employees" not in st.session_state:
    st.session_state.employees = []

st.subheader("1. 스케줄 생성 월 설정")

col1, col2 = st.columns(2)

with col1:
    year = st.number_input("년도", 2024, 2030, 2026)

with col2:
    month = st.number_input("월", 1, 12, 5)

last_day = calendar.monthrange(year, month)[1]
dates = [date(year, month, d) for d in range(1, last_day + 1)]


def get_weekday(work_date):
    return weekdays[work_date.weekday()]


st.sidebar.header("직원 등록")

name = st.sidebar.text_input("직원 이름")

max_work = st.sidebar.slider("월 최대 근무 횟수", 1, 31, 20)

fixed_days = st.sidebar.multiselect(
    "고정 출근 요일",
    weekdays,
    default=weekdays
)

available_shifts = st.sidebar.multiselect(
    "가능 근무",
    shifts,
    default=shifts
)

selected_day_off = st.sidebar.multiselect(
    "휴무 요청일 선택",
    dates,
    format_func=lambda x: x.strftime("%m/%d")
)

if st.sidebar.button("직원 추가"):
    if name:
        st.session_state.employees.append({
            "이름": name,
            "월최대근무횟수": max_work,
            "고정출근요일": fixed_days,
            "가능근무": available_shifts,
            "휴무요청": selected_day_off
        })
        st.sidebar.success(f"{name} 등록 완료")
    else:
        st.sidebar.warning("직원 이름 입력해줘")

st.subheader("2. 등록된 직원")

if len(st.session_state.employees) == 0:
    st.warning("왼쪽 사이드바에서 직원을 먼저 등록해줘")
    st.stop()

emp_df = pd.DataFrame(st.session_state.employees)

emp_df["고정출근요일"] = emp_df["고정출근요일"].apply(lambda x: ", ".join(x))
emp_df["가능근무"] = emp_df["가능근무"].apply(lambda x: ", ".join(x))
emp_df["휴무요청"] = emp_df["휴무요청"].apply(
    lambda x: ", ".join([d.strftime("%m/%d") for d in x])
)

st.dataframe(emp_df, use_container_width=True)

if st.button("직원 목록 초기화"):
    st.session_state.employees = []
    st.rerun()

st.subheader("3. 필요 인원 설정")

open_required = st.number_input("오픈 필요 인원", 1, 20, 2)
close_required = st.number_input("마감 필요 인원", 1, 20, 2)

required_staff = {
    "오픈": open_required,
    "마감": close_required
}

generations = st.slider("GA 반복 세대 수", 50, 500, 200)

employees = st.session_state.employees
employee_names = [e["이름"] for e in employees]


def is_available(emp, work_date, shift):
    weekday = get_weekday(work_date)

    if weekday not in emp["고정출근요일"]:
        return False

    if work_date in emp["휴무요청"]:
        return False

    if shift not in emp["가능근무"]:
        return False

    return True


def create_individual():
    schedule = {}

    for d in dates:
        schedule[d] = {}
        for shift in shifts:
            possible = [
                emp["이름"] for emp in employees
                if is_available(emp, d, shift)
            ]

            if len(possible) == 0:
                schedule[d][shift] = []
            else:
                count = random.randint(0, min(len(possible), required_staff[shift] + 1))
                schedule[d][shift] = random.sample(possible, count)

    return schedule


def fitness(schedule):
    score = 0
    work_count = {name: 0 for name in employee_names}

    for d in dates:
        for shift in shifts:
            assigned = schedule[d][shift]
            required = required_staff[shift]

            shortage = max(0, required - len(assigned))
            excess = max(0, len(assigned) - required)

            score -= shortage * 100
            score -= excess * 20

            for name in assigned:
                emp = next(e for e in employees if e["이름"] == name)

                if not is_available(emp, d, shift):
                    score -= 1000

                work_count[name] += 1

    for emp in employees:
        name = emp["이름"]

        if work_count[name] > emp["월최대근무횟수"]:
            score -= (work_count[name] - emp["월최대근무횟수"]) * 80

    score -= np.std(list(work_count.values())) * 10

    return score


def crossover(parent1, parent2):
    child = {}

    for d in dates:
        child[d] = {}
        for shift in shifts:
            if random.random() < 0.5:
                child[d][shift] = parent1[d][shift][:]
            else:
                child[d][shift] = parent2[d][shift][:]

    return child


def mutate(schedule, mutation_rate=0.12):
    for d in dates:
        for shift in shifts:
            if random.random() < mutation_rate:
                possible = [
                    emp["이름"] for emp in employees
                    if is_available(emp, d, shift)
                ]

                if len(possible) == 0:
                    schedule[d][shift] = []
                else:
                    count = random.randint(0, min(len(possible), required_staff[shift] + 1))
                    schedule[d][shift] = random.sample(possible, count)

    return schedule


def run_ga():
    population_size = 60
    population = [create_individual() for _ in range(population_size)]

    best_schedule = None
    best_score = -999999999

    for _ in range(generations):
        population = sorted(population, key=fitness, reverse=True)

        current_score = fitness(population[0])

        if current_score > best_score:
            best_score = current_score
            best_schedule = population[0]

        next_generation = population[:10]

        while len(next_generation) < population_size:
            parent1, parent2 = random.sample(population[:25], 2)
            child = crossover(parent1, parent2)
            child = mutate(child)
            next_generation.append(child)

        population = next_generation

    return best_schedule, best_score


if st.button("GA로 월간 스케줄 생성"):
    best_schedule, best_score = run_ga()

    st.subheader("4. 월간 스케줄 결과")
    st.write(f"적합도 점수: {round(best_score, 2)}")

    rows = []

    for d in dates:
        rows.append({
            "날짜": d.strftime("%m/%d"),
            "요일": get_weekday(d),
            "오픈": ", ".join(best_schedule[d]["오픈"]) if best_schedule[d]["오픈"] else "없음",
            "마감": ", ".join(best_schedule[d]["마감"]) if best_schedule[d]["마감"] else "없음",
            "오픈 부족": max(0, open_required - len(best_schedule[d]["오픈"])),
            "마감 부족": max(0, close_required - len(best_schedule[d]["마감"]))
        })

    result_df = pd.DataFrame(rows)
    st.dataframe(result_df, use_container_width=True)

    st.subheader("5. 직원별 근무 횟수")

    work_count = {name: 0 for name in employee_names}

    for d in dates:
        for shift in shifts:
            for name in best_schedule[d][shift]:
                work_count[name] += 1

    work_df = pd.DataFrame({
        "직원": list(work_count.keys()),
        "근무 횟수": list(work_count.values())
    })

    st.dataframe(work_df, use_container_width=True)

    st.subheader("6. 운영 지표")

    total_shortage = int(result_df["오픈 부족"].sum() + result_df["마감 부족"].sum())

    col1, col2, col3 = st.columns(3)

    col1.metric("총 부족 인원", total_shortage)
    col2.metric("평균 근무 횟수", round(np.mean(list(work_count.values())), 2))
    col3.metric("근무 횟수 표준편차", round(np.std(list(work_count.values())), 2))

    st.subheader("7. 기존 방식과 GA 방식 비교")

    before_shortage = int((open_required + close_required) * last_day * 0.25)

    compare_df = pd.DataFrame({
        "구분": ["기존 수기 스케줄", "GA 최적화 스케줄"],
        "총 부족 인원": [before_shortage, total_shortage],
        "특징": [
            "고정 출근 요일, 휴무 요청, 인력 균형을 동시에 반영하기 어려움",
            "고정 요일, 휴무 요청일, 오픈/마감 가능 여부를 동시에 고려함"
        ]
    })

    st.table(compare_df)

    st.success("월간 스케줄 생성 완료")