import os
import time
import re
import ffmpeg
import tweepy
import requests

API_KEY = os.getenv("trr8P5NeVuboG5CjDENrGwVwj")
API_KEY_SECRET = os.getenv("1Z2b9fxeODdF6Xms4r69KLhfsGHq0yXoimMq1DwQbkXvSZRN2D")
ACCESS_TOKEN = os.getenv("1990911553718345728-e7hc3e50PM6f4XpvVRSTsOsKKHBoMj")
ACCESS_TOKEN_SECRET = os.getenv("od2fsrk99ksDQBCTVV1srehxIwS8jyZgFDOutilMO7IAL")
BEARER_TOKEN = os.getenv("AAAAAAAAAAAAAAAAAAAAABIE5gEAAAAA9uN80W3T%2FvuDntHIlEOCBtT5l24%3D4HqeRHq4Z6PaDirhcFH7P5fsXEJiYTaKpWMLQ4JKauxGVoTQqk
")

client = tweepy.Client(
    bearer_token=BEARER_TOKEN,
    consumer_key=API_KEY,
    consumer_secret=API_KEY_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_TOKEN_SECRET
)

auth = tweepy.OAuth1UserHandler(API_KEY, API_KEY_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
api = tweepy.API(auth)

LAST_SEEN_FILE = "last_seen.txt"

def get_last_seen():
    if not os.path.exists(LAST_SEEN_FILE):
        return None
    with open(LAST_SEEN_FILE, "r") as f:
        return f.read().strip()

def set_last_seen(tweet_id):
    with open(LAST_SEEN_FILE, "w") as f:
        f.write(str(tweet_id))

def parse_cut_command(text):
    pattern = r"cut\s+(\d+:\d+)-(\d+:\d+)"
    match = re.search(pattern, text.lower())
    if match:
        return match.group(1), match.group(2)
    return None, None

def download_video(url):
    video = requests.get(url)
    filename = "input.mp4"
    with open(filename, "wb") as f:
        f.write(video.content)
    return filename

def trim_video(input_file, start, end):
    output_file = "output.mp4"
    (
        ffmpeg
        .input(input_file, ss=start, to=end)
        .output(output_file, codec="copy")
        .overwrite_output()
        .run()
    )
    return output_file

def run_bot():
    print("MakeItAHighlight bot is now running...")
    last_seen = get_last_seen()

    while True:
        mentions = client.get_mentions_timeline(since_id=last_seen, expansions="attachments.media_keys", media_fields="url")

        if mentions.data:
            for mention in reversed(mentions.data):
                print("Processing:", mention.id)
                set_last_seen(mention.id)

                start, end = parse_cut_command(mention.text)
                if not start:
                    client.create_tweet(
                        text="Please use the format: cut 0:05-0:17",
                        in_reply_to_tweet_id=mention.id
                    )
                    continue

                media_key = mention.attachments["media_keys"][0]
                media_url = None
                for media in mentions.includes["media"]:
                    if media.media_key == media_key:
                        media_url = media.url

                if not media_url:
                    client.create_tweet(
                        text="I couldn't find a video on that tweet.",
                        in_reply_to_tweet_id=mention.id
                    )
                    continue

                input_file = download_video(media_url)
                output_file = trim_video(input_file, start, end)

                api.update_status_with_media(
                    status=f"Here's your highlight! 🔥 ({start} - {end})",
                    filename=output_file,
                    in_reply_to_status_id=mention.id,
                )

        time.sleep(15)

if __name__ == "__main__":
    run_bot()
