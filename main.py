import os
import time
import re
import ffmpeg
import tweepy
import requests
from tweepy.errors import TooManyRequests  # 👈 add this

API_KEY = os.getenv("API_KEY")
API_KEY_SECRET = os.getenv("API_KEY_SECRET")
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")
ACCESS_TOKEN_SECRET = os.getenv("ACCESS_TOKEN_SECRET")
BEARER_TOKEN = os.getenv("BEARER_TOKEN")

client = tweepy.Client(
    bearer_token=BEARER_TOKEN,
    consumer_key=API_KEY,
    consumer_secret=API_KEY_SECRET,
    access_token=ACCESS_TOKEN,
    access_token_secret=ACCESS_TOKEN_SECRET,
)

auth = tweepy.OAuth1UserHandler(API_KEY, API_KEY_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
api = tweepy.API(auth)

LAST_SEEN_FILE = "last_seen.txt"

# ... keep get_last_seen, set_last_seen, parse_cut_command,
#     download_video, trim_video exactly as before ...


def run_bot():
    print("MakeItAHighlight bot is now running...")
    last_seen = get_last_seen()

    me = client.get_me()
    user_id = me.data.id

    while True:
        try:
            # 🔁 call the API
            if last_seen:
                mentions = client.get_users_mentions(
                    id=user_id,
                    since_id=last_seen,
                    expansions=["attachments.media_keys"],
                    media_fields=["url"],
                )
            else:
                mentions = client.get_users_mentions(
                    id=user_id,
                    expansions=["attachments.media_keys"],
                    media_fields=["url"],
                )

            if mentions.data:
                for mention in reversed(mentions.data):
                    print("Processing:", mention.id)
                    set_last_seen(mention.id)

                    start, end = parse_cut_command(mention.text)
                    if not start:
                        client.create_tweet(
                            text="Please use the format: cut 0:05-0:17",
                            in_reply_to_tweet_id=mention.id,
                        )
                        continue

                    if not mention.attachments or "media_keys" not in mention.attachments:
                        client.create_tweet(
                            text="I couldn't find a video on that tweet.",
                            in_reply_to_tweet_id=mention.id,
                        )
                        continue

                    media_key = mention.attachments["media_keys"][0]
                    media_url = None

                    if mentions.includes and "media" in mentions.includes:
                        for media in mentions.includes["media"]:
                            if media.media_key == media_key:
                                media_url = media.url

                    if not media_url:
                        client.create_tweet(
                            text="I couldn't find a video on that tweet.",
                            in_reply_to_tweet_id=mention.id,
                        )
                        continue

                    input_file = download_video(media_url)
                    output_file = trim_video(input_file, start, end)

                    api.update_status_with_media(
                        status=f"Here's your highlight! 🔥 ({start} - {end})",
                        filename=output_file,
                        in_reply_to_status_id=mention.id,
                    )

            # ⏱️ poll less often so we don’t spam the API
            time.sleep(60)

        except TooManyRequests as e:
            # 💥 hit rate limit – chill for 5 minutes
            print("Rate limited by Twitter. Sleeping for 5 minutes...")
            time.sleep(300)
        except Exception as e:
            # Any other error – log and retry later
            print("Unexpected error:", e)
            time.sleep(60)


if __name__ == "__main__":
    run_bot()
