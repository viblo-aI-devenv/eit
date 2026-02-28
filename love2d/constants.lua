-- constants.lua  (eit_constants.py equivalent)

BLOCK_SIZE          = 24

TO_NEXT_LEVEL       = 5
DOWN_TIME           = 500    -- ms between automatic block-down ticks at level 0
DROP_TIME           = 10     -- ms between ticks when hard-dropping
DOWN_TIME_DELTA     = 1.07   -- downtime = downtime / DOWN_TIME_DELTA per level-up
SPECIAL_TIME        = 50     -- ms between special-effect ticks
PACKET_TIME         = 20000  -- ms that Packet effect lasts
SPAWN_SPECIAL_TIME  = 30000  -- ms between special block spawns
REMOVE_SPECIAL_TIME = 8000   -- ms before spawn at which the old special is removed
EXTRA_ANTIS         = 4      -- extra weight for Anti in random special selection
