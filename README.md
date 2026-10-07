# Load completion dummy API

A public, stateless source and sink for testing load-job completion handlers.
Adapted from the small local Python fixture, with the same sample records and
success/failure response bodies. Uses only the Python standard library.

## Routes

| Method | Path | Result |
| --- | --- | --- |
| GET | `/` | Endpoint directory |
| GET | `/health` | 200, `{"status":"healthy"}` |
| GET | `/extract` | 200, two sample records with `id`, `name`, and `workflow` |
| POST | `/load` | 200, `{"accepted":true,"message":"Sample received"}` |
| POST | `/load/fail` | Intentional 500, `{"accepted":false,"message":"Intentional test failure"}` |
| GET | `/requests` | 501: persistent request history is unavailable |

POST endpoints require valid JSON, capped at 1 MiB. Invalid JSON returns 400;
larger bodies return 413. Responses are not cached. No authentication is required.

## QA workflow

1. Set the extract URL to `https://YOUR-DEPLOYMENT/extract` with method GET.
2. Pass the records through the workflow's transform.
3. Set the HTTP load URL to `https://YOUR-DEPLOYMENT/load`, method POST, JSON body.
4. Run the workflow with the success completion action enabled and check its Mongo output.
5. Change the load URL to `/load/fail`, run again, and check the error completion action.
6. Also test failing loads with only success enabled and successful loads with only error enabled; neither should run a completion action.

The 500 response is intentional. This API does not execute the completion action:
the load worker does that. Use a fresh workflow execution for each case.

## Request evidence

The original local fixture wrote request bodies to a file and exposed `/requests`.
This deployment is stateless: no request bodies, headers, or credentials are
stored or logged by the application. Known extract/load requests emit timestamp,
method, route, and status to Vercel runtime logs. `/requests` explicitly returns
501 rather than presenting incomplete in-memory history. Use synthetic test data.

## Local development

```sh
python3 api/index.py
python3 -m unittest discover -s tests -v
```

The local server listens on `127.0.0.1:5290`.

## Deployment

Deploy in the personal Vercel workspace with the Other framework preset.
`vercel.json` routes requests to the Python function. No environment variables,
external services, or secrets are required. The production endpoint is public.
