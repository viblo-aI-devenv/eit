# Eit — Love2D Port Specification

Target platforms: RetroDeck / EmulationStation-DE (Linux x86_64), Android TV.
Distribution: `.love` file (RetroDeck), wrapped APK (Android TV).
Input: gamepads first, keyboard still supported.

---

## 1. Project layout

```
love2d/
├── main.lua          # love.load / love.update / love.draw / love.keypressed
├── constants.lua     # eit_constants.py
├── blocks.lua        # blocks.py  (block-part classes + block shapes)
├── blockfield.lua    # blockfield.py
├── playerfield.lua   # playerfield.py
├── datamanager.lua   # datamanager.py  (asset loading)
├── ui.lua            # menus + dialogs (replaces PGU + dialogs.py)
├── settings.lua      # load/save settings.cfg equivalent (plain Lua table → file)
├── scoretable.lua    # Scoretable class + persistence (replaces pickle)
├── images/           # copied as-is from Python version
├── sounds/           # WAV files copied as-is
├── music/            # MOD/S3M files (Love2D uses SDL_mixer which reads MOD/S3M natively)
└── fonts/
    └── freesansbold.ttf
```

No subdirectories of `love2d/` need renaming; the asset paths are unchanged.

---

## 2. Love2D API mapping

| Python / pygame / OpenGL          | Love2D equivalent                                    |
|-----------------------------------|------------------------------------------------------|
| `pygame.init()`                   | implicit in `love.load()`                            |
| `pygame.display.set_mode()`       | `love.window.setMode(w, h, {fullscreen=…})`          |
| `pygame.event.get()`              | callbacks: `love.keypressed`, `love.joystickpressed` |
| `pygame.time.Clock.tick(fps)`     | `love.timer.getDelta()` in `love.update(dt)`         |
| `pygame.mixer.Sound.play()`       | `love.audio.newSource(path,"static"):play()`         |
| `pygame.mixer.music.play(-1)`     | `love.audio.newSource(path,"stream"):setLooping(true):play()` |
| `glClear(…)`                      | `love.graphics.clear(0,0,0,1)`                       |
| `glBindTexture / glBegin(QUADS)`  | `love.graphics.draw(image, x, y)`                    |
| `glOrtho` 2-D projection          | Love2D default (pixel coords, y-down)                |
| `glBlendFunc(SRC_ALPHA, …)`       | `love.graphics.setBlendMode("alpha")`  (default)     |
| `glColor4d(r,g,b,a)`             | `love.graphics.setColor(r,g,b,a)`                    |
| `glutBitmapCharacter` (broken)    | `love.graphics.print(text, x, y)`                    |
| `configobj` / `pickle`            | `love.filesystem.write/read` + `require` / `load`   |
| `pygame.image.load` → GL texture  | `love.graphics.newImage(path)`                       |
| Display lists (`glNewList`)       | Not needed — Love2D `draw()` is cheap enough         |

---

## 3. Rendering model

The Python code draws with raw OpenGL. Each piece is a 24×24-pixel quad textured
from a sprite strip.

In Love2D:

- Load `images/standard.png` as a single `Image`.
- For each color/type, create a `Quad` covering the correct 24-wide slice:
  ```lua
  -- standard strip: 8 frames × 24 px wide, 96 px tall (used rows 0.25–1.0)
  -- The Python tex coords compress the strip to 75 % height; the actual pixel
  -- rows used are y=0 to y=72 (top) out of 96 total.
  -- Simplest: just load the image and use Quads for the full 24×24 cell.
  local IW = standard:getWidth()   -- should be 192 (8 * 24)
  local IH = standard:getHeight()
  quads["Red"]    = love.graphics.newQuad(24,  0, 24, 24, IW, IH)
  quads["Green"]  = love.graphics.newQuad(48,  0, 24, 24, IW, IH)
  -- etc.
  ```
- Similarly for `images/special.png` (22 frames):
  ```lua
  local SW = special:getWidth()
  local SH = special:getHeight()
  quads["Faster"] = love.graphics.newQuad(0,   0, 24, 24, SW, SH)
  quads["Slower"] = love.graphics.newQuad(24,  0, 24, 24, SW, SH)
  -- etc.
  ```
