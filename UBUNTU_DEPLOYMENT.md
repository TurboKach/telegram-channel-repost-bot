# Ubuntu VPS Deployment Guide - Fonts

## Required Fonts for Watermarking

The bot requires TrueType fonts for proper watermark rendering. The code tries fonts in this order:

1. **Liberation Sans** (recommended - usually pre-installed)
2. **DejaVu Sans** (common fallback)
3. **Ubuntu Font** (Ubuntu-specific)

## Check Installed Fonts

On your Ubuntu VPS, run:

```bash
ls /usr/share/fonts/truetype/liberation/
ls /usr/share/fonts/truetype/dejavu/
ls /usr/share/fonts/truetype/ubuntu/
```

## Install Fonts (if needed)

### Option 1: Liberation Fonts (Recommended)
```bash
sudo apt update
sudo apt install fonts-liberation
```

### Option 2: DejaVu Fonts
```bash
sudo apt update
sudo apt install fonts-dejavu
```

### Option 3: Ubuntu Fonts
```bash
sudo apt update
sudo apt install fonts-ubuntu
```

## Verify Font Installation

After installation, verify fonts are available:

```bash
fc-list | grep -i liberation
fc-list | grep -i dejavu
fc-list | grep -i ubuntu
```

## What if No Fonts Are Available?

The code will automatically fall back to PIL's default font, but this will result in very small text. It's highly recommended to install at least one of the font packages above.

## Testing Fonts on VPS

You can test which font is being used by checking the bot logs. When a watermark is applied, you'll see:

```
Found available font: /usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf
```

or

```
No TrueType fonts found, using default font
```

If you see the second message, install fonts using the commands above.

## Recommended for Production

Install Liberation fonts - they're the most reliable and commonly pre-installed:

```bash
sudo apt update
sudo apt install fonts-liberation
```

Then restart your bot:

```bash
# If using systemd
sudo systemctl restart your-bot-service

# If using docker
docker compose restart

# If running manually
# Stop the bot and restart it
```
