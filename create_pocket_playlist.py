name: Pocket Playlist Generator

on:
  schedule:
    - cron: '*/15 * * * *'
  push:
    paths:
      - '**'
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - name: Check out repository code
        uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.9'

      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests
          # No selenium needed anymore!

      - name: Run Playlist Generator Script
        run: python create_pocket_playlist.py

      - name: Commit and Push Changes
        run: |
          git config --global user.name "GitHub Action"
          git config --global user.email "action@github.com"
          git add pocket_playlist.m3u
          git commit -m "Auto-update Playlist" || echo "No changes to commit"
          git pull origin main --rebase
          git push origin main