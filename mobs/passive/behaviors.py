mobs/passive/behaviors.py
Purpose: Nodes for idle, wander, graze, flock_align (simple cohesion), flee_from_threat (player or recent damage), sleep_at_day/night variants. Default BT: idle/graze→detect_threat→flee→calm→idle.
Dependencies: core.senses (threat scan), core.navigation (steer/wander), core.base_model, DMG time_manager.