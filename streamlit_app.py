import sqlite3
import streamlit as st
import pandas as pd
import folium
from streamlit_folium import st_folium
from textblob import TextBlob
import plotly.express as px
import time

# Connect to SQLite database
conn = sqlite3.connect('places_reviews.db', check_same_thread=False)
c = conn.cursor()

# Create the tables if they don't exist
def init_db():
    c.execute('''CREATE TABLE IF NOT EXISTS reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    place TEXT,
                    review TEXT,
                    rating INTEGER
                )''')
    conn.commit()

# Initialize the database
init_db()

# Prepopulate the database with some example data
example_data = [
    ('성심당 본점', '빵이 정말 맛있어요!', 5),
    ('대전 스카이로드', '야경이 정말 아름다워요.', 4),
    ('으능정이 문화의 거리', '문화와 예술이 가득한 곳입니다.', 4),
    ('성심당 본점', '크로와상이 아주 훌륭합니다!', 5),
    ('대전아트센터', '아름다운 공연을 즐겼습니다.', 5),
]

# Insert example data only if there are no existing reviews
c.execute("SELECT COUNT(*) FROM reviews")
if c.fetchone()[0] == 0:
    c.executemany('INSERT INTO reviews (place, review, rating) VALUES (?, ?, ?)', example_data)
    conn.commit()

# Places data
places = {
    '성심당 본점': {'lat': 36.327692, 'lng': 127.427078},
    '대전 스카이로드': {'lat': 36.329269, 'lng': 127.428858},
    '으능정이 문화의 거리': {'lat': 36.329575, 'lng': 127.427977},
    '대전아트센터': {'lat': 36.322589, 'lng': 127.423216},
    '대전시청': {'lat': 36.321655, 'lng': 127.427138},
    '대전근현대사전시관': {'lat': 36.323374, 'lng': 127.430164},
}

# Helper functions for the database
def fetch_reviews(place):
    c.execute('SELECT * FROM reviews WHERE place = ?', (place,))
    return c.fetchall()

def insert_review(place, review, rating):
    c.execute('INSERT INTO reviews (place, review, rating) VALUES (?, ?, ?)', (place, review, rating))
    conn.commit()

def delete_review(review_id):
    c.execute('DELETE FROM reviews WHERE id = ?', (review_id,))
    conn.commit()

def update_review(review_id, new_review):
    c.execute('UPDATE reviews SET review = ? WHERE id = ?', (new_review, review_id))
    conn.commit()

# Analyze sentiment of reviews
def analyze_sentiment(review):
    blob = TextBlob(review)
    sentiment = blob.sentiment.polarity  # Value between -1 (negative) and 1 (positive)
    if sentiment > 0.1:
        return "Positive"
    elif sentiment < -0.1:
        return "Negative"
    else:
        return "Neutral"

# Streamlit App UI
st.set_page_config(page_title="성심당 방문객 추천 시스템", layout="wide", initial_sidebar_state="collapsed")
st.title("🎉 성심당 방문객 추천 시스템")
st.markdown("**대전광역시 중구에서 추천하는 관광지와 메뉴를 확인하세요!**")

# --- Sidebar: Age and Gender Selection ---
st.sidebar.header("👥 나이대 및 성별 선택")
age_group = st.sidebar.selectbox("나이를 선택해주세요", ["20대", "30대", "40대 이상"])
gender = st.sidebar.selectbox("성별을 선택해주세요", ["남자", "여자"])

# --- Recommended Places Section ---
st.subheader(f"🏆 {age_group} {gender} 추천 장소")
place_options = {
    '20대': {
        '남자': ['대전 스카이로드', '대전아트센터'],
        '여자': ['성심당 본점', '으능정이 문화의 거리'],
    },
    '30대': {
        '남자': ['대전근현대사전시관'],
        '여자': ['대전시청'],
    },
    '40대 이상': {
        '남자': ['성심당 본점'],
        '여자': ['성심당 본점', '대전 스카이로드'],
    },
}

recommended_places = place_options[age_group][gender]
st.write(", ".join(recommended_places))

