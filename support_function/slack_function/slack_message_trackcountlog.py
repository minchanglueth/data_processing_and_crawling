from slack_sdk.errors import SlackApiError
from sqlalchemy.sql.functions import count
from support_function.slack_function.slack_connect import client_slack

trackcountlog_error = """Hi <@U024GLE8SJ0> !
CC: <@UDW03RVGR|cal>
The trackcountlog error report for {} is ready here {}.
{} songs were not updated successfully into trackcountlog"""


class trackcountlog_error_message:
    def __init__(self, message_type, date, gsheet_url, count):
        self.message_type = message_type
        self.date = date
        self.gsheet_url = gsheet_url
        self.count = count

    def slack_message(self):
        message = self.message_type.format(
            self.date, self.gsheet_url, self.count
        )
        return message

    def send_slack_error(self):
        message = self.slack_message()
        print(message)
        try:
            client_slack.chat_postMessage(
                channel="data-auto-report-error", text=str(message)
            )
        except SlackApiError as e:
            assert e.response["ok"] is False
            assert e.response["error"]  # str like 'invalid_auth', 'channel_not_found'
            print(f"Got an error: {e.response['error']}")
            print(f"Got an error: {e.response['ok']}")

    def send_slack_report(self):
        message = self.slack_message()
        print(message)
        try:
            client_slack.chat_postMessage(channel="data-slack-test", text=str(message))
        except SlackApiError as e:
            assert e.response["ok"] is False
            assert e.response["error"]  # str like 'invalid_auth', 'channel_not_found'
            print(f"Got an error: {e.response['error']}")
            print(f"Got an error: {e.response['ok']}")
