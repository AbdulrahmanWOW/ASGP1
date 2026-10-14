"""Framework adapters. Each one is a thin gate in front of tool execution that delegates every
decision to :class:`asgp_sdk.guard.ToolGuard` (DESIGN.md §9–10).

Import the adapter you need directly, e.g. ``from asgp_sdk.adapters.langchain import
ASGPMiddleware``; optional framework dependencies are only imported by their own module.
"""
