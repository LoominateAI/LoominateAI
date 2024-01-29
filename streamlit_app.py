import streamlit as st
import requests
from summarizer import Summarizer
import newspaper
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import smtplib
import spacy

class EmailSender:
    def __init__(self, email_from, email_to, passwd):
        self.email_from = email_from
        self.email_to = email_to
        self.passwd = passwd

    def send_email(self, title, contents):
        msg = MIMEMultipart('alternative')
        msg['Subject'] = title
        msg['From'] = self.email_from
        msg['To'] = self.email_to
        part = MIMEText(contents, 'html')
        msg.attach(part)
        s = smtplib.SMTP_SSL('smtp.gmail.com', port=465)
        s.login(self.email_from, self.passwd)
        s.sendmail(self.email_from, self.email_to, msg.as_string())
        s.quit()

@st.cache(hash_funcs={"MyUnhashableClass": lambda _: None})
def load_spacy_model():
    return spacy.load("en_core_web_sm")

@st.cache(hash_funcs={"MyUnhashableClass": lambda _: None})
def load_bert_summarizer():
    return Summarizer('bert-large-uncased')

def bert_extractive_summarize(text, summarizer):
    summary = summarizer(text)
    return summary

def get_news(api_key, category):
    base_url = "https://newsapi.org/v2/top-headlines"
    params = {"apiKey": api_key, "country": "us", "category": category}
    response = requests.get(base_url, params=params).json()
    return [{"title": a['title'], "url": a['url']} for a in response.get("articles", []) if a['title'] != "[Removed]"]

@st.cache(hash_funcs={"MyUnhashableClass": lambda _: None})
def clean_and_extract_informative(text, nlp):
    doc = nlp(text)
    informative_paragraphs = [p.text.strip() for p in doc.sents if p and not p.text.startswith(("By", "Sign up", "Subscribe", "Download the app"))]
    return ' '.join(informative_paragraphs)

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
        email_sender.send_email('Daily News', html_content)

    else:
        st.warning(f"No valid headlines found for category {category}.")
