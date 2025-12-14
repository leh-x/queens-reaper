# Queen's Reaper - Discord Photosensitive Content Moderator

## Docker Setup & Usage

### Prerequisites
- Docker and Docker Compose installed
- Discord bot token in `.env` file

### Quick Start

**1. Build and start the bot:**
```bash
docker-compose up -d
```

**2. View logs:**
```bash
docker-compose logs -f
```

**3. Stop the bot:**
```bash
docker-compose down
```

### Common Commands

```bash
# Start the bot (in background)
docker-compose up -d

# Start the bot (with logs in foreground)
docker-compose up

# Stop the bot
docker-compose down

# Restart the bot
docker-compose restart

# View live logs
docker-compose logs -f

# View last 100 lines of logs
docker-compose logs --tail=100

# Rebuild after code changes
docker-compose up -d --build

# Check if container is running
docker-compose ps

# Execute command in running container
docker-compose exec discord-bot bash
```

### File Structure

```
Queens-Reaper/
├── bot.py                 # Main bot code
├── requirements.txt       # Python dependencies
├── .env                   # Bot token (not in git)
├── Dockerfile            # Docker image definition
├── docker-compose.yml    # Docker compose configuration
├── .dockerignore         # Files to exclude from image
└── README.md            # This file
```

### Environment Variables

Create a `.env` file:
```
DISCORD_BOT_TOKEN=your_token_here
```

### Updating the Bot

After making code changes:

```bash
# Rebuild and restart
docker-compose up -d --build

# Or do it in steps
docker-compose down
docker-compose build
docker-compose up -d
```

### Troubleshooting

**Bot won't start:**
```bash
# Check logs
docker-compose logs

# Check container status
docker-compose ps

# Rebuild from scratch
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

**Out of memory:**
```bash
# Check resource usage
docker stats queens-reaper

# Uncomment resource limits in docker-compose.yml
```

**Need to access container shell:**
```bash
docker-compose exec discord-bot bash
```

### Deployment to Raspberry Pi

**1. Install Docker on Pi:**
```bash
curl -sSL https://get.docker.com | sh
sudo usermod -aG docker $USER
# Log out and back in
sudo apt-get install docker-compose-plugin
```

**2. Copy files to Pi:**
```bash
# From your computer
scp -r Queens-Reaper/ pi@raspberrypi.local:~/
```

**3. On the Pi:**
```bash
cd ~/Queens-Reaper
docker-compose up -d
```

**4. Set to start on boot:**
Docker containers with `restart: unless-stopped` will automatically start when the Pi boots.

### Resource Usage

Expected resource usage:
- **RAM:** ~150-300 MB
- **CPU:** <5% idle, spikes during video analysis
- **Disk:** ~500 MB for image + temporary files

### Production Recommendations

1. **Enable logging rotation** to prevent disk fill
2. **Monitor with health checks** (already configured)
3. **Set resource limits** if running multiple services
4. **Backup your .env file** securely

### Development Workflow

**On Windows (testing):**
```bash
# Make code changes
# Test in Docker
docker-compose up --build

# If it works, commit
git add .
git commit -m "Your changes"
git push
```

**On Raspberry Pi (production):**
```bash
# Pull latest code
git pull

# Rebuild and restart
docker-compose up -d --build
```

### Multi-Service Setup

To run multiple services on your Pi, create a project structure:

```
/home/pi/
├── queens-reaper/
│   └── docker-compose.yml
├── other-service/
│   └── docker-compose.yml
```

Or combine into one `docker-compose.yml`:

```yaml
version: '3.8'
services:
  discord-bot:
    build: ./queens-reaper
    restart: unless-stopped
  
  other-service:
    image: some/image
    restart: unless-stopped
```

### Security Notes

- `.env` file is in `.gitignore` - never commit tokens
- Container runs as non-root user (Python image default)
- Only necessary ports are exposed (none by default)
- Dependencies are pinned in requirements.txt

### Support

For issues:
1. Check logs: `docker-compose logs -f`
2. Verify .env file exists and has token
3. Ensure Discord bot has Message Content Intent enabled
4. Check bot permissions in Discord server
