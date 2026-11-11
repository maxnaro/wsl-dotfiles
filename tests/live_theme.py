"""Exercise a running Neovim instance against temporary theme state.

Run with python3 tests/live_theme.py after installing the Neovim plugins.
"""
import os,tempfile,subprocess,json,pathlib
root=pathlib.Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as tmp:
 t=pathlib.Path(tmp); c=t/'config'; s=t/'state'; (c/'dotfiles/theme').mkdir(parents=True); (s/'dotfiles/theme').mkdir(parents=True)
 (c/'dotfiles/theme/palette.json').write_text((root/'themes/chocolatier.json').read_text())
 (s/'dotfiles/theme/mode').write_text('dark\n')
 lua='''vim.opt.rtp:prepend("/home/max/dotfiles/nvim/.config/nvim")
vim.opt.rtp:prepend("/home/max/.local/share/nvim/lazy/chocolatier.nvim")
vim.opt.rtp:prepend("/home/max/.local/share/nvim/lazy/lush.nvim")
vim.o.termguicolors = true
local spec = dofile("/home/max/dotfiles/nvim/.config/nvim/lua/plugins/colorscheme.lua")
spec[1].config()
local lazygit = dofile("/home/max/dotfiles/nvim/.config/nvim/lua/plugins/lazygit.lua")
local opts = {}
lazygit[1].opts(nil, opts)
assert(opts.lazygit.configure == false)
local overlay = vim.fn.stdpath("cache") .. "/lazygit-theme.yml"
assert(opts.lazygit.env.LG_CONFIG_FILE:find(overlay, 1, true))
local function check_lazygit(mode)
  local config = vim.json.decode(table.concat(vim.fn.readfile(overlay), "\\n"))
  local p = require("config.palette")
  assert(config.gui.colorScheme == mode)
  assert(config.gui.theme.defaultFgColor[1] == p.fg)
  assert(config.gui.theme.activeBorderColor[1] == p.cyan)
  assert(config.gui.theme.selectedLineBgColor[1] == "default")
  assert(config.os.editPreset == "nvim-remote")
end
check_lazygit("dark")
assert(vim.o.background == "dark")
assert(require("config.palette").fg == "#D3AF86")
vim.fn.writefile({"light"}, vim.env.XDG_STATE_HOME .. "/dotfiles/theme/mode")
assert(vim.wait(1500, function() return vim.o.background == "light" end, 20), "watcher missed light")
check_lazygit("light")
assert(require("config.palette").fg == "#221A0F")
assert(vim.g.colors_name == "kimbie_light")

assert(vim.api.nvim_get_hl(0,{name="Comment",link=false}).fg == tonumber("84613D",16))
assert(vim.api.nvim_get_hl(0,{name="Pmenu"}).bg == tonumber("E4C6A5",16))
local function transparent()
  for _, name in ipairs({"Normal", "NormalNC", "NormalFloat", "SignColumn", "FoldColumn", "StatusLine", "StatusLineNC", "FloatBorder", "WinSeparator", "LazyGitFloat"}) do
    assert(vim.api.nvim_get_hl(0, {name=name, link=false}).bg == nil, name .. " lost transparency")
  end
end
transparent()
vim.cmd("colorscheme kimbie_light")
transparent()
assert(vim.g.terminal_color_0 == "#FBEBD4")
spec[2].opts.colorscheme()
assert(vim.g.colors_name == "kimbie_light", "LazyVim startup callback selected wrong scheme")
transparent()
vim.fn.writefile({"dark"}, vim.env.XDG_STATE_HOME .. "/dotfiles/theme/mode")
assert(vim.wait(1500, function() return vim.o.background == "dark" end,20), "watcher missed dark")
check_lazygit("dark")
assert(vim.g.colors_name == "chocolatier")
assert(vim.api.nvim_get_hl(0,{name="Normal",link=false}).bg == nil)
assert(require("config.palette").fg == "#D3AF86")
vim.cmd("qa!")
'''
 lua = lua.replace("/home/max/dotfiles", str(root)).replace("/home/max/.local/share", str(pathlib.Path(os.environ.get("XDG_DATA_HOME", str(pathlib.Path.home()/".local/share")))))
 # Startup must also honour a saved light mode before any watcher event.
 startup = lua[:lua.index('assert(vim.o.background == "dark")')].replace('check_lazygit("dark")', 'check_lazygit("light")') + 'assert(vim.o.background == "light")\nassert(vim.g.colors_name == "kimbie_light")\n\nassert(vim.api.nvim_get_hl(0, {name="Normal", link=false}).bg == nil)\nvim.cmd("qa!")\n'
 (s/'dotfiles/theme/mode').write_text('light\n')
 p=t/'startup.lua'; p.write_text(startup)
 result=subprocess.run(['nvim','--headless','-i','NONE','-u','NONE','-l',str(p)],env=dict(os.environ,XDG_CONFIG_HOME=str(c),XDG_STATE_HOME=str(s),XDG_CACHE_HOME=str(t/"cache")),capture_output=True,text=True,timeout=8)
 assert result.returncode == 0, result.stdout + result.stderr
 (s/'dotfiles/theme/mode').write_text('dark\n')
 p=t/'test.lua';p.write_text(lua)
 result=subprocess.run(['nvim','--headless','-i','NONE','-u','NONE','-l',str(p)],env=dict(os.environ,XDG_CONFIG_HOME=str(c),XDG_STATE_HOME=str(s),XDG_CACHE_HOME=str(t/"cache")),capture_output=True,text=True,timeout=8)
 print(result.stdout, result.stderr, end="")
 assert result.returncode==0
 print('Neovim theme watcher: dark -> light -> dark passed')
