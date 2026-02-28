-- scoretable.lua
-- Direct Lua port of the Scoretable class from eit.py.
-- Persistence via love.filesystem + serpent (replaces pickle + scoretable.dat).

local serpent = require("lib/serpent")

local SCORETABLE_FILE = "scoretable.dat"

-- ---------------------------------------------------------------------------
-- Scoretable
-- ---------------------------------------------------------------------------

Scoretable = {}
Scoretable.__index = Scoretable

--- Load or create a Scoretable.
function Scoretable.load()
    local self = setmetatable({}, Scoretable)
    self.stats = {}

    if love.filesystem.getInfo(SCORETABLE_FILE) then
        local data = love.filesystem.read(SCORETABLE_FILE)
        if data then
            local ok, val = serpent.load(data)
            if ok and type(val) == "table" then
                self.stats = val
            end
        end
    end
    return self
end

--- Persist the scoretable to disk.
function Scoretable:save()
    love.filesystem.write(SCORETABLE_FILE, serpent.dump(self.stats))
end

--- Return the stats list sorted by Rank Points descending.
-- Each entry is { name, stat_table }.
function Scoretable:getList()
    local list = {}
    for name, stat in pairs(self.stats) do
        table.insert(list, {name, stat})
    end
    table.sort(list, function(a, b)
        return (a[2]["Rank Points"] or 0) > (b[2]["Rank Points"] or 0)
    end)
    return list
end

--- Ensure a player entry exists in stats.
local function ensureEntry(stats, name)
    if stats[name] == nil then
        stats[name] = {
            Matches     = 0,
            Score       = 0,
            Lines       = 0,
            ["Max Level"]   = 0,
            ["Rank Points"] = 0,
            Winns       = 0,
        }
    end
end

--- Record the result of a finished game.
-- @param winner  table with fields: Name, Score, Lines, Level
-- @param losers  array of tables with the same fields
function Scoretable:insertResult(winner, losers)
    -- Update winner entry
    ensureEntry(self.stats, winner.Name)
    local ws = self.stats[winner.Name]
    ws.Matches     = ws.Matches + 1
    ws.Score       = ws.Score   + winner.Score
    ws.Lines       = ws.Lines   + winner.Lines
    ws["Max Level"]   = math.max(winner.Level, ws["Max Level"])
    ws.Winns       = ws.Winns + 1

    -- Update each loser + calculate rank-point transfer
    for _, loser in ipairs(losers) do
        ensureEntry(self.stats, loser.Name)
        local ls = self.stats[loser.Name]
        ls.Matches     = ls.Matches + 1
        ls.Score       = ls.Score   + loser.Score
        ls.Lines       = ls.Lines   + loser.Lines
        ls["Max Level"]   = math.max(loser.Level, ls["Max Level"])

        local w_rp = ws["Rank Points"]
        local l_rp = ls["Rank Points"]
        local rp
        if w_rp > l_rp + 5 then
            rp = 5
        else
            rp = math.floor((w_rp - l_rp) / 2) + 5
        end
        ws["Rank Points"] = ws["Rank Points"] + rp
        ls["Rank Points"] = ls["Rank Points"] - rp
    end
end
