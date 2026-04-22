import os
import json
import html
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from openai import OpenAI


# =========================
# 1. 기본 설정
# =========================
#load_dotenv()
#
#api_key = os.getenv("OPENAI_API_KEY")
#if not api_key:
#    raise ValueError("OPENAI_API_KEY가 .env 파일에 없습니다.")
#
#client = OpenAI(api_key=api_key)

# =========================
# 1-1. Streamlit API Key 설정
# =========================
api_key = st.secrets["OPENAI_API_KEY"]
client = OpenAI(api_key=api_key)

st.set_page_config(
    page_title="지출결의서 자동 생성기",
    page_icon="🧾",
    layout="wide"
)


# =========================
# 2. 공통 함수
# =========================
def number_to_korean(num: int) -> str:
    if num == 0:
        return "영원정"

    units = ["", "만", "억", "조"]
    nums = ["", "일", "이", "삼", "사", "오", "육", "칠", "팔", "구"]
    small_units = ["", "십", "백", "천"]

    def four_digit_to_korean(n: int) -> str:
        result = ""
        digit_str = str(n).zfill(4)

        for i, ch in enumerate(digit_str):
            digit = int(ch)
            if digit == 0:
                continue

            pos = 4 - i - 1
            if digit == 1 and pos > 0:
                result += small_units[pos]
            else:
                result += nums[digit] + small_units[pos]

        return result

    parts = []
    unit_index = 0

    while num > 0:
        part = num % 10000
        if part > 0:
            parts.append(four_digit_to_korean(part) + units[unit_index])
        num //= 10000
        unit_index += 1

    return "".join(reversed(parts)) + "원정"


def calculate_supply_vat(total_amount: int):
    supply_amount = int(round(total_amount / 1.1))
    vat_amount = total_amount - supply_amount
    return supply_amount, vat_amount


def format_date_korean(date_str: str) -> str:
    if not date_str:
        today = datetime.today()
        return f"{today.year}년 {today.month}월 {today.day}일"

    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return f"{dt.year}년 {dt.month}월 {dt.day}일"
    except ValueError:
        today = datetime.today()
        return f"{today.year}년 {today.month}월 {today.day}일"


def extract_expense_json(user_input: str) -> dict:
    system_prompt = """
너는 회사 지출결의서 작성 보조 AI이다.
사용자의 자연어 입력을 바탕으로 지출결의서 작성에 필요한 정보를 추출하라.

반드시 아래 JSON 형식으로만 응답하라.
설명, 주석, 코드블록 없이 JSON만 출력하라.

JSON 구조:
{
  "expense_date": "YYYY-MM-DD 형식의 날짜",
  "department": "부서명",
  "position": "직급",
  "requester": "청구인 이름",
  "vendor": "거래처명",
  "purpose": "적요에 들어갈 내용",
  "total_amount": 숫자,
  "payment_method": "결제수단",
  "notes": "비고"
}

규칙:
1. 정보가 없으면 빈 문자열 "" 또는 숫자 0으로 넣어라.
2. total_amount는 반드시 숫자만 넣어라.
3. 날짜는 가능한 경우 YYYY-MM-DD 형식으로 변환하라.
4. purpose는 짧고 명확하게 작성하라.
5. JSON 외 다른 문장은 출력하지 마라.
"""

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_input}
        ],
        temperature=0
    )

    result_text = response.choices[0].message.content.strip()
    return json.loads(result_text)


def render_template(template_path: str, data: dict) -> str:
    template = Path(template_path).read_text(encoding="utf-8")

    expense_date = data.get("expense_date", "")
    department = data.get("department", "")
    position = data.get("position", "")
    requester = data.get("requester", "")
    vendor = data.get("vendor", "")
    purpose = data.get("purpose", "")
    total_amount = int(data.get("total_amount", 0))
    payment_method = data.get("payment_method", "")
    notes = data.get("notes", "")

    supply_amount, vat_amount = calculate_supply_vat(total_amount)
    amount_hangul = number_to_korean(total_amount)
    request_date = format_date_korean(expense_date)
    summary_text = f"{vendor} / {purpose}".strip(" /")

    values = {
        "{{department}}": department,
        "{{position}}": position,
        "{{requester}}": requester,
        "{{amount_hangul}}": amount_hangul,
        "{{total_amount}}": f"{total_amount:,}",
        "{{summary_text}}": summary_text,
        "{{supply_amount}}": f"{supply_amount:,}",
        "{{vat_amount}}": f"{vat_amount:,}",
        "{{payment_method}}": payment_method,
        "{{notes}}": notes,
        "{{request_date}}": request_date,
    }

    html_result = template
    for key, value in values.items():
        html_result = html_result.replace(key, str(value))

    return html_result


