- name: Execute Telegram Alert Agent
        env:
          TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
        run: python agent_bot.py
