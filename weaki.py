import pandas as pd
import plotly.express as px
import streamlit as st

CSV_FILE = "scored_articles_sample.csv"

# ---------------------------------------------------------------- page setup
st.set_page_config(
    page_title="WikiCompleteness Explorer", page_icon="🌐", layout="wide"
)

st.title("🌐 Wikipedia Article Completeness Scorecard")
st.caption(
    "Article names and links come from Wikipedia, licensed under "
    "[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). "
    "Source data: Wikimedia Structured Wikipedia Dataset. "
    "Scores are our own calculation, not Wikipedia's, and are not endorsed "
    "by Wikimedia."
)


# ---------------------------------------------------------------- load data
@st.cache_data
def load_data():
    return pd.read_csv(CSV_FILE)


try:
    df = load_data()
except FileNotFoundError:
    st.error(
        f"'{CSV_FILE}' not found. Make sure the CSV is in the same folder "
        "as weaki.py."
    )
    st.stop()

needed = {"name", "url", "score", "gaps", "sections", "references",
          "has_infobox", "list_or_disambig"}
missing = needed - set(df.columns)
if missing:
    st.error(f"The CSV is missing these columns: {sorted(missing)}. "
             "Re-run the scoring script and use its new CSV.")
    st.stop()

# ---------------------------------------------------------------- sidebar
st.sidebar.header("Filter & Exploration Controls")

hide_lists = st.sidebar.checkbox(
    "Hide list and disambiguation pages", value=True,
    help="Pages like 'List of ...' are short by design, so they are not "
         "real weak articles.",
)

score_range = st.sidebar.slider("Completeness score range", 0, 100, (0, 100))

sort_option = st.sidebar.selectbox(
    "Sort articles by",
    [
        "Least complete first (lowest score)",
        "Most complete first (highest score)",
        "Middle of the pack (near median)",
    ],
)

search_query = st.sidebar.text_input("Search article title", "")

# ---------------------------------------------------------------- filtering
base_df = df[~df["list_or_disambig"]].copy() if hide_lists else df.copy()

filtered_df = base_df[
    (base_df["score"] >= score_range[0]) & (base_df["score"] <= score_range[1])
].copy()

if search_query:
    filtered_df = filtered_df[
        filtered_df["name"].str.contains(search_query, case=False, na=False)
    ].copy()

if sort_option.startswith("Least"):
    display_df = filtered_df.sort_values("score", ascending=True).head(50)
elif sort_option.startswith("Most"):
    display_df = filtered_df.sort_values("score", ascending=False).head(50)
else:
    if len(filtered_df) > 0:
        median_score = filtered_df["score"].median()
        filtered_df["diff_from_middle"] = (filtered_df["score"] - median_score).abs()
        display_df = filtered_df.sort_values("diff_from_middle").head(50)
    else:
        display_df = filtered_df

# ---------------------------------------------------------------- metrics
col1, col2, col3 = st.columns(3)
col1.metric("Articles in sample", len(base_df))
col2.metric("Matching your filters", len(filtered_df))
col3.metric("Average score", f"{base_df['score'].mean():.1f}/100")

st.info(
    "This is a random sample from one language edition, not all of "
    "Wikipedia. The score measures **completeness** (text, references, "
    "sections), not writing quality or how important the topic is."
)

st.divider()

# ---------------------------------------------------------------- chart
st.subheader("📊 Score distribution")
fig = px.histogram(
    base_df,
    x="score",
    nbins=20,
    title="Distribution of completeness scores",
    labels={"score": "Score (0-100)"},
    color_discrete_sequence=["#4F46E5"],
)
st.plotly_chart(fig, width="stretch")

# ---------------------------------------------------------------- article feed
st.subheader("📋 Article inspection feed (top 50)")

if len(display_df) == 0:
    st.info("No articles match your filters. Try changing the slider or search.")

for _, row in display_df.iterrows():
    with st.expander(f"Score {row['score']}/100 — {row['name']}"):
        st.write(f"**Gaps:** {row['gaps']}")
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.write(f"**Sections:** {int(row['sections'])}")
        col_b.write(f"**References:** {int(row['references'])}")
        col_c.write(f"**Infobox:** {'Yes' if row['has_infobox'] else 'No'}")
        col_d.write(f"**Text length:** {int(row['text_chars'])} chars"
                    if "text_chars" in row else "")

        if pd.notna(row.get("url")) and str(row["url"]).strip():
            url = row["url"]
        else:
            lang = row.get("lang", "en")
            url = f"https://{lang}.wikipedia.org/wiki/{str(row['name']).replace(' ', '_')}"
        st.markdown(f"[🔗 Open on Wikipedia]({url})")