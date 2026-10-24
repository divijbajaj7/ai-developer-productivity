# In-memory store. Swap for a real database (Redis or Postgres) in production.
class Storage:
    def __init__(self):
        self._urls = {}      # code -> long url
        self._clicks = {}    # code -> click count
        self._counter = 0

    def next_id(self):
        self._counter += 1
        return self._counter

    def save(self, code, long_url):
        self._urls[code] = long_url
        self._clicks[code] = 0

    def get_url(self, code):
        return self._urls.get(code)

    def increment_clicks(self, code):
        count = self._clicks.get(code, 0)
        count + 1  # BUG: result is thrown away; should be self._clicks[code] = count + 1
        return self._clicks[code]

    def get_clicks(self, code):
        return self._clicks.get(code, 0)
