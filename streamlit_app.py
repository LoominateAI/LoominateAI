import streamlit as st
import requests
from transformers import pipeline
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

@st.cache(allow_output_mutation=True)  # Allow mutation for model loading
def load_models():
    nlp_model = spacy.load("en_core_web_sm")
    summarizer = pipeline("summarization", model="facebook/bart-large-cnn", tokenizer="facebook/bart-large-cnn")  # Load BART model
    return nlp_model, summarizer

def clean_and_extract_informative(text, nlp):
    doc = nlp(text)
    informative_paragraphs = [p.text.strip() for p in doc.sents if p and not p.text.startswith(("By", "Sign up", "Subscribe", "Download the app"))]
    return ' '.join(informative_paragraphs)

def summarize_with_bart(text, summarizer):
    summary = summarizer(text, max_length=150, min_length=30, do_sample=False)[0]['summary_text']  # Adjust parameters as needed
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
            # Option 1: Skipping problematic articles
            try:
                article = newspaper.Article(article_data['url'])
                article.download()
                article.parse()

                if not article.text:
                    st.warning(f"Article {idx} is empty. Skipping...")
                    continue

                cleaned_text = clean_and_extract_informative(article.text, nlp)
                summary = summarize_with_bart(cleaned_text, summarizer)
                summaries.append(summary)

            except Exception as e:
                st.warning(f"Unable to read article {idx}. Error: {str(e)}")

            # Option 2: Alternative summarization method
            # Uncomment this block and comment out the above try-except block if using this option
            # try:
            #     article = newspaper.Article(article_data['url'])
            #     article.download()
            #     article.parse()
            #     summary = summarize_with_bart(article.text, summarizer)
            #     summaries.append(summary)
            # except Exception as e:
            #     st.warning(f"Unable to read article {idx}. Error: {str(e)}")

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



st.title("News Headlines App")
email_to = st.text_input("Enter your email:")
if st.button("Submit"):
    if email_to:
        st.success(f"Email submitted: {email_to}")
    else:
        st.warning("Please enter a valid email.")

selected_categories = st.multiselect("Select your categories:", ["business", "entertainment", "health", "science", "sports", "technology"])

if st.button("Summarize News Headlines"):
    api_key = st.secrets["api_key"]
    email_from = st.secrets["email_from"]
    passwd = st.secrets["passwd"]

    if api_key and selected_categories and email_to:
        nlp_model, summarizer_model = load_models()

        email_sender = EmailSender(email_from, email_to, passwd)
        for category in selected_categories:
            summarize_articles(api_key, category, email_to, email_sender, nlp_model, summarizer_model)
            st.write("---")

    else:
        st.warning("Please provide a valid email and select at least one category.")

