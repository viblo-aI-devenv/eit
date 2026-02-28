-- datamanager.lua
-- Equivalent of datamanager.py
-- Loads all images, quads, sounds, music and provides playback helpers.

require("constants")

DataManager = {}
DataManager.__index = DataManager

function DataManager.new()
    local self = setmetatable({}, DataManager)
    self.images      = {}   -- key → love.graphics.Image
    self.quads       = {}   -- key → love.graphics.Quad  (per block type)
    self.backgrounds = {}   -- key → love.graphics.Image  (tiling backgrounds)
    self.sounds      = {}   -- not used directly; use named fields below
    self.players          = {}
    self.gameover_players = {}
    self.music_source     = nil
    self.musicEnabled     = true
    self.fullscreen       = false

    -- Sounds loaded eagerly in DataManager:load()
    self.placesound    = nil
    self.gameoversound = nil
    self.welcomesound  = nil
    self.specialsounds = {}

    self.font = nil
    return self
end

--- Load all assets.  Call once from love.load() after the window is open.
function DataManager:load()
    -- -----------------------------------------------------------------------
    -- Textures
    -- -----------------------------------------------------------------------
    self.images["standard"]          = love.graphics.newImage("images/standard.png")
    self.images["special"]           = love.graphics.newImage("images/special.png")
    self.images["bw"]                = love.graphics.newImage("images/bw.png")
    self.images["background_border"] = love.graphics.newImage("images/background_border.png")
    self.images["background_info"]   = love.graphics.newImage("images/background_info.png")

    -- -----------------------------------------------------------------------
    -- Quads for standard block strip (8 frames × 24 px wide)
    -- Strip x layout (0-based frame index):
    --   frame 0 = Blue, 1 = Red, 2 = Green, 3 = Purple, 4 = Yellow,
    --   frame 5 = Pink, 6 = Cyan, 7 = Grey
    -- This matches the Python tex_offset values (n/8, (n+1)/8).
    -- -----------------------------------------------------------------------
    local stdImg = self.images["standard"]
    local sw, sh = stdImg:getDimensions()
    local stdNames = {"Blue","Red","Green","Purple","Yellow","Pink","Cyan","Grey"}
    for i, name in ipairs(stdNames) do
        self.quads[name] = love.graphics.newQuad((i-1)*BLOCK_SIZE, 0,
                                                  BLOCK_SIZE, BLOCK_SIZE,
                                                  sw, sh)
    end

    -- -----------------------------------------------------------------------
    -- Quads for special block strip (22 frames × 24 px wide)
    -- Order matches SPECIAL_NAMES in blocks.lua / Python SPECIAL_PARTS list.
    -- -----------------------------------------------------------------------
    local spImg = self.images["special"]
    local spw, sph = spImg:getDimensions()
    local spNames = {
        "Faster","Slower","Stair","Fill","Rumble","Inverse","Switch","Packet",
        "Flip","Mini","Blink","Blind","Background","Anti","Bridge","Trans",
        "Clear","Question","SZ","Color","Ring","Castle",
    }
    for i, name in ipairs(spNames) do
        self.quads[name] = love.graphics.newQuad((i-1)*BLOCK_SIZE, 0,
                                                  BLOCK_SIZE, BLOCK_SIZE,
                                                  spw, sph)
    end

    -- -----------------------------------------------------------------------
    -- Background tiles
    -- -----------------------------------------------------------------------
    local bgFiles = love.filesystem.getDirectoryItems("images/backgrounds")
    for _, f in ipairs(bgFiles) do
        if f:match("%.png$") then
            local key = f:gsub("%.png$","")
            local img = love.graphics.newImage("images/backgrounds/"..f)
            img:setWrap("repeat", "repeat")
            self.backgrounds[key] = img
        end
    end

    -- -----------------------------------------------------------------------
    -- Font
    -- -----------------------------------------------------------------------
    self.font = love.graphics.newFont("fonts/freesansbold.ttf", 14)

    -- -----------------------------------------------------------------------
    -- Sounds  (static = loaded fully into memory, suitable for short SFX)
    -- -----------------------------------------------------------------------
    local function snd(filename)
        local ok, src = pcall(love.audio.newSource, "sounds/"..filename, "static")
        if ok then return src else return nil end
    end

    self.placesound    = snd("DEEK.WAV")
    self.gameoversound = snd("RASPB.WAV")
    self.welcomesound  = snd("WELCOME.WAV")

    local specialMap = {
        Faster     = "LASER.WAV",
        Slower     = "PONG.WAV",
        Stair      = "FLOOP.WAV",
        Fill       = "POP2.WAV",
        Rumble     = "BOUNCE.WAV",
        Inverse    = "VIBRABEL.WAV",
        Flip       = "BOOMOOH-1.WAV",
        Switch     = "ECHOFST1.WAV",
        Packet     = "PLICK.WAV",
        Clear      = "WHOOSH1.WAV",
        Question   = "PLOP1.WAV",
        Bridge     = "BOTTLED.WAV",
        Mini       = "FUU.WAV",
        Color      = "SPACEBO.WAV",
        Trans      = "PINC.WAV",
        SZ         = "PLINK2.WAV",
        Anti       = "SIGH.WAV",
        Background = "KLOUNK.WAV",
        Blind      = "TICK.WAV",
        Blink      = "ZING.WAV",
    }
    for k, v in pairs(specialMap) do
        self.specialsounds[k] = snd(v)
    end
end

--- Play a named special sound (silently ignores missing entries).
function DataManager:playSpecial(name)
    local s = self.specialsounds[name]
    if s then
        -- Clone the source so multiple overlapping plays work
        local clone = s:clone()
        clone:play()
    end
end

--- Start a random background music track (loops indefinitely).
function DataManager:playRandomMusic()
    if not self.musicEnabled then return end
    local files = love.filesystem.getDirectoryItems("music")
    if not files or #files == 0 then return end

    -- Filter to known audio extensions
    local valid = {}
    for _, f in ipairs(files) do
        local ext = f:match("%.(%w+)$")
        if ext then
            ext = ext:lower()
            if ext == "ogg" or ext == "mp3" or ext == "wav"
               or ext == "mod" or ext == "s3m" or ext == "xm" or ext == "it" then
                table.insert(valid, f)
            end
        end
    end
    if #valid == 0 then return end

    local f = valid[love.math.random(#valid)]
    if self.music_source then
        self.music_source:stop()
        self.music_source = nil
    end
    local ok, src = pcall(love.audio.newSource, "music/"..f, "stream")
    if ok then
        self.music_source = src
        self.music_source:setLooping(true)
        self.music_source:play()
    end
end

--- Stop music.
function DataManager:stopMusic()
    if self.music_source then
        self.music_source:stop()
    end
end
