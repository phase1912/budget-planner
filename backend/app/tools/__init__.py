"""Extensible tool interface for the AI agent.

Tools let the agent call application-side functions (database lookups, budget
calculations, etc.) during a multi-turn conversation.  F3.1 does not use
custom tools — extraction is a single vision call — but this package lays
the groundwork for future agent capabilities like goal-optimization advice
where the agent needs to read spending data to make recommendations.
"""
