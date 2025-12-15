"""
WSGI entry point cho PythonAnywhere
File này được sử dụng bởi PythonAnywhere để chạy FastAPI app
FastAPI là ASGI app, cần adapter để chạy trên WSGI server của PythonAnywhere
"""
import sys
import os
import asyncio
from io import BytesIO

# Thêm đường dẫn project vào Python path
path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.insert(0, path)

# Import app từ main.py
from main import app

# WSGI wrapper để chạy ASGI app (FastAPI) trên WSGI server
class ASGItoWSGI:
    """Adapter để chạy ASGI app trên WSGI server"""
    
    def __init__(self, asgi_app):
        self.asgi_app = asgi_app
        self.loop = None
    
    def _get_or_create_loop(self):
        """Lấy hoặc tạo event loop"""
        try:
            return asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            return loop
    
    def _wsgi_to_asgi_scope(self, environ):
        """Convert WSGI environ sang ASGI scope"""
        method = environ['REQUEST_METHOD']
        path = environ.get('PATH_INFO', '/')
        query_string = environ.get('QUERY_STRING', '').encode()
        
        # Headers
        headers = []
        for key, value in environ.items():
            if key.startswith('HTTP_'):
                header_name = key[5:].replace('_', '-').lower()
                headers.append([header_name.encode(), value.encode()])

        # Các header đặc biệt không có tiền tố HTTP_
        if 'CONTENT_TYPE' in environ:
            headers.append([b'content-type', environ['CONTENT_TYPE'].encode()])
        if 'CONTENT_LENGTH' in environ and environ['CONTENT_LENGTH']:
            headers.append([b'content-length', environ['CONTENT_LENGTH'].encode()])
        
        # Body
        try:
            content_length = int(environ.get('CONTENT_LENGTH') or 0)
        except (ValueError, TypeError):
            content_length = 0

        try:
            if content_length > 0:
                body = environ['wsgi.input'].read(content_length)
            else:
                body = environ['wsgi.input'].read()
        except:
            body = b''
        
        scope = {
            'type': 'http',
            'method': method,
            'path': path,
            'query_string': query_string,
            'headers': headers,
            'body': body,
            'client': [environ.get('REMOTE_ADDR', '127.0.0.1'), environ.get('REMOTE_PORT', 0)],
            'server': [environ.get('SERVER_NAME', 'localhost'), int(environ.get('SERVER_PORT', 80))],
            'scheme': environ.get('wsgi.url_scheme', 'http'),
            'root_path': environ.get('SCRIPT_NAME', ''),
            'http_version': '1.1',
            'raw_path': path.encode(),
        }
        return scope
    
    def _asgi_to_wsgi_response(self, status, headers, body):
        """Convert ASGI response sang WSGI format"""
        status_code = int(status.split()[0])
        response_headers = [(name.decode(), value.decode()) for name, value in headers]
        
        # Collect body chunks
        body_chunks = []
        async def receive_body():
            async for chunk in body:
                if chunk['type'] == 'http.response.body':
                    body_chunks.append(chunk.get('body', b''))
        
        loop = self._get_or_create_loop()
        loop.run_until_complete(receive_body())
        
        return status_code, response_headers, b''.join(body_chunks)
    
    def __call__(self, environ, start_response):
        """WSGI application interface"""
        scope = self._wsgi_to_asgi_scope(environ)
        
        # Collect ASGI messages
        messages = []
        request_sent = False
        
        async def receive():
            """ASGI receive callable"""
            nonlocal request_sent
            if not request_sent:
                request_sent = True
                return {
                    'type': 'http.request',
                    'body': scope['body'],
                    'more_body': False
                }
            # Return empty dict to signal end of request
            return {'type': 'http.disconnect'}
        
        async def send(message):
            """ASGI send callable"""
            messages.append(message)
        
        # Run ASGI app
        loop = self._get_or_create_loop()
        try:
            loop.run_until_complete(self.asgi_app(scope, receive, send))
        except Exception as e:
            # Fallback error response
            start_response('500 Internal Server Error', [('Content-Type', 'text/plain')])
            return [f'Error: {str(e)}'.encode()]
        
        # Process ASGI messages
        status_code = 500
        response_headers = []
        body_chunks = []
        
        for message in messages:
            if message['type'] == 'http.response.start':
                status_code = message['status']
                response_headers = [
                    (name.decode() if isinstance(name, bytes) else name,
                     value.decode() if isinstance(value, bytes) else value)
                    for name, value in message['headers']
                ]
            elif message['type'] == 'http.response.body':
                body_chunks.append(message.get('body', b''))
                # If more_body is False or not present, this is the last chunk
                if not message.get('more_body', False):
                    break
        
        # Default response if no messages received
        if not response_headers:
            status_code = 500
            response_headers = [('Content-Type', 'text/plain')]
            body_chunks = [b'Internal Server Error']
        
        # Start WSGI response
        status_text = f"{status_code} OK"
        start_response(status_text, response_headers)
        
        # Return body
        return body_chunks if body_chunks else [b'']

# Tạo WSGI application
application = ASGItoWSGI(app)

