-- ui.lua
-- Gamepad-navigable menu system for the Love2D Eit port.
-- Replaces the PGU-based GUI dialogs (dialogs.py + Main.__init__).
--
-- Screen layout (1024×768):
--   Left column  (x≈30):   "Active Profiles" + 4 slot buttons
--   Centre column (x≈340): Start Game / Highscores / Edit Profiles / Help / Quit
--   Right column (x≈600):  fullscreen + music toggles
--   Title banner at top-left
--
-- Navigation:
--   D-pad up/down (or arrow keys) move between items in the focused column.
--   D-pad left/right (or arrow keys) switch columns.
--   A / Enter  = confirm / activate.
--   B / ESC    = back / cancel.
--   Start      = Start Game shortcut.

-- ---------------------------------------------------------------------------
-- Very small retained-mode widget kit
-- ---------------------------------------------------------------------------

local function newLabel(text, x, y, color)
    return { kind="label", text=text, x=x, y=y, color=color or {0,1,0,1} }
end

local function newButton(text, x, y, w, h, action)
    return { kind="button", text=text, x=x, y=y, w=w or 160, h=h or 28,
             action=action, focused=false, color={1,1,1,1} }
end

--- Simple vertical menu: array of buttons, one focused at a time.
local Menu = {}
Menu.__index = Menu

function Menu.new(items)
    local self = setmetatable({}, Menu)
    self.items   = items   -- array of button tables
    self.cursor  = 1
    return self
end