- Background tiling uses `love.graphics.draw(bg, quad, x, y)` with a tiling Quad
  spanning the field, or `love.graphics.setWrap("repeat","repeat")` and draw the
  full field rectangle.
- The `bw.png` Color-effect overlay: draw a full-field rectangle with the bw image
  at a scrolling UV offset — replicate using a Quad whose viewport shifts each frame
  based on the current block position.

**Coordinate system**: Python uses y-down (same as Love2D), so no coordinate flip
is needed. The field top-left screen offset is `(px, py)`.

---

## 4. constants.lua

Direct translation; no logic:

```lua
TO_NEXT_LEVEL     = 5
DOWN_TIME         = 500   -- ms
DROP_TIME         = 10    -- ms
DOWN_TIME_DELTA   = 1.07
SPECIAL_TIME      = 50    -- ms
PACKET_TIME       = 20000 -- ms
SPAWN_SPECIAL_TIME= 30000 -- ms
REMOVE_SPECIAL_TIME=8000  -- ms
EXTRA_ANTIS       = 4
BLOCK_SIZE        = 24
```

---

## 5. blocks.lua

### 5.1 BlockPart

```lua
-- blocks.lua
BlockPart = {}
BlockPart.__index = BlockPart

function BlockPart.new(x, y, texKey, texOffset, isSpecial)
    local self = setmetatable({}, BlockPart)
    self.x          = x
    self.y          = y
    self.texKey     = texKey      -- "standard" or "special"
    self.quadKey    = texOffset   -- key into dm.quads table, e.g. "Red"
    self.isSpecial  = isSpecial or false
    self.type       = nil         -- set by subtype
    return self
end

function BlockPart:draw(dm, mini, trans)
    if self.y == 0 then return end
    local img   = dm.images[self.texKey]
    local quad  = dm.quads[self.quadKey]
    local sx, sy = self.x * BLOCK_SIZE, self.y * BLOCK_SIZE
    local scale = (mini and self.texKey ~= "Grey") and 0.4 or 1.0
    love.graphics.setColor(1, 1, 1, trans and 0.35 or 1.0)
    love.graphics.draw(img, quad, sx, sy, 0, scale, scale)
    love.graphics.setColor(1, 1, 1, 1)
end

function BlockPart:move(dx, dy)
    self.x = self.x + dx
    self.y = self.y + dy
end
```

### 5.2 Special block-part constructors

Each of the 22 specials becomes a factory function:

```lua
local SPECIAL_QUADS = {
    "Faster","Slower","Stair","Fill","Rumble","Inverse","Switch","Packet",
    "Flip","Mini","Blink","Blind","Background","Anti","Bridge","Trans",
    "Clear","Question","SZ","Color","Ring","Castle",
}

local function makeSpecial(typeName)
    return function(dm, x, y)
        local bp = BlockPart.new(x or 0, y or 0, "special", typeName, true)
        bp.type = typeName
        return bp
    end
end

for _, name in ipairs(SPECIAL_QUADS) do
    _G["BlockPart"..name] = makeSpecial(name)
end
```

### 5.3 Standard color constructors

```lua
local STANDARD_COLORS = {"Pink","Purple","Yellow","Cyan","Blue","Green","Red"}
STANDARD_PARTS = {}
for _, c in ipairs(STANDARD_COLORS) do
    _G["BlockPart"..c] = function(dm, x, y)
        return BlockPart.new(x or 0, y or 0, "standard", c, false)
    end
    table.insert(STANDARD_PARTS, _G["BlockPart"..c])
end

BlockPartGrey = function(dm, x, y)
    return BlockPart.new(x or 0, y or 0, "standard", "Grey", false)
end
```

### 5.4 Block (tetrominoes)

