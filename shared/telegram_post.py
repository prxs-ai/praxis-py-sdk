#!/usr/bin/env python3
"""
Telegram Message Poster
Posts messages to Telegram channels using Telegram Bot API
"""
import json
import sys
import os
import argparse
import datetime
import requests

def main():
    parser = argparse.ArgumentParser(description='Telegram message poster for Dagger using Telegram Bot API')
    parser.add_argument('--message', type=str, help='Message content to post')
    parser.add_argument('--channel', type=str, help='Channel ID (optional, uses default from env if not provided)')
    
    args = parser.parse_args()
    
    message = args.message or os.environ.get('message') or os.environ.get('MESSAGE')
    if not message:
        print(json.dumps({
            "status": "error",
            "message": "No message provided. Use --message parameter or set env var 'message'/'MESSAGE'."
        }))
        return
    
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    
    channel_id = os.environ.get("TELEGRAM_CHANNEL_ID")
    
    try:
        api_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        
        payload = {
            "chat_id": channel_id,
            "text": message,
            "parse_mode": "Markdown"  # Support markdown formatting
        }
        
        print(json.dumps({
            "status": "processing",
            "message": f"📤 Posting message to Telegram channel..."
        }))
        
        # Send the request to Telegram API
        response = requests.post(api_url, json=payload, timeout=30)
        response_data = response.json()
        
        if response.status_code == 200 and response_data.get('ok'):
            # Success - extract message info
            message_data = response_data.get('result', {})
            message_id = message_data.get('message_id')
            chat_info = message_data.get('chat', {})
            chat_title = chat_info.get('title', 'Unknown Channel')
            chat_username = chat_info.get('username', '')
            
            # Create timestamp for logging
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Create message preview (first 100 chars)
            message_preview = message[:100] + ("..." if len(message) > 100 else "")
            
            # Generate Telegram link if possible
            telegram_link = None
            if chat_username:
                telegram_link = f"https://t.me/{chat_username}/{message_id}"
            elif str(channel_id).startswith('-100'):
                # For supergroups/channels, convert to public link format if username exists
                pass  # We need username for public link
            
            # Save posting log
            reports_dir = "/shared/reports"
            os.makedirs(reports_dir, exist_ok=True)
            
            log_data = {
                'metadata': {
                    'posted_at': datetime.datetime.now().isoformat(),
                    'channel_id': channel_id,
                    'channel_title': chat_title,
                    'message_id': message_id,
                    'bot_token_used': f"...{bot_token[-10:]}" if bot_token else None
                },
                'message': {
                    'content': message,
                    'length': len(message),
                    'preview': message_preview
                },
                'telegram_response': response_data
            }
            
            log_filename = f"telegram_post_{timestamp}.json"
            log_filepath = os.path.join(reports_dir, log_filename)
            
            with open(log_filepath, 'w', encoding='utf-8') as f:
                json.dump(log_data, f, ensure_ascii=False, indent=2)
            
            result = {
                "status": "success",
                "message": f"✅ Successfully posted message to {chat_title}",
                "data": {
                    "channel_id": channel_id,
                    "channel_title": chat_title,
                    "channel_username": chat_username,
                    "message_id": message_id,
                    "message_preview": message_preview,
                    "message_length": len(message),
                    "telegram_link": telegram_link,
                    "posted_at": datetime.datetime.now().isoformat(),
                    "saved_to": log_filename,
                    "saved_to_path": log_filepath,
                    "download_url": f"{os.environ.get('AGENT_BASE_URL', 'http://localhost:8000')}/reports/{log_filename}"
                }
            }
            
        else:
            # Error from Telegram API
            error_description = response_data.get('description', 'Unknown error')
            error_code = response_data.get('error_code', response.status_code)
            
            result = {
                "status": "error",
                "message": f"Telegram API error ({error_code}): {error_description}",
                "details": {
                    "error_code": error_code,
                    "description": error_description,
                    "response_status": response.status_code
                }
            }
            
    except requests.exceptions.Timeout:
        result = {
            "status": "error",
            "message": "Request timeout - Telegram API did not respond within 30 seconds"
        }
    except requests.exceptions.ConnectionError:
        result = {
            "status": "error", 
            "message": "Connection error - Unable to connect to Telegram API"
        }
    except requests.exceptions.RequestException as e:
        result = {
            "status": "error",
            "message": f"Request error: {str(e)}"
        }
    except Exception as e:
        result = {
            "status": "error",
            "message": f"Error posting to Telegram: {str(e)}"
        }
    
    print(json.dumps(result, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()