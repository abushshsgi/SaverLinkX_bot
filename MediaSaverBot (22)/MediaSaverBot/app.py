import os
import logging
from flask import Flask, render_template_string
from config import BOT_TOKEN
from models import init_db  # Import the database initializer function

logger = logging.getLogger(__name__)
app = Flask(__name__)

# Initialize database
init_db(app)

@app.route('/')
def home():
    # Get bot information
    try:
        from telegram import Bot
        import asyncio
        
        async def get_bot_info():
            if not BOT_TOKEN:
                return {"username": "your_bot_username", "name": "Media Downloader Bot"}
            bot = Bot(token=BOT_TOKEN)
            bot_info = await bot.get_me()
            return {"username": bot_info.username, "name": bot_info.first_name}
        
        bot_info = asyncio.run(get_bot_info())
        bot_username = bot_info["username"]
        bot_name = bot_info["name"]
    except Exception as e:
        logger.error(f"Failed to get bot info: {str(e)}")
        bot_username = "your_bot_username"
        bot_name = "Media Downloader Bot"
    
    html = '''
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{{ bot_name }} - Telegram Video Downloader</title>
        <link href="https://cdn.replit.com/agent/bootstrap-agent-dark-theme.min.css" rel="stylesheet">
        <style>
            body {
                padding-top: 2rem;
            }
            .bot-icon {
                max-width: 150px;
                margin-bottom: 2rem;
            }
            .features-list {
                text-align: left;
                max-width: 600px;
                margin: 0 auto;
            }
        </style>
    </head>
    <body>
        <div class="container" data-bs-theme="dark">
            <div class="text-center mb-5">
                <img src="https://upload.wikimedia.org/wikipedia/commons/8/82/Telegram_logo.svg" alt="Bot Icon" class="bot-icon">
                <h1 class="display-4">{{ bot_name }}</h1>
                <p class="lead">A Telegram bot for downloading videos from Instagram and YouTube</p>
                <a href="https://t.me/{{ bot_username }}" class="btn btn-primary mt-3" target="_blank">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-telegram me-2" viewBox="0 0 16 16">
                        <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0M8.287 5.906q-1.168.486-4.666 2.01-.567.225-.595.442c-.03.243.275.339.69.47l.175.055c.408.133.958.288 1.243.294q.39.01.868-.32 3.269-2.206 3.374-2.23c.05-.012.12-.026.166.016s.042.12.037.141c-.03.129-1.227 1.241-1.846 1.817-.193.18-.33.307-.358.336a8 8 0 0 1-.188.186c-.38.366-.664.64.015 1.088.327.216.589.393.85.571.284.194.568.387.936.629q.14.092.27.187c.331.236.63.448.997.414.214-.02.435-.22.547-.82.265-1.417.786-4.486.906-5.751a1.4 1.4 0 0 0-.013-.315.34.34 0 0 0-.114-.217.53.53 0 0 0-.31-.093c-.3.005-.763.166-2.984 1.09"/>
                    </svg>
                    Open in Telegram
                </a>
            </div>
            
            <div class="row justify-content-center mb-5">
                <div class="col-md-8">
                    <div class="card">
                        <div class="card-header">
                            <h3>Features</h3>
                        </div>
                        <div class="card-body features-list">
                            <ul class="list-group list-group-flush">
                                <li class="list-group-item">✅ Download videos from YouTube</li>
                                <li class="list-group-item">✅ Download videos from Instagram</li>
                                <li class="list-group-item">✅ Simple, user-friendly interface</li>
                                <li class="list-group-item">✅ Fast and reliable performance</li>
                                <li class="list-group-item">✅ Completely free to use</li>
                            </ul>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="row justify-content-center mb-5">
                <div class="col-md-8">
                    <div class="card">
                        <div class="card-header">
                            <h3>How to Use</h3>
                        </div>
                        <div class="card-body">
                            <ol class="text-start">
                                <li class="mb-3">Search for <strong>@{{ bot_username }}</strong> on Telegram or click the button above</li>
                                <li class="mb-3">Start a chat with the bot by clicking on <strong>Start</strong></li>
                                <li class="mb-3">Copy a YouTube or Instagram video URL</li>
                                <li class="mb-3">Send the URL to the bot</li>
                                <li class="mb-3">Wait for the bot to process and download the video</li>
                                <li>Enjoy your downloaded video!</li>
                            </ol>
                        </div>
                    </div>
                </div>
            </div>
            
            <footer class="text-center mt-5 mb-5">
                <p>© 2025 Media Downloader Bot. All rights reserved.</p>
                <p>
                    <a href="#" class="text-decoration-none me-3">Privacy Policy</a>
                    <a href="#" class="text-decoration-none me-3">Terms of Service</a>
                    <a href="#" class="text-decoration-none">Support</a>
                </p>
            </footer>
        </div>
    </body>
    </html>
    '''
    
    return render_template_string(html, bot_username=bot_username, bot_name=bot_name)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)