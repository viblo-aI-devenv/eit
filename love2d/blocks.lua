-- blocks.lua
-- Equivalent of blocks.py
-- Provides: BlockPart, all 22 special block-part constructors,
--           8 standard color constructors, SPECIAL_PARTS, STANDARD_PARTS,
--           Block and the 7 tetromino shapes, ALL_BLOCKS.
--
-- Drawing is done by the caller passing the DataManager (dm) which owns
-- the loaded images and quads tables.

require("constants")

-- ---------------------------------------------------------------------------
-- BlockPart
-- ---------------------------------------------------------------------------

BlockPart = {}
BlockPart.__index = BlockPart

--- Create a new block part.
-- @param x     grid x position (0-based)
-- @param y     grid y position (0-based)
-- @param texKey  "standard" or "special"  (key into dm.images)
-- @param quadKey  key into dm.quads, e.g. "Red", "Faster"
-- @param isSpecial  boolean
function BlockPart.new(x, y, texKey, quadKey, isSpecial)
    local self = setmetatable({}, BlockPart)
    self.x         = x
    self.y         = y
    self.texKey    = texKey
    self.quadKey   = quadKey
    self.isSpecial = isSpecial or false
    self.type      = nil   -- set by special subtypes
    return self
end

--- Draw this block part.
-- Must be called inside a coordinate frame where (0,0) is the field's top-left
-- (i.e. after love.graphics.push() + translate to field origin).
-- @param dm    DataManager
-- @param mini  boolean – draw at 40 % scale
-- @param trans boolean – draw semi-transparent (Ice/Trans effect)
function BlockPart:draw(dm, mini, trans)
    if self.y == 0 then return end   -- row 0 is the hidden spawn row
    local img  = dm.images[self.texKey]
    local quad = dm.quads[self.quadKey]
    if not img or not quad then return end

    local px = self.x * BLOCK_SIZE
    local py = self.y * BLOCK_SIZE

    love.graphics.push()
    love.graphics.translate(px, py)

    if mini and self.quadKey ~= "Grey" then
        -- centre the mini block in the cell
        love.graphics.translate(BLOCK_SIZE * 0.3, BLOCK_SIZE * 0.3)
        love.graphics.scale(0.4, 0.4)
    end

    if trans and self.quadKey ~= "Grey" then
        love.graphics.setColor(1, 1, 1, 0.35)
    else
        love.graphics.setColor(1, 1, 1, 1)
    end

    love.graphics.draw(img, quad, 0, 0)
    love.graphics.setColor(1, 1, 1, 1)
    love.graphics.pop()
end

function BlockPart:move(dx, dy)
    self.x = self.x + dx
    self.y = self.y + dy
end

-- ---------------------------------------------------------------------------
-- Special block-part constructors  (22 types, same order as SPECIAL_PARTS)
-- ---------------------------------------------------------------------------

local SPECIAL_NAMES = {
    "Faster", "Slower", "Stair",  "Fill",   "Rumble", "Inverse",
    "Switch", "Packet", "Flip",   "Mini",   "Blink",  "Blind",
    "Background", "Anti", "Bridge", "Trans", "Clear",  "Question",
    "SZ",     "Color",  "Ring",   "Castle",
}

SPECIAL_PARTS = {}

for _, name in ipairs(SPECIAL_NAMES) do
    local typeName = name   -- capture for closure
    local ctor = function(dm, x, y)
        local bp = BlockPart.new(x or 0, y or 0, "special", typeName, true)
        bp.type = typeName
        return bp
    end
    _G["BlockPart" .. name] = ctor
    table.insert(SPECIAL_PARTS, ctor)
end

-- Add EXTRA_ANTIS extra Anti entries (matches Python: SPECIAL_PARTS + [Anti]*4)
-- This weighting is applied in blockfield.lua spawn_special().

-- ---------------------------------------------------------------------------
-- Standard color block-part constructors  (8 colors, matches standard.png strip)
-- Strip layout (x offset * 24 px, 0-based):
--   0=Blue  1=Red  2=Green  3=Purple  4=Yellow  5=Pink  6=Cyan  7=Grey
-- The Python tex_offset values confirm this mapping via (n/8, (n+1)/8).
-- ---------------------------------------------------------------------------

local STANDARD_NAMES = {"Blue","Red","Green","Purple","Yellow","Pink","Cyan","Grey"}

STANDARD_PARTS = {}

for _, name in ipairs(STANDARD_NAMES) do
    local colorName = name
    local ctor = function(dm, x, y)
        return BlockPart.new(x or 0, y or 0, "standard", colorName, false)
    end
    _G["BlockPart" .. name] = ctor
    -- Grey is NOT in STANDARD_PARTS (Python excludes it too)
    if name ~= "Grey" then
        table.insert(STANDARD_PARTS, ctor)
    end
end

-- ---------------------------------------------------------------------------
-- Block  (tetromino base class)
-- ---------------------------------------------------------------------------

Block = {}
Block.__index = Block

function Block.new(dm)
    local self = setmetatable({}, Block)
    self.parts = {}
    self.dm    = dm
    return self
end