```lua
Block = {}
Block.__index = Block

function Block.new(dm)
    local self = setmetatable({}, Block)
    self.parts = {}
    self.dm    = dm
    return self
end

function Block:rotate(dir)
    local pivot = self.parts[1]
    local px, py = pivot.x, pivot.y
    for i = 2, #self.parts do
        local bp = self.parts[i]
        bp.x = bp.x - px
        bp.y = bp.y - py
        if dir == "cw" then
            bp.x, bp.y = -bp.y, bp.x
        else
            bp.x, bp.y = bp.y, -bp.x
        end
        bp.x = bp.x + px
        bp.y = bp.y + py
    end
end

function Block:move(dx, dy)
    for _, bp in ipairs(self.parts) do bp:move(dx, dy) end
end

function Block:draw(dm)
    for _, bp in ipairs(self.parts) do bp:draw(dm) end
end
```

Tetrominoes follow exactly the Python layout (same pivot/offset logic). `BlockO`
overrides `rotate` to be a no-op. `BlockI` uses the inherited rotate.

```lua
ALL_BLOCKS = {BlockI, BlockT, BlockO, BlockL, BlockJ, BlockS, BlockZ}
```

---

## 6. blockfield.lua

Direct translation of `blockfield.py`. Key notes:

- `self.blockparts` is a 23-row × 10-col 2-D table (1-indexed in Lua but **keep
  0-indexed values stored in `.x`/`.y`** of each BlockPart to match Python, since
  the collision logic uses raw index arithmetic). Use `self.grid[y+1][x+1]` as the
  Lua container but expose `get(x,y)` / `set(x,y,bp)` helpers.
- `blockparts_list` remains a flat list for iteration.
- `random_block()` uses `love.math.random`.
- The `draw()` method:
  - draw background border image
  - draw background tile (tiling quad)
  - iterate `blockparts_list`, call `bp:draw(dm, mini, trans)` per active effect
  - draw Color overlay if active (scrolling bw quad)
  - draw `currentblock` (skip if Blink effect and `blink` is odd)
  - draw `nextblock` (skip if Blind effect)
  - draw active effect icons in the HUD strip

---

## 7. playerfield.lua

### 7.1 Input — gamepad mapping

Replace keyboard bindings with gamepad buttons. Each player maps to a
`love.joystick` instance (`love.joystick.getJoysticks()[player_id]`).

Default gamepad layout (Xbox / PS standard):

| Action       | Button/Axis             |
|--------------|-------------------------|
| Move Left    | D-pad left / left stick left |
| Move Right   | D-pad right / left stick right |
| Soft Drop    | D-pad down / left stick down |
| Hard Drop    | Button A (cross)         |
| Rotate CW    | Button B (circle) or R shoulder |
| Rotate CCW   | Button X (square) or L shoulder |
| Use Antidote | Button Y (triangle)      |
| Change Target| Right bumper / R2        |
| Pause        | Start                    |

Keyboard fallback: same as Python defaults, stored in `settings.lua`.

Implementation: poll in `love.gamepadpressed(joystick, button)` and
`love.keypressed(key)` callbacks. Both feed into a shared `player:onAction(action)`
method.

### 7.2 Key differences from Python

- `frametime` → `dt` in seconds (Love2D `love.update(dt)`).
  Multiply all millisecond thresholds by `1000` when comparing, **or** convert
  constants to seconds at load time. Easiest: keep constants in ms and pass
  `dt * 1000` everywhere.
- `pygame.event.post(USEREVENT, utype="GameOver")` → call a callback / set a flag
  that `main.lua` checks after each `player:update()`.
- Profile/keybinding storage: `settings.lua` reads/writes a Lua table serialised
  with `love.filesystem`.

### 7.3 draw()

- Use `love.graphics.setFont(dm.font)` and `love.graphics.print(text, x, y)` to
  replace the broken `glutBitmapCharacter` calls. This fixes the invisible text bug.
- Draw info panel image, name, target, score, level, packet bar, antidote icons,
  then call `self.field:draw(dm)`.

---

## 8. datamanager.lua

