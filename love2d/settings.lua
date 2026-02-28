-- settings.lua
-- Replaces configobj-based settings.cfg and profiles.cfg from the Python port.
-- Uses love.filesystem (LÖVE save directory) for persistence.
-- Serialisation via lib/serpent.lua.

local serpent = require("lib/serpent")

-- ---------------------------------------------------------------------------
-- Default key bindings per player slot (Love2D key names)
-- ---------------------------------------------------------------------------

local DEFAULT_PROFILES = {
    ["Player1"] = {
        left   = "a",     right  = "d",      cw    = "q",
        ccw    = "w",     down   = "s",      drop  = "lctrl",
        anti   = "lshift", change = "tab",
    },
    ["Player2"] = {
        left   = "left",  right  = "right",  cw    = "6",
        ccw    = "up",    down   = "down",   drop  = "space",
        anti   = "rshift", change = "return",
    },
    ["Player3"] = {
        left   = "kp4",   right  = "kp6",    cw    = "kp5",
        ccw    = "kp8",   down   = "kp2",    drop  = "kp0",
        anti   = "kp1",   change = "kp3",
    },
    ["Player4"] = {
        left   = "f",     right  = "h",      cw    = "t",
        ccw    = "y",     down   = "g",      drop  = "lalt",
        anti   = "z",     change = "x",
    },
}

-- ---------------------------------------------------------------------------
-- Internal helpers
-- ---------------------------------------------------------------------------

local SETTINGS_FILE  = "settings.dat"
local PROFILES_FILE  = "profiles.dat"

local function loadFile(path)
    if not love.filesystem.getInfo(path) then return nil end
    local data = love.filesystem.read(path)
    if not data then return nil end
    local ok, val = serpent.load(data)
    if not ok then return nil end
    return val
end

local function saveFile(path, tbl)
    love.filesystem.write(path, serpent.dump(tbl))
end

-- ---------------------------------------------------------------------------
-- Settings  (fullscreen, music flags + active profiles for each player slot)
-- ---------------------------------------------------------------------------

Settings = {}
Settings.__index = Settings

function Settings.new()
    local self = setmetatable({}, Settings)

    local data = loadFile(SETTINGS_FILE) or {}

    self.fullscreen      = (data.fullscreen ~= false)   -- default true on TV
    self.music           = (data.music      ~= false)   -- default true
    -- active_profiles[0..3]: profile name string or "None"
    self.active_profiles = data.active_profiles or {"Player1","None","None","None"}

    return self
end

function Settings:save()
    saveFile(SETTINGS_FILE, {
        fullscreen      = self.fullscreen,
        music           = self.music,
        active_profiles = self.active_profiles,
    })
end

-- ---------------------------------------------------------------------------
-- Profiles  (named key bindings)
-- ---------------------------------------------------------------------------

Profiles = {}
Profiles.__index = Profiles

function Profiles.new()
    local self = setmetatable({}, Profiles)
    self._data = loadFile(PROFILES_FILE)
    if not self._data then
        -- Seed with defaults
        self._data = {}
        for name, keys in pairs(DEFAULT_PROFILES) do
            self._data[name] = {}
            for k, v in pairs(keys) do self._data[name][k] = v end
        end
        self:save()
    end
    return self
end

--- Return a sorted list of profile names.
function Profiles:names()
    local out = {}
    for name in pairs(self._data) do table.insert(out, name) end
    table.sort(out)
    return out
end

--- Return the key-binding table for a named profile, or nil.
function Profiles:get(name)
    return self._data[name]
end

--- Create a new profile with default bindings.
-- Generates a unique name if "Player" is taken.
function Profiles:createNew()
    local base = "Player"
    local name = base
    while self._data[name] ~= nil do name = name .. "_" end
    self._data[name] = {
        left="left", right="right", cw="up",    ccw="z",
        down="down",  drop="space",  anti="rshift", change="return",
    }
    self:save()
    return name
end

--- Save / update a profile.
function Profiles:set(name, keys)
    name = string.sub(name, 1, 8)
    if name == "" then return end
    self._data[name] = {}
    for k, v in pairs(keys) do self._data[name][k] = v end
    self:save()
end

--- Delete a profile by name.
function Profiles:delete(name)
    self._data[name] = nil
    self:save()
end

function Profiles:save()
    saveFile(PROFILES_FILE, self._data)
end
