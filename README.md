# Queen's Reaper

A Python-based Discord moderation bot that helps protect photosensitive users by automatically detecting and removing harmful content (flashing images, strobe GIFs, etc.).

## Key Features
- **Photosensitive Safety:** Scans media attachments for rapid flashing/strobe patterns and removes them automatically.
- **Automated Quality Assurance:** Integrated CI/CD pipeline that runs unit tests on every push. Failed tests automatically generate GitHub Issues assigned to the contributor.
- **Containerized Deployment:** Fully Dockerized for easy, portable self-hosting on any server.
- **Modular Architecture:** Built with extensible event handlers for easy feature expansion.

## Quick Start

### Prerequisites
- Python 3.10+
- A Discord Bot Token (create one at the [Discord Developer Portal](https://discord.com/developers/applications))

### Setup
1. Clone the repository:
   ```bash
   git clone https://github.com/leh-x/queens-reaper.git
   cd queens-reaper
   ```
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up your Discord bot token:
   - Create an `.env` file
   - Add your token:
      ```
      DISCORD_BOT_TOKEN=your_token_here
      ```
4. Run:
   ```
   python bot.py
   ```

## Docker Deployment
For containerized setup and production deployment instructions, see [DOCKER_README.md](./DOCKER_README.md).

## CI/CD
This project utilizes **GitHub Actions** for continuous integration:
- **Automated Testing:** pytest suite runs on every push to main.
- **Auto-Triage:** If tests fail, a GitHub Issue is automatically created with a link to the failed build log and assigned to the author of the commit.

## Tech Stack
- **Language:** Python 3.10
- **Testing:** pytest
- **CI/CD:** GitHub Actions
- **Containerization:** Docker