```lua
DataManager = {}
DataManager.__index = DataManager

function DataManager.new()
    local dm = setmetatable({}, DataManager)
    dm.images = {}
    dm.quads  = {}
    dm.sounds = {}
    dm.music_source = nil
    dm.players = {}
    dm.gameover_players = {}
    return dm
end

function DataManager:load()
    -- Textures
    dm.images["standard"]          = love.graphics.newImage("images/standard.png")
    dm.images["special"]           = love.graphics.newImage("images/special.png")
    dm.images["bw"]                = love.graphics.newImage("images/bw.png")
    dm.images["background_border"] = love.graphics.newImage("images/background_border.png")
    dm.images["background_info"]   = love.graphics.newImage("images/background_info.png")
    -- Build quads for standard (8 frames, width=192, height=96; use top 24px)
    local sw = dm.images["standard"]:getWidth()
    local sh = dm.images["standard"]:getHeight()
    local stdNames = {"Blue","Red","Green","Purple","Yellow","Pink","Cyan","Grey"}
    for i, name in ipairs(stdNames) do
        dm.quads[name] = love.graphics.newQuad((i-1)*24, 0, 24, 24, sw, sh)
    end
    -- Build quads for special (22 frames)
    local spNames = {"Faster","Slower","Stair","Fill","Rumble","Inverse","Switch",
                     "Packet","Flip","Mini","Blink","Blind","Background","Anti",
                     "Bridge","Trans","Clear","Question","SZ","Color","Ring","Castle"}
    local spw = dm.images["special"]:getWidth()
    local sph = dm.images["special"]:getHeight()
    for i, name in ipairs(spNames) do
        dm.quads[name] = love.graphics.newQuad((i-1)*24, 0, 24, 24, spw, sph)
    end
    -- Background tiles
    dm.backgrounds = {}
    local files = love.filesystem.getDirectoryItems("images/backgrounds")
    for _, f in ipairs(files) do
        if f:match("%.png$") then
            local key = f:gsub("%.png$","")
            dm.backgrounds[key] = love.graphics.newImage("images/backgrounds/"..f)
            dm.backgrounds[key]:setWrap("repeat","repeat")
        end
    end
    -- Font
    dm.font = love.graphics.newFont("fonts/freesansbold.ttf", 14)
    -- Sounds
    local snd = function(name)
        return love.audio.newSource("sounds/"..name, "static")
    end
    dm.placesound    = snd("DEEK.WAV")
    dm.gameoversound = snd("RASPB.WAV")
    dm.welcomesound  = snd("WELCOME.WAV")
    dm.specialsounds = {
        Faster="LASER.WAV", Slower="PONG.WAV", Stair="FLOOP.WAV", Fill="POP2.WAV",
        Rumble="BOUNCE.WAV", Inverse="VIBRABEL.WAV", Flip="BOOMOOH-1.WAV",
        Switch="ECHOFST1.WAV", Packet="PLICK.WAV", Clear="WHOOSH1.WAV",
        Question="PLOP1.WAV", Bridge="BOTTLED.WAV", Mini="FUU.WAV",
        Color="SPACEBO.WAV", Trans="PINC.WAV", SZ="PLINK2.WAV", Anti="SIGH.WAV",
        Background="KLOUNK.WAV", Blind="TICK.WAV", Blink="ZING.WAV",
    }
    for k, v in pairs(dm.specialsounds) do
        dm.specialsounds[k] = snd(v)
    end
end

function DataManager:playRandomMusic()
    local files = love.filesystem.getDirectoryItems("music")
    if #files == 0 then return end
    local f = files[love.math.random(#files)]
    if dm.music_source then dm.music_source:stop() end
    dm.music_source = love.audio.newSource("music/"..f, "stream")
    dm.music_source:setLooping(true)
    dm.music_source:play()
end
```

**Note on MOD/S3M**: Love2D uses SDL_mixer (via luasound/OpenAL on some builds).
Tracker format support depends on the platform. On desktop Linux with the standard
Love2D package, MOD/S3M playback works via the bundled `libmodplug`. On Android,
support is unreliable. Safest approach:

- Keep MOD/S3M files as-is and test.
- If Android playback fails, convert to OGG with `ffmpeg -i input.mod output.ogg`
  and update the music loader. This is deferred to testing.

