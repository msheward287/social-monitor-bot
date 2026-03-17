import requests
import json
import base64
import os

# Configuration
REDDIT_CLIENT_ID = 'x'
REDDIT_CLIENT_SECRET = 'x'
REDDIT_USER_AGENT = 'x'
GOOGLE_API_KEY = 'x'
TWITTER_API_KEY = 'x'
TWITTER_API_SECRET_KEY = 'x'
SLACK_WEBHOOK_URL = 'x'

KEYWORDS = ['add', 'keywords', 'in', 'here']
SEEN_FILE = 'seen_posts.json'

def load_seen_posts():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE, 'r') as f:
            return set(json.load(f))
    return set()

def save_seen_posts(seen_posts):
    with open(SEEN_FILE, 'w') as f:
        json.dump(list(seen_posts), f)

def get_reddit_access_token():
    auth = base64.b64encode(f"{REDDIT_CLIENT_ID}:{REDDIT_CLIENT_SECRET}".encode()).decode()
    headers = {'Authorization': f'Basic {auth}', 'User-Agent': REDDIT_USER_AGENT}
    data = {'grant_type': 'client_credentials'}
    response = requests.post("https://www.reddit.com/api/v1/access_token", headers=headers, data=data)
    response_data = response.json()
    return response_data['access_token']

def get_twitter_bearer_token():
    auth = base64.b64encode(f"{TWITTER_API_KEY}:{TWITTER_API_SECRET_KEY}".encode()).decode()
    headers = {
        'Authorization': f'Basic {auth}',
        'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8'
    }
    data = {'grant_type': 'client_credentials'}
    response = requests.post("https://api.twitter.com/oauth2/token", headers=headers, data=data)
    response_data = response.json()
    return response_data['access_token']

def safe_get_json(response):
    try:
        return response.json()
    except json.JSONDecodeError:
        return None

def search_reddit(keyword, access_token):
    url = f'https://oauth.reddit.com/search?q={keyword}'
    headers = {'Authorization': f'Bearer {access_token}', 'User-Agent': REDDIT_USER_AGENT}
    response = requests.get(url, headers=headers)
    data = safe_get_json(response)
    if data:
        return data.get('data', {}).get('children', [])
    return []

def search_google_reviews(keyword):
    url = f'https://maps.googleapis.com/maps/api/place/textsearch/json?query={keyword}&key={GOOGLE_API_KEY}'
    response = requests.get(url)
    data = safe_get_json(response)
    results = []
    if data:
        for place in data.get('results', []):
            place_id = place.get('place_id')
            if place_id:
                place_details_url = f'https://maps.googleapis.com/maps/api/place/details/json?place_id={place_id}&key={GOOGLE_API_KEY}'
                details_response = requests.get(place_details_url)
                details_data = safe_get_json(details_response)
                if details_data:
                    result = {
                        'name': place.get('name'),
                        'address': place.get('formatted_address'),
                        'url': details_data.get('result', {}).get('url')
                    }
                    results.append(result)
    return results

def search_twitter(keyword, bearer_token):
    url = f'https://api.twitter.com/2/tweets/search/recent?query={keyword}'
    headers = {'Authorization': f'Bearer {bearer_token}'}
    response = requests.get(url, headers=headers)
    data = safe_get_json(response)
    if data:
        return data.get('data', [])
    return []

def send_to_slack(message):
    payload = {'text': message}
    requests.post(SLACK_WEBHOOK_URL, data=json.dumps(payload), headers={'Content-Type': 'application/json'})

def main():
    seen_posts = load_seen_posts()
    reddit_access_token = get_reddit_access_token()
    twitter_bearer_token = get_twitter_bearer_token()

    for keyword in KEYWORDS:
        reddit_results = search_reddit(keyword, reddit_access_token)
        google_results = search_google_reviews(keyword)
        twitter_results = search_twitter(keyword, twitter_bearer_token)

        for post in reddit_results:
            if post['data']['id'] not in seen_posts:
                seen_posts.add(post['data']['id'])
                send_to_slack(f"Reddit: {post['data']['title']} - {post['data']['url']}")

        for review in google_results:
            review_id = review.get('url')
            if review_id not in seen_posts:
                seen_posts.add(review_id)
                send_to_slack(f"Google Review: {review['name']} - {review['address']} - {review['url']}")

        for tweet in twitter_results:
            if tweet['id'] not in seen_posts:
                seen_posts.add(tweet['id'])
                send_to_slack(f"Twitter: {tweet['text']} - https://twitter.com/i/web/status/{tweet['id']}")

    save_seen_posts(seen_posts)

if __name__ == "__main__":
    main()
