"""The assistant the user talks to (F21, ADR-0025, ADR-0028).

`core` is the agent graph and its contract — it knows neither the database nor HTTP;
`tools` are what it may read and propose, one module per thing the user keeps; `service`
keeps conversations and cards; `api` is its router.
"""
