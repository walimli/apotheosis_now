# DEVELOPER INSTRUCTIONS

Welcome to the team Codex! So glad to have you. Are you excited to work in pygame?

## MANDATORY WORKFLOW REQUIREMENTS

### Planning Step Protocol
**ALWAYS** begin every new task with a Planning Step:
1. **Investigate** as directed by the user
2. **Formulate** a complete TODO list regarding the request
3. **Create** a multi-phase plan if the task is complex
4. **Ask the user for confirmation** of the TODO list before proceeding
5. **Wait for explicit approval** before writing any code

### Pre-Code Requirements
- **NEVER** change or write code unless the Planning Step has been completed
- **NEVER** proceed without user confirmation of the TODO list
- Code changes are only permitted after explicit user approval

### Implementation Standards
- **NEVER** institute fallbacks in code
- A change either works or it doesn't - failures must be immediately visible
- **NEVER** add debug messages for in-game behaviors unless explicitly instructed
- All code changes must be direct and purposeful

### Testing and Execution Restrictions
- **NEVER** attempt to use `main.py` or run the game yourself
- **You cannot run the game or test implementations independently**
- **ALWAYS** ask the user to test the game when verification is needed
- **NEVER** create test files or ad hoc testing environments
- **NEVER** create external test implementations outside the main game

### Change Management
- **NEVER** make changes the user has not requested or agreed to
- **NEVER** create backwards compatibility for legacy code when implementing new functions

Remember our company motto: Minimum Viable Product!

## Event-Driven Updates (Do Not Poll Per Frame)

- General principles
  - Prefer event-driven updates over per-frame polling for state changes and input.
  - Only run deterministic, time-based work in `update()` (e.g., physics, animation, timers, rendering prep).

- Anti-patterns to avoid
  - Cross-system polling in update loops (signature: `if external_system.flag: ...`).
  - Input polling in update loops (`pygame.key.get_pressed()`, `pygame.mouse.get_pos()`, `pygame.mouse.get_pressed()`).
  - Busy loops or ad hoc frame loops outside the central state manager.

- Input handling rules
  - Use pygame events (KEYDOWN/UP, MOUSEMOTION, MOUSEBUTTONDOWN/UP, MOUSEWHEEL) or the `PlayInputBus` to react to input.
  - Cache cursor position/hover state on events; do not re-query devices in `update()`.
  - Use axis aggregation via the input bus for movement; do not implement custom key scanning.

- Cross-system state changes
  - Use explicit signals/listeners or a shared bus for state transitions (e.g., `CraftingStateChanged(active: bool)`).
  - Subscribe during bootstrap and seed initial state once; unsubscribe/clear on teardown.
  - Do not reach across systems in `update()` to check flags; maintain local state set by events.

- Implementation standards (enforced)
  - No fallbacks or legacy code paths once event-driven wiring is in place.
  - Do not keep deprecated polling code; remove it as part of the change.

- PR checklist
  - No uses of `pygame.key.get_pressed()`, `pygame.mouse.get_pressed()`, or `pygame.mouse.get_pos()` inside update paths.
  - No cross-system flag reads inside `update()` (search for `.active`, `.enabled`, `is_*` across systems).
  - Input logic reacts via events/`PlayInputBus`; hover/selection updated on `MOUSEMOTION`.
  - Cross-system coupling uses listeners/callbacks or bus signals, wired once in bootstrap.
  - New/changed systems document why any per-frame work is required.