---

## 9. settings.lua (persistence)

Replaces `configobj` + `pickle`.

```lua
-- settings.lua
local Settings = {}

local DEFAULTS = {
    profiles = {
        ["Player1"] = {left="left",right="right",cw="x",ccw="z",
                       down="down",drop="space",anti="lshift",change="tab",
                       gamepad=1},
        ["Player2"] = {left="left",right="right",cw="x",ccw="z",
                       down="down",drop="space",anti="rshift",change="return",
                       gamepad=2},
    },
    active = {"Player1","Player2","None","None"},
    fullscreen = false,
    music = true,
}

function Settings.load()
    local ok, data = pcall(function()
        local chunk = love.filesystem.read("settings.lua")
        return load("return "..chunk)()
    end)
    if ok and data then return data end
    return Settings.copy(DEFAULTS)
end

function Settings.save(data)
    -- serialise as a Lua literal
    love.filesystem.write("settings.lua", serpent.dump(data))
end
```

Use the `serpent` library (single-file, MIT, included in `love2d/lib/serpent.lua`)
for Lua table serialisation.

### Scoretable

```lua
-- scoretable.lua
-- stats[name] = {Matches=0,Score=0,Lines=0,MaxLevel=0,RankPoints=0,Winns=0}
function Scoretable.load()  -- reads love.filesystem "scoretable.lua"
function Scoretable.save()  -- writes love.filesystem "scoretable.lua"
function Scoretable:insertResult(winner, losers)  -- same ELO-ish formula
function Scoretable:getList()                      -- sorted by RankPoints
```

---

## 10. ui.lua (menus and dialogs)

Replace PGU entirely with a hand-drawn Love2D UI. All menus are navigable by
gamepad d-pad + A/B. No mouse required (but mouse still works for desktop).

### 10.1 Game states

```
Menu → Game → Paused → Game
                    ↘ GameOver → Game (restart)
                              ↘ Menu
```

### 10.2 Main menu layout (640×500 logical, scaled to window)

```
[Logo image]          [main_right.png]
Active Players:
  P1: [name btn]  Clear
  P2: [name btn]  Clear
  P3: [name btn]  Clear
  P4: [name btn]  Clear

              [Start Game]
              [Highscores]
              [Edit Profiles]
              [Help]
              [Quit]

Fullscreen: [toggle]
Music:      [toggle]
```

Implement with a simple list of focusable "widgets". D-pad moves focus;
A activates; B goes back.

### 10.3 Dialogs

| Dialog               | Purpose                                     |
|----------------------|---------------------------------------------|
| SelectProfileDialog  | Pick an existing profile for a slot         |
| ManageProfilesDialog | Create / edit / delete profiles + key binds |
| ViewScoreDialog      | Show scoretable                             |
| HelpDialog           | Show special block list with icons          |

Each dialog is a full-screen overlay drawn on top of the menu.
Profile key-binding editor: highlight a field, press any key/button to assign.

---

## 11. main.lua structure

```lua
function love.load()
    dm = DataManager.new()
    dm:load()
    settings = Settings.load()
    scoretable = Scoretable.load()
    state = "Menu"
    ui = UI.new(dm, settings, scoretable)
    love.window.setMode(1024, 768, {fullscreen=settings.fullscreen, resizable=true})
end

function love.update(dt)
    if state == "Menu" then
        ui:update(dt)
    elseif state == "Game" or state == "Paused" then
        if state == "Game" then
            for _, p in ipairs(dm.players) do
                p:update(dt * 1000)  -- pass ms like Python
            end
            checkGameOver()
        end
    end
end

function love.draw()
    if state == "Menu" then
        ui:draw()
    elseif state == "Game" or state == "Paused" or state == "GameOver" then
        love.graphics.clear(0,0,0,1)
        for _, p in ipairs(dm.players) do p:draw(dm) end
        if state == "Paused"   then drawPauseOverlay()   end
        if state == "GameOver" then drawGameOverOverlay() end
    end
end

function love.keypressed(key, scancode, isrepeat)
    -- route to ui or active player
end

function love.gamepadpressed(joystick, button)
    -- route to active player by joystick id
end
```

