# Day 1 Notes

## Uvicorn

Uvicorn runs our web server.

It listens for HTTP requests on port 8081 and passes them to our FastAPI
application.

For example:

`curl -> Uvicorn -> FastAPI -> response`

## ASGI

ASGI is a standard way for an async web server and a Python web application to
communicate.

Uvicorn is the server, FastAPI is the application, and ASGI connects the two.

We do not normally work with ASGI directly because FastAPI handles it for us.

## Event loop

The event loop manages asynchronous work.

When our handler runs `await asyncio.sleep(...)`, the event loop can work on
other requests while this request waits.

Using `time.sleep(...)` would block the event loop, stopping other requests from
being handled during the wait.

## HTTPX

HTTPX is an HTTP client. It sends HTTP requests and reads the responses.

In our tests, HTTPX sends requests directly to the FastAPI application using
`ASGITransport`. This means the tests do not need to start Uvicorn or use a real
network port.

Later, the gateway will use HTTPX to send requests to the backend services.

## Simple mental model

```text
Uvicorn    = receives requests
FastAPI    = handles requests
ASGI       = connects Uvicorn and FastAPI
Event loop = manages async work
HTTPX      = sends requests
```