function Menu:up()
    self.cursor = ((self.cursor - 2) % #self.items) + 1
end

function Menu:down()
    self.cursor = (self.cursor % #self.items) + 1
end

function Menu:activate()
    local item = self.items[self.cursor]
    if item and item.action then item.action() end
end

function Menu:draw(font, active)
    local g = love.graphics
    for i, btn in ipairs(self.items) do
        local focused = active and (i == self.cursor)
        if focused then
            g.setColor(1, 1, 0, 1)   -- yellow highlight
            g.rectangle("fill", btn.x - 4, btn.y - 2, btn.w + 8, btn.h + 4)
            g.setColor(0, 0, 0, 1)
        else
            g.setColor(0.15, 0.15, 0.15, 0.8)
            g.rectangle("fill", btn.x - 4, btn.y - 2, btn.w + 8, btn.h + 4)
            g.setColor(btn.color[1], btn.color[2], btn.color[3], btn.color[4] or 1)
        end
        if font then g.setFont(font) end
        g.print(btn.text, btn.x, btn.y)
    end
end

-- ---------------------------------------------------------------------------
-- Sub-screens (modal overlays)
-- ---------------------------------------------------------------------------

-- ---- SelectProfile overlay ------------------------------------------------

local SelectProfile = {}
SelectProfile.__index = SelectProfile

function SelectProfile.new(profiles, onSelect, onCancel)
    local self   = setmetatable({}, SelectProfile)
    self.profiles = profiles
    self.onSelect = onSelect
    self.onCancel = onCancel
    self.names    = profiles:names()
    self.cursor   = 1
    return self
end

function SelectProfile:refresh()
    self.names  = self.profiles:names()
    self.cursor = math.min(self.cursor, math.max(1, #self.names))
end

function SelectProfile:up()
    if #self.names == 0 then return end
    self.cursor = ((self.cursor - 2) % #self.names) + 1
end

function SelectProfile:down()
    if #self.names == 0 then return end
    self.cursor = (self.cursor % #self.names) + 1
end

function SelectProfile:draw(font)
    local g  = love.graphics
    local cx = 300
    local cy = 200
    local w  = 400
    local h  = 320
    g.setColor(0.1, 0.1, 0.1, 0.95)
    g.rectangle("fill", cx, cy, w, h)
    g.setColor(0, 1, 0, 1)
    g.rectangle("line", cx, cy, w, h)
    if font then g.setFont(font) end
    g.setColor(0, 1, 0, 1)
    g.print("Select Profile", cx + 10, cy + 8)
    for i, name in ipairs(self.names) do
        local iy = cy + 40 + (i-1) * 28
        if i == self.cursor then
            g.setColor(1, 1, 0, 1)
            g.rectangle("fill", cx + 8, iy - 2, w - 16, 26)
            g.setColor(0, 0, 0, 1)
        else
            g.setColor(1, 1, 1, 1)
        end
        g.print(name, cx + 12, iy)
    end
    g.setColor(0.6, 0.6, 0.6, 1)
    g.print("[A/Enter] Select   [B/Esc] Cancel", cx + 10, cy + h - 28)
end

function SelectProfile:confirm()
    if #self.names == 0 then return end
    if self.onSelect then self.onSelect(self.names[self.cursor]) end
end

function SelectProfile:cancel()
    if self.onCancel then self.onCancel() end
end

-- ---- ManageProfiles overlay -----------------------------------------------
-- Simplified: list of profiles + New / Edit name / Delete buttons.
-- Full key rebinding via keyboard is complex on a gamepad; we keep it
-- text-only (name editing) and leave key-mapping to a "Edit Keys" sub-screen.

local ManageProfiles = {}
ManageProfiles.__index = ManageProfiles

function ManageProfiles.new(profiles, font)
    local self      = setmetatable({}, ManageProfiles)
    self.profiles   = profiles
    self.font       = font
    self.names      = profiles:names()
    self.cursor     = 1
    self.mode       = "list"   -- "list" | "edit"
    self.editName   = ""
    self.editKeys   = {}
    self.keyField   = 1   -- which key-binding is being edited
    self.KEY_LABELS = {"left","right","cw","ccw","down","drop","anti","change"}
    return self
end

function ManageProfiles:refresh()
    self.names  = self.profiles:names()
    self.cursor = math.min(self.cursor, math.max(1, #self.names))
end

function ManageProfiles:up()
    if self.mode == "list" then
        if #self.names == 0 then return end
        self.cursor = ((self.cursor - 2) % #self.names) + 1
    elseif self.mode == "edit" then
        self.keyField = ((self.keyField - 2) % #self.KEY_LABELS) + 1
    end
end

function ManageProfiles:down()
    if self.mode == "list" then
        if #self.names == 0 then return end
        self.cursor = (self.cursor % #self.names) + 1
    elseif self.mode == "edit" then
        self.keyField = (self.keyField % #self.KEY_LABELS) + 1
    end
end

--- Press A in list mode → enter edit mode for selected profile.
function ManageProfiles:activateSelected()
    if self.mode == "list" and #self.names > 0 then
        local name = self.names[self.cursor]
        local existing = self.profiles:get(name) or {}
        self.editName = name
        self.editKeys = {}
        for _, k in ipairs(self.KEY_LABELS) do
            self.editKeys[k] = existing[k] or ""
        end
        self.keyField = 1
        self.mode = "edit"
    end
end

--- Press X in list mode → create new profile.
function ManageProfiles:createNew()
    if self.mode == "list" then
        local name = self.profiles:createNew()
        self:refresh()
        -- position cursor on new entry
        for i, n in ipairs(self.names) do
            if n == name then self.cursor = i; break end
        end
    end
end

--- Press Y in list mode → delete selected profile.
function ManageProfiles:deleteSelected()
    if self.mode == "list" and #self.names > 0 then
        self.profiles:delete(self.names[self.cursor])
        self:refresh()
    end
end

--- In edit mode, a key was pressed: record it for the current field.
function ManageProfiles:recordKey(key)
    if self.mode ~= "edit" then return end
    self.editKeys[self.KEY_LABELS[self.keyField]] = key
end

--- Confirm edit (save).
function ManageProfiles:confirmEdit()
    if self.mode == "edit" then
        self.profiles:set(self.editName, self.editKeys)
        self:refresh()
        self.mode = "list"
    end
end

--- Cancel edit.
function ManageProfiles:cancelEdit()
    self.mode = "list"
    self:refresh()
end

function ManageProfiles:draw(font)
    local g  = love.graphics
    local cx = 150
    local cy = 100
    local w  = 724
    local h  = 500
    g.setColor(0.05, 0.05, 0.05, 0.97)
    g.rectangle("fill", cx, cy, w, h)
    g.setColor(0, 1, 0, 1)
    g.rectangle("line", cx, cy, w, h)
    if font then g.setFont(font) end

    if self.mode == "list" then
        g.setColor(0, 1, 0, 1)
        g.print("Manage Profiles", cx + 10, cy + 8)
        for i, name in ipairs(self.names) do
            local iy = cy + 44 + (i-1) * 28
            if i == self.cursor then
                g.setColor(1, 1, 0, 1)
                g.rectangle("fill", cx + 8, iy - 2, w - 16, 26)
                g.setColor(0, 0, 0, 1)
            else
                g.setColor(1, 1, 1, 1)
            end
            g.print(name, cx + 12, iy)
        end
        g.setColor(0.6, 0.6, 0.6, 1)
        g.print("[A/Enter] Edit   [X] New   [Y] Delete   [B/Esc] Close",
                cx + 10, cy + h - 28)
    else
        -- Edit mode
        g.setColor(0, 1, 0, 1)
        g.print("Edit Profile: " .. self.editName, cx + 10, cy + 8)
        g.setColor(0.7, 0.7, 0.7, 1)
        g.print("Press the desired key for each binding,\nthen A/Enter to save.",
                cx + 10, cy + 30)
        for i, k in ipairs(self.KEY_LABELS) do
            local iy = cy + 80 + (i-1) * 36
            if i == self.keyField then
                g.setColor(1, 1, 0, 1)
                g.rectangle("fill", cx + 8, iy - 2, w - 16, 32)
                g.setColor(0, 0, 0, 1)
            else
                g.setColor(1, 1, 1, 1)
            end
            local label = k:upper()
            local val   = self.editKeys[k] or "?"
            g.print(string.format("%-14s %s", label, val), cx + 12, iy + 4)
        end
        g.setColor(0.6, 0.6, 0.6, 1)
        g.print("[any key] bind   [A/Enter] Save   [B/Esc] Cancel",
                cx + 10, cy + h - 28)
    end
end

-- ---- ViewScore overlay ----------------------------------------------------

local ViewScore = {}
ViewScore.__index = ViewScore

function ViewScore.new(scoretable)
    local self       = setmetatable({}, ViewScore)
    self.scoretable  = scoretable
    return self
end

function ViewScore:draw(font)
    local g  = love.graphics
    local cx = 150
    local cy = 100
    local w  = 724
    local h  = 500
    g.setColor(0.05, 0.05, 0.05, 0.97)
    g.rectangle("fill", cx, cy, w, h)
    g.setColor(0, 1, 0, 1)
    g.rectangle("line", cx, cy, w, h)
    if font then g.setFont(font) end
    g.setColor(0, 1, 0, 1)
    g.print("Highscores", cx + 10, cy + 8)

    -- Header
    local cols = {cx+12, cx+130, cx+280, cx+390, cx+490, cx+580}
    local headers = {"Rank Pts","Name","Tot Score","Tot Lines","Max Lvl","W/L"}
    g.setColor(0, 1, 0, 1)
    for i, h_lbl in ipairs(headers) do
        g.print(h_lbl, cols[i], cy + 38)
    end

    local list = self.scoretable:getList()
    for i, entry in ipairs(list) do
        local name, stat = entry[1], entry[2]
        local iy = cy + 64 + (i-1) * 24
        if iy > cy + h - 40 then break end
        g.setColor(1, 1, 1, 1)
        g.print(tostring(stat["Rank Points"] or 0), cols[1], iy)
        g.print(name,                               cols[2], iy)
        g.print(tostring(stat.Score   or 0),        cols[3], iy)
        g.print(tostring(stat.Lines   or 0),        cols[4], iy)
        g.print(tostring(stat["Max Level"] or 0),   cols[5], iy)
        local wl = tostring(stat.Winns or 0) .. "/" ..
                   tostring((stat.Matches or 0) - (stat.Winns or 0))
        g.print(wl, cols[6], iy)
    end

    g.setColor(0.6, 0.6, 0.6, 1)
    g.print("[B/Esc/Enter] Close", cx + 10, cy + h - 28)
end

-- ---- HelpDialog -----------------------------------------------------------

local HelpInfo = {}
HelpInfo.__index = HelpInfo

function HelpInfo.new()
    return setmetatable({}, HelpInfo)
end

local SPECIAL_NAMES = {
    "Rabbit","Turtle","Stair","Fill","Rumble","Inverse",
    "Switch","Packet","Flip","Mini","Blink","Blind",
    "Background","Antidote","Bridge","Ice","Clear","Question",
    "SZ","Blackout","Ring","Castle",
}

function HelpInfo:draw(font, dm)
    local g  = love.graphics
    local cx = 100
    local cy = 60
    local w  = 824
    local h  = 620
    g.setColor(0.05, 0.05, 0.05, 0.97)
    g.rectangle("fill", cx, cy, w, h)
    g.setColor(0, 1, 0, 1)
    g.rectangle("line", cx, cy, w, h)
    if font then g.setFont(font) end
    g.setColor(0, 1, 0, 1)
    g.print("Help - Special Blocks", cx + 10, cy + 8)

    -- Draw 2-column grid of special icons + names
    local cols   = 2
    local itemW  = math.floor(w / cols)
    local itemH  = 28
    local startY = cy + 40

    for i, name in ipairs(SPECIAL_NAMES) do
        local col  = (i - 1) % cols
        local row  = math.floor((i - 1) / cols)
        local ix   = cx + 10 + col * itemW
        local iy   = startY + row * itemH
        -- Draw icon quad if available
        if dm and dm.images["special"] and dm.quads and dm.quads[name] then
            g.setColor(1, 1, 1, 1)
            g.draw(dm.images["special"], dm.quads[name], ix, iy - 2)
            g.setColor(1, 1, 1, 1)
            g.print(name, ix + 28, iy)
        else
            g.setColor(1, 1, 1, 1)
            g.print("[" .. name .. "]", ix, iy)
        end
    end

    -- Controls reference
    local gy = startY + math.ceil(#SPECIAL_NAMES / cols) * itemH + 10
    g.setColor(0, 1, 0, 1)
    g.print("Gamepad Controls:", cx + 10, gy)
    g.setColor(1, 1, 1, 1)
    local ctls = {
        "D-Pad / Left Stick : Move",
        "A (Cross)          : Hard Drop",
        "B (Circle)         : Rotate CW",
        "X (Square)         : Rotate CCW",
        "Y (Triangle)       : Use Antidote",
        "Right Shoulder     : Change Target",
        "Start              : Pause",
    }
    for j, line in ipairs(ctls) do
        g.print(line, cx + 10, gy + 20 + (j-1)*20)
    end

    g.setColor(0.6, 0.6, 0.6, 1)
    g.print("[B/Esc/Enter] Close", cx + 10, cy + h - 28)
end

-- ---------------------------------------------------------------------------
-- MainMenu
-- ---------------------------------------------------------------------------

MainMenu = {}
MainMenu.__index = MainMenu

function MainMenu.new(settings, profiles, scoretable, onStart, onQuit)
    local self = setmetatable({}, MainMenu)
    self.settings   = settings
    self.profiles   = profiles
    self.scoretable = scoretable
    self.onStart    = onStart
    self.onQuit     = onQuit

    -- Columns: 0=slots, 1=actions, 2=options
    self.col         = 1   -- currently focused column (0-based)
    self.overlay     = nil -- "select" | "manage" | "score" | "help"
    self.editSlot    = nil -- which slot is being assigned (1-4)

    self:_buildMenus()
    return self
end

function MainMenu:_buildMenus()
    local s    = self.settings
    local px   = 260   -- x of the actions column
    local sy   = 300   -- y start for action buttons

    -- Column 1: Start Game / Highscores / Edit Profiles / Help / Quit
    self.actionMenu = Menu.new({
        newButton("Start Game",    px, sy,      160, 28, function() self:_startGame()      end),
        newButton("Highscores",    px, sy + 40, 160, 28, function() self:_openScore()      end),
        newButton("Edit Profiles", px, sy + 80, 160, 28, function() self:_openManage()     end),
        newButton("Help",          px, sy +120, 160, 28, function() self:_openHelp()       end),
        newButton("Quit",          px, sy +160, 160, 28, function() self.onQuit()           end),
    })

    -- Column 0: Slot buttons (P1–P4)
    local slotX = 30
    local slotY = 300
    self.slotMenu = Menu.new({})
    self:_rebuildSlotMenu(slotX, slotY)

    -- Column 2: Options
    local optX = 460
    local optY = 300
    self.optionMenu = Menu.new({
        newButton(self:_fsLabel(), optX, optY,      200, 28,
            function()
                s.fullscreen = not s.fullscreen
                s:save()
                love.window.setFullscreen(s.fullscreen)
                self.optionMenu.items[1].text = self:_fsLabel()
            end),
        newButton(self:_musicLabel(), optX, optY+40, 200, 28,
            function()
                s.music = not s.music
                s:save()
                self.optionMenu.items[2].text = self:_musicLabel()
            end),
    })
end

function MainMenu:_fsLabel()
    return "Fullscreen: " .. (self.settings.fullscreen and "ON" or "OFF")
end

function MainMenu:_musicLabel()
    return "Music: " .. (self.settings.music and "ON" or "OFF")
end

function MainMenu:_rebuildSlotMenu(x, y)
    local s = self.settings
    self.slotMenu.items = {}
    for slot = 1, 4 do
        local name = s.active_profiles[slot] or "None"
        local lbl  = "P" .. slot .. ": " .. name
        local btn  = newButton(lbl, x, y + (slot-1)*36, 200, 28,
            function()
                self.editSlot = slot
                local sp = SelectProfile.new(self.profiles,
                    function(chosen)
                        self.settings.active_profiles[slot] = chosen
                        self.settings:save()
                        self:_rebuildSlotMenu(x, y)
                        self.overlay = nil
                    end,
                    function() self.overlay = nil end
                )
                sp:refresh()
                self.selectProfileUI = sp
                self.overlay = "select"
            end)
        table.insert(self.slotMenu.items, btn)
    end
    -- "Clear slot" handled by pressing Y on a slot entry
end

function MainMenu:_startGame()
    -- Ensure at least one active profile
    local any = false
    for i = 1, 4 do
        if self.settings.active_profiles[i] ~= "None" then any = true; break end
    end
    if not any then return end  -- nothing to do
    if self.onStart then self.onStart() end
end

function MainMenu:_openScore()
    self.viewScoreUI = ViewScore.new(self.scoretable)
    self.overlay = "score"
end

function MainMenu:_openManage()
    self.manageUI = ManageProfiles.new(self.profiles, nil)
    self.overlay  = "manage"
end

function MainMenu:_openHelp()
    self.helpUI  = HelpInfo.new()
    self.overlay = "help"
end

--- Called by main.lua when returning to menu (refresh stale data).
function MainMenu:refresh(settings, profiles, scoretable)
    self.settings   = settings
    self.profiles   = profiles
    self.scoretable = scoretable
    self.overlay    = nil
    self:_buildMenus()
end

-- Column accessors
local COL_COUNT = 3
local function colMenu(self, c)
    if c == 0 then return self.slotMenu
    elseif c == 1 then return self.actionMenu
    else return self.optionMenu end
end

function MainMenu:update(dt)
    -- nothing time-dependent in the menu
end

function MainMenu:draw(dm)
    local g = love.graphics
    local font = dm and dm.font or nil

    -- Background
    g.setColor(0, 0, 0, 1)
    g.rectangle("fill", 0, 0, 1024, 768)

    -- Title
    g.setColor(0, 1, 0, 1)
    if font then g.setFont(font) end
    g.print("E I T", 30, 40)
    g.setColor(0.5, 0.5, 0.5, 1)
    g.print("A multiplayer Tetris battle", 30, 70)

    -- Section headers
    g.setColor(0, 1, 0, 1)
    g.print("Active Profiles",  30, 270)
    g.print("Menu",            260, 270)
    g.print("Options",         460, 270)

    -- Menus
    self.slotMenu:draw(font, self.col == 0)
    self.actionMenu:draw(font, self.col == 1)
    self.optionMenu:draw(font, self.col == 2)

    -- Navigation hint
    g.setColor(0.4, 0.4, 0.4, 1)
    g.print("D-pad/Arrows: navigate   A/Enter: select   B/Esc: back   Start: start game",
            30, 740)

    -- Draw overlay if any
    if self.overlay == "select" and self.selectProfileUI then
        self.selectProfileUI:draw(font)
    elseif self.overlay == "manage" and self.manageUI then
        self.manageUI:draw(font)
    elseif self.overlay == "score" and self.viewScoreUI then
        self.viewScoreUI:draw(font)
    elseif self.overlay == "help" and self.helpUI then
        self.helpUI:draw(font, dm)
    end
end

-- ---- Input routing --------------------------------------------------------

function MainMenu:keypressed(key)
    if self.overlay == "select" then
        local sp = self.selectProfileUI
        if key == "up"     then sp:up()
        elseif key == "down"  then sp:down()
        elseif key == "return" or key == "kpenter" then sp:confirm()
        elseif key == "escape" then sp:cancel()
        end
        return
    end

    if self.overlay == "manage" then
        local mp = self.manageUI
        if mp.mode == "edit" then
            if key == "escape" then
                mp:cancelEdit()
            elseif key == "return" or key == "kpenter" then
                mp:confirmEdit()
            elseif key == "up" then mp:up()
            elseif key == "down" then mp:down()
            else
                mp:recordKey(key)
            end
        else
            if key == "up"    then mp:up()
            elseif key == "down"  then mp:down()
            elseif key == "return" or key == "kpenter" then mp:activateSelected()
            elseif key == "x"    then mp:createNew()
            elseif key == "y"    then mp:deleteSelected()
            elseif key == "escape" then self.overlay = nil
            end
        end
        return
    end

    if self.overlay == "score" or self.overlay == "help" then
        if key == "escape" or key == "return" or key == "kpenter" then
            self.overlay = nil
        end
        return
    end

    -- No overlay — navigate columns / items
    if key == "left"  then self.col = (self.col - 1 + COL_COUNT) % COL_COUNT
    elseif key == "right" then self.col = (self.col + 1) % COL_COUNT
    elseif key == "up"    then colMenu(self, self.col):up()
    elseif key == "down"  then colMenu(self, self.col):down()
    elseif key == "return" or key == "kpenter" then colMenu(self, self.col):activate()
    elseif key == "f2" then self:_startGame()
    end
end

function MainMenu:gamepadpressed(joystick, button)
    -- Map gamepad buttons to logical actions and re-use keypressed logic
    local map = {
        dpleft      = "left",
        dpright     = "right",
        dpup        = "up",
        dpdown      = "down",
        a           = "return",
        b           = "escape",
        start       = "f2",
    }
    local key = map[button]
    if key then self:keypressed(key) end

    -- X = new profile in manage overlay
    if button == "x" and self.overlay == "manage" then
        self.manageUI:createNew()
    end
    -- Y = delete profile / clear slot
    if button == "y" then
        if self.overlay == "manage" then
            self.manageUI:deleteSelected()
        elseif self.overlay == nil then
            -- Clear the selected slot
            if self.col == 0 then
                local slot = self.slotMenu.cursor
                self.settings.active_profiles[slot] = "None"
                self.settings:save()
                local sx, sy = 30, 300
                self:_rebuildSlotMenu(sx, sy)
            end
        end
    end
end
