-- playerfield.lua
-- Equivalent of playerfield.py
-- Manages one player's state: input (keyboard + gamepad), scoring, special
-- effects, block timing, and drawing the info panel.

require("constants")
require("blocks")
require("blockfield")

-- ---------------------------------------------------------------------------
-- Default keyboard bindings (Love2D key names)
-- ---------------------------------------------------------------------------

local DEFAULT_KEYS = {
    [0] = { left="a",    right="d",     cw="q",    ccw="w",
            down="s",    drop="lctrl",  anti="lshift", change="tab" },
    [1] = { left="left", right="right", cw="6",    ccw="up",
            down="down", drop="space",  anti="rshift",  change="return" },
    [2] = { left="left", right="right", cw="6",    ccw="up",
            down="down", drop="space",  anti="rshift",  change="return" },
    [3] = { left="kp2",  right="kp8",   cw="kp.",  ccw="kp0",
            down="kp5",  drop="kpenter",anti="kp/",     change="kp*" },
}

-- Default gamepad button bindings (Love2D gamepad button names).
-- These are applied when a joystick is assigned to a player slot.
local DEFAULT_PAD = {
    left   = "dpleft",
    right  = "dpright",
    cw     = "b",        -- B / Circle
    ccw    = "x",        -- X / Square
    down   = "dpdown",
    drop   = "a",        -- A / Cross
    anti   = "y",        -- Y / Triangle
    change = "rightshoulder",
}

-- ---------------------------------------------------------------------------
-- PlayerField
-- ---------------------------------------------------------------------------

PlayerField = {}
PlayerField.__index = PlayerField

--- Create a new PlayerField.
-- @param dm       DataManager
-- @param id       0-based player index
-- @param name     player name string
-- @param px       screen x of field top-left (before BlockField border offset)
-- @param py       screen y of field top-left
-- @param profile  table with key bindings (optional; falls back to defaults)
-- @param joystick love.Joystick object or nil
function PlayerField.new(dm, id, name, px, py, profile, joystick)
    local self = setmetatable({}, PlayerField)

    self.dm       = dm
    self.id       = id
    self.name     = name
    self.px       = px
    self.py       = py
    self.joystick = joystick   -- nil if no gamepad assigned

    self.field = BlockField.new(dm, px, py)

    -- Stats
    self.score  = 0
    self.level  = 0
    self.lines  = 0

    -- Target for sending specials
    self.target   = nil
    self.gameover = false

    -- Level/timing
    self.to_nextlevel = TO_NEXT_LEVEL
    self.downtime     = DOWN_TIME
    self.cstime       = 0    -- accumulated ms toward next auto-down
    self.droptime     = 0    -- accumulated ms when hard-dropping
    self.dropping     = false

    -- Special-effect state
    self.lines_to_add  = {}  -- queue of {y, line} pairs
    self.specialtime   = 0
    self.rumbles       = 0
    self.rumbleblocks  = {}
    self.packettime    = 0
    self.antidotes     = 0
    self.spawntime     = SPAWN_SPECIAL_TIME - 4000

    -- Key bindings (Love2D key names)
    local kb = profile or DEFAULT_KEYS[id] or DEFAULT_KEYS[0]
    self.keys = {
        left   = kb.left   or DEFAULT_KEYS[0].left,
        right  = kb.right  or DEFAULT_KEYS[0].right,
        cw     = kb.cw     or DEFAULT_KEYS[0].cw,
        ccw    = kb.ccw    or DEFAULT_KEYS[0].ccw,
        down   = kb.down   or DEFAULT_KEYS[0].down,
        drop   = kb.drop   or DEFAULT_KEYS[0].drop,
        anti   = kb.anti   or DEFAULT_KEYS[0].anti,
        change = kb.change or DEFAULT_KEYS[0].change,
    }

    -- Callback: called when this player gets a game-over condition.
    -- Set by main.lua:  player.onGameOver = function(player) ... end
    self.onGameOver = nil

    return self
end

-- ---------------------------------------------------------------------------
-- Scoring
-- ---------------------------------------------------------------------------

