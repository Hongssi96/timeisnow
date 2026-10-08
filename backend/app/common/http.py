"""Shared provider HTTP opener; callers never log provider payloads."""
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None
