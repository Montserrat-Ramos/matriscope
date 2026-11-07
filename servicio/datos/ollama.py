"""C7: interfaz de Ollama mediante HTTP local, sin servicios de modelos externos."""

import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ModelUnavailable(RuntimeError):
    pass


class OllamaAdapter:
    def __init__(self, base_url: str, timeout: int = 90):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout

    def _request(self, path: str, payload=None, timeout=None):
        data = json.dumps(payload).encode('utf-8') if payload is not None else None
        request = Request(
            self.base_url + path,
            data=data,
            headers={'Content-Type': 'application/json'},
            method='POST' if payload is not None else 'GET',
        )
        try:
            with urlopen(request, timeout=timeout or self.timeout) as result:
                return json.loads(result.read().decode('utf-8'))
        except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
            raise ModelUnavailable(f'Ollama no responde en {path}: {exc}') from exc

    def models(self):
        data = self._request('/api/tags', timeout=3)
        return [m.get('name', '') for m in data.get('models', [])]

    def model_manifest(self):
        """Captura nombres y digests para documentar la versión utilizada."""
        data=self._request('/api/tags',timeout=3)
        return [{'name':m.get('name',''),'digest':m.get('digest','')}
                for m in data.get('models',[])]

    def embed(self, texts, model: str):
        if not texts:
            return []
        data = self._request('/api/embed', {'model': model, 'input': texts})
        embeddings = data.get('embeddings')
        if not isinstance(embeddings, list) or len(embeddings) != len(texts):
            raise ModelUnavailable('Ollama respondió sin embeddings para todos los fragmentos.')
        return embeddings

    def chat(self, messages, model: str, json_mode: bool = False, timeout=None):
        payload = {'model': model, 'messages': messages, 'stream': False,
                   'options': {'temperature': 0.1}}
        if json_mode:
            payload['format'] = 'json'
        data = self._request('/api/chat', payload, timeout=timeout)
        content = data.get('message', {}).get('content', '')
        if not content:
            raise ModelUnavailable('Ollama devolvió una respuesta vacía.')
        return content

