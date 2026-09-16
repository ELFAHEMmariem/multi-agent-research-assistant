# Architecture

## Flow

```
POST /research
      |
      v
 planner_node ---------------------------> checkpoint (Redis) + trace event
      |
      v
 researcher_node <---revise (max 1x)---+
      |         \                      |
      | accept/skip \--- supervisor ---+
      v
  more sub-questions? --yes--> researcher_node (loop)
      | no
      v
  writer_node ---> citation_check ---> checkpoint + trace event
      |
      v
   status: done
```

## Why GraphState is the single source of truth

Every node reads and writes the same `GraphState` object (see
`app/schemas/state.py`). Nodes never pass ad hoc dicts between each other —
this is what lets `checkpoint.save_state` serialize the *entire* run after
any node, and what lets a resumed process reconstruct exactly where it left
off without replaying completed sub-questions.

## Why budgets are code, not prompt text

`app/graph/budgets.py` is checked after every node via `check_all_budgets`.
If a run exceeds `MAX_TOTAL_TOKENS` or `WALL_CLOCK_SECONDS`, it raises
`BudgetExceeded`, which `build_graph.run_graph` catches and turns into
`status="failed"` with a reason — never a silent overrun.

## Why revision is capped at exactly one

`app/graph/supervisor.py::review_research` checks `revision_count` and
returns `"skip"` once a sub-question has already been revised once. This
is the single mechanism preventing runaway cost from a stubborn sub-question.
