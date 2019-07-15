from sanic import Sanic

# The Sanic application. This is defined in its own file so that it can be
# imported into other modules and have hooks defined without encountering
# cyclic imports.
app = Sanic()
