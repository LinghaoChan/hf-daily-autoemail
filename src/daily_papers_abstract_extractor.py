import json
import os
import sys
from datetime import datetime
import re
import markdown
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import schedule
import time
import argparse

def clean_text(text):
    # Replace newlines with spaces
    text = text.replace('\n', ' ')
    # Remove any resulting multiple spaces
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def json_to_markdown(json_data):
    if not json_data:
        return None  # Return None for empty data
    
    # Extract the date from the first paper's publishedAt field
    first_paper_date = datetime.fromisoformat(json_data[0]['paper']['publishedAt'].replace('Z', '+00:00'))
    date_str = first_paper_date.strftime('%Y-%m-%d')
    
    markdown_content = f"# Daily Papers Summary for {date_str}\n\n"
    
    for article in json_data:
        paper = article['paper']
        title = clean_text(paper['title'])
        summary = clean_text(paper['summary'])
        paper_id = paper['id']
        img = article["thumbnail"]
        authorlist = [author['name'] for author in paper['authors']]
        authors = ', '.join(authorlist) if authorlist else "Unknown"
        
        hf_link = f"https://huggingface.co/papers/{paper_id}"
        arxiv_link = f"https://arxiv.org/pdf/{paper_id}"
        
        markdown_content += f"## {title}\n\n"
        markdown_content += f"**Authors:** {authors}\n\n"
        markdown_content += f"[Open in Hugging Face]({hf_link}) | [Open PDF]({arxiv_link})\n\n"
        markdown_content += f"{summary}\n\n"
        markdown_content += f"![image](img)"
    
    return markdown_content

def get_output_filename(input_filename):
    # Extract date from input filename (assuming format daily_papers_YYYYMMDD.json)
    date_str = input_filename.split('_')[-1].split('.')[0]
    return f"daily_papers_summary_{date_str}.md"

def process_daily_papers(input_file):
    # Load the JSON data
    with open(input_file, 'r', encoding='utf-8') as file:
        data = json.load(file)

    # Convert JSON to markdown
    markdown_output = json_to_markdown(data)
    
    if markdown_output is None:
        msg = f"Warning: {input_file} is empty. No markdown file will be created."
        print(msg)
        delete = 'y'
        if delete == 'y':
            os.remove(input_file)
            print(f"Deleted {input_file}")
        return msg

    # Get the output filename based on the input filename
    output_filename = get_output_filename(os.path.basename(input_file))

    # Create the data/output directory if it doesn't exist
    output_dir = os.path.join('data', 'output')
    os.makedirs(output_dir, exist_ok=True)

    # Check if output file already exists
    output_path = os.path.join(output_dir, output_filename)
    if os.path.exists(output_path):
        print(f"Output file {output_filename} already exists. Skipping conversion.")
        return

    # Write the markdown content to the file in the output directory
    with open(output_path, 'w') as file:
        file.write(markdown_output)

    print(f"Markdown file '{output_path}' has been created successfully.")

# Function to process all files in the 'data/input' directory
def process_all_files():
    input_dir = os.path.join('data', 'input')  # Set the input directory path
    input_files = [f for f in os.listdir(input_dir) if f.endswith('.json')]  # List all JSON files in the directory
    
    if not input_files:  # Check if there are no files to process
        print("No input files found in data/input directory.")
        return

    # Loop through the input files, sort them, and process each one
    for input_file in sorted(input_files):
        input_path = os.path.join(input_dir, input_file)  # Full path to the file
        print(f"Processing {input_path}...")  # Print the file being processed
        process_daily_papers(input_path)  # Call function to process the file

# Function to send an email with the provided markdown file
def send_markdown_email(markdown_file):

    # Read the content of the markdown file
    with open(markdown_file, "r", encoding="utf-8") as md_file:
        markdown_content = md_file.read()

    # Convert markdown content to HTML format
    html_content = markdown.markdown(markdown_content)
    
    today = datetime.today().strftime('%Y%m%d')  # Get today's date in YYYYMMDD format

    # Create the email
    msg = MIMEMultipart("alternative")
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = f"Hugging Face Daily Papers Summary {today}"  # Set email subject

    # Attach the HTML content to the email
    msg.attach(MIMEText(html_content, "html"))

    # Try to send the email
    try:
        server = smtplib.SMTP('smtp.office365.com', 587)  # Connect to the Outlook SMTP server
        server.starttls()  # Start TLS encryption
        server.login(sender_email, password)  # Login to the email account
        server.sendmail(sender_email, receiver_email, msg.as_string())  # Send the email
        server.quit()  # Close the connection
        print("=====================Email sent successfully=====================")    
    except Exception as e:
        print(f"=====================! E-mail sending failed: {e}=====================")  # Print error message if sending fails

# Main function to download, process, and send email
def process_and_send_email():
    today = datetime.today().strftime('%Y%m%d')  # Get today's date in YYYYMMDD format
    print(f"=====================Running {today} Hugging Face Daily Papers Script=====================")
    os.system(f"python src/download_daily_papers.py {today}")  # Run the download script
    json_file = f"./data/input/daily_papers_{today}.json"  # Path to the JSON file
    msg = process_daily_papers(json_file)  # Process the downloaded JSON file
    if msg is not None:
        if "Warning" in msg:
            return
    markdown_file = f"./data/output/daily_papers_summary_{today}.md"  # Path to the markdown summary
    send_markdown_email(markdown_file)  # Send the email with the markdown content

# Schedule the process to run every day at 12:00 PM
schedule.every().day.at("15:00:00").do(process_and_send_email)

# Keep the script running and checking the schedule
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sender_email", type=str, help="Sender's email address")
    parser.add_argument("--receiver_email", type=str, help="Receiver's email address")
    parser.add_argument("--password", type=str, help="Email account password")
    args = parser.parse_args()
    sender_email = args.sender_email
    receiver_email = args.receiver_email
    password = args.password
    while True:
        schedule.run_pending()  # Run the scheduled tasks when the time is due
        time.sleep(1)  # Wait 60 seconds before checking the schedule again