import threading


# In-memory store. Swap for a real database (Redis or Postgres) in production.
class Storage:
    def __init__(self):
        self._urls = {}      # code -> long url
        self._clicks = {}    # code -> click count
        self._counter = 0
        self._lock = threading.Lock()  # guards the id counter

    def next_id(self):
        with self._lock:
            self._counter += 1
            return self._counter

    def save(self, code, long_url):
        self._urls[code] = long_url
        self._clicks[code] = 0

    def get_url(self, code):
        return self._urls.get(code)

    def increment_clicks(self, code):
        if code not in self._urls:
            return 0  # never saved; don't create a click entry
        count = self._clicks.get(code, 0)
        self._clicks[code] = count + 1
        return self._clicks[code]

    def get_clicks(self, code):
        return self._clicks.get(code, 0)
