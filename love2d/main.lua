-- main.lua
-- Love2D entry point.  Implements the state machine:
--   Menu → Game → Paused → GameOver → Menu
--
-- Player field positions mirror the Python layout:
--   Player 1: x=16,          y=16
--   Player 2: x=248+16=264,  y=16
--   Player 3: x=496+16=512,  y=16   (248*2+16)
--   Player 4: x=744+16=760,  y=16   (248*3+16)
-- Total canvas: 1024 × 768

require("constants")
require("blocks")
require("blockfield")
require("datamanager")
require("playerfield")
require("settings")
require("scoretable")
require("ui")

-- ---------------------------------------------------------------------------
-- Module-level state
-- ---------------------------------------------------------------------------

local state     = "Menu"   -- "Menu" | "Game" | "Paused" | "GameOver"
local dm        = nil      -- DataManager (created once per game session)
local players   = {}       -- array of PlayerField
local goverPlayers = {}    -- players that have ended
local scoretable = nil
local settings  = nil
local profiles  = nil
local menuUI    = nil      -- UI object (see ui.lua)

local WINDOW_W = 1024
local WINDOW_H = 768

-- ---------------------------------------------------------------------------
-- love.load
-- ---------------------------------------------------------------------------

function love.load()
    love.window.setTitle("Eit")
    love.window.setMode(WINDOW_W, WINDOW_H, {
        fullscreen = false,   -- overridden once settings are loaded
        resizable  = false,
        vsync      = true,
    })

    -- Load persistence
    settings  = Settings.new()
    profiles  = Profiles.new()
    scoretable = Scoretable.load()

    -- Apply fullscreen from saved setting
    love.window.setFullscreen(settings.fullscreen)

    -- Build DataManager (loads all assets once)
    dm = DataManager.new()
    dm:load()
    dm.musicEnabled = settings.music

    -- Build the main menu UI
    menuUI = MainMenu.new(settings, profiles, scoretable,
        function() startGame() end,         -- onStart
        function()                           -- onQuit
            love.event.quit()
        end
    )

    love.graphics.setBackgroundColor(0, 0, 0)
end

-- ---------------------------------------------------------------------------
-- Game lifecycle
-- ---------------------------------------------------------------------------

function startGame()
    players    = {}
    goverPlayers = {}

    -- Determine which player slots are active
    local slotX = {
        [1] = 16,
        [2] = 248 + 16,
        [3] = 248 * 2 + 16,
        [4] = 248 * 3 + 16,
    }

    -- Assign joysticks to slots in order of connected joysticks
    local joysticks = love.joystick.getJoysticks()

    local joyIdx = 1
    for slot = 1, 4 do
        local profileName = settings.active_profiles[slot]
        if profileName and profileName ~= "None" then
            local profile = profiles:get(profileName)
            local joy     = joysticks[joyIdx]   -- may be nil
            if joy then joyIdx = joyIdx + 1 end

            local pf = PlayerField.new(dm, slot - 1, profileName,
                                       slotX[slot], 16, profile, joy)

            -- Wire the gameover callback
            pf.onGameOver = function(p)
                table.insert(goverPlayers, p)
                -- The last remaining player (or the last one to fall) wins
                local activeCnt = 0
                for _, pl in ipairs(players) do
                    if not pl.gameover then activeCnt = activeCnt + 1 end
                end
                if activeCnt == 0 then
                    -- Everyone is gone — the last to go is declared winner
                    endGame(p)
                elseif activeCnt == 1 and #players > 1 then
                    -- One survivor — find them
                    for _, pl in ipairs(players) do
                        if not pl.gameover then endGame(pl); break end
                    end
                end
            end

            table.insert(players, pf)
        end
    end

    -- Set dm.players before calling nextTarget so the loop inside it works
    dm.players = players

    -- Set initial targets
    for _, p in ipairs(players) do
        p:nextTarget()
    end

    if settings.music then
        dm:playRandomMusic()
    end

    if dm.welcomesound then dm.welcomesound:play() end

    state = "Game"
end

function endGame(winner)
    -- Calculate and persist stats
    local loserStats = {}
    for _, p in ipairs(players) do
        local entry = { Name = p.name, Score = p.score, Lines = p.lines, Level = p.level }
        if p ~= winner then
            table.insert(loserStats, entry)
        end
    end
    local winnerStat = { Name = winner.name, Score = winner.score,
                         Lines = winner.lines, Level = winner.level }
    scoretable:insertResult(winnerStat, loserStats)
    scoretable:save()

    state = "GameOver"
