import telegram
from telegram import Bot

class TelegramFacade(object):

    def __init__(self, token):
        self.token = token
        self.client = Bot(self.token)

    def send_message(self, cid, message):
        """Sends a markdown message to our telegram user.
        Args:
            message: String, markdown representing a message to send.
        Returns:
            Telegram response object.
        """
        return self.client.send_message(
            cid,
            message,
            parse_mode = telegram.ParseMode.HTML
        )

    def get_updates(self):
      return self.client.getUpdates()