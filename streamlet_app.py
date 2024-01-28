import streamlit as st
import requests
from summarizer import Summarizer
import newspaper
import spacy
#!/usr/bin/env python3

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import getpass
class email():
    """
    create and sends an email
    """
    def __init__(self,emailfrom=None,emailto=None):
        self.emailfrom = emailfrom
        self.emailto = emailto

    def send(self,title,contents,passwd):
        me = self.emailfrom
        you = self.emailto

        msg = MIMEMultipart('alternative')
        msg['Subject'] = title
        msg['From'] = me
        msg['To'] = you

        part = MIMEText(contents, 'html')
        msg.attach(part)

        s = smtplib.SMTP_SSL('smtp.gmail.com',port=465)
        s.login(self.emailfrom ,passwd)
        s.sendmail(me, you, msg.as_string())
        s.quit()

email_from = st.secrets["email_from"]
email_to = st.secrets["email_to"]
passwd = st.secrets["passwd"]


def load_model():
    return spacy.load("en_core_web_sm")

nlp = load_model()

def clean_and_extract_informative(text):
    doc = nlp(text)
    informative_paragraphs = [p.text.strip() for p in doc.sents if p and not p.text.startswith(("By", "Sign up", "Subscribe", "Download the app"))]
    return ' '.join(informative_paragraphs)

def bert_extractive_summarize(text):
    return Summarizer()(text)

def get_news(api_key, category):
    base_url = "https://newsapi.org/v2/top-headlines"
    params = {"apiKey": api_key, "country": "us", "category": category}
    response = requests.get(base_url, params=params).json()
    return [{"title": a['title'], "url": a['url']} for a in response.get("articles", []) if a['title'] != "[Removed]"]

def summarize_articles(api_key, category, emailto):
    headlines = get_news(api_key, category)
    if headlines:
        summaries = []
        for idx, article_data in enumerate(headlines[:5], start=1):
            st.write(f"{idx}. {article_data['title']}")
            try:
                article = newspaper.Article(article_data['url'])
                article.download()
                article.parse()
                cleaned_text = clean_and_extract_informative(article.text)
                summary = bert_extractive_summarize(cleaned_text)
                summaries.append(summary)
            except Exception as e:
                st.warning(f"Unable to read article. Error: {str(e)}")

        combined_summary = "\n\n".join(summaries)
        st.write("Combined Summary:")
        st.write(combined_summary)
        em = email(email_from,emailto)
        html_content = f"""
        <html>
          <body>
            <h1>Daily News Summary</h1>     
            <p>{combined_summary}</p>   
          </body>
        </html>
        """
        
        em.send(f'Daily News', html_content,passwd)
    else:
        st.warning(f"No valid headlines found for category {category}.")

st.title("News Headlines App")
emailto = st.text_input("Enter your email:")
if st.button("Submit"):
    if emailto:
        # Process the email (you can add your logic here)
        st.success(f"Email submitted: {emailto}")
    else:
        st.warning("Please enter a valid email.")

selected_categories = st.multiselect("Select your categories:", ["business", "entertainment", "health", "science", "sports", "technology"])

if st.button("Summarize News Headlines"):
    api_key = st.secrets["api_key"]
    if api_key and selected_categories and emailto:
        for category in selected_categories:
            summarize_articles(api_key, category, emailto)
            st.write("---")
    else:
        st.warning("Please provide a valid email and select at least one category.")

