-- blockfield.lua
-- Equivalent of blockfield.py
-- Manages the 10×23 playing grid, spawning/placing blocks, row clearing,
-- special block lifecycle, field effects, and drawing.

require("constants")
require("blocks")

-- ---------------------------------------------------------------------------
-- Helpers
-- ---------------------------------------------------------------------------

local function randChoice(t)
    return t[love.math.random(#t)]
end

local function randChoiceWeighted(base, extra, extraWeight)
    -- Returns a random entry from `base`, but with `extra` appearing `extraWeight`
    -- extra times (simulates Python: choice(SPECIAL_PARTS + [Anti]*4))
    local pool = {}
    for _, v in ipairs(base)    do table.insert(pool, v) end
    for _ = 1, extraWeight      do table.insert(pool, extra) end
    return pool[love.math.random(#pool)]
end

local function shuffle(t)
    for i = #t, 2, -1 do
        local j = love.math.random(i)
        t[i], t[j] = t[j], t[i]
    end
end

-- ---------------------------------------------------------------------------
-- BlockField
-- ---------------------------------------------------------------------------

BlockField = {}
BlockField.__index = BlockField

--- Create a new BlockField.
-- @param dm   DataManager
-- @param px   screen x of top-left corner (field content, before border offset)
-- @param py   screen y of top-left corner
function BlockField.new(dm, px, py)
    local self = setmetatable({}, BlockField)
    self.dm = dm

    -- 4-pixel border offset (mirrors Python's self.px = px + 4)
    self.px = px + 4
    self.py = py + 4

    -- 2-D grid: grid[y+1][x+1] = BlockPart or nil  (y,x are 0-based in game logic)
    self.grid = {}
    for y = 0, 22 do
        self.grid[y] = {}
        for x = 0, 9 do
            self.grid[y][x] = nil
        end
    end

    -- Flat list of all placed BlockParts for fast iteration
    self.blockparts_list = {}

    -- The one special block currently on the field (or nil)
    self.special_block = nil

    -- Active field effects: each entry is a BlockPart-like token, or nil.
    self.effects = {
        Inverse    = nil,
        Mini       = nil,
        Blink      = nil,
        Blind      = nil,
        Trans      = nil,
        SZ         = nil,
        Color      = nil,
    }
    self.blink = 0   -- counter toggled by PlayerField to flash the current block

    -- Current falling block and the queued next block
    self.currentblock = nil
    self.nextblock    = nil

    -- Background texture key for this field
    self.background_tile = self:randomBackground()

    return self
end

-- ---------------------------------------------------------------------------
-- Grid accessors
-- ---------------------------------------------------------------------------

function BlockField:get(x, y)
    return self.grid[y] and self.grid[y][x]
end

function BlockField:set(x, y, bp)
    if self.grid[y] then
        self.grid[y][x] = bp
    end
end

-- ---------------------------------------------------------------------------
-- Insert / remove helpers
-- ---------------------------------------------------------------------------

function BlockField:removeBP(x, y)
    local old = self:get(x, y)
    if old ~= nil then
        if old == self.special_block then
            self.special_block = nil
        end
        for i, bp in ipairs(self.blockparts_list) do
            if bp == old then
                table.remove(self.blockparts_list, i)
                break
            end
        end
    end
    self:set(x, y, nil)
end

function BlockField:insertBP(x, y, bp)
    self:removeBP(x, y)
    bp.x = x
    bp.y = y
    self:set(x, y, bp)
    table.insert(self.blockparts_list, bp)
end

function BlockField:replaceBP(oldBP, newBP)
    self:insertBP(oldBP.x, oldBP.y, newBP)
end

-- ---------------------------------------------------------------------------
-- Special block spawning
-- ---------------------------------------------------------------------------

function BlockField:spawnSpecial()
    if #self.blockparts_list == 0 then return end
    self:removeSpecial()
    local old = randChoice(self.blockparts_list)
    -- Weight Anti with EXTRA_ANTIS (4) extra slots
    local Ctor = randChoiceWeighted(SPECIAL_PARTS, BlockPartAnti, EXTRA_ANTIS)
    local bp = Ctor(self.dm)
    self:replaceBP(old, bp)
    self.special_block = bp
end

function BlockField:removeSpecial()
    local old = self.special_block
    if old == nil then return end
    local Ctor = randChoice(STANDARD_PARTS)
    local bp = Ctor(self.dm)
    self:replaceBP(old, bp)
    self.special_block = nil
end

-- ---------------------------------------------------------------------------
-- Block management
-- ---------------------------------------------------------------------------

function BlockField:randomBlock()
    if self.effects.SZ ~= nil then
        return randChoice({BlockS, BlockZ})
    else
        return randChoice(ALL_BLOCKS)
    end
end

function BlockField:randomBackground()
    local keys = {}
    for k, _ in pairs(self.dm.backgrounds) do
        table.insert(keys, k)
    end
    if #keys == 0 then return nil end
    return keys[love.math.random(#keys)]
end

--- Spawn the next block onto the field.
-- Returns true if valid position, false if game-over condition.
function BlockField:addBlock()
    local x = randChoice({3, 4, 5, 6})
    local y = 0

    if self.nextblock == nil then
        -- First call: generate both currentblock and nextblock from scratch
        local CurClass = self:randomBlock()
        local NxtClass = self:randomBlock()
        self.currentblock = CurClass.new(self.dm, x, y)
        self.nextblock    = NxtClass.new(self.dm, 0, 1)
        -- Orient nextblock for display
        if NxtClass == BlockT then
            self.nextblock:rotate("ccw")
            self.nextblock:move(-1, 0)
        elseif NxtClass == BlockO then
            self.nextblock:move(0, 1)
        end
    else
        -- Promote nextblock → currentblock (same shape, new spawn position)
        self.currentblock = self.nextblock._class.new(self.dm, x, y)
        -- Generate new nextblock
        local NxtClass = self:randomBlock()
        self.nextblock = NxtClass.new(self.dm, 0, 1)
        if NxtClass == BlockT then
            self.nextblock:rotate("ccw")
            self.nextblock:move(-1, 0)
        elseif NxtClass == BlockO then
            self.nextblock:move(0, 1)
        end
    end

    return self:inValidPosition(self.currentblock)
end

function BlockField:inValidPosition(block)
    for _, bp in ipairs(block.parts) do
        if bp.y < 0 or bp.x < 0 or bp.x > 9 or bp.y > 22 then
            return false
        end
        if self:get(bp.x, bp.y) ~= nil then
            return false
        end
    end
    return true
end

function BlockField:rotateBlock(dir)
    if self.currentblock == nil then return end
    self.currentblock:rotate(dir)
    if not self:inValidPosition(self.currentblock) then
        -- undo
        local inv = (dir == "cw") and "ccw" or "cw"
        self.currentblock:rotate(inv)
    end
end

function BlockField:placeCurrentBlock(dm)
    for _, bp in ipairs(self.currentblock.parts) do
        self:insertBP(bp.x, bp.y, bp)
    end
    self.currentblock = nil
    if dm.placesound then dm.placesound:play() end
end

-- ---------------------------------------------------------------------------
-- Row clearing
-- ---------------------------------------------------------------------------

--- Remove all full rows.
-- Returns (count, special_block_or_nil)
function BlockField:removeFullRows()
    local fullLines = {}
    for y = 0, 22 do
        local full = true
        for x = 0, 9 do
            if self.grid[y][x] == nil then
                full = false
                break
            end
        end
        if full then
            table.insert(fullLines, y)
        end
    end

    -- Sort bottom-to-top so each removeLine() doesn't shift the y-indices of
    -- rows that are yet to be removed (same fix needed in the Python original).
    table.sort(fullLines, function(a, b) return a > b end)

    local specialBlock = nil
    for _, y in ipairs(fullLines) do
        local tmp = self:removeLine(y)
        if tmp ~= nil then specialBlock = tmp end
    end
    return #fullLines, specialBlock
end

function BlockField:removeLine(y)
    local special = nil
    for x = 0, 9 do
        local bp = self.grid[y][x]
        if bp and bp.isSpecial then
            special = bp
        end
        self:removeBP(x, y)
    end
    -- Shift everything above this line down by one
    for row = y - 1, 0, -1 do
        for x = 0, 9 do
            if self.grid[row][x] ~= nil then
                self:moveBP(x, row, x, row + 1)
            end
        end
    end
    return special
end

function BlockField:moveBP(fromX, fromY, toX, toY)
    local bp = self.grid[fromY][fromX]
    self.grid[fromY][fromX] = nil
    self.grid[toY][toX]     = bp
    if bp then
        bp.x = toX
        bp.y = toY
    end
end

-- ---------------------------------------------------------------------------
-- add_line  (Stair / Bridge / Packet / Ring effects add junk lines)
-- ---------------------------------------------------------------------------

function BlockField:topIndex()
    local top = 22
    for _, bp in ipairs(self.blockparts_list) do
        if bp.y <= top then
            top = bp.y - 1
        end
    end
    return math.max(top, 0)
end

--- Add a junk line.
-- top=true  → insert at the top (pushes stack down, Bridge / Stair style)
-- top=false → shift everything up and add at bottom (Packet style)
function BlockField:addLine(top)
    if top then
        local y = self:topIndex()
        local bps = {nil}  -- one gap
        for _ = 1, 9 do
            table.insert(bps, randChoice(STANDARD_PARTS)(self.dm))
        end
        shuffle(bps)
        for x = 0, 9 do
            local bp = bps[x + 1]
            if bp ~= nil then
                self:insertBP(x, y, bp)
            else
                self:removeBP(x, y)
            end
        end
    else
        -- Shift rows 1..22 upward (decrease y by 1)
        for y = 1, 22 do
            for x = 0, 9 do
                if self.grid[y][x] ~= nil then
                    self:moveBP(x, y, x, y - 1)
                end
            end
        end
        -- Fill row 22
        local bps = {nil}
        for _ = 1, 9 do
            table.insert(bps, randChoice(STANDARD_PARTS)(self.dm))
        end
        shuffle(bps)
        for x = 0, 9 do
            local bp = bps[x + 1]
            if bp ~= nil then
                self:insertBP(x, 22, bp)
            end
        end
    end
end

-- ---------------------------------------------------------------------------
-- Flip  (Yin & Yang special)
-- ---------------------------------------------------------------------------

function BlockField:flip()
    local top    = self:topIndex() + 1
    local middle = top + math.floor((22 - top) / 2)
    for offset = 0, middle - top do
        local y1 = top    + offset
        local y2 = 22     - offset
        if y1 >= y2 then break end
        for x = 0, 9 do
            self.grid[y1][x], self.grid[y2][x] = self.grid[y2][x], self.grid[y1][x]
            if self.grid[y1][x] then self.grid[y1][x].y = y1 end
            if self.grid[y2][x] then self.grid[y2][x].y = y2 end
        end
    end
end

-- ---------------------------------------------------------------------------
-- Clear field
-- ---------------------------------------------------------------------------

function BlockField:clearField()
    for y = 0, 22 do
        for x = 0, 9 do
            self.grid[y][x] = nil
        end
    end
    self.blockparts_list = {}
    self.special_block   = nil
end

-- ---------------------------------------------------------------------------
-- Drawing
-- ---------------------------------------------------------------------------

--- Draw the entire field including border, background, blocks, current block,
--- next block preview, and active-effect icons.
-- Must be called with no current transform (uses absolute screen coordinates).
function BlockField:draw(dm)
    local g = love.graphics
    local px, py = self.px, self.py

    -- Background border
    if dm.images["background_border"] then
        g.setColor(1, 1, 1, 1)
        g.draw(dm.images["background_border"], px - 4, py - 4)
    end

    -- Background tile  (240×528, clipped to field interior)
    local bgKey = self.background_tile
    if bgKey and dm.backgrounds[bgKey] then
        local bgImg  = dm.backgrounds[bgKey]
        local bgW    = bgImg:getWidth()
        local bgH    = bgImg:getHeight()
        local fieldW, fieldH = 240, 528
        g.setColor(1, 1, 1, 1)
        g.setScissor(px, py, fieldW, fieldH)
        for ty = 0, math.ceil(fieldH / bgH) do
            for tx = 0, math.ceil(fieldW / bgW) do
                g.draw(bgImg, px + tx * bgW, py + ty * bgH)
            end
        end
        g.setScissor()
    end

    -- Placed block parts  (offset by -BLOCK_SIZE in y to hide row 0)
    g.push()
    g.translate(px, py - BLOCK_SIZE)
    local mini  = self.effects.Mini  ~= nil
    local trans = self.effects.Trans ~= nil
    for _, bp in ipairs(self.blockparts_list) do
        bp:draw(dm, mini, trans)
    end
    g.pop()

    -- Color / Blackout overlay (bw.png, scrolling UV to follow current block)
    if self.effects.Color ~= nil and dm.images["bw"] then
        local bwImg = dm.images["bw"]
        -- Compute a scroll offset based on current block position (matches Python)
        local dx, dy = 0, 0
        if self.currentblock then
            local pivot = self.currentblock.parts[1]
            dx = (pivot.x + 1) / (10.0 * 2) + 0.50
            dy = pivot.y      / (22.0 * 2) + 0.50
        end
        -- Tile bw image over the field with the UV offset simulated by shifting draw origin
        local bwW  = bwImg:getWidth()
        local bwH  = bwImg:getHeight()
        local offX = (-dx * bwW * 2) % bwW   -- wrap to one tile width
        local offY = (-dy * bwH * 2) % bwH
        g.setColor(1, 1, 1, 0.9)
        g.setScissor(px, py, 240, 528)
        g.push()
        g.translate(px - offX, py - offY)
        for ty = -1, math.ceil(528 / bwH) + 1 do
            for tx = -1, math.ceil(240 / bwW) + 1 do
                g.draw(bwImg, tx * bwW, ty * bwH)
            end
        end
        g.pop()
        g.setScissor()
        g.setColor(1, 1, 1, 1)
    end

    -- Current block  (skip if Blink effect and blink counter is nonzero)
    if self.currentblock ~= nil then
        local skip = (self.effects.Blink ~= nil) and (self.blink % 2 == 1)
        if not skip then
            g.push()
            g.translate(px, py - BLOCK_SIZE)
            self.currentblock:draw(dm, mini, trans)
            g.pop()
        end
    end

    -- Next block preview  (hidden during Blind effect)
    if self.nextblock ~= nil and self.effects.Blind == nil then
        g.push()
        g.translate(px + 175, py + 567)
        self.nextblock:draw(dm, false, false)
        g.pop()
    end

    -- Active-effect icon strip (row of block-part icons in the HUD panel)
    g.push()
    g.translate(px + 2, py + 677)
    local iconX = 0
    for _, sbp in pairs(self.effects) do
        if sbp ~= nil then
            sbp:draw(dm, false, false)
            iconX = iconX + BLOCK_SIZE
        end
    end
    g.pop()
end
