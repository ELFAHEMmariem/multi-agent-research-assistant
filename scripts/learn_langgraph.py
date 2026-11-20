
from typing import TypedDict

from langgraph.graph import StateGraph, START, END


# 1. Define shared state
class DemoState(TypedDict):
    question: str
    message: str


# 2. Define first node
def first_node(state: DemoState) -> dict:
    print("Executing first node")

    return {
        "message": f"Research started: {state['question']}"
    }


# 3. Define second node
def second_node(state: DemoState) -> dict:
    print("Executing second node")

    return {
        "message": state["message"] + " | Processing completed"
    }


# 4. Build the graph
builder = StateGraph(DemoState)

builder.add_node("first", first_node)
builder.add_node("second", second_node)

builder.add_edge(START, "first")
builder.add_edge("first", "second")
builder.add_edge("second", END)

graph = builder.compile()


# 5. Execute the graph
if __name__ == "__main__":
    result = graph.invoke({
        "question": "What are AI security risks?",
        "message": ""
    })

    print(result)