def make_open_in_new_tab_button(html_content: str, button_text: str = "새 창에서 열기") -> str:
    html_js = json.dumps(html_content)

    return f"""
    <!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                margin: 0;
                padding: 0;
                background: transparent;
                font-family: Arial, sans-serif;
            }}

            .wrap {{
                padding-top: 8px;
            }}

            .open-btn {{
                width: 100%;
                background-color: #6C7EA6;
                color: white;
                border: none;
                padding: 12px 16px;
                border-radius: 10px;
                font-size: 16px;
                font-weight: 600;
                cursor: pointer;
                transition: background-color 0.2s ease;
            }}

            .open-btn:hover {{
                background-color: #5B6D93;
            }}
        </style>
    </head>
    <body>
        <div class="wrap">
            <button class="open-btn" onclick="openExpenseDoc()">
                {html.escape(button_text)}
            </button>
        </div>

        <script>
            function openExpenseDoc() {{
                const htmlContent = {html_js};
                const blob = new Blob([htmlContent], {{ type: "text/html;charset=utf-8" }});
                const url = URL.createObjectURL(blob);

                const newWindow = window.open(url, "_blank");

                if (!newWindow) {{
                    alert("새 창이 차단되었습니다. 브라우저 팝업 차단을 해제해주세요.");
                }}
            }}
        </script>
    </body>
    </html>
    """


# =========================
# 3. 세션 상태 초기화
# =========================
if "result_json" not in st.session_state:
    st.session_state.result_json = None

if "result_html" not in st.session_state:
    st.session_state.result_html = None


# =========================
# 4. 화면
# =========================
st.title("🧾 지출결의서 자동 생성기")

left, right = st.columns([1, 1.2])

with left:
    st.subheader("✏️ 지출 내용 입력")

    st.markdown(
        """
        <style>
        .guide-box {
            background: var(--secondary-background-color);
            color: var(--text-color);
            border: 1px solid rgba(128, 128, 128, 0.25);
            border-radius: 12px;
            padding: 16px 18px;
            margin-bottom: 14px;
            line-height: 1.7;
            font-size: 14px;
        }
    
        .guide-box .guide-title {
            font-weight: 700;
            margin-bottom: 8px;
            color: var(--text-color);
        }
    
        .guide-box .guide-example {
            color: var(--text-color);
            opacity: 0.8;
        }
        </style>
    
        <div class="guide-box">
            <div class="guide-title">입력 안내</div>
            <div>1. 지출 내역 1건에 대해 처리 가능합니다.</div>
            <div>
                2. 지출 내용을 편하게 입력해주세요.<br>
                <span class="guide-example">
                    ex) 2026년 3월 30일 마케팅팀 대리 홍길동이 스타벅스에서 고객 미팅용 다과를 33000원 결제했다.
                </span>
            </div>
            <div>
                3. [날짜, 금액, 목적, 기안자(소속, 직급, 성명), 결제 수단, 비고]의 내용을 AI Agent가 대신 판단하여 지출결의서를 만들어 줍니다!
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    sample_text = """2026년 3월 30일 마케팅팀 대리 홍길동이 스타벅스에서 고객 미팅용 다과를 33000원 결제했다."""
    user_input = st.text_area(
        "지출 내용을 입력하세요",
        value=sample_text,
        height=220
    )

    if st.button("지출결의서 생성", use_container_width=True):
        try:
            result_json = extract_expense_json(user_input)
            result_html = render_template("expense_template_onepage.html", result_json)

            st.session_state.result_json = result_json
            st.session_state.result_html = result_html

            st.success("생성이 완료되었습니다.")
        except Exception as e:
            st.error(f"오류가 발생했습니다: {e}")

    if st.session_state.result_json:
        st.subheader("✅ 추출된 내용")
        st.json(st.session_state.result_json)

with right:
    st.subheader("📄 지출결의서 미리보기")

    if st.session_state.result_html:
        preview_html = st.session_state.result_html

        # 문서 미리보기
        components.html(preview_html, height=900, scrolling=True)

        # 새 창 열기 버튼
        components.html(
            make_open_in_new_tab_button(preview_html, "새 창에서 열기"),
            height=70,
            scrolling=False
        )

        st.info("새 창에서 열린 문서에서 Ctrl + P를 눌러 PDF로 저장하세요.")
    else:
        st.info("왼쪽에서 내용을 입력한 뒤 '지출결의서 생성' 버튼을 눌러주세요.")
