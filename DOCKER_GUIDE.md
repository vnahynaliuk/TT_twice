# Docker Guide for Telegram Bot

## What is Docker?

Docker is like a **virtual computer inside your computer**. Instead of installing software directly on your system, Docker creates a lightweight container that:

- ✅ Contains your bot code
- ✅ Contains all dependencies (Python, ffmpeg, libraries)
- ✅ Runs exactly the same everywhere
- ✅ Doesn't interfere with your system

**Analogy:** If software was food delivery:
- **Without Docker:** Each restaurant has to have different kitchens everywhere
- **With Docker:** Package the kitchen once, ship it anywhere, works identical

---

## Installing Docker

### On macOS:
1. Download [Docker Desktop](https://www.docker.com/products/docker-desktop)
2. Install it
3. Open Terminal and verify:
   ```bash
   docker --version
   ```

### On Linux (Ubuntu/Debian):
```bash
sudo apt update
sudo apt install docker.io
sudo systemctl start docker
docker --version
```

### On Windows:
1. Download [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop)
2. Install and restart
3. Open PowerShell and verify:
   ```powershell
   docker --version
   ```

---

## Understanding Dockerfile

A `Dockerfile` is like a recipe that tells Docker how to build your bot container.

**Our Dockerfile:**
```dockerfile
FROM python:3.11-slim
```
- Start with Python 3.11 image (lightweight)

```dockerfile
WORKDIR /app
```
- Create working directory inside container

```dockerfile
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*
```
- Install ffmpeg (needed for video processing)

```dockerfile
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
```
- Copy requirements file and install all Python packages

```dockerfile
COPY . .
```
- Copy your bot code into container

```dockerfile
CMD ["python", "bot.py"]
```
- When container starts, run the bot

---

## Docker Commands Explained

### 1. **Build an image**
```bash
docker build -t tiktok-bot .
```
- `-t tiktok-bot` = give it a name
- `.` = use Dockerfile in current directory
- Creates a blueprint (image) of your bot

**Output:** You'll see it downloading Python, installing packages, etc.

### 2. **Run a container**
```bash
docker run -e TELEGRAM_BOT_TOKEN=your_token_here tiktok-bot
```
- `-e TELEGRAM_BOT_TOKEN=...` = set environment variable
- `tiktok-bot` = use the image we built
- Creates and starts a container from the image

**What happens:**
- Container starts
- Bot runs inside
- You see bot logs in Terminal

### 3. **Stop a container**
```bash
Ctrl+C
```
or
```bash
docker stop container_name
```

### 4. **List running containers**
```bash
docker ps
```

### 5. **List all images**
```bash
docker images
```

### 6. **Remove an image**
```bash
docker rmi tiktok-bot
```

---

## Step-by-Step: Running Your Bot in Docker

### Step 1: Build the image
```bash
cd /Users/valeriianahynaliuk/git/tiktok-bot
docker build -t tiktok-bot .
```

Wait for it to complete. You'll see:
```
Successfully tagged tiktok-bot:latest
```

### Step 2: Run the container
```bash
docker run -e TELEGRAM_BOT_TOKEN=8514195672:AAEOpyHdy-hlTJuTtbnBgJRyNKUxALt3KRU tiktok-bot
```

**Output:**
```
2026-03-23 20:50:46,429 - telegram.ext.Application - INFO - Application started
```

Bot is now running in a Docker container!

### Step 3: Test the bot
- Send a message to your bot on Telegram
- It should respond (downloading, etc.)

### Step 4: Stop the bot
```bash
Ctrl+C
```

---

## Docker on Different Machines

### Same code, 3 different machines:

**Your Mac:**
```bash
docker run -e TELEGRAM_BOT_TOKEN=your_token tiktok-bot
```

**Friend's Mac:**
```bash
docker run -e TELEGRAM_BOT_TOKEN=your_token tiktok-bot
```

**Linux Server:**
```bash
docker run -e TELEGRAM_BOT_TOKEN=your_token tiktok-bot
```

**All work identically!** No need to:
- Install Python
- Install ffmpeg
- Deal with dependency issues
- Worry about Python versions

---

## Docker vs Virtual Environment

### Virtual Environment (.venv)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python bot.py
```
✅ Lightweight
✅ Easy to start
❌ Only works on your machine's OS
❌ Need to install ffmpeg manually

### Docker
```bash
docker build -t tiktok-bot .
docker run -e TELEGRAM_BOT_TOKEN=your_token tiktok-bot
```
✅ Works on any OS (Mac, Linux, Windows)
✅ Everything included (ffmpeg, Python, packages)
✅ Easy to deploy to cloud
❌ Slightly heavier (~300MB)
❌ Need Docker installed

---

## Deploying Docker to Cloud

### Option 1: Railway.app with Docker

1. Create `railway.toml`:
   ```toml
   [build]
   dockerfile = "Dockerfile"
   
   [deploy]
   startCommand = "python bot.py"
   ```

2. Push to GitHub
3. Connect to Railway
4. Railway automatically uses Dockerfile
5. Bot runs in Railway's servers

### Option 2: Docker Hub (Share with friends)

1. Create Docker Hub account
2. Build image:
   ```bash
   docker build -t yourusername/tiktok-bot .
   ```

3. Push to Docker Hub:
   ```bash
   docker login
   docker push yourusername/tiktok-bot
   ```

4. Friends can run it:
   ```bash
   docker run -e TELEGRAM_BOT_TOKEN=token yourusername/tiktok-bot
   ```

### Option 3: AWS/Google Cloud

- Both support Docker containers directly
- Upload Dockerfile
- They handle deployment

---

## Docker Volumes (Keeping Files)

Current setup deletes videos after sending. To keep them:

```bash
docker run \
  -e TELEGRAM_BOT_TOKEN=your_token \
  -v /Users/you/tiktok-bot/downloads:/app/downloads \
  tiktok-bot
```

- `-v local_path:container_path` = share folder
- Videos saved in your Mac's `downloads/` folder

---

## Useful Docker Tips

### See what's inside a running container:
```bash
docker exec -it container_id bash
```
Then you're inside the container, can run commands.

### See container logs:
```bash
docker logs container_name
```

### Run container in background:
```bash
docker run -d -e TELEGRAM_BOT_TOKEN=token tiktok-bot
```
- `-d` = detached mode (runs in background)

### Restart automatically on failure:
```bash
docker run --restart=always -e TELEGRAM_BOT_TOKEN=token tiktok-bot
```

---

## Common Issues

### Issue: "Docker command not found"
**Solution:** Docker not installed. Download from docker.com

### Issue: "Cannot connect to Docker daemon"
**Solution:** Docker not running. Open Docker Desktop app.

### Issue: "ffmpeg not found in container"
**Solution:** Already included in our Dockerfile. Rebuild it:
```bash
docker build -t tiktok-bot .
```

### Issue: Bot starts but doesn't respond
**Solution:** Check token is correct:
```bash
docker logs container_id
```

---

## Summary

| Task | Command |
|------|---------|
| Install Docker | Download from docker.com |
| Build image | `docker build -t tiktok-bot .` |
| Run bot | `docker run -e TELEGRAM_BOT_TOKEN=token tiktok-bot` |
| Stop bot | `Ctrl+C` |
| See logs | `docker logs container_id` |
| Deploy to Railway | Push Dockerfile to GitHub → Railway connects |

---

## Quick Decision

**Use Docker if:**
- ✅ Deploying to cloud/server
- ✅ Sharing with friends
- ✅ Want guaranteed same behavior everywhere

**Don't need Docker if:**
- ✅ Just running locally on Mac
- ✅ Don't care about deployment

For you: **Railway.app is simpler.** But Docker is good to know!
