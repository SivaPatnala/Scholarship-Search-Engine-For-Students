import streamlit as st
import pandas as pd
import nltk
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics import ndcg_score
from nltk.corpus import stopwords
import string
import numpy as np

# Download NLTK stopwords
nltk.download('stopwords')

# Function to clean text
def clean_text(text):
    text = text.lower()
    text = ''.join([c for c in text if c not in string.punctuation])
    tokens = text.split()
    tokens = [word for word in tokens if word not in stopwords.words('english')]
    return ' '.join(tokens)

# Load data and preprocess
@st.cache
def load_data():
    df = pd.read_csv('scholarship.csv', encoding='utf-8')
    df['combined_text'] = (
        df['Scholarship Details'].fillna('') + ' ' +
        df['Eligibility'].fillna('') + ' ' +
        df['University'].fillna('') + ' ' +
        df['Amount'].fillna('')
    )
    df['cleaned'] = df['combined_text'].apply(clean_text)
    return df

@st.cache(allow_output_mutation=True)
def fit_vectorizer(cleaned_texts):
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(cleaned_texts)
    return vectorizer, tfidf_matrix

def search_scholarships(query, vectorizer, tfidf_matrix, df, top_n=5):
    query_cleaned = clean_text(query)
    query_vector = vectorizer.transform([query_cleaned])
    cosine_sim = cosine_similarity(query_vector, tfidf_matrix).flatten()
    top_indices = cosine_sim.argsort()[-top_n:][::-1]
    return df.iloc[top_indices], cosine_sim, top_indices

# Streamlit App
st.title("🎓 Scholarship Search Engine")
st.markdown("Enter a query like: *scholarships for BTech students in Andhra Pradesh*")

# Session state for feedback
if 'feedback' not in st.session_state:
    st.session_state.feedback = {}

# Load data and vectorizer
df = load_data()
vectorizer, tfidf_matrix = fit_vectorizer(df['cleaned'])

# Search input
query = st.text_input("🔍 Type your scholarship query:")

if query:
    results, cosine_sim, top_indices = search_scholarships(query, vectorizer, tfidf_matrix, df)
    st.subheader("🔎 Top Matching Scholarships")

    if not results.empty:
        for idx, (_, row) in enumerate(results.iterrows()):
            scholarship_id = row.name  # Unique identifier
            st.markdown(f"""
            ---
            #### 🏫 **{row['University']}** - _{row['State'] if 'State' in row else 'N/A'}_
            **💰 Amount:** {row['Amount']}  
            **🗓 Deadline:** {row['Deadline'] if 'Deadline' in row else 'N/A'}  
            **📌 Scholarship Details:**  
            {row['Scholarship Details']}  
            **🎯 Eligibility:**  
            {row['Eligibility']}
            """)

            # Collect relevance feedback
            feedback = st.selectbox(
                f"🔁 Rate relevance for this result:",
                ["No feedback", "Not relevant (0)", "Slightly relevant (1)", "Relevant (2)", "Highly relevant (3)"],
                key=f"feedback_{scholarship_id}"
            )

            if feedback != "No feedback":
                st.session_state.feedback[scholarship_id] = int(feedback[-2])

        # Compute NDCG based on user feedback
        if st.session_state.feedback:
            feedback_indices = list(st.session_state.feedback.keys())
            relevance_scores = [st.session_state.feedback[i] for i in feedback_indices]
            predicted_scores = [cosine_sim[i] for i in feedback_indices]

            true_relevance = np.array([relevance_scores])
            predicted = np.array([predicted_scores])

            ndcg = ndcg_score(true_relevance, predicted)
            st.success(f"📈 NDCG based on your feedback: **{ndcg:.4f}**")

    else:
        st.warning("😕 No scholarships matched your search.")
else:
    st.info("Start by entering a query to find scholarships.")

# Footer
st.markdown("---")
st.markdown("### ℹ️ Results are based on scholarship details, eligibility, university, and amount.")
st.markdown("### 📊 Feedback is used to evaluate ranking quality using NDCG.")
