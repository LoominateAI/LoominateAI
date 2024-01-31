import streamlit as st
import requests
from summarizer import Summarizer
import newspaper
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import spacy
import re

class EmailSender:
    def __init__(self, email_from, passwd):
        self.email_from = email_from
        self.passwd = passwd

    def send_verification_email(self, email_to):
        subject = "Email Verification"
        body = "This is a test email to verify your email address."
        msg = MIMEMultipart()
        msg['Subject'] = subject
        msg['From'] = self.email_from
        msg['To'] = email_to
        msg.attach(MIMEText(body, 'plain'))

        with smtplib.SMTP_SSL('smtp.gmail.com', port=465) as server:
            server.login(self.email_from, self.passwd)
            server.sendmail(self.email_from, email_to, msg.as_string())

@st.cache(hash_funcs={"MyUnhashableClass": lambda _: None})
def load_spacy_model():
    return spacy.load("en_core_web_sm")

@st.cache(hash_funcs={"MyUnhashableClass": lambda _: None})
def load_bert_summarizer():
    return Summarizer('bert-large-uncased')

def is_valid_email(email):
    pattern = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return re.match(pattern, email)

def clean_and_extract_informative(text, nlp):
    doc = nlp(text)
    informative_paragraphs = [p.text.strip() for p in doc.sents if p and not p.text.startswith(("By", "Sign up", "Subscribe", "Download the app"))]
    return ' '.join(informative_paragraphs)

def bert_extractive_summarize(text, summarizer):
    summary = summarizer(text)
    return summary

def get_news(api_key, category):
    base_url = "https://newsapi.org/v2/top-headlines"
    params = {"apiKey": api_key, "country": "us", "category": category}
    response = requests.get(base_url, params=params).json()
    return [{"title": a['title'], "url": a['url']} for a in response.get("articles", []) if a['title'] != "[Removed]"]

def summarize_articles(api_key, category, email_to, email_sender, nlp, summarizer):
    headlines = get_news(api_key, category)
    if headlines:
        summaries = []
        for idx, article_data in enumerate(headlines[:5], start=1):
            st.write(f"{idx}. {article_data['title']}")
            try:
                article = newspaper.Article(article_data['url'])
                article.download()
                article.parse()
                cleaned_text = clean_and_extract_informative(article.text, nlp)
                summary = bert_extractive_summarize(cleaned_text, summarizer)
                summaries.append(summary)
            except Exception as e:
                st.warning(f"Unable to read article. Error: {str(e)}")

        combined_summary = "\n\n".join(summaries)
        st.write("Combined Summary:")
        st.write(combined_summary)

        html_content = f"""
        <html>
          <body>
            <h1>Daily News Summary</h1>     
            <p>{combined_summary}</p>   
          </body>
        </html>
        """
        email_sender.send_verification_email(email_to)
        st.success(f"Thank you for submitting your email: {email_to}")
    else:
        st.warning(f"No valid headlines found for category {category}.")

st.title("News Headlines App")
email_to = st.text_input("Enter your email:")
if st.button("Submit"):
    if email_to and is_valid_email(email_to):
        api_key = st.secrets["api_key"]
        email_from = st.secrets["email_from"]
        passwd = st.secrets["passwd"]

        nlp_model = load_spacy_model()
        summarizer_model = load_bert_summarizer()

        email_sender = EmailSender(email_from, passwd)
        summarize_articles(api_key, "technology", email_to, email_sender, nlp_model, summarizer_model)
    else:
        st.warning("Please enter a valid email.")