# --- Search and Display Map Section ---
st.subheader("🗺️ 장소 위치 확인")
search_query = st.text_input("🔍 장소 검색", "")
filtered_places = [place for place in places.keys() if search_query.lower() in place.lower()]

selected_place = st.selectbox("장소 선택", filtered_places if filtered_places else list(places.keys()))

# Display Map with increased width and height (width set to 100% for full screen width)
m = folium.Map(location=[36.327692, 127.427078], zoom_start=13, width='100%', height=600)
for place, coords in places.items():
    folium.Marker(location=[coords['lat'], coords['lng']], popup=place).add_to(m)

# Display the map using Streamlit's st_folium
st_folium(m, width=1920, height=600)  # Adjust this width for larger screens if needed

# --- Reviews Section ---
st.subheader(f"📝 {selected_place}에 대한 리뷰 목록")
reviews = fetch_reviews(selected_place)

if reviews:
    for review in reviews:
        sentiment = analyze_sentiment(review[2])
        st.markdown(f"**리뷰**: {review[2]} \n**별점**: {'★' * review[3]}{'☆' * (5 - review[3])} \n**감정 분석**: {sentiment}")
        st.markdown("---")
else:
    st.write(f"아직 {selected_place}에 대한 리뷰가 없습니다.")

# --- Review Submission Section ---
st.subheader("리뷰 작성 및 제출")
review_text = st.text_area("리뷰 작성")

# Using star icons for rating selection
stars = ["★☆☆☆☆", "★★☆☆☆", "★★★☆☆", "★★★★☆", "★★★★★"]
rating = st.select_slider("별점 선택", options=stars)

# Convert the star rating to a numeric value (1-5)
rating_value = stars.index(rating) + 1

if st.button("리뷰 제출"):
    if review_text.strip():
        insert_review(selected_place, review_text, rating_value)
        st.success(f"리뷰가 제출되었습니다! (별점: {rating_value}점)")
        st.experimental_rerun()  # Refresh the page to show the new review
    else:
        st.warning("리뷰 내용을 입력하세요.")

# --- Download CSV Section ---
if st.button("리뷰 CSV 다운로드"):
    review_data = fetch_reviews(selected_place)
    if review_data:
        df = pd.DataFrame(review_data, columns=["ID", "Place", "Review", "Rating"])
        st.download_button("다운로드", df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8'), "reviews.csv", "text/csv")
    else:
        st.warning("다운로드할 리뷰가 없습니다.")

# --- Review Count Visualization Section ---
st.subheader("📊 장소별 리뷰 수")
place_names = [place for place in places.keys()]
review_counts = [len(fetch_reviews(place)) for place in place_names]

# Plotly bar chart for review counts
fig = px.bar(
    x=place_names,
    y=review_counts,
    labels={'x': '장소', 'y': '리뷰 수'},
    text=review_counts,
    title="장소별 리뷰 수",
    template="plotly_white"
)

# Adjust the y-axis to only show integer values
fig.update_layout(
    xaxis_title="장소",
    yaxis_title="리뷰 수",
    font=dict(size=14),
    title_font=dict(size=20, color='blue'),
    xaxis_tickangle=0,
    yaxis=dict(
        tickmode="linear",
        tick0=1,
        dtick=1  # This ensures that the y-axis ticks are integers
    )
)

st.plotly_chart(fig)

# --- Review Management Section (Edit/Delete) ---
st.subheader("🛠 리뷰 관리")
if reviews:
    review_to_edit = st.selectbox("수정할 리뷰 선택", [(r[0], r[2]) for r in reviews], format_func=lambda x: f"리뷰 {x[0]}: {x[1]}")
    review_id = review_to_edit[0]
    new_review_text = st.text_area("리뷰 수정", review_to_edit[1])

    if st.button("리뷰 수정"):
        if new_review_text.strip():
            update_review(review_id, new_review_text)
            st.success("리뷰가 수정되었습니다!")
            st.experimental_rerun()
        else:
            st.warning("리뷰 내용을 입력하세요.")

    if st.button("리뷰 삭제"):
        delete_review(review_id)
        st.success("리뷰가 삭제되었습니다!")
        st.experimental_rerun()