`love.window.setMode` with `resizable=true` and Love2D's default canvas means
the game will letterbox automatically if the TV is a different resolution.
For 4K TVs, pass `{fullscreen=true, fullscreentype="desktop"}`.

---

## 12. Screen layout at 1024×768 (same as Python)

| Players | Field width each | X offsets (field left edge) |
|---------|------------------|-----------------------------|
| 1       | 240 px           | 16                          |
| 2       | 240 px           | 16, 264                     |
| 3       | 240 px           | 16, 264, 512                |
| 4       | 240 px           | 16, 264, 512, 760           |

Each `PlayerField` is 248 px wide (240 field + 8 border); screen height = 768 px
covers the 536 px field + 200 px info strip + some margin.

At runtime the fields are positioned exactly as in Python:
`PlayerField(dm, id, name, id * 248 + 16, 16)`.

---

## 13. Gamepad profile storage

Because gamepads replace keys, profiles store both:
```lua
profiles["Alice"] = {
    gamepad = 1,           -- joystick index (1-based)
    -- keyboard fallback:
    left="a", right="d", cw="q", ccw="w",
    down="s", drop="lctrl", anti="lshift", change="tab",
}
```

The gamepad button mapping is fixed (not user-configurable in v1); only the
keyboard fallback is editable in the profile editor.

---

## 14. RetroDeck / EmulationStation-DE integration

Place `eit.love` in:
```
~/retrodeck/roms/love/eit.love
```
EmulationStation-DE will auto-detect it under the LOVE system.
Scrape metadata by adding `eit.xml` alongside or via the built-in scraper.

Launch command configured by RetroDeck:
```
love %ROM%
```

---

## 15. Android TV packaging

```bash
# On desktop, using Love2D Android build tools:
# https://github.com/love2d/love-android
cp -r love2d/ src/
./gradlew assembleRelease
# Output: app/build/outputs/apk/release/app-release.apk
```

Key `AndroidManifest` settings:
- `android:screenOrientation="landscape"`
- `<uses-feature android:name="android.hardware.gamepad" android:required="false"/>`
- `<uses-feature android:name="android.hardware.touchscreen" android:required="false"/>`

Love2D maps Android gamepad events to `love.gamepadpressed` automatically.

---

## 16. Implementation order

1. **`constants.lua`** — trivial, no deps
2. **`blocks.lua`** — pure logic, no rendering; verify with unit tests
3. **`blockfield.lua`** — depends on blocks; verify grid operations
4. **`datamanager.lua`** — asset loading; test by running `love .` and checking textures load
5. **`playerfield.lua`** — depends on all of the above; wire keyboard input first
6. **`main.lua`** (game loop only, no menus) — start a hardcoded 2-player game and play-test
7. **`ui.lua`** — full menu system, profile management, scoretable
8. **`settings.lua` / `scoretable.lua`** — persistence layer
9. Gamepad input — swap keyboard routing for joystick callbacks
10. Android APK build + TV test
11. (optional) MOD/S3M → OGG conversion if Android audio fails

---

## 17. Known differences / simplifications

| Item                        | Python behaviour              | Love2D port                        |
|-----------------------------|-------------------------------|------------------------------------|
| Text rendering              | broken (glutBitmapCharacter is no-op) | fixed: `love.graphics.print`  |
| Menu system                 | PGU widget toolkit            | custom drawn, gamepad-navigable     |
| Persistence format          | configobj INI + pickle binary | plain Lua table literals            |
| Display lists               | used for standard block quads | not needed                          |
| Texture upload              | manual `glTexImage2D`         | `love.graphics.newImage`            |
| Music format                | MOD/S3M via pygame.mixer      | MOD/S3M via Love2D (test on Android)|
| Key repeat                  | `pygame.key.set_repeat()` off | no repeat needed (Love2D default)   |
| I-block rotation bug        | present (noted in source)     | preserve bug for now; fix later     |
