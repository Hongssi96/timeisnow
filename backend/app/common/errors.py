"""Shared API error contract. Codes and messages follow the Notion specification."""


class AuthError(Exception):
    def __init__(self, status, code, message, headers=None):
        self.status, self.code, self.message, self.headers = status, code, message, headers
