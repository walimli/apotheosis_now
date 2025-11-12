# constants.py
PLAYER_SIZE = 64
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600


# World/tiles
TILE_SIZE = 64
CHUNK_SIZE_TILES = 32
VIEW_DISTANCE_CHUNKS = 1  # 1 => 3x3 neighborhood
CHUNK_PIXELS = TILE_SIZE * CHUNK_SIZE_TILES

# Player
PLAYER_SIZE = 64
PLAYER_SPEED = 256.0

# Player collision (feet AABB) for 64px sprite
PLAYER_FEET_W = 28
PLAYER_FEET_H = 24

# Actions
ACTION_PUNCH_DURATION = 0.5  # seconds
PLAYER_ATTACK_COOLDOWN = 0.5  # seconds between spacebar attacks

# Timing
FRAME_RATE = 60


# In a constants file
LAYER_PLAYER = 1 << 0
LAYER_ENEMY = 1 << 1
LAYER_PROJECTILE = 1 << 2
LAYER_WALL = 1 << 3
LAYER_PICKUP = 1 << 4
LAYER_FRIENDLY = 1 << 5  # e.g. allied NPCs
