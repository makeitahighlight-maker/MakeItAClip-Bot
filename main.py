import os
import time
import tweepy
import requests
import ffmpeg

# -----------------------------
# AUTH SETUP
# -----------------------------
API_KEY = os.getenv("API_KEY")
API_KEY_SECRET = os.getenv("API_KEY_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")

auth = tweepy.OAuth1UserHandler(
    API_KEY,
    API_KEY_SECRET,
    ACCESS_TOKEN,
    ACCESS_TOKEN_SECRET
)

client = tweepy.Client(
    bearer_token=BEARER_TOKEN,
    consumer_key=API_KEY,
    consumer_secret=API_KEY_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_TOKEN_SECRET
)

api_v1 = tweepy.API(auth)

# -----------------------------
# VIDEO DOWNLOAD / CLIP CUTTING
# -----------------------------

def download_video(url, output="input.mp4"):
    print("Downloading video:", url)
    r = requests.get(url)

    with open(output, "wb") as f:
        f.write(r.content)

    print("Video saved:", output)
    return output


def create_clip(input_file, start, end, output_file="highlight.mp4"):
    print(f"Creating clip {start} → {end}")

    (
        ffmpeg
        .input(input_file, ss=start, to=end)
        .output(output_file)
        .overwrite_output()
        .run()
    )

    print("Clip created:", output_file)
    return output_file


# -----------------------------
# BOT MAIN LOGIC
# -----------------------------

def run_bot():
    print("Bot is starting...")
    last_seen_id = None

    while True:
        try:
            print("Checking for mentions...")

            mentions = client.get_users_mentions(
                client.get_me().data.id,
                since_id=last_seen_id,
                expansions="attachments.media_keys",
                media_fields="url"
            )

            if mentions.data:
                for mention in mentions.data:
                    print("Processing mention:", mention.text)

                    last_seen_id = mention.id

                    text = mention.text.lower()

                    # Extract times
                    import re
                    match = re.search(r"(\d+):(\d+)-(\d+):(\d+)", text)

                    if not match:
                        print("No valid timestamp in tweet.")
                        continue

                    start = f"{match.group(1)}:{match.group(2)}"
                    end = f"{match.group(3)}:{match.group(4)}"

                    # Get attached video
                    if "attachments" not in mention.data:
                        print("No video attached.")
                        continue

                    media_key = mention.data["attachments"]["media_keys"][0]
                    media = mentions.includes["media"]

                    video_url = None
                    for m in media:
                        if m.media_key == media_key and "url" in m:
                            video_url = m.url

                    if not video_url:
                        print("No downloadable video found.")
                        continue

                    # Process clip
                    input_file = download_video(video_url)
                    output_file = create_clip(input_file, start, end)

                    # Upload
                    media_id = api_v1.media_upload(output_file).media_id_string

                    client.create_tweet(
                        text=f"🎥 Highlight ({start}-{end})",
                        in_reply_to_tweet_id=mention.id,
                        media_ids=[media_id]
                    )

                    print("Reply sent with highlight!")

            else:
                print("No new mentions.")

            time.sleep(60)

        except tweepy.TooManyRequests:
            print("Rate limited. Waiting 15 minutes...")
            time.sleep(900)

        except Exception as e:
            print("Unexpected error:", str(e))
            time.sleep(60)


# -----------------------------
# ENTRY POINT
# -----------------------------
if __name__ == "__main__":
    print("MakeItAHighlight bot is now running...")
    run_bot()