--- Add four block parts (a, b, c, d) – mirrors Python Block.add()
function Block:add(a, b, c, d)
    table.insert(self.parts, a)
    table.insert(self.parts, b)
    table.insert(self.parts, c)
    table.insert(self.parts, d)
end

--- Move all parts by (dx, dy)
function Block:move(dx, dy)
    for _, bp in ipairs(self.parts) do bp:move(dx, dy) end
end

--- Rotate around the first part.
-- dir = "cw" (clockwise) or "ccw" (counter-clockwise)
function Block:rotate(dir)
    local pivot = self.parts[1]
    local px, py = pivot.x, pivot.y
    for i = 2, #self.parts do
        local bp = self.parts[i]
        bp.x = bp.x - px
        bp.y = bp.y - py
        local ox = bp.x
        if dir == "cw" then
            bp.x = -bp.y
            bp.y =  ox
        else
            bp.x =  bp.y
            bp.y = -ox
        end
        bp.x = bp.x + px
        bp.y = bp.y + py
    end
end

--- Draw all parts.
-- @param dm    DataManager
-- @param mini  boolean
-- @param trans boolean
function Block:draw(dm, mini, trans)
    for _, bp in ipairs(self.parts) do
        bp:draw(dm, mini, trans)
    end
end

-- ---------------------------------------------------------------------------
-- The 7 tetrominoes  (exact same shapes / colors as Python)
-- ---------------------------------------------------------------------------

-- Helper: create a tetromino class table.
-- Each class has a .new(dm, x, y) constructor that also stores self._class = Class
-- so that blockfield.lua can re-instantiate the same shape for the preview block.
local function makeBlockClass(parentMeta, ctorFn)
    local Class = {}
    Class.__index = setmetatable(Class, {__index = parentMeta})
    function Class.new(dm, x, y)
        local self = Block.new(dm)
        setmetatable(self, Class)
        self._class = Class   -- store class reference for re-instantiation
        ctorFn(self, dm, x, y)
        return self
    end
    return Class
end

-- O – 2×2 square, purple, cannot rotate
BlockO = makeBlockClass(Block, function(self, dm, x, y)
    local a = BlockPartPurple(dm, 0, 0)
    local b = BlockPartPurple(dm, 1, 0)
    local c = BlockPartPurple(dm, 0, 1)
    local d = BlockPartPurple(dm, 1, 1)
    self:add(a, b, c, d)
    self:move(x, y)
end)
function BlockO:rotate(_dir) end   -- O does not rotate

-- I – vertical bar, red
BlockI = makeBlockClass(Block, function(self, dm, x, y)
    local a = BlockPartRed(dm, 0, 1)  -- pivot (index 1)
    local b = BlockPartRed(dm, 0, 0)
    local c = BlockPartRed(dm, 0, 2)
    local d = BlockPartRed(dm, 0, 3)
    self:add(a, b, c, d)
    self:move(x, y)
end)
-- I uses the default Block:rotate() – the Python "BUG; FIXME" is preserved.

-- T – T-shape, cyan
BlockT = makeBlockClass(Block, function(self, dm, x, y)
    local a = BlockPartCyan(dm, 1, 1)  -- pivot
    local b = BlockPartCyan(dm, 0, 1)
    local c = BlockPartCyan(dm, 2, 1)
    local d = BlockPartCyan(dm, 1, 2)
    self:add(a, b, c, d)
    self:move(x, y)
end)

-- L – L-shape, green
BlockL = makeBlockClass(Block, function(self, dm, x, y)
    local a = BlockPartGreen(dm, 0, 1)  -- pivot
    local b = BlockPartGreen(dm, 0, 0)
    local c = BlockPartGreen(dm, 0, 2)
    local d = BlockPartGreen(dm, 1, 2)
    self:add(a, b, c, d)
    self:move(x, y)
end)

-- J – J-shape, blue
BlockJ = makeBlockClass(Block, function(self, dm, x, y)
    local a = BlockPartBlue(dm, 1, 1)  -- pivot
    local b = BlockPartBlue(dm, 1, 0)
    local c = BlockPartBlue(dm, 0, 2)
    local d = BlockPartBlue(dm, 1, 2)
    self:add(a, b, c, d)
    self:move(x, y)
end)

-- S – S-shape, pink
BlockS = makeBlockClass(Block, function(self, dm, x, y)
    local a = BlockPartPink(dm, 0, 1)  -- pivot
    local b = BlockPartPink(dm, 0, 0)
    local c = BlockPartPink(dm, 1, 1)
    local d = BlockPartPink(dm, 1, 2)
    self:add(a, b, c, d)
    self:move(x, y)
end)

-- Z – Z-shape, yellow
BlockZ = makeBlockClass(Block, function(self, dm, x, y)
    local a = BlockPartYellow(dm, 0, 1)  -- pivot
    local b = BlockPartYellow(dm, 1, 0)
    local c = BlockPartYellow(dm, 1, 1)
    local d = BlockPartYellow(dm, 0, 2)
    self:add(a, b, c, d)
    self:move(x, y)
end)

ALL_BLOCKS = {BlockI, BlockT, BlockO, BlockL, BlockJ, BlockS, BlockZ}