function PlayerField:doScore(lines)
    self.lines = self.lines + lines

    if     lines == 1 then self.score = self.score + (self.level + 1) * 40
    elseif lines == 2 then self.score = self.score + (self.level + 1) * 100
    elseif lines == 3 then self.score = self.score + (self.level + 1) * 300
    elseif lines == 4 then self.score = self.score + (self.level + 1) * 1200
    end

    -- Hasten special spawn when lines are cleared
    if self.field.special_block == nil then
        self.spawntime = self.spawntime + 200
    end

    self.to_nextlevel = self.to_nextlevel - lines
    if self.to_nextlevel <= 0 then
        self.to_nextlevel = self.to_nextlevel + TO_NEXT_LEVEL
        self.level        = self.level + 1
        self.downtime      = self.downtime / DOWN_TIME_DELTA
    end
end

-- ---------------------------------------------------------------------------
-- Target cycling
-- ---------------------------------------------------------------------------

function PlayerField:nextTarget()
    -- Sort active (non-gameover) players by id
    local ok = {}
    for _, p in ipairs(self.dm.players) do
        if not p.gameover then
            table.insert(ok, p)
        end
    end
    table.sort(ok, function(a,b) return a.id < b.id end)

    if #ok == 0 then self.target = nil; return end

    -- Find current position in ok list
    local curIdx = nil
    if self.target ~= nil and not self.target.gameover then
        for i, p in ipairs(ok) do
            if p == self.target then curIdx = i; break end
        end
    end
    if curIdx == nil then
        -- Find self in list
        for i, p in ipairs(ok) do
            if p == self then curIdx = i; break end
        end
    end

    -- Pick the next player after curIdx, wrapping around
    local nextIdx = (curIdx % #ok) + 1
    local candidate = ok[nextIdx]
    self.target = (candidate ~= self) and candidate or nil
end

-- ---------------------------------------------------------------------------
-- Gameover
-- ---------------------------------------------------------------------------

function PlayerField:doGameover()
    if self.dm.gameoversound then self.dm.gameoversound:play() end
    self.gameover = true
    if self.onGameOver then self.onGameOver(self) end
end

-- ---------------------------------------------------------------------------
-- Block movement
-- ---------------------------------------------------------------------------

--- Move the current block in direction "Down", "Left", or "Right".
-- Returns true if the block was placed (landed), false otherwise.
function PlayerField:moveBlock(dir)
    local field = self.field
    if field.currentblock == nil then
        local ok = field:addBlock()
        if not ok then self:doGameover() end
        return false
    end

    if dir == "Down" then
        field.currentblock:move(0, 1)
        if not field:inValidPosition(field.currentblock) then
            field.currentblock:move(0, -1)
            field:placeCurrentBlock(self.dm)
            return true   -- block placed
        end
    elseif dir == "Left" then
        field.currentblock:move(-1, 0)
        if not field:inValidPosition(field.currentblock) then
            field.currentblock:move(1, 0)
        end
    elseif dir == "Right" then
        field.currentblock:move(1, 0)
        if not field:inValidPosition(field.currentblock) then
            field.currentblock:move(-1, 0)
        end
    end
    return false
end

-- ---------------------------------------------------------------------------
-- Special-effect activation  (mirrors playerfield.py activate_special)
-- ---------------------------------------------------------------------------

function PlayerField:activateSpecial(special_block)
    if special_block == nil then return end
    local t   = special_block.type
    local dm  = self.dm
    local tgt = self.target

    if t == "Faster" then
        dm:playSpecial("Faster")
        if tgt then tgt.downtime = tgt.downtime * 0.75 end

    elseif t == "Slower" then
        dm:playSpecial("Slower")
        self.downtime = self.downtime + 10.0 * DOWN_TIME_DELTA

    elseif t == "Stair" then
        if tgt then
            local bp = randChoice(STANDARD_PARTS)(dm)
            table.insert(tgt.lines_to_add, {22, {{0, bp}, {1, nil}}})
            for x = 1, 8 do
                bp = randChoice(STANDARD_PARTS)(dm)
                table.insert(tgt.lines_to_add, {22 - x, {{x-1, nil}, {x, bp}, {x+1, nil}}})
            end
            bp = randChoice(STANDARD_PARTS)(dm)
            table.insert(tgt.lines_to_add, {13, {{8, nil}, {9, bp}}})
        end

    elseif t == "Fill" then
        if tgt then
            for y = 22, 13, -1 do
                local bps = {nil}
                for _ = 1, 9 do table.insert(bps, randChoice(STANDARD_PARTS)(dm)) end
                shuffleTable(bps)
                local line = {}
                for x = 0, 9 do table.insert(line, {x, bps[x+1]}) end
                table.insert(tgt.lines_to_add, {y, line})
            end
        end

    elseif t == "Rumble" then
        if tgt then
            tgt.rumbles      = 5
            tgt.rumbleblocks = tgt:getRumbleBlocks()
        end

    elseif t == "Inverse" then
        dm:playSpecial("Inverse")
        if tgt then
            tgt.field.effects.Inverse = BlockPartInverse(dm, 0, 1)
        end

    elseif t == "Switch" then
        dm:playSpecial("Switch")
        if tgt then
            self.field.grid,      tgt.field.grid      = tgt.field.grid,      self.field.grid
            self.field.blockparts_list, tgt.field.blockparts_list =
                tgt.field.blockparts_list, self.field.blockparts_list
            self.field.special_block, tgt.field.special_block =
                tgt.field.special_block,  self.field.special_block
            self.rumbles  = 0;  self.rumbleblocks  = {}
            tgt.rumbles   = 0;  tgt.rumbleblocks   = {}
        end

    elseif t == "Packet" then
        self.packettime = PACKET_TIME

    elseif t == "Flip" then
        dm:playSpecial("Flip")
        if tgt then tgt.field:flip() end

    elseif t == "Mini" then
        dm:playSpecial("Mini")
        if tgt then tgt.field.effects.Mini = BlockPartMini(dm, 1, 1) end

    elseif t == "Blink" then
        dm:playSpecial("Blink")
        if tgt then tgt.field.effects.Blink = BlockPartBlink(dm, 2, 1) end

    elseif t == "Blind" then
        dm:playSpecial("Blind")
        if tgt then tgt.field.effects.Blind = BlockPartBlind(dm, 3, 1) end

    elseif t == "Background" then
        dm:playSpecial("Background")
        if tgt then tgt.field.background_tile = tgt.field:randomBackground() end

    elseif t == "Anti" then
        self.antidotes = math.min(self.antidotes + 1, 4)

    elseif t == "Bridge" then
        dm:playSpecial("Bridge")
        if tgt then
            tgt.field:addLine(true)
            tgt.field:addLine(true)
        end

    elseif t == "Trans" then
        dm:playSpecial("Trans")
        if tgt then tgt.field.effects.Trans = BlockPartTrans(dm, 4, 1) end

    elseif t == "Clear" then
        dm:playSpecial("Clear")
        self.field:clearField()

    elseif t == "Question" then
        dm:playSpecial("Question")
        if tgt then
            local list = tgt.field.blockparts_list
            local half = math.floor(#list * 0.5)
            -- pick `half` random entries and remove them
            local indices = {}
            for i = 1, #list do indices[i] = i end
            shuffleTable(indices)
            -- collect bps to remove (work from a snapshot)
            local toRemove = {}
            for i = 1, half do
                table.insert(toRemove, list[indices[i]])
            end
            for _, bp in ipairs(toRemove) do
                tgt.field:removeBP(bp.x, bp.y)
            end
        end

    elseif t == "SZ" then
        dm:playSpecial("SZ")
        if tgt then tgt.field.effects.SZ = BlockPartSZ(dm, 5, 1) end

    elseif t == "Color" then
        dm:playSpecial("Color")
        if tgt then tgt.field.effects.Color = BlockPartColor(dm, 6, 1) end

    elseif t == "Ring" then
        if tgt then
            for _, entry in ipairs(self:ring()) do
                table.insert(tgt.lines_to_add, entry)
            end
        end

    elseif t == "Castle" then
        if tgt then
            tgt.field:clearField()
            for _, entry in ipairs(self:castle()) do
                table.insert(tgt.lines_to_add, entry)
            end
        end
    end
end

-- ---------------------------------------------------------------------------
-- Castle / Ring junk-line patterns  (direct port from playerfield.py)
-- ---------------------------------------------------------------------------

function PlayerField:getRumbleBlocks()
    local blocks = {}
    for y = 1, 22 do
        for x = 0, 9 do
            if self.field.grid[y] and self.field.grid[y][x] ~= nil then
                table.insert(blocks, self.field.grid[y][x])
                if #blocks > 5 then return blocks end
            end
        end
    end
    return blocks
end

function PlayerField:castle()
    local dm = self.dm
    local G  = BlockPartGrey
    return {
        {22, {{2,G(dm)},{3,G(dm)},{4,G(dm)},{5,G(dm)},{6,G(dm)},{7,G(dm)}}},
        {21, {{2,G(dm)},{3,G(dm)},{4,G(dm)},{6,G(dm)},{7,G(dm)}}},
        {20, {{2,G(dm)},{3,G(dm)},{4,G(dm)},{6,G(dm)},{7,G(dm)}}},
        {19, {{2,G(dm)},{4,G(dm)},{5,G(dm)},{6,G(dm)},{7,G(dm)}}},
        {18, {{2,G(dm)},{4,G(dm)},{5,G(dm)},{6,G(dm)},{7,G(dm)}}},
        {17, {{2,G(dm)},{3,G(dm)},{4,G(dm)},{5,G(dm)},{7,G(dm)}}},
        {16, {{2,G(dm)},{3,G(dm)},{4,G(dm)},{5,G(dm)},{7,G(dm)}}},
        {15, {{2,G(dm)},{3,G(dm)},{5,G(dm)},{6,G(dm)},{7,G(dm)}}},
        {14, {{2,G(dm)},{3,G(dm)},{5,G(dm)},{6,G(dm)},{7,G(dm)}}},
        {13, {{1,G(dm)},{2,G(dm)},{3,G(dm)},{4,G(dm)},{5,G(dm)},{6,G(dm)},{7,G(dm)},{8,G(dm)}}},
        {12, {{1,G(dm)},{2,G(dm)},{3,G(dm)},{4,G(dm)},{5,G(dm)},{6,G(dm)},{7,G(dm)},{8,G(dm)}}},
        {11, {{1,G(dm)},{2,G(dm)},{4,G(dm)},{5,G(dm)},{7,G(dm)},{8,G(dm)}}},
    }
end

function PlayerField:ring()
    local dm = self.dm
    local S  = function() return randChoice(STANDARD_PARTS)(dm) end
    local lines = {}
    table.insert(lines, {22, {{3,nil},{4,nil},{5,nil},{6,nil}}})
    table.insert(lines, {21, {{1,nil},{2,nil},{3,S()},{4,S()},{5,S()},{6,S()},{7,nil},{8,nil}}})
    table.insert(lines, {20, {{0,nil},{1,S()},{2,S()},{3,nil},{4,nil},{5,nil},{6,nil},{7,S()},{8,S()},{9,nil}}})
    table.insert(lines, {19, {{0,nil},{1,S()},{2,nil},{7,nil},{8,S()},{9,nil}}})
    for y = 18, 15, -1 do
        table.insert(lines, {y, {{0,S()},{1,nil},{8,nil},{9,S()}}})
    end
    table.insert(lines, {14, {{0,nil},{1,S()},{2,nil},{7,nil},{8,S()},{9,nil}}})
    table.insert(lines, {13, {{0,nil},{1,S()},{2,S()},{3,nil},{4,nil},{5,nil},{6,nil},{7,S()},{8,S()},{9,nil}}})
    table.insert(lines, {12, {{1,nil},{2,nil},{3,S()},{4,S()},{5,S()},{6,S()},{7,nil},{8,nil}}})
    table.insert(lines, {11, {{3,nil},{4,nil},{5,nil},{6,nil}}})
    return lines
end

-- ---------------------------------------------------------------------------
-- handle_specials  (queued line-add + rumble ticks)
-- ---------------------------------------------------------------------------

function PlayerField:handleSpecials()
    if #self.lines_to_add > 0 then
        self.dm:playSpecial("Stair")
        local entry = table.remove(self.lines_to_add, 1)
        local y, line = entry[1], entry[2]
        for _, pair in ipairs(line) do
            local x, bp = pair[1], pair[2]
            if bp ~= nil then
                self.field:insertBP(x, y, bp)
            else
                self.field:removeBP(x, y)
            end
        end
    end

    if self.rumbles > 0 then
        self.dm:playSpecial("Rumble")
        for _, rb in ipairs(self.rumbleblocks) do
            local nx = rb.x + love.math.random(-1, 1)  -- -1, 0, or 1
            local ny = rb.y + love.math.random(-1, 0)  -- -1 or 0
            if nx >= 0 and nx <= 9 and ny >= 2 and ny <= 22 then
                if self.field:get(nx, ny) == nil then
                    self.field:set(rb.x, rb.y, nil)
                    self.field:set(nx, ny, rb)
                    rb.x = nx
                    rb.y = ny
                end
            end
        end
        self.rumbles = self.rumbles - 1
        if love.math.random() > 0.1 and #self.rumbleblocks > 0 then
            table.remove(self.rumbleblocks)
        end
        if self.rumbles <= 0 then self.rumbleblocks = {} end
    end
end

-- ---------------------------------------------------------------------------
-- Input handling  (called from love.keypressed / love.gamepadpressed)
-- ---------------------------------------------------------------------------

--- Process a named action for this player.
-- @param action  one of: "left","right","cw","ccw","down","drop","anti","change"
function PlayerField:onAction(action)
    if self.gameover then return end

    if action == "down" then
        self:moveBlock("Down")

    elseif action == "left" then
        if self.field.effects.Inverse ~= nil then
            self:moveBlock("Right")
        else
            self:moveBlock("Left")
        end

    elseif action == "right" then
        if self.field.effects.Inverse ~= nil then
            self:moveBlock("Left")
        else
            self:moveBlock("Right")
        end

    elseif action == "cw" then
        if self.field.effects.Inverse ~= nil then
            self.field:rotateBlock("ccw")
        else
            self.field:rotateBlock("cw")
        end

    elseif action == "ccw" then
        if self.field.effects.Inverse ~= nil then
            self.field:rotateBlock("cw")
        else
            self.field:rotateBlock("ccw")
        end

    elseif action == "drop" then
        self.dropping = true
        self.droptime = 0

    elseif action == "anti" then
        if self.antidotes > 0 then
            self.dm:playSpecial("Anti")
            for k, _ in pairs(self.field.effects) do
                self.field.effects[k] = nil
            end
            self.antidotes = self.antidotes - 1
        end

    elseif action == "change" then
        self:nextTarget()
    end
end

--- Check a keyboard key press against this player's bindings.
-- Called from love.keypressed in main.lua.
function PlayerField:onKey(key)
    for action, bound in pairs(self.keys) do
        if key == bound then
            self:onAction(action)
            return
        end
    end
end

--- Check a gamepad button press against this player's slot.
-- Called from love.gamepadpressed in main.lua.
function PlayerField:onGamepadButton(joystick, button)
    if joystick ~= self.joystick then return end
    for action, bound in pairs(DEFAULT_PAD) do
        if button == bound then
            self:onAction(action)
            return
        end
    end
end

--- Check gamepad axis (left stick / d-pad axis) — called each frame.
-- We handle held-down for left/right/down via axis polling in update().

-- ---------------------------------------------------------------------------
-- Update  (call each frame with dt in seconds; we convert to ms internally)
-- ---------------------------------------------------------------------------

function PlayerField:update(dt)
    if self.gameover then return end

    -- Re-target if current target has gone out
    if self.target ~= nil and self.target.gameover then
        self:nextTarget()
    end

    local ms = dt * 1000   -- work in milliseconds like Python
    self.cstime      = self.cstime      + ms
    self.droptime    = self.droptime    + ms
    self.specialtime = self.specialtime + ms
    self.spawntime   = self.spawntime   + ms
    if self.packettime > 0 then
        self.packettime = self.packettime - ms
    end

    -- Gamepad axis polling for held directions
    if self.joystick then
        -- Left stick horizontal
        local ax = self.joystick:getAxis(1)  -- axis 1 = left stick X
        if ax < -0.5 then self:onAction("left")  end
        if ax >  0.5 then self:onAction("right") end
        -- Left stick vertical (down only)
        local ay = self.joystick:getAxis(2)
        if ay > 0.5 then self:onAction("down") end
    end

    -- FPS-safe auto-down
    while self.cstime > self.downtime and not self.dropping do
        local placed = self:moveBlock("Down")
        self.cstime  = self.cstime - self.downtime

        if placed then
            local cleared, special = self.field:removeFullRows()
            self:activateSpecial(special)
            self:doScore(cleared)
            -- Packet: each cleared line adds a junk line to target
            if self.packettime > 0 and self.target then
                for _ = 1, cleared do
                    self.target.field:addLine(false)
                    self.dm:playSpecial("Packet")
                end
            end
            -- Tetris (4 lines): add two bridge lines to target
            if cleared == 4 and self.target then
                self.dm:playSpecial("Bridge")
                self.target.field:addLine(true)
                self.target.field:addLine(true)
            end
        end
    end
    if self.cstime < 0 then self.cstime = 0 end

    -- FPS-safe hard drop
    if self.dropping then
        while self.droptime > DROP_TIME do
            local placed  = self:moveBlock("Down")
            self.droptime = self.droptime - DROP_TIME
            if placed then
                local cleared, special = self.field:removeFullRows()
                self:activateSpecial(special)
                self.dropping = false
                self.droptime = 0
                self:doScore(cleared)
                if self.packettime > 0 and self.target then
                    for _ = 1, cleared do
                        self.dm:playSpecial("Packet")
                        self.target.field:addLine(false)
                    end
                end
                if cleared == 4 and self.target then
                    self.dm:playSpecial("Bridge")
                    self.target.field:addLine(true)
                    self.target.field:addLine(true)
                end
                break
            end
        end
    end
    if self.droptime < 0 then self.droptime = 0 end

    -- Special-effect tick
    if self.specialtime > SPECIAL_TIME then
        self:handleSpecials()
        self.specialtime = 0
        self.field.blink = self.field.blink + 1
        if self.field.blink > 5 then self.field.blink = 0 end
    end
    if self.specialtime < 0 then self.specialtime = 0 end

    -- Special block lifecycle
    if self.spawntime > SPAWN_SPECIAL_TIME - REMOVE_SPECIAL_TIME then
        self.field:removeSpecial()
    end
    if self.spawntime > SPAWN_SPECIAL_TIME then
        self.field:spawnSpecial()
        self.spawntime = 0
    end
end

-- ---------------------------------------------------------------------------
-- Draw
-- ---------------------------------------------------------------------------

function PlayerField:draw(dm)
    local g  = love.graphics
    local px = self.px
    local py = self.py

    -- Grey out gameover players
    if self.gameover then
        g.setColor(0.7, 0.7, 0.7, 1)
    else
        g.setColor(1, 1, 1, 1)
    end

    -- Info panel background (background_info.png, 248×200 below the field)
    if dm.images["background_info"] then
        g.draw(dm.images["background_info"], px, py + 536)
    end

    -- Text: name, target, score, level
    local font = dm.font
    if font then
        g.setFont(font)
        g.setColor(1, 1, 1, 1)
        g.print(self.name,                          px + 10, py + 560)
        local tgtName = self.target and ("Target: "..self.target.name) or "Target: None"
        g.print(tgtName,                            px + 10, py + 580)
        g.print("Score: " .. tostring(self.score),  px + 10, py + 600)
        g.print("Level: " .. tostring(self.level),  px + 10, py + 620)
    end

    -- Packet timer bar (stack of packet icons)
    if self.packettime > 0 and dm.images["special"] and dm.quads["Packet"] then
        local s      = self.packettime / PACKET_TIME
        local count  = math.ceil(s * 4.0)
        g.setColor(1, 1, 1, 1)
        for i = 0, count - 1 do
            g.draw(dm.images["special"], dm.quads["Packet"],
                   px + 155 - 12, py + 677 - i * 24 - 12)
        end
    end

    -- Antidote icons
    if dm.images["special"] and dm.quads["Anti"] then
        g.setColor(1, 1, 1, 1)
        for i = 0, self.antidotes - 1 do
            g.draw(dm.images["special"], dm.quads["Anti"],
                   px + 27 + 24 * i - 12, py + 669)
        end
    end

    -- The playing field itself
    g.setColor(1, 1, 1, 1)
    self.field:draw(dm)
end

-- ---------------------------------------------------------------------------
-- Module-level helpers used by activate_special
-- ---------------------------------------------------------------------------

function randChoice(t)
    return t[love.math.random(#t)]
end

function shuffleTable(t)
    for i = #t, 2, -1 do
        local j = love.math.random(i)
        t[i], t[j] = t[j], t[i]
    end
end
