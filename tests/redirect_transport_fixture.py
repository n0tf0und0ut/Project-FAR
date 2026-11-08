"""Native urllib redirect processing over an in-memory HTTP transport.

The canonical suite forbids network access. This fixture substitutes only the
HTTP transport; urllib's redirect/error handlers execute unchanged.
"""
from email.message import Message
import io
import urllib.request
import urllib.response


class RedirectTransport:
    def __init__(self, body):
        self.body = body
        self.requests = []
        self.forbidden = []
        self._build = urllib.request.build_opener

    def build_opener(self, *handlers):
        owner = self
        class HTTPTransport(urllib.request.HTTPHandler):
            def http_open(self, request):
                owner.requests.append((request.get_method(), request.full_url))
                headers = Message()
                if request.full_url.endswith('/forbidden'):
                    owner.forbidden.append(request.full_url)
                    status, body = 200, b'{}'
                else:
                    headers['Location'] = '/forbidden'
                    status, body = 302, owner.body
                response = urllib.response.addinfourl(io.BytesIO(body), headers, request.full_url, status)
                response.msg = 'Found' if status == 302 else 'OK'
                return response
        # Explicitly disable proxies only for this in-memory test transport.
        return self._build(urllib.request.ProxyHandler({}), *handlers, HTTPTransport())
