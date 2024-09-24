import psycopg2
import os
import json  # Import the json module to handle JSON operations
import boto3

def read_data_from_postgres():
    conn = None
    cursor = None
    results = []
    
    try:
        conn = psycopg2.connect(
            host=os.environ['DB_HOST'],
            database=os.environ['DB_NAME'],
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD']
        )
        cursor = conn.cursor()
        
        # Fetch data from the feedback table
        cursor.execute("SELECT id, feedback FROM fintech_feedback WHERE sentiment_label IS NULL")
        results = cursor.fetchall()
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()
    
    return results

def analyze_sentiment(feedback):
    comprehend = boto3.client('comprehend')
    response = comprehend.detect_sentiment(
        Text=feedback,
        LanguageCode='en'  # Change this to the appropriate language code if necessary
    )
    return response['Sentiment'], response['SentimentScore']

def update_sentiment_in_postgres(feedback_id, sentiment_label, sentiment_score):
    conn = None
    cursor = None
    
    try:
        conn = psycopg2.connect(
            host=os.environ['DB_HOST'],
            database=os.environ['DB_NAME'],
            user=os.environ['DB_USER'],
            password=os.environ['DB_PASSWORD']
        )
        cursor = conn.cursor()
        
        # Update the sentiment_label, sentiment scores, and sentiment_analysis field in the database
        cursor.execute("""
            UPDATE fintech_feedback 
            SET sentiment_label = %s, 
                positive_score = %s, 
                negative_score = %s, 
                neutral_score = %s, 
                mixed_score = %s,
                sentiment_analysis = TRUE  -- Set sentiment_analysis to true
            WHERE id = %s
        """, (
            sentiment_label,
            sentiment_score['Positive'],
            sentiment_score['Negative'],
            sentiment_score['Neutral'],
            sentiment_score['Mixed'],
            feedback_id
        ))
        
        conn.commit()
        print(f"Sentiment updated for feedback ID: {feedback_id}")
    
    except Exception as e:
        print(f"Error updating sentiment: {e}")
    
    finally:
        if cursor is not None:
            cursor.close()
        if conn is not None:
            conn.close()

def lambda_handler(event, context):
    feedback_data = read_data_from_postgres()
    
    for feedback in feedback_data:
        feedback_id = feedback[0]
        feedback_text = feedback[1]
        sentiment, sentiment_score = analyze_sentiment(feedback_text)
        update_sentiment_in_postgres(feedback_id, sentiment, sentiment_score)
