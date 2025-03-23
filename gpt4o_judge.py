import requests
import json
import logging
import time
import argparse

from constants import *

def get_chat_gpt_response(prompt, api_key, max_retries=5, retry_delay=2):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-4o",
        "messages": [
            {
                "role": "system", 
                "content": "You are ChatGPT, a large language model trained by OpenAI, based on the GPT-4 architecture. You are chatting with the user via the ChatGPT iOS app. This means most of the time your lines should be a sentence or two, unless the user's request requires reasoning or long-form outputs. Never use emojis, unless explicitly asked to. Knowledge cutoff: 2023-10 Current date: 2024-08-15. Image input capabilities: Enabled Personality: v2"
            },
            {
                "role": "user", 
                "content": prompt
            }
        ]
    }

    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=headers, json=data, timeout=20)
            response.raise_for_status()  
            return response.json()
        except requests.RequestException as e:
            logging.error(f"Request failed (attempt {attempt + 1}): {e}")
            if attempt < max_retries - 1:  
                time.sleep(retry_delay)
            else:
                return {"error": str(e)}


def process_description(video_key, video_data, api_key, prompt, delay_between_requests):
    response = get_chat_gpt_response(prompt, api_key)
    time.sleep(delay_between_requests)

    if 'error' in response:
        video_data['judgement'] = ''
        print(f"video processing: {video_key} fail.")
        return video_key
    else:
        judgement = response.get('choices', [{}])[0].get('message', {}).get('content', 'No judgement available')
        video_data['judgement'] = judgement
        print(f"video processing: {video_key} succeed.")
        return None



def main(json_file_path, api_key, output_file_path, delay_between_requests):
    try:
        with open(json_file_path, 'r') as f:
            data = json.load(f)
    except Exception as e:
        logging.error(f"Failed to read JSON file: {e}")
        return

    error_key = []
    for split, videos in data.items():
        for video_key, video_data in videos.items():
            desc = video_data.get('desc', '')
            if not desc:
                print(f"No description found for video {video_key}")
                video_data['judgement'] = ''
                continue
                
            if split == 'interleave':
                prompt = interleave.format(desc, video_data['event_info']['unexpected'])
            elif split == 'entire':
                prompt = entire.format(desc, video_data['event_info']['caption'])
            else:
                prompt = misleading.format(desc, video_data['event_info']['caption'])
                 
            return_video_key = process_description(video_key, video_data, api_key, prompt, delay_between_requests)
            if return_video_key is not None:
                error_key.append(return_video_key)
                
    print (error_key)
    
    try:
        with open(output_file_path, 'w') as f:
            json.dump(data, f, indent=4)
        logging.info(f"Results saved to {output_file_path}")
    except Exception as e:
        logging.error(f"Failed to write JSON file: {e}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json_file_path", type=str, required=True)
    parser.add_argument("--output_file_path", type=str, required=True)
    parser.add_argument("--delay_between_requests", type=int, default=0)
    parser.add_argument("--api_key", type=str, required=True)
    args = parser.parse_args()

    json_file_path = args.json_file_path
    output_file_path = args.output_file_path
    delay_between_requests = args.delay_between_requests
    api_key = args.api_key

    main(json_file_path, api_key, output_file_path, delay_between_requests)
