#!/usr/local/bin/python
#app.run(debug = False, host='0.0.0.0',port=80)

from tornado.wsgi import WSGIContainer
from tornado.ioloop import IOLoop
from tornado.web import FallbackHandler, RequestHandler, Application
#from flasky import app
from arxiver import app

class MainHandler(RequestHandler):
  def get(self):
    self.write("This message comes from Tornado ^_^")

tr = WSGIContainer(app)

application = Application([
(r"/tornado", MainHandler),
(r".*", FallbackHandler, dict(fallback=tr)),
])

if __name__ == "__main__":
  application.listen(80)
  IOLoop.instance().start()