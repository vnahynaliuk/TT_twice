# Telegram Video Downloader Bot

A Telegram bot that downloads videos from TikTok, Instagram Reels, YouTube, and Twitter/X.

## Features

✅ Download videos from multiple platforms:
- TikTok
- Instagram Reels
- YouTube (full videos & shorts)
- Twitter/X

✅ Commands:
- `/start` - Welcome message
- `/help` - Show help
- `/about` - About the bot

## Prerequisites

- Python 3.8+
- ffmpeg (for video processing)

## Installation

### Local Setup (macOS/Linux/Windows)

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd tiktok-bot
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create `.env` file**
   ```bash
   touch .env
   ```
   Add your bot token:
   ```
   TELEGRAM_BOT_TOKEN=your_token_here
   ```

5. **Get your bot token from @BotFather on Telegram**

6. **Run the bot**
   ```bash
   python bot.py
   ```

## Server Deployment (24/7 Running)

### Option 1: Using Railway (Recommended - Free & Easy)

1. **Create account on [railway.app](https://railway.app)**
2. **Connect your GitHub repository**
3. **Add environment variables** in Railway dashboard:
   - `TELEGRAM_BOT_TOKEN=your_token`
4. **Add `Procfile` to root directory**:
   ```
   worker: python bot.py
   ```
5. **Deploy** - Railway will automatically run your bot

### Option 2: Using Heroku

1. **Create account on [heroku.com](https://heroku.com)**
2. **Install Heroku CLI**
3. **Create Procfile**:
   ```
   worker: python bot.py
   ```
4. **Deploy**:
   ```bash
   heroku login
   heroku create your-app-name
   heroku config:set TELEGRAM_BOT_TOKEN=your_token
   git push heroku main
   heroku ps:scale worker=1
   ```

### Option 3: Using VPS (DigitalOcean, Linode, AWS)

1. **SSH into your server**
2. **Install dependencies**:
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip ffmpeg
   ```
3. **Clone and setup**:
   ```bash
   git clone <your-repo-url>
   cd tiktok-bot
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
4. **Create `.env` file with token**
5. **Run with systemd** (to keep it running):
   Create `/etc/systemd/system/tiktok-bot.service`:
   ```ini
   [Unit]
   Description=Telegram Video Downloader Bot
   After=network.target

   [Service]
   Type=simple
   User=ubuntu
   WorkingDirectory=/home/ubuntu/tiktok-bot
   ExecStart=/home/ubuntu/tiktok-bot/venv/bin/python bot.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```
   
   Enable and start:
   ```bash
   sudo systemctl enable tiktok-bot
   sudo systemctl start tiktok-bot
   ```

### Option 4: Using Docker (For Any Server)

Create `Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
```

Build and run:
```bash
docker build -t tiktok-bot .
docker run -e TELEGRAM_BOT_TOKEN=your_token tiktok-bot
```

## Recommended: Railway.app (Easiest for Beginners)

**Why Railway?**
- ✅ Free tier (good for starting)
- ✅ Auto-deploys from GitHub
- ✅ Handles ffmpeg automatically
- ✅ Environment variables via GUI
- ✅ Logs accessible from dashboard
- ✅ One-click deploy

**Steps:**
1. Push code to GitHub
2. Sign up on railway.app
3. Connect GitHub repo
4. Add `TELEGRAM_BOT_TOKEN` env variable
5. Done! Bot runs 24/7

## Troubleshooting

**Bot not responding?**
- Check token is correct
- Verify bot is running: `ps aux | grep bot.py`
- Check logs for errors

**Download fails?**
- Ensure ffmpeg is installed: `ffmpeg -version`
- Check file size < 50MB
- Verify URL is correct

**On macOS, install ffmpeg:**
```bash
brew install ffmpeg
```

## License

MIT