end

-- ---------------------------------------------------------------------------
-- love.update
-- ---------------------------------------------------------------------------

function love.update(dt)
    if state == "Game" then
        for _, p in ipairs(players) do
            p:update(dt)
        end
    elseif state == "Menu" then
        menuUI:update(dt)
    end
end

-- ---------------------------------------------------------------------------
-- love.draw
-- ---------------------------------------------------------------------------

function love.draw()
    local g = love.graphics
    g.setColor(1, 1, 1, 1)

    if state == "Menu" then
        menuUI:draw()

    elseif state == "Game" or state == "Paused" or state == "GameOver" then
        -- Draw all player fields
        for _, p in ipairs(players) do
            p:draw(dm)
        end

        if state == "Paused" then
            drawOverlay("Game Paused", "(press Start/P to unpause)")
        elseif state == "GameOver" then
            drawOverlay("GAME OVER!", "(press Start/F2 to restart, ESC to quit)")
        end
    end
end

--- Draw a centred semi-transparent overlay banner.
function drawOverlay(line1, line2)
    local g = love.graphics
    local cx, cy = WINDOW_W / 2, WINDOW_H / 2
    local bw, bh = 500, 100

    g.setColor(0.2, 0.2, 0.2, 0.7)
    g.rectangle("fill", cx - bw/2, cy - bh/2, bw, bh)

    g.setColor(1, 1, 1, 1)
    if dm and dm.font then
        g.setFont(dm.font)
    end
    local tw1 = g.getFont():getWidth(line1)
    local tw2 = g.getFont():getWidth(line2)
    g.print(line1, cx - tw1/2, cy - 28)
    g.print(line2, cx - tw2/2, cy + 8)
end

-- ---------------------------------------------------------------------------
-- love.keypressed
-- ---------------------------------------------------------------------------

function love.keypressed(key)
    if state == "Menu" then
        menuUI:keypressed(key)
        return
    end

    -- Global hot-keys
    if key == "escape" then
        if state == "Game" or state == "Paused" or state == "GameOver" then
            dm:stopMusic()
            state = "Menu"
            menuUI:refresh(settings, profiles, scoretable)
        end
        return
    end

    if (key == "pause" or key == "p") then
        if state == "Game" then
            state = "Paused"
        elseif state == "Paused" then
            state = "Game"
        end
        return
    end

    if key == "f2" then
        if state == "Game" or state == "Paused" or state == "GameOver" then
            dm:stopMusic()
            startGame()
        end
        return
    end

    -- Dispatch to players (only in Game state)
    if state == "Game" then
        for _, p in ipairs(players) do
            p:onKey(key)
        end
    end
end

-- ---------------------------------------------------------------------------
-- love.gamepadpressed
-- ---------------------------------------------------------------------------

function love.gamepadpressed(joystick, button)
    if state == "Menu" then
        menuUI:gamepadpressed(joystick, button)
        return
    end

    -- Start button = pause
    if button == "start" then
        if state == "Game" then
            state = "Paused"
        elseif state == "Paused" then
            state = "Game"
        elseif state == "GameOver" then
            dm:stopMusic()
            startGame()
        end
        return
    end

    if button == "back" then
        -- Back/Select → return to menu
        if state == "Game" or state == "Paused" or state == "GameOver" then
            dm:stopMusic()
            state = "Menu"
            menuUI:refresh(settings, profiles, scoretable)
        end
        return
    end

    if state == "Game" then
        for _, p in ipairs(players) do
            p:onGamepadButton(joystick, button)
        end
    end
end

-- ---------------------------------------------------------------------------
-- love.joystickadded / removed  (hot-plug support)
-- ---------------------------------------------------------------------------

function love.joystickadded(joystick)
    -- Re-assign only if we are in the menu (safe to do so)
    -- During gameplay, joystick assignment is fixed for the session.
end

function love.joystickremoved(joystick)
    -- Disassociate from any player that owned it
    for _, p in ipairs(players) do
        if p.joystick == joystick then
            p.joystick = nil
        end
    end
end
