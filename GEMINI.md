# Project: Apotheosis Now

## Project Overview

This project is a 2D RPG/crafting game named "The Dark Lord of Crafting", developed in Python using the Pygame library. The game features a modern rendering pipeline with OpenGL shaders (via `moderngl`), a physics engine (`pymunk`), and a performant architecture leveraging an Entity-Component-System (ECS) pattern. The codebase is well-structured, with a clear separation of concerns between game states, services, and the ECS core.

### Key Technologies:

*   **Game Engine:** Pygame
*   **Rendering:** `moderngl` for OpenGL shaders and GPU-accelerated rendering.
*   **Physics:** `pymunk` for 2D physics simulations.
*   **Performance:** `numba` for JIT compilation of performance-critical code.
*   **Architecture:** State Machine and Entity-Component-System (ECS).
*   **UI:** `pygame_gui` for in-game UI elements.
*   **Mapping:** `PyTMX` for loading maps created in the Tiled editor.

## Building and Running

**Dependencies:**

The project's dependencies are listed in `dependencies.txt`. They can be installed using pip:

```bash
pip install -r dependencies.txt
```

**Running the Game:**

The main entry point for the game is `main.py`. To run the game, execute the following command:

```bash
python main.py
```

**Testing:**

The project does not have a dedicated test suite. The `AGENTS.md` file explicitly states that the AI agent should not create or run tests, but should rely on the user for verification.

## Development Conventions

The `AGENTS.md` file outlines a strict, plan-driven development workflow:

1.  **Planning Step:** Before any code is written, a detailed TODO list must be created and approved by the user.
2.  **No Direct Execution:** The AI agent is not allowed to run the game or create test files. All verification must be done by the user.
3.  **Event-Driven Design:** The codebase emphasizes an event-driven approach over per-frame polling for input and state changes.
4.  **No Fallbacks:** Code changes should be direct and purposeful, without fallbacks for legacy code.

The project uses modern Python features, including type hints, and has a well-organized structure that separates different aspects of the game into distinct modules.